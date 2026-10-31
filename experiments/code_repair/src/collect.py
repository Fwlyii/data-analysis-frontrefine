"""Resumable paired repair collection. Credentials stay in the parent process."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import datetime as dt
import fcntl
import importlib.util
import json
import pickle
import random
import re
import signal
import threading
import time
import urllib.error
import urllib.request

from common import (ROOT, CONFIG, ARMS, dump, extract_code, feedback_message,
                    initial_prompt, load_config, load_tasks, records, run_kernel,
                    sha, timestamp)

spec=importlib.util.spec_from_file_location("position_collector",ROOT/"experiments/document_qa/src/collect_document_positions.py")
limiter=importlib.util.module_from_spec(spec)
spec.loader.exec_module(limiter)


def identity(model,task,arm,round_):
    return f"{model}|{task}|{arm}|{round_}"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pilot",action="store_true")
    args=parser.parse_args()
    config=load_config()
    out=ROOT/config["raw_output"]
    plan=json.loads((out/"plan.json").read_text())
    if sha(CONFIG.read_bytes())!=plan["config_sha256"]:
        raise ValueError("Configuration differs from frozen plan")
    if not json.loads((out/"reference-preflight.json").read_text())["complete"]:
        raise ValueError("References must all pass before collection")
    tasks=load_tasks(config)
    ids=plan["pilot_tasks"] if args.pilot else plan["tasks"]
    keys=limiter.load_keys(None)
    lock_handle=(out/".collection.lock").open("w")
    fcntl.flock(lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda *_:stop.set())
    io_lock=threading.RLock()
    eval_gate=threading.Semaphore(config["evaluation_concurrency"])
    raw={r["record_id"]:r for r in records(out/"responses.jsonl")}
    evaluated={r["record_id"]:r for r in records(out/"evaluations.jsonl")}
    if len(raw)!=len(records(out/"responses.jsonl")) or len(evaluated)!=len(records(out/"evaluations.jsonl")):
        raise ValueError("Duplicate saved record identities")
    handles={name:(out/(name+".jsonl")).open("a",encoding="utf-8")
             for name in ("responses","evaluations","attempts","events")}
    lanes={m:limiter.Lane(config["initial_tpm"],config["maximum_tpm"],stop,
                         config["initial_rpm"],config["maximum_rpm"]) for m in config["models"]}
    # Restore the provider's rolling budget rather than resetting it on resume.
    now_wall=dt.datetime.now(dt.timezone.utc)
    for event in records(out/"attempts.jsonl"):
        age=(now_wall-dt.datetime.fromisoformat(event["timestamp"])).total_seconds()
        if 0<=age<61 and event["model"] in lanes:
            lane=lanes[event["model"]]
            moment=time.monotonic()-age
            lane.recent.append([moment,(event.get("usage") or {}).get("total_tokens") or 2000])
            lane.request_times.append(moment)
            if event["http_status"]==429:
                lane.cooldown=max(lane.cooldown,time.monotonic()+61-age)
    dispatch=Counter()
    failures=[]
    started=time.monotonic()
    expected=len(ids)*len(config["models"])*(1+len(ARMS)*(config["rounds"]-1))

    def clean(value):
        value=str(value)
        for key in keys:
            value=value.replace(key,"[REDACTED]")
        return re.sub(r"sk-[A-Za-z0-9_-]{20,}","[REDACTED]",value)

    def append(name,row):
        with io_lock:
            handles[name].write(json.dumps(row,ensure_ascii=False)+"\n")
            handles[name].flush()

    def event(kind,rid,**kwargs):
        append("events",{"timestamp":timestamp(),"event_type":kind,"record_id":rid,**kwargs})

    def evaluate(row):
        rid=row["record_id"]
        if rid in evaluated:
            return evaluated[rid]
        task=tasks[row["task_id"]]
        with eval_gate:
            oracle=pickle.loads((out/"oracles"/(row["task_id"].replace("/","_")+".pkl")).read_bytes())
            result=run_kernel(config,task,code=row["code"],oracle=oracle)
        result={"record_id":rid,"model":row["model"],"task_id":row["task_id"],
                "arm":row["arm"],"round":row["round"],"timestamp":timestamp(),**result}
        append("evaluations",result)
        with io_lock:
            evaluated[rid]=result
        event("test",rid,public_pass=result["public"]["passed"],hidden_pass=result["hidden"]["passed"],full_pass=result["full_pass"])
        return result

    def job(model,tid,arm,round_):
        rid=identity(model,tid,arm,round_)
        if rid in raw:
            evaluate(raw[rid])
            return
        if stop.is_set():
            return
        parent=None
        feedback=None
        messages=[{"role":"user","content":initial_prompt(tasks[tid])}]
        if round_ and arm!="resample":
            parent=identity(model,tid,"seed" if round_==1 else arm,round_-1)
            previous=raw[parent]
            feedback=feedback_message(arm,evaluated[parent])
            messages=previous["request"]["messages"]+[
                {"role":"assistant","content":previous["content"]},
                {"role":"user","content":feedback}]
        payload={"model":model,"messages":messages,"temperature":config["temperature"],
                 "top_p":config["top_p"],"max_tokens":config["max_tokens"],"stream":False}
        if "Qwen3" in model:
            payload["enable_thinking"]=config["qwen3_enable_thinking"]
        lane=lanes[model]
        text_for_budget="\n".join(m["content"] for m in messages)
        for attempt in range(1,config["max_attempts"]+1):
            entry=lane.acquire(text_for_budget)
            if entry is None:
                return
            with io_lock:
                slot=dispatch[model]%len(keys)
                dispatch[model]+=1
            begin=time.monotonic()
            status,response,error,trace=None,None,None,None
            try:
                request=urllib.request.Request(config["endpoint"],data=json.dumps(payload).encode(),
                    headers={"Authorization":"Bearer "+keys[slot],"Content-Type":"application/json"})
                # The machine's local proxy is intermittent; bypass it for this request only.
                opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(request,timeout=120) as result:
                    status=result.status
                    response=json.load(result)
                    trace=result.headers.get("x-siliconcloud-trace-id")
                if response.get("model")!=model:
                    raise ValueError("Provider returned a different model identifier")
                content=response["choices"][0]["message"].get("content")
                if not isinstance(content,str) or not content.strip():
                    raise ValueError("Provider returned empty content")
            except urllib.error.HTTPError as exc:
                status=exc.code
                error=clean(exc.read().decode(errors="replace"))[:1800]
            except Exception as exc:
                error=clean(type(exc).__name__+": "+str(exc))[:1800]
            usage=(response or {}).get("usage") or {}
            lane.observe(entry,usage,status,error)
            attempt_row={"timestamp":timestamp(),"record_id":rid,"model":model,"attempt":attempt,
                         "credential_slot":slot,"http_status":status,"usage":usage,"error":error,
                         "seconds":round(time.monotonic()-begin,3),"provider_trace":trace}
            append("attempts",attempt_row)
            if error is None:
                code=extract_code(content)
                row={"record_id":rid,"batch_id":config["batch_id"],"timestamp":timestamp(),
                     "model":model,"task_id":tid,"arm":arm,"round":round_,"parent_id":parent,
                     "shared_seed_id":identity(model,tid,"seed",0),
                     "feedback_source_id":parent if arm in ("pass_fail","counterexample") else None,
                     "feedback":feedback,"request":payload,"response":response,
                     "content":content,"code":code,"code_sha256":sha(code.encode()),"usage":usage,
                     "seconds":attempt_row["seconds"],"finish_reason":response["choices"][0].get("finish_reason"),
                     "config_sha256":plan["config_sha256"]}
                append("responses",row)
                with io_lock:
                    raw[rid]=row
                event("api",rid,model=model,task_id=tid,arm=arm,round=round_,usage=usage)
                if parent:
                    event("edit",rid,parent_id=parent,code_changed=raw[parent]["code_sha256"]!=row["code_sha256"])
                evaluate(row)
                return
            event("error",rid,http_status=status,error=error)
            if status in (401,402,403):
                raise RuntimeError("Provider credential/billing error: "+str(status))
            if attempt<config["max_attempts"]:
                stop.wait(min(30,2**attempt))
        raise RuntimeError("API retry budget exhausted: "+rid)

    selected=set(ids)
    def progress(round_):
        with io_lock:
            counts=Counter(r["model"] for r in raw.values() if r["task_id"] in selected)
            evaluated_count=sum(r["task_id"] in selected for r in evaluated.values())
        state={"timestamp":timestamp(),"scope":"pilot" if args.pilot else "full","round":round_,
               "responses":sum(counts.values()),"expected":expected,"evaluated":evaluated_count,"by_model":dict(counts),
               "rate_limits":{m:l.ratelimits for m,l in lanes.items()},
               "tpm_budget":{m:l.budget for m,l in lanes.items()},
               "seconds":round(time.monotonic()-started,1),"failures":failures[-10:]}
        dump(out/"collection-status.json",state)
        print(json.dumps(state,ensure_ascii=False),flush=True)

    pools={}
    try:
        for round_ in range(config["rounds"]):
            jobs=[(m,t,a,round_) for m in config["models"] for t in ids
                  for a in (["seed"] if round_==0 else ARMS)]
            random.Random(config["pilot_seed"]+round_).shuffle(jobs)
            pools={m:ThreadPoolExecutor(max_workers=max(1,config["max_concurrency"]//len(config["models"])))
                   for m in config["models"]}
            pending={pools[j[0]].submit(job,*j):j for j in jobs}
            progress(round_)
            last_progress=time.monotonic()
            while pending:
                finished,_=wait(pending,timeout=30,return_when=FIRST_COMPLETED)
                for future in finished:
                    j=pending.pop(future)
                    try:
                        future.result()
                    except Exception as exc:
                        failures.append({"job":j,"error":clean(exc)[:1800]})
                        stop.set()
                if not finished or not pending or time.monotonic()-last_progress>=30:
                    progress(round_)
                    last_progress=time.monotonic()
                if stop.is_set():
                    for future in pending:
                        future.cancel()
            for pool in pools.values():
                pool.shutdown(wait=True,cancel_futures=True)
            if stop.is_set():
                break
        progress(round_)
    finally:
        stop.set()
        for pool in pools.values():
            pool.shutdown(wait=True,cancel_futures=True)
        for handle in handles.values():
            handle.close()
    if failures:
        raise SystemExit(2)
    if sum(r["task_id"] in selected for r in raw.values())!=expected:
        raise SystemExit(3)


if __name__=="__main__":
    main()
