"""Import saved code-generation scores and build anonymous, offline UI evidence.

No model requests, code execution, or regrading. The source score is preserved.
Use --anonymous to recompute using the public numeric feature snapshot alone.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, csv, gzip, hashlib, json, math
import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
SOURCE = ROOT / "data/raw/code_generation"
OUT = ROOT / "app/data"
REPORT = ROOT / "reports/code_generation"
MODELS = {"deepseek-flash": "deepseek", "qwen2.5-7b-instruct-cloud": "qwen", "qwen3-8b-cloud": "qwen3"}
NAMES = {"deepseek": "DeepSeek Flash", "qwen": "Qwen2.5 7B", "qwen3": "Qwen3 8B"}
COLORS = {"deepseek": "#3978b6", "qwen": "#8958b4", "qwen3": "#2c8d83"}
FIELDS = ["id", "question", "model", "prompt", "sample", "passed", "error", "output_tokens", "input_tokens", "total_tokens", "latency_seconds", "finish", "environment_excluded", "level"]
COMMIT = "9dfc5923d3e0e099accca7a709c420c0d531a58b"
CORE = ["NoCoT", "DefaultCoT", "BeConcise", "BulletPoints", "WordLimit(25)", "TokenLimit(100)", "NoProperGrammar", "OnlyNumbers"]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")


def number(v, integer=False):
    if v in (None, "", "nan", "None"):
        return None
    return int(v) if integer else float(v)


def source_rows():
    path = SOURCE / "source_scores/scores.csv.gz"
    source_meta = json.loads((SOURCE / "SOURCE.json").read_text())
    if source_meta["commit"] != COMMIT:
        raise ValueError("Unexpected source commit")
    for rel, expected in source_meta["files"].items():
        if Path(rel).name == "README.md":
            continue  # Release documentation is normalized; raw payloads are pinned separately.
        if rel.startswith("data/"):
            target = SOURCE / rel.removeprefix("data/")
        elif rel.startswith("derived/"):
            target = SOURCE / "source_scores" / rel.removeprefix("derived/")
        else:
            continue  # Original docs/code/figures live in their content directories.
        if digest(target) != expected:
            raise ValueError("Raw source artifact changed: " + rel)
    with gzip.open(path, "rt", newline="") as handle:
        original = list(csv.DictReader(handle))
    task_map = {t: f"T{i+1:03}" for i, t in enumerate(dict.fromkeys(r["task_id"] for r in original))}
    result = []
    seen = set()
    for i, r in enumerate(original):
        key = (r["analysis_model"], r["task_id"], r["analysis_prompt_id"], int(r["analysis_turn_id"]))
        if key in seen:
            raise ValueError("Duplicate generation key")
        seen.add(key)
        if r["normalization"] != "target-function-ast-v2" or r["sandboxed"].lower() != "true":
            raise ValueError("Unexpected grading provenance")
        excluded = r["analysis_error_category"] == "environment_error"
        passed = None if excluded else {"True": 1, "False": 0}[r["analysis_passed"]]
        result.append(dict(zip(FIELDS, [f"Y{i+1:06}", task_map[r["task_id"]], MODELS[r["analysis_model"]],
            r["analysis_prompt_id"], int(r["analysis_turn_id"]), passed,
            r["analysis_error_category"], number(r["output_tokens"], True), number(r["input_tokens"], True),
            number(r["total_tokens"], True), number(r["latency_seconds"]), r["finish_reason"] or None,
            excluded, r["level"] or None])))
    prompt_specs = json.loads((SOURCE / "prompts.json").read_text())
    provenance = {"repository": source_meta["repository"], "branch": "code_generation", "commit": COMMIT,
        "scorer": "target-function-ast-v2", "source_scores_sha256": digest(path),
        "source_checksums_sha256": digest(SOURCE / "CHECKSUMS.json"),
        "api_calls_during_integration": 0, "generated_code_executed_during_integration": False}
    with (SOURCE/"source_scores/model_summary.csv").open() as handle:
        provenance["source_model_reference"]=[{"model":MODELS[r["model"]],"pass":[float(r[f"pass_at_{k}"]) for k in [1,3,5]]} for r in csv.DictReader(handle)]
    return result, prompt_specs, provenance


def build(rows, prompt_specs, provenance):
    if len(rows) != 90210 or len({r["id"] for r in rows}) != 90210:
        raise ValueError("Expected 90,210 distinct saved generations")
    if sum(r["environment_excluded"] for r in rows) != 465:
        raise ValueError("Expected 465 environment exclusions")
    prompts = list(prompt_specs)
    if len(prompts) != 31:
        raise ValueError("Expected 31 prompt conditions")
    groups = defaultdict(list)
    for r in rows:
        groups[r["model"], r["question"], r["prompt"]].append(r)
    if len(groups) != 3*194*31 or any(sorted(r["sample"] for r in g) != [1,2,3,4,5] for g in groups.values()):
        raise ValueError("Incomplete 194 x 31 x 5 x 3 design")
    excluded_tasks = sorted({r["question"] for r in rows if r["environment_excluded"]})
    if len(excluded_tasks) != 1:
        raise ValueError("Expected one common environment-excluded task")
    eligible = [r for r in rows if not r["environment_excluded"]]
    for r in rows:
        if (r["question"] in excluded_tasks) != r["environment_excluded"]:
            raise ValueError("Environment exclusions differ across conditions")
    # Keep the source task-cluster order. Anonymous task IDs retain this order.
    units = []
    for (model, task, prompt), g in groups.items():
        if g[0]["environment_excluded"]:
            continue
        g = sorted(g, key=lambda r:r["sample"])
        c = sum(r["passed"] for r in g)
        pk = [1 - (math.comb(5-c,k)/math.comb(5,k) if 5-c >= k else 0) for k in range(1,6)]
        cum = np.maximum.accumulate([r["passed"] for r in g]).astype(float).tolist()
        units.append({"model": model, "question": task, "prompt": prompt, "pass": pk, "cumulative": cum})
    indices = np.random.default_rng(91).integers(0, 193, (5000,193))

    def interval(per_task):
        a = np.asarray(per_task, dtype=float)
        if len(a) != 193:
            raise ValueError("Each comparison must use 193 common task clusters")
        draws = a[indices].mean(axis=1)
        low, high = np.quantile(draws, [.025,.975], axis=0)
        return a.mean(axis=0).tolist(), low.tolist(), high.tolist()

    stats, task_vectors = [], {}
    for model in NAMES:
        model_units = [u for u in units if u["model"] == model]
        for prompt in ["__all"] + prompts:
            us = model_units if prompt == "__all" else [u for u in model_units if u["prompt"] == prompt]
            bytask = defaultdict(list)
            for u in us:
                bytask[u["question"]].append(u)
            pvec = [np.mean([u["pass"] for u in g], axis=0) for g in bytask.values()]
            cvec = [np.mean([u["cumulative"] for u in g], axis=0) for g in bytask.values()]
            pv, pl, ph = interval(pvec)
            cv, cl, ch = interval(cvec)
            marg = np.diff(np.asarray(cvec), axis=1)
            mv, ml, mh = interval(marg)
            rs = [r for r in eligible if r["model"] == model and (prompt == "__all" or r["prompt"] == prompt)]
            counts = Counter(r["error"] for r in rs if not r["passed"])
            output = [r["output_tokens"] for r in rs if r["output_tokens"] is not None]
            stats.append({"model":model,"prompt":prompt,"n":len(rs),"questions":193,"units":len(us),
                "pass":pv,"pass_low":pl,"pass_high":ph,"cumulative":cv,"cumulative_low":cl,"cumulative_high":ch,
                "marginal":mv,"marginal_low":ml,"marginal_high":mh,"errors":dict(counts),
                "source_records":194*5*(31 if prompt=="__all" else 1),"environment_excluded":5*(31 if prompt=="__all" else 1),
                "successes":sum(r["passed"] for r in rs),"mean_output_tokens":float(np.mean(output)),
                "median_output_tokens":float(np.median(output)),"truncated":sum(r["finish"]=="length" for r in rs)})
            task_vectors[model,prompt] = (dict(zip(bytask, pvec)), dict(zip(bytask, cvec)))
    pairs=[]
    for a,b in [("deepseek","qwen"),("deepseek","qwen3"),("qwen","qwen3")]:
        av,bv=task_vectors[a,"__all"][0],task_vectors[b,"__all"][0]
        values,lo,hi=interval([np.asarray(av[t])-np.asarray(bv[t]) for t in av])
        pairs.append({"left":a,"right":b,"difference":values,"low":lo,"high":hi})
    contrasts=[]
    for model in NAMES:
        baseline=task_vectors[model,"NoCoT"][0]
        for prompt in prompts:
            target=task_vectors[model,prompt][0]
            values,lo,hi=interval([np.asarray(target[t])-np.asarray(baseline[t]) for t in target])
            contrasts.append({"model":model,"prompt":prompt,"difference":values,"low":lo,"high":hi})
    missing={k:sum(r[k] is None or r[k]=="" for r in rows) for k in FIELDS}
    result={"schema_version":"code-study-v1","provenance":provenance,"records":len(rows),"eligible_records":len(eligible),
        "environment_excluded":465,"tasks":194,"eligible_tasks":193,"excluded_tasks":excluded_tasks,
        "prompts":prompts,"prompt_specs":prompt_specs,"core":CORE,"models":[{"id":m,"name":n,"color":COLORS[m]} for m,n in NAMES.items()],
        "stats":stats,"pairs":pairs,"contrasts":contrasts,"error_categories":sorted({r["error"] for r in eligible if not r["passed"]}),
        "bootstrap":{"cluster":"question","draws":5000,"seed":91,"kind":"percentile","multiple_comparison_adjustment":False},
        "sampling_mode":"independent single-turn; no previous output or test feedback supplied",
        "source_comparison":{},"missing":missing}
    # The source reference is numeric and travels with the anonymous input.
    if provenance.get("source_model_reference"):
        errors=[]
        for r in provenance["source_model_reference"]:
            x=next(s for s in stats if s["model"]==r["model"] and s["prompt"]=="__all")
            for i,k in enumerate([1,3,5]):errors.append(abs(x["pass"][k-1]-r["pass"][i]))
        result["source_comparison"]={"model_pass_1_3_5_max_abs_difference":max(errors),"new_k_values":[2,4],
            "new_k_method":"same unbiased estimator applied to all five saved outcomes; no interpolation",
            "cumulative_ci_method":"task-cluster bootstrap recomputed; source cumulative Wilson intervals are not reused"}
        if max(errors)>1e-10:raise ValueError("Model point estimates disagree with source")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anonymous", action="store_true")
    args=p.parse_args()
    OUT.mkdir(exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
    feature=OUT/"code-features.json.gz"
    if args.anonymous:
        payload=json.loads(gzip.decompress(feature.read_bytes()))
        rows=[dict(zip(payload["fields"],r)) for r in payload["rows"]]
        old=json.loads((OUT/"code-evidence.json").read_text())
        specs,prov=old["prompt_specs"],old["provenance"]
    else:
        rows,specs,prov=source_rows()
        payload={"schema_version":"code-study-features-v1","fields":FIELDS,"rows":[[r[k] for k in FIELDS] for r in rows]}
        feature.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(",", ":"),allow_nan=False).encode(),mtime=0))
    result=build(rows,specs,prov)
    result["features_sha256"]=digest(feature)
    dump(OUT/"code-evidence.json",result)
    dump(REPORT/"integration-audit.json",{k:result[k] for k in ["provenance","records","eligible_records","environment_excluded","tasks","eligible_tasks","excluded_tasks","source_comparison","missing","features_sha256"]})
    flat=[]
    for s in result["stats"]:
        row={k:s[k] for k in ["model","prompt","n","questions","units","source_records","environment_excluded","successes","mean_output_tokens","median_output_tokens","truncated"]}
        for key in ["pass","pass_low","pass_high","cumulative","cumulative_low","cumulative_high","marginal","marginal_low","marginal_high"]:
            for i,v in enumerate(s[key],2 if key.startswith("marginal") else 1):row[f"{key}_{i}"]=v
        for key in result["error_categories"]:row["error_count_"+key]=s["errors"].get(key,0)
        flat.append(row)
    with (REPORT/"conditions.csv").open("w",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    for filename,items,keys in [("paired-model-differences.csv",result["pairs"],["left","right"]),("prompt-vs-no-cot.csv",result["contrasts"],["model","prompt"])]:
        with (REPORT/filename).open("w",newline="") as h:
            w=csv.writer(h);w.writerow(keys+["k","difference","ci_low","ci_high"])
            for r in items:
                for i in range(5):w.writerow([r[k] for k in keys]+[i+1,r["difference"][i],r["low"][i],r["high"][i]])
    processed=ROOT/"data/processed/code_generation";processed.mkdir(exist_ok=True,parents=True)
    meanings=["匿名回答ID","匿名共同题目ID","统一模型键","代码适配提示ID","独立采样次序1–5","源测试结果；环境排除为null","源错误类别；环境记录独立排除","返回token数","输入token数","总token数","生成延迟秒","源结束原因","共同环境排除标记","源题目依赖层级"]
    with (processed/"data_dictionary.tsv").open("w",newline="") as h:
        w=csv.writer(h,delimiter="\t");w.writerow(["field","meaning","missing_count","source","policy"])
        for k,m in zip(FIELDS,meanings):w.writerow([k,m,result["missing"][k],"saved scores.csv.gz; identity anonymized","preserve source; do not fill missing as zero"])
    # Extend the common metadata without overwriting the original QA audit.
    meta=ROOT/"data/processed"; table="code_prompt_eval.anonymous_scores"
    missing_rows=[]; dictionary_rows=[]
    types=["string","string","category","category","integer","integer|null","category","integer","integer","integer","number","category","boolean","category"]
    for k,m,t in zip(FIELDS,meanings,types):
        n=result["missing"][k]; reasons={"common_environment_exclusion":n} if k=="passed" and n else {}
        missing_rows.append(dict(table=table,field=k,total_rows=len(rows),missing_count=n,missing_rate=n/len(rows),empty_container_count=0,reason_counts=reasons))
        dictionary_rows.append(dict(table=table,field=k,type=t,meaning=m,origin_kind="anonymized_identity" if k in ["id","question"] else "source_observation",source_or_rule="code-generation@9dfc592 derived/scores.csv.gz; scripts/cleaning/import_code_generation.py",applicability="all 90,210 saved rows; performance excludes 465 common environment rows",missing_policy="preserve null; never zero-fill or count environmental exclusion as model failure",missing_reasons_observed=json.dumps(reasons),total_rows=len(rows),missing_count=n,missing_rate=n/len(rows),empty_container_count=0))
    for filename,new_rows in [("data_dictionary.tsv",dictionary_rows),("missingness_report.csv",missing_rows)]:
        path=meta/filename
        if not path.exists():continue
        delimiter="\t" if path.suffix==".tsv" else ","
        with path.open(newline="") as h:
            reader=csv.DictReader(h,delimiter=delimiter); headers=reader.fieldnames
            old=[r for r in reader if r["table"]!=table]
        with path.open("w",newline="") as h:
            writer=csv.DictWriter(h,fieldnames=headers,delimiter=delimiter);writer.writeheader();writer.writerows(old)
            writer.writerows({k:json.dumps(v) if isinstance(v,dict) else v for k,v in r.items()} for r in new_rows)
    path=meta/"missingness_report.json"
    if path.exists():
        d=json.loads(path.read_text());d["fields"]=[r for r in d["fields"] if r["table"]!=table]+missing_rows
        d["code_generation_scope"]="90,210 anonymous saved scores; only passed has 465 environmental nulls"
        dump(path,d)
    path=meta/"quality_report.json"
    if path.exists():
        d=json.loads(path.read_text());d["code_generation_integration"]={"source_commit":COMMIT,"records":90210,"eligible_records":89745,"environment_excluded":465,"anonymous_fields":14,"model_api_calls":0,"generated_code_executed":False,"source_point_estimate_max_difference":result["source_comparison"].get("model_pass_1_3_5_max_abs_difference")};dump(path,d)
    print(f"Code study: {len(rows):,} saved responses; {result['eligible_records']:,} eligible; 465 excluded; 96 aggregate conditions. No API calls or code execution.")


if __name__=="__main__":main()
