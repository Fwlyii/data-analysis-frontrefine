"""Freeze scenarios and preflight trusted benchmark references. No API calls."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import pickle
import random

from common import ROOT, CONFIG, dump, load_config, load_tasks, run_kernel, sha, timestamp


def main():
    config=load_config()
    if sha((ROOT/config["dataset"]).read_bytes())!=config["dataset_sha256"]:
        raise ValueError("Dataset hash mismatch")
    tasks=load_tasks(config)
    if len(tasks)!=config["expected_tasks"]:
        raise ValueError("Unexpected benchmark size")
    ids=sorted(tasks,key=lambda x:int(x.split("/")[-1]))
    pilot=sorted(random.Random(config["pilot_seed"]).sample(ids,config["pilot_size"]),key=lambda x:int(x.split("/")[-1]))
    out=ROOT/config["raw_output"]
    out.mkdir(parents=True,exist_ok=True)
    (out/"oracles").mkdir(exist_ok=True)
    split_rows=[]
    for tid in ids:
        t=tasks[tid]
        base={json.dumps(v,sort_keys=True) for v in t["base_input"]}
        plus=[json.dumps(v,sort_keys=True) for v in t["plus_input"]]
        split_rows.append({"task_id":tid,"base_cases":len(t["base_input"]),"plus_cases":len(plus),
                           "plus_overlaps_base":sum(v in base for v in plus),
                           "new_unique_plus_inputs":len(set(plus)-base)})
    dump(out/"test-split-audit.json",{"tasks":split_rows,
         "base_cases":sum(r["base_cases"] for r in split_rows),
         "plus_cases":sum(r["plus_cases"] for r in split_rows),
         "plus_overlaps_base":sum(r["plus_overlaps_base"] for r in split_rows),
         "new_unique_plus_inputs":sum(r["new_unique_plus_inputs"] for r in split_rows),
         "policy":"Preserve upstream inputs unchanged. Only base results can be projected into feedback. Joint task pass is a boolean; test cases are not treated as independent samples."})
    plan={"batch_id":config["batch_id"],"prepared_at":timestamp(),"tasks":ids,"pilot_tasks":pilot,
          "diagnostic_cases":sum(len(t["base_input"]) for t in tasks.values()),
          "hidden_cases":sum(len(t["plus_input"]) for t in tasks.values()),
          "config_sha256":sha(CONFIG.read_bytes()),"dataset_sha256":config["dataset_sha256"]}
    if (out/"plan.json").exists():
        previous=json.loads((out/"plan.json").read_text())
        if previous["config_sha256"]!=plan["config_sha256"]:
            raise ValueError("A different frozen configuration already exists")
    else:
        dump(out/"plan.json",plan)
    checks=[]
    def one(tid):
        path=out/"oracles"/(tid.replace("/","_")+".pkl")
        meta=path.with_suffix(".json")
        if path.exists() and meta.exists():
            old=json.loads(meta.read_text())
            if old["oracle_sha256"]!=sha(path.read_bytes()):
                raise ValueError("Reference cache hash mismatch")
            return old
        result,oracle=run_kernel(config,tasks[tid],oracle_mode=True)
        blob=pickle.dumps(oracle)
        path.write_bytes(blob)
        record={"task_id":tid,"reference_pass":result["full_pass"],"oracle_sha256":sha(blob),
                "base_cases":len(tasks[tid]["base_input"]),"hidden_cases":len(tasks[tid]["plus_input"]),
                "evaluation_seconds":result["evaluation_seconds"],"sandboxed":True}
        dump(meta,record)
        return record
    errors=[]
    with ThreadPoolExecutor(max_workers=config["evaluation_concurrency"]) as pool:
        pending={pool.submit(one,tid):tid for tid in ids}
        for f in as_completed(pending):
            try:
                checks.append(f.result())
            except Exception as exc:
                errors.append({"task_id":pending[f],"error":str(exc)[:1600]})
            if (len(checks)+len(errors))%20==0:
                print(json.dumps({"reference_complete":len(checks),"reference_errors":len(errors),"expected":len(ids)}),flush=True)
    dump(out/"reference-preflight.json",{"complete":len(checks)==len(ids),"references":sorted(checks,key=lambda x:x["task_id"]),"errors":errors,"api_calls":0})
    if errors:
        print(json.dumps(errors,ensure_ascii=False,indent=2))
        raise SystemExit(2)
    print(json.dumps({"reference_preflight":"complete","tasks":len(ids),"pilot_tasks":pilot,"api_calls":0},ensure_ascii=False))


if __name__=="__main__":
    main()
