from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import pickle
import re
import signal
import subprocess
import sys
import tempfile
import time

import psutil

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
CONFIG=Path(os.getenv("COURSE_REPAIR_CONFIG", str(ROOT/"configs/code_repair.json")))
ARMS=["resample","self_review","pass_fail","counterexample"]
MODEL_NAMES={"Qwen/Qwen2.5-7B-Instruct":"Qwen2.5-7B","Qwen/Qwen3-8B":"Qwen3-8B"}


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
    tmp.replace(path)


def load_config():
    return json.loads(CONFIG.read_text())


def load_tasks(config):
    with gzip.open(ROOT/config["dataset"],"rt") as f:
        return {r["task_id"]:r for line in f if (r:=json.loads(line))}


def records(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def extract_code(text):
    blocks=re.findall(r"```(?:python|py)?\s*\n(.*?)```",text,re.S|re.I)
    if blocks:
        return "\n\n".join(block.strip() for block in blocks)
    return text.strip()


def initial_prompt(task):
    return ("Implement the following Python programming task. Return the complete implementation "
            "in one Python code block, including required imports. Preserve the specified interface.\n\n"+task["prompt"])


def feedback_message(arm,evaluation):
    instruction=("Review your previous implementation against the original task. Correct any correctness issue "
                 "you find; otherwise preserve the working implementation. Return the complete implementation "
                 "in one Python code block, including required imports. Preserve the specified interface.")
    if arm=="self_review":
        return instruction
    public=evaluation["public"]
    feedback={"diagnostic_status":"PASS" if public["passed"] else "FAIL"}
    if arm=="counterexample" and not public["passed"]:
        feedback["first_failure"]=public["first_failure"]
    return "Diagnostic test feedback:\n"+json.dumps(feedback,ensure_ascii=False)+"\n\n"+instruction


def run_kernel(config,task,code=None,oracle=None,oracle_mode=False):
    python=Path(os.path.abspath(sys.executable))
    vendor=(ROOT/config["evalplus_source"]).resolve()
    worker=Path(__file__).with_name("worker.py").resolve()
    # Each candidate gets its own directory and an allowlist of readable runtime paths.
    with tempfile.TemporaryDirectory(prefix="course-code-repair-") as temp:
        job=Path(temp).resolve()
        payload_path=job/"payload.pkl"
        result_path=job/"result.json"
        oracle_path=job/"oracle.pkl"
        payload={"mode":"oracle" if oracle_mode else "candidate","task":task,"code":code,"oracle":oracle,"oracle_output":str(oracle_path)}
        payload_path.write_bytes(pickle.dumps(payload))
        runtime=Path(sys.base_prefix).resolve()
        envprefix=Path(sys.prefix).resolve()
        quote=lambda s: json.dumps(str(s))
        allow=[f'(subpath {quote(p)})' for p in [runtime,envprefix,vendor,job,"/System","/usr","/Library/Apple","/private/etc"]]
        profile=("(version 1)\n(deny default)\n(import \"system.sb\")\n"
                 "(allow process*)\n(allow sysctl-read)\n(allow file-read-metadata)\n"
                 +"(allow file-read* "+" ".join(allow)+f' (literal {quote(worker)}) (subpath "/dev"))\n'
                 +f'(allow file-write* (subpath {quote(job)}) (literal "/dev/null"))\n(deny network*)\n')
        command=["/usr/bin/sandbox-exec","-p",profile,str(python),"-I","-X","utf8",str(worker),str(payload_path),str(result_path),str(vendor)]
        started=time.monotonic()
        proc=subprocess.Popen(command,cwd=job,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                              env={"PATH":"/usr/bin:/bin","TMPDIR":str(job),"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1","OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1"})
        killed=None
        while proc.poll() is None:
            if time.monotonic()-started>config["evaluation_timeout_s"]:
                killed="wall_timeout"
            try:
                if psutil.Process(proc.pid).memory_info().rss>config["memory_limit_mb"]*1024*1024:
                    killed="memory_limit"
            except psutil.Error:
                pass
            if killed:
                os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.04)
        stdout,stderr=proc.communicate()
        if result_path.exists():
            result=json.loads(result_path.read_text())
            if "reference_error" in result:
                raise RuntimeError("Reference preflight failed: "+json.dumps(result))
        elif (killed or proc.returncode in (-signal.SIGKILL,-signal.SIGXCPU)) and not oracle_mode:
            killed=killed or "cpu_or_process_resource_limit"
            failure={"passed":False,"cases_checked":0,"total_cases":len(task["base_input"]),
                     "first_failure":{"case_index":None,"input":None,"expected":None,"actual":None,"error_type":killed,"error_message":killed}}
            result={"public":failure,"hidden":{"passed":False},"full_pass":False}
        else:
            raise RuntimeError(f"Isolated evaluator failed (exit {proc.returncode}): "+stderr.decode(errors="replace")[-1800:])
        result["evaluation_seconds"]=round(time.monotonic()-started,4)
        result["sandboxed"]=True
        if oracle_mode:
            if not result["full_pass"] or not oracle_path.exists():
                raise RuntimeError("Reference did not pass its evaluation")
            return result,pickle.loads(oracle_path.read_bytes())
        return result
