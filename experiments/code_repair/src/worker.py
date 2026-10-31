"""One isolated evaluation. Launched only through common.run_kernel."""
from __future__ import annotations

import ast
import copy
import json
import pickle
from pathlib import Path
import resource
import sys
import time
import warnings

sys.path.insert(0, sys.argv[3])
import numpy as np
from evalplus.eval import is_floats
from evalplus.eval._special_oracle import _poly
from evalplus.eval.utils import reliability_guard, swallow_io, time_limit


def short(value, limit=1800):
    try:
        text=repr(value)
    except BaseException:
        return "<unrepresentable>"
    return text[:limit] + ("...[truncated]" if len(text)>limit else "")


def matches(entry, inp, actual, expected, atol):
    if entry=="find_zero":
        return bool(abs(_poly(*inp, actual))<=atol)
    exact=actual==expected
    if atol==0 and is_floats(expected):
        atol=1e-6
    if not exact and atol!=0:
        if type(actual)!=type(expected):
            return False
        if isinstance(expected,(list,tuple)) and len(actual)!=len(expected):
            return False
        return bool(np.allclose(actual,expected,rtol=1e-7,atol=atol))
    return bool(exact)


def check(fn, entry, inputs, expected, times, atol):
    for i,(inp,exp,ref_time) in enumerate(zip(inputs,expected,times)):
        actual=None
        try:
            with time_limit(max(1.0,20*ref_time)):
                with swallow_io():
                    actual=fn(*copy.deepcopy(inp))
                if not matches(entry,inp,actual,exp,atol):
                    raise AssertionError("Output does not satisfy the diagnostic oracle")
        except BaseException as exc:
            return {"passed":False,"cases_checked":i+1,"total_cases":len(inputs),
                    "first_failure":{"case_index":i,"input":short(inp),"expected":short(exp),
                                     "actual":short(actual),"error_type":type(exc).__name__,
                                     "error_message":str(exc)[:1000]}}
    return {"passed":True,"cases_checked":len(inputs),"total_cases":len(inputs),"first_failure":None}


def main():
    payload_path=Path(sys.argv[1])
    result_path=Path(sys.argv[2])
    payload=pickle.loads(payload_path.read_bytes())
    task=payload["task"]
    mode=payload["mode"]
    oracle=payload.get("oracle")
    result_handle=result_path.open("wb")
    oracle_handle=Path(payload["oracle_output"]).open("wb") if mode=="oracle" else None
    resource.setrlimit(resource.RLIMIT_CPU,(45,45))
    file_limit=(512 if mode=="oracle" else 8)*1024*1024
    resource.setrlimit(resource.RLIMIT_FSIZE,(file_limit,file_limit))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_NPROC,(0,0))
    reliability_guard(maximum_memory_bytes=None)
    code=task["prompt"]+task["canonical_solution"] if mode=="oracle" else payload["code"]
    namespace={"__name__":"candidate"}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree=ast.parse(code)
            with time_limit(5),swallow_io():
                exec(compile(tree,"<candidate>","exec"),namespace)
        fn=namespace[task["entry_point"]]
    except BaseException as exc:
        failure={"passed":False,"cases_checked":0,"total_cases":len(task["base_input"]),
                 "first_failure":{"case_index":None,"input":None,"expected":None,"actual":None,
                                  "error_type":type(exc).__name__,"error_message":str(exc)[:1000]}}
        result={"public":failure,"hidden":{"passed":False,"cases_checked":0,"total_cases":len(task["plus_input"])},"full_pass":False}
        result_handle.write(json.dumps(result).encode())
        result_handle.close()
        return
    if mode=="oracle":
        oracle={}
        try:
            for name,inputs in [("base",task["base_input"]),("plus",task["plus_input"])]:
                outputs,times=[],[]
                for inp in inputs:
                    start=time.monotonic()
                    with time_limit(5),swallow_io():
                        outputs.append(fn(*copy.deepcopy(inp)))
                    times.append(time.monotonic()-start)
                oracle[name]={"outputs":outputs,"times":times}
            oracle_handle.write(pickle.dumps(oracle))
            oracle_handle.close()
        except BaseException as exc:
            result_handle.write(json.dumps({"reference_error":type(exc).__name__,"message":str(exc)[:1000]}).encode())
            result_handle.close()
            return
    public=check(fn,task["entry_point"],task["base_input"],oracle["base"]["outputs"],oracle["base"]["times"],task["atol"])
    hidden=check(fn,task["entry_point"],task["plus_input"],oracle["plus"]["outputs"],oracle["plus"]["times"],task["atol"])
    result={"public":public,"hidden":hidden,"full_pass":bool(public["passed"] and hidden["passed"])}
    result_handle.write(json.dumps(result,ensure_ascii=False).encode())
    result_handle.close()


if __name__=="__main__":
    main()
