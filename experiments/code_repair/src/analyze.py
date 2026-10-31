"""Offline paired analysis; no API calls and no execution of model programs."""
from __future__ import annotations

import argparse
import ast
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import re

import numpy as np

from common import (ROOT, ARMS, MODEL_NAMES, dump, feedback_message, load_config,
                    load_tasks, records, sha, timestamp)
from collect import identity

LABELS={"resample":"Independent resampling","self_review":"Self-review",
        "pass_fail":"Pass / fail feedback","counterexample":"Counterexample feedback"}
ZH={"resample":"独立重抽","self_review":"无反馈自查","pass_fail":"通过/失败反馈","counterexample":"具体失败用例"}
COLORS={"resample":"#858A91","self_review":"#B77B37","pass_fail":"#40768E","counterexample":"#A84C58"}


def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:
        return
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k:(str(v).lower() if isinstance(v,bool) else v) for k,v in row.items()} for row in rows)


def ast_hash(code):
    try:
        return sha(ast.dump(ast.parse(code),include_attributes=False).encode())
    except SyntaxError:
        return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pilot",action="store_true")
    parser.add_argument("--partial",action="store_true")
    args=parser.parse_args()
    config=load_config()
    out=ROOT/config["raw_output"]
    plan=json.loads((out/"plan.json").read_text())
    ids=plan["pilot_tasks"] if args.pilot else plan["tasks"]
    selected=set(ids)
    raw_list=records(out/"responses.jsonl")
    eval_list=records(out/"evaluations.jsonl")
    raw={r["record_id"]:r for r in raw_list}
    ev={r["record_id"]:r for r in eval_list}
    if len(raw)!=len(raw_list) or len(ev)!=len(eval_list):
        raise ValueError("Duplicate record IDs")
    expected=len(ids)*len(config["models"])*(1+len(ARMS)*(config["rounds"]-1))
    required=[identity(m,t,a,r) for m in config["models"] for t in ids
              for r in range(config["rounds"]) for a in (["seed"] if r==0 else ARMS)]
    missing=[rid for rid in required if rid not in raw or rid not in ev]
    if missing and not args.partial:
        raise ValueError(f"Incomplete paired data: {len(missing)} missing records")
    # Use only tasks with every arm/round present in partial monitoring.
    ids=[t for t in ids if all(identity(m,t,a,r) in raw and identity(m,t,a,r) in ev
           for m in config["models"] for r in range(config["rounds"])
           for a in (["seed"] if r==0 else ARMS))]
    if not ids:
        print(json.dumps({"complete_tasks":0,"missing":len(missing)}))
        return
    tasks=load_tasks(config)
    checks=Counter()
    for rid in required:
        if rid not in raw or rid not in ev:
            continue
        r=raw[rid]
        if re.search(r"sk-[A-Za-z0-9_-]{25,}",json.dumps(r)):
            raise ValueError("Possible credential in raw record; stop export")
        if r["config_sha256"]!=plan["config_sha256"]:
            raise ValueError("Protocol hash mismatch")
        if r["response"]["model"]!=r["model"]:
            raise ValueError("Provider model mismatch")
        if r["usage"]["total_tokens"]!=r["usage"]["prompt_tokens"]+r["usage"]["completion_tokens"]:
            raise ValueError("Inconsistent provider token accounting")
        if r["model"].endswith("Qwen3-8B") and r["request"].get("enable_thinking") is not False:
            raise ValueError("Qwen3 thinking configuration mismatch")
        if r["parent_id"]:
            p=raw[r["parent_id"]]
            expected_feedback=feedback_message(r["arm"],ev[p["record_id"]])
            expected_messages=p["request"]["messages"]+[
                {"role":"assistant","content":p["content"]},
                {"role":"user","content":expected_feedback}]
            if r["feedback"]!=expected_feedback or r["request"]["messages"]!=expected_messages:
                raise ValueError("History/feedback mismatch")
            checks["verified_parent_feedback_and_history"]+=1
        else:
            if len(r["request"]["messages"])!=1 or r["feedback"] is not None:
                raise ValueError("Independent generation contains feedback")
            checks["verified_independent_requests"]+=1
        # Feedback equality above proves only the public projection was used.
        if not ev[rid].get("sandboxed"):
            raise ValueError("Unsandboxed evaluation")
        checks["verified_sandboxed_evaluations"]+=1
        checks["truncated_responses"]+=r["finish_reason"]=="length"
        checks["nonzero_reasoning_usage"]+=(r["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens",0)>0
    scope="pilot" if args.pilot else "full"
    report=ROOT/"reports/code_repair"/scope
    report.mkdir(parents=True,exist_ok=True)
    split_audit=json.loads((out/"test-split-audit.json").read_text())
    dump(report/"test-split-audit.json",split_audit)
    processed=ROOT/"data/processed/code_repair"/scope
    n=len(ids)
    rng=np.random.default_rng(config["bootstrap"]["seed"])
    bootstrap_indices=rng.integers(0,n,size=(config["bootstrap"]["resamples"],n))

    def ci(values):
        values=np.asarray(values,float)
        return [float(v) for v in np.quantile(values[bootstrap_indices].mean(axis=1),[.025,.975])]

    features=[]
    matrices={}
    samples={}
    curves=[]
    finals=[]
    transitions=Counter()
    examples=[]
    for model in config["models"]:
        seeds=np.array([ev[identity(model,t,"seed",0)]["full_pass"] for t in ids],bool)
        for arm in ARMS:
            full=np.zeros((n,config["rounds"]),bool)
            public=full.copy()
            hidden=full.copy()
            tokens=np.zeros_like(full,dtype=int)
            rows=[]
            for i,tid in enumerate(ids):
                seq=[]
                cumulative=0
                for r in range(config["rounds"]):
                    rid=identity(model,tid,"seed" if r==0 else arm,r)
                    source=raw[rid]
                    score=ev[rid]
                    seq.append(source)
                    full[i,r]=score["full_pass"]
                    public[i,r]=score["public"]["passed"]
                    hidden[i,r]=score["hidden"]["passed"]
                    tokens[i,r]=source["usage"]["total_tokens"]
                    cumulative+=tokens[i,r]
                    parent=seq[-2] if r else None
                    current_ast=ast_hash(source["code"])
                    previous_ast=ast_hash(parent["code"]) if parent else None
                    changed=current_ast!=previous_ast if current_ast and previous_ast else None
                    failure=score["public"]["first_failure"]
                    features.append({"model":MODEL_NAMES[model],"task_id":tid,"arm":arm,"round":r,
                        "full_pass":bool(full[i,r]),"diagnostic_pass":bool(public[i,r]),"hidden_pass":bool(hidden[i,r]),
                        "initial_full_pass":bool(seeds[i]),"input_tokens":source["usage"]["prompt_tokens"],
                        "output_tokens":source["usage"]["completion_tokens"],"total_tokens":int(tokens[i,r]),
                        "cumulative_tokens":int(cumulative),"code_changed_from_previous":changed,
                        "code_text_changed_from_previous":source["code_sha256"]!=parent["code_sha256"] if parent else None,
                        "public_error_type":failure["error_type"] if failure else "pass",
                        "finish_reason":source["finish_reason"],"evaluation_seconds":score["evaluation_seconds"],
                        "physical_record_id":rid,"shared_seed":r==0})
                    if r:
                        prev=ev[seq[-2]["record_id"]]
                        prior_error=(prev["public"]["first_failure"] or {}).get("error_type","pass")
                        current_error=(failure or {}).get("error_type","pass")
                        transitions[model,arm,r,prior_error,current_error]+=1
                rows.append(seq)
            matrices[model,arm]=(full,public,hidden,tokens)
            samples[model,arm]=rows
            ever=np.maximum.accumulate(full,axis=1)
            stops=np.where(public.any(axis=1),public.argmax(axis=1),config["rounds"]-1)
            stopped=full[np.arange(n),stops]
            final=full[:,-1]
            repaired=(~seeds)&final
            regressed=seeds&(~final)
            rec={"model":MODEL_NAMES[model],"arm":arm,"tasks":n,"initial_success":int(seeds.sum()),
                 "final_success":int(final.sum()),"final_rate":float(final.mean()),"final_ci":ci(final),
                 "first_diagnostic_pass_success":int(stopped.sum()),"first_diagnostic_pass_rate":float(stopped.mean()),
                 "stop_policy_mean_calls":float((stops+1).mean()),
                 "stop_policy_mean_tokens":float(np.mean([tokens[i,:s+1].sum() for i,s in enumerate(stops)])),
                 "ever_success":int(ever[:,-1].sum()),"repaired":int(repaired.sum()),
                 "initial_failures":int((~seeds).sum()),"regressed":int(regressed.sum()),
                 "net_gain_pp":float((final.astype(int)-seeds.astype(int)).mean()*100),
                 "net_gain_ci_pp":[v*100 for v in ci(final.astype(int)-seeds.astype(int))],
                 "diagnostic_pass_hidden_fail_final":int((public[:,-1]&~hidden[:,-1]).sum()),
                 "mean_all_five_tokens":float(tokens.sum(axis=1).mean()),
                 "mean_all_five_input_tokens":float(np.mean([sum(s["usage"]["prompt_tokens"] for s in seq) for seq in rows])),
                 "mean_all_five_output_tokens":float(np.mean([sum(s["usage"]["completion_tokens"] for s in seq) for seq in rows]))}
            finals.append(rec)
            for r in range(config["rounds"]):
                low,high=ci(full[:,r])
                curves.append({"model":MODEL_NAMES[model],"arm":arm,"round":r,"calls":r+1,"tasks":n,
                     "success":int(full[:,r].sum()),"rate":float(full[:,r].mean()),"ci_low":low,"ci_high":high,
                     "diagnostic_rate":float(public[:,r].mean()),"hidden_rate":float(hidden[:,r].mean()),
                     "diagnostic_pass_hidden_fail":int((public[:,r]&~hidden[:,r]).sum()),
                     "ever_success_rate":float(ever[:,r].mean()),
                     "mean_cumulative_tokens":float(tokens[:,:r+1].sum(axis=1).mean())})
    contrasts=[]
    for model in config["models"]:
        for arm,baseline in [("counterexample","resample"),("counterexample","self_review"),
                             ("counterexample","pass_fail"),("pass_fail","self_review"),
                             ("self_review","resample")]:
            af,ap,_,_=matrices[model,arm]
            bf,bp,_,_=matrices[model,baseline]
            for policy in ("final","first_diagnostic_pass"):
                select=lambda f,p: f[:,-1] if policy=="final" else f[np.arange(n),np.where(p.any(axis=1),p.argmax(axis=1),f.shape[1]-1)]
                a=select(af,ap)
                b=select(bf,bp)
                d=a.astype(int)-b.astype(int)
                low,high=ci(d)
                contrasts.append({"model":MODEL_NAMES[model],"arm":arm,"baseline":baseline,"policy":policy,
                     "tasks":n,"arm_wins":int((a&~b).sum()),"baseline_wins":int((b&~a).sum()),
                     "delta_pp":float(d.mean()*100),"ci_low_pp":low*100,"ci_high_pp":high*100})
    pooled=[]
    for arm,baseline in [("counterexample","resample"),("counterexample","self_review"),("counterexample","pass_fail")]:
        for policy in ("final","first_diagnostic_pass"):
            differences=[]
            for model in config["models"]:
                af,ap,_,_=matrices[model,arm]
                bf,bp,_,_=matrices[model,baseline]
                select=lambda f,p: f[:,-1] if policy=="final" else f[np.arange(n),np.where(p.any(axis=1),p.argmax(axis=1),f.shape[1]-1)]
                differences.append(select(af,ap).astype(int)-select(bf,bp).astype(int))
            # Keep both models of a task together in every bootstrap draw.
            task_differences=np.mean(differences,axis=0)
            lo,hi=ci(task_differences)
            pooled.append({"arm":arm,"baseline":baseline,"policy":policy,"task_clusters":n,
                "model_task_pairs":n*len(config["models"]),"delta_pp":float(task_differences.mean()*100),
                "ci_low_pp":lo*100,"ci_high_pp":hi*100})
    # Concrete traces chosen by explicit outcome rules; these illustrate rather than estimate effects.
    for model in config["models"]:
        for category in ("feedback_repair","regression","diagnostic_hidden_gap"):
            arm="self_review" if category=="regression" else "counterexample"
            preferred=["HumanEval/102","HumanEval/127"] if category=="feedback_repair" else ["HumanEval/124","HumanEval/22"]
            ordered=[t for t in preferred if t in ids]+[t for t in ids if t not in preferred]
            for tid in ordered:
                seed=identity(model,tid,"seed",0)
                seq=samples[model,arm][ids.index(tid)]
                scores=[ev[r["record_id"]] for r in seq]
                chosen=None
                if category=="feedback_repair" and not scores[0]["full_pass"]:
                    chosen=next((i for i in range(1,len(seq)) if scores[i]["full_pass"] and not scores[i-1]["public"]["passed"]),None)
                elif category=="regression" and scores[0]["full_pass"]:
                    chosen=next((i for i in range(1,len(seq)) if not scores[i]["full_pass"]),None)
                elif category=="diagnostic_hidden_gap":
                    chosen=next((i for i in range(len(seq)) if scores[i]["public"]["passed"] and not scores[i]["hidden"]["passed"]),None)
                if chosen is not None:
                    examples.append({"category":category,"model":MODEL_NAMES[model],"task_id":tid,"arm":arm,
                        "prompt":tasks[tid]["prompt"],"round":chosen,
                        "before_code":seq[max(chosen-1,0)]["code"],"feedback":seq[chosen]["feedback"],
                        "after_code":seq[chosen]["code"],"before_score":scores[max(chosen-1,0)],"after_score":scores[chosen]})
                    break
    write_csv(processed/"features.csv",features)
    event_rows=[]
    event_source=records(out/"events.jsonl")
    for kind,expected_ids in [("api",set(required)-set(missing)),("test",set(required)-set(missing)),
                              ("edit",{rid for rid in required if rid in raw and raw[rid]["parent_id"]})]:
        seen={e["record_id"] for e in event_source if e["event_type"]==kind}
        if expected_ids-seen:
            raise ValueError("Missing recorded "+kind+" events")
        checks["verified_"+kind+"_events"]=len(expected_ids)
    for index,event in enumerate(event_source):
        model,tid,arm,r=event["record_id"].split("|")
        if tid not in ids:
            continue
        event_rows.append({"event_id":index,"timestamp":event["timestamp"],"event_type":event["event_type"],
            "model":MODEL_NAMES[model],"task_id":tid,"arm":arm,"round":int(r),
            "full_pass":event.get("full_pass"),"diagnostic_pass":event.get("public_pass"),
            "hidden_pass":event.get("hidden_pass"),"code_changed":event.get("code_changed"),
            "http_status":event.get("http_status"),
            "total_tokens":(event.get("usage") or {}).get("total_tokens")})
    write_csv(processed/"events.csv",event_rows)
    write_csv(report/"curves.csv",curves)
    write_csv(report/"contrasts.csv",contrasts)
    write_csv(report/"pooled-contrasts.csv",pooled)
    write_csv(report/"summary.csv",[{**r,"final_ci":json.dumps(r["final_ci"]),"net_gain_ci_pp":json.dumps(r["net_gain_ci_pp"])} for r in finals])
    repair_attempts=[]
    state_summary=[]
    for model in config["models"]:
        for arm in ARMS:
            full,public,hidden,_=matrices[model,arm]
            for group,mask in [("initially_correct",full[:,0]),("diagnostic_failure",~public[:,0]),
                               ("hidden_only_failure",public[:,0]&~hidden[:,0])]:
                state_summary.append({"model":MODEL_NAMES[model],"arm":arm,"initial_state":group,
                    "tasks":int(mask.sum()),"final_success":int(full[mask,-1].sum()),
                    "final_success_rate":float(full[mask,-1].mean()) if mask.any() else None,
                    "ever_success":int(np.maximum.accumulate(full,axis=1)[mask,-1].sum())})
            for r in range(1,config["rounds"]):
                failed=~public[:,r-1]
                source_rows=[rows[r] for rows in samples[model,arm]]
                previous_rows=[rows[r-1] for rows in samples[model,arm]]
                unchanged=np.array([a["code_sha256"]==b["code_sha256"] for a,b in zip(source_rows,previous_rows)])
                repair_attempts.append({"model":MODEL_NAMES[model],"arm":arm,"round":r,
                    "previous_diagnostic_failures":int(failed.sum()),
                    "unchanged_after_failure":int((failed&unchanged).sum()),
                    "diagnostic_fixed":int((failed&public[:,r]).sum()),
                    "full_fixed":int((failed&full[:,r]).sum()),
                    "previous_hidden_only_failures":int((public[:,r-1]&~hidden[:,r-1]).sum()),
                    "hidden_only_fixed":int((public[:,r-1]&~hidden[:,r-1]&full[:,r]).sum())})
    write_csv(report/"repair-attempts.csv",repair_attempts)
    write_csv(report/"initial-state-summary.csv",state_summary)
    blindspots=[]
    for model in config["models"]:
        for tid in ids:
            seed=ev[identity(model,tid,"seed",0)]
            if seed["public"]["passed"] and not seed["hidden"]["passed"]:
                t=tasks[tid]
                i=seed["hidden"]["first_failure"]["case_index"]
                blindspots.append({"model":MODEL_NAMES[model],"task_id":tid,"plus_case_index":i,
                    "failure_input_overlaps_base":t["plus_input"][i] in t["base_input"],
                    "final_success_by_arm":{a:ev[identity(model,tid,a,config["rounds"]-1)]["full_pass"] for a in ARMS}})
    dump(report/"blindspot-audit.json",{"conditions":blindspots,"count":len(blindspots),
         "first_failure_is_new_input":sum(not b["failure_input_overlaps_base"] for b in blindspots)})
    write_csv(report/"error-transitions.csv",[{"model":MODEL_NAMES[m],"arm":a,"round":r,"from":f,"to":t,"count":v} for (m,a,r,f,t),v in sorted(transitions.items())])
    dump(report/"examples.json",examples)
    dump(report/"results.json",{"scope":scope,"tasks":n,"summary":finals,"contrasts":contrasts,
                                "pooled_contrasts":pooled,"curves":curves})
    checks["physical_records_in_scope"]=sum(r["task_id"] in selected for r in raw.values())
    checks["logical_rows"]=len(features)
    checks["credential_pattern_matches"]=0
    dump(report/"integrity.json",{"timestamp":timestamp(),"complete":not missing,"scope":scope,"tasks":n,
         "expected_physical_responses":expected,"checks":dict(checks),"missing_count":len(missing),
         "dataset_sha256":plan["dataset_sha256"],"config_sha256":plan["config_sha256"],
         "bootstrap":config["bootstrap"],"raw_responses_sha256":sha((out/"responses.jsonl").read_bytes()),
         "evaluations_sha256":sha((out/"evaluations.jsonl").read_bytes())})
    lines=["# 代码多轮修复实验"+("：20 题试采" if args.pilot else "：完整结果"),"",
        f"HumanEval+ Mini v0.1.10，{n} 题 × 2 模型；同一初稿、四组、初稿加四次后续生成。",
        "主指标：当前版本同时通过诊断测试与额外隐藏测试。95% 区间按题目配对 bootstrap。", "",
        "| 模型 | 组别 | 初稿 | 第五版 | 修好 / 初错 | 改坏 / 初对 | 净增益 pp | 诊断通过即停止 | 五次平均 Token |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in finals:
        lines.append(f"| {r['model']} | {ZH[r['arm']]} | {r['initial_success']}/{n} | {r['final_success']}/{n} | {r['repaired']}/{r['initial_failures']} | {r['regressed']}/{r['initial_success']} | {r['net_gain_pp']:+.2f} [{r['net_gain_ci_pp'][0]:+.2f}, {r['net_gain_ci_pp'][1]:+.2f}] | {r['first_diagnostic_pass_success']}/{n} | {r['mean_all_five_tokens']:.0f} |")
    lines += ["","## 配对比较","","| 模型 | 对比 | 最后一版差值 pp（95% CI） | 净胜题数 |","|---|---|---:|---:|"]
    for r in contrasts:
        if r["policy"]=="final":
            lines.append(f"| {r['model']} | {ZH[r['arm']]} − {ZH[r['baseline']]} | {r['delta_pp']:+.2f} [{r['ci_low_pp']:+.2f}, {r['ci_high_pp']:+.2f}] | {r['arm_wins']} − {r['baseline_wins']} |")
    lines += ["","## 阅读口径","",
        "- 独立重抽组的第五版是第五个候选；累计曾成功率另列于 curves.csv，隐藏结果不能用于实际选择候选。",
        "- ‘诊断通过即停止’只使用可见诊断结果选版本；隐藏测试仍只用于最终计分。",
        "- 五轮固定采集即使诊断通过仍继续自查，便于观察回退；现实策略可在诊断通过时停止。",
        "- HumanEval+ Mini 是自包含函数题，新增数据与原 CodePromptEval 项目型题目分开汇总。",
        "- 上游 plus 中有 49 条输入与 base 重复，另有 1,058 个不同于 base 的新输入；保留上游用例，逐题联合通过计分，按题目计算区间。",
        "- 按请求次数配对，真实 Token 不同；输入历史的成本已计入。",
        "- 具体案例见 examples.md；完整性检查见 integrity.json。", ""]
    (report/"findings.md").write_text("\n".join(lines))
    case_lines=["# 实际修复轨迹","","以下按结果规则挑选，用于说明现象；总体效应以全量统计为准。",""]
    for e in examples:
        case_lines += [f"## {e['model']} · {e['task_id']} · {e['category']}","","```python",e['prompt'],"```","",
             "修改前：","```python",e['before_code'],"```","","实际传回的反馈：","```text",e['feedback'] or '初稿，无反馈',"```","",
             "修改后：","```python",e['after_code'],"```","",
             f"同时通过诊断与隐藏：{e['before_score']['full_pass']} → {e['after_score']['full_pass']}。",
             f"修改后诊断通过：{e['after_score']['public']['passed']}；隐藏通过：{e['after_score']['hidden']['passed']}。",""]
    (report/"examples.md").write_text("\n".join(case_lines))
    plot(report,config,curves,finals)
    print(json.dumps({"report":str(report),"tasks":n,"checks":dict(checks),"summary":finals},ensure_ascii=False))


def plot(report,config,curves,finals):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font=Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")
    if font.exists():
        font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.family":"Times New Roman","font.size":11,"svg.fonttype":"none",
        "axes.spines.top":False,"axes.spines.right":False,"axes.linewidth":.7,
        "xtick.major.width":.7,"ytick.major.width":.7,"figure.facecolor":"white","axes.labelsize":12})
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.8),sharey=True)
    styles={"resample":("--","s"),"self_review":(":","D"),"pass_fail":("-.","^"),"counterexample":("-","o")}
    lower=max(0,int((min(r["rate"] for r in curves)*100-3)//5)*5)
    upper=min(100,int(np.ceil((max(r["rate"] for r in curves)*100+3)/5))*5)
    for ax,model in zip(axes,config["models"]):
        for arm in ARMS:
            rows=[r for r in curves if r["model"]==MODEL_NAMES[model] and r["arm"]==arm]
            line,marker=styles[arm]
            ax.plot([r["calls"] for r in rows],[r["rate"]*100 for r in rows],
                    marker=marker,ms=4.5,lw=1.6,linestyle=line,markerfacecolor="white",
                    markeredgewidth=1.1,color=COLORS[arm],label=LABELS[arm])
        ax.set_title(MODEL_NAMES[model],fontweight="bold",pad=12)
        ax.set_xticks([1,2,3,4,5])
        ax.set_xlabel("Candidate generation (1 = initial)")
        ax.set_ylim(lower,upper)
        ax.set_yticks(np.arange(lower,upper+1,5))
        ax.grid(axis="y",color="#E5E7E9",lw=.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Full test pass rate (%)")
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.04))
    fig.subplots_adjust(bottom=.25,wspace=.12,left=.07,right=.98,top=.88)
    for ext in ("svg","png","pdf"):
        fig.savefig(report/("01-five-rounds."+ext),dpi=220,bbox_inches="tight")
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.5),sharex=True)
    repair_xlim=(-max(r["regressed"]/r["tasks"]*100 for r in finals)-2,
                  max(r["repaired"]/r["tasks"]*100 for r in finals)+2)
    for ax,model in zip(axes,config["models"]):
        rows=[r for r in finals if r["model"]==MODEL_NAMES[model]]
        y=np.arange(len(rows))
        ax.barh(y,[r["repaired"]/r["tasks"]*100 for r in rows],color="#40768E",height=.5,label="Initially wrong → correct")
        ax.barh(y,[-r["regressed"]/r["tasks"]*100 for r in rows],color="#A84C58",height=.5,label="Initially correct → wrong")
        for i,r in enumerate(rows):
            gain=r["repaired"]/r["tasks"]*100
            loss=r["regressed"]/r["tasks"]*100
            if gain:
                ax.text(gain+.2,i,f"+{gain:.1f}",va="center",ha="left",fontsize=10)
            if loss:
                ax.text(-loss-.2,i,f"−{loss:.1f}",va="center",ha="right",fontsize=10)
            if not gain and not loss:
                ax.text(.2,i,"0",va="center",fontsize=10)
        ax.axvline(0,color="#4D5258",lw=.7)
        ax.set_xlim(*repair_xlim)
        ax.set_yticks(y,[LABELS[r["arm"]] for r in rows],fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel("Contribution to pass-rate change (pp)")
        ax.set_title(MODEL_NAMES[model],fontweight="bold",pad=10)
        ax.grid(axis="x",color="#E5E7E9",lw=.5)
        ax.set_axisbelow(True)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.03))
    fig.subplots_adjust(wspace=.75,bottom=.25,left=.19,right=.98,top=.88)
    for ext in ("svg","png","pdf"):
        fig.savefig(report/("02-repair-and-regression."+ext),dpi=220,bbox_inches="tight")
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.5),sharey=True)
    for ax,model in zip(axes,config["models"]):
        rows=[r for r in finals if r["model"]==MODEL_NAMES[model]]
        x=np.arange(4)
        inputs=np.array([r["mean_all_five_input_tokens"] for r in rows])/1000
        outputs=np.array([r["mean_all_five_output_tokens"] for r in rows])/1000
        ax.bar(x,inputs,width=.55,color="#A6B5C0",label="Input / history")
        ax.bar(x,outputs,bottom=inputs,width=.55,color="#40768E",label="Output")
        for i,total in enumerate(inputs+outputs):
            ax.text(i,total+.08,f"{total:.2f}",ha="center",va="bottom",fontsize=10)
        ax.set_xticks(x,["Resample","Self-review","Pass / fail","Counterexample"],rotation=18,ha="right",fontsize=10)
        ax.set_title(MODEL_NAMES[model],fontweight="bold",pad=10)
        ax.set_axisbelow(True)
        ax.grid(axis="y",color="#E5E7E9",lw=.5)
        ax.margins(y=.2)
    axes[0].set_ylabel("Mean tokens per task, five calls (×1,000)")
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.08))
    fig.subplots_adjust(bottom=.28,wspace=.15,left=.08,right=.98,top=.88)
    for ext in ("svg","png","pdf"):
        fig.savefig(report/("03-token-cost."+ext),dpi=220,bbox_inches="tight")
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.9),sharey=True,sharex=True)
    for ax,model in zip(axes,config["models"]):
        rows=[r for r in finals if r["model"]==MODEL_NAMES[model]]
        for r in rows:
            color=COLORS[r["arm"]]
            xs=[r["mean_all_five_tokens"]/1000,r["stop_policy_mean_tokens"]/1000]
            ys=[r["final_rate"]*100,r["first_diagnostic_pass_rate"]*100]
            ax.plot(xs,ys,color=color,lw=1.1,alpha=.75)
            ax.scatter(xs[0],ys[0],s=34,marker="s",facecolors="white",edgecolors=color,linewidths=1.2,zorder=3)
            ax.scatter(xs[1],ys[1],s=34,marker="o",color=color,zorder=3,label=LABELS[r["arm"]])
        ax.set_title(MODEL_NAMES[model],fontweight="bold",pad=12)
        ax.set_ylim(lower,upper)
        ax.set_yticks(np.arange(lower,upper+1,5))
        ax.set_xlim(0,6.6)
        ax.set_xticks([0,1,2,3,4,5,6])
        ax.set_xlabel("Mean tokens per task (×1,000)")
        ax.grid(color="#E5E7E9",lw=.5)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("Full test pass rate (%)")
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",ncol=2,frameon=False,bbox_to_anchor=(.5,-.08))
    fig.text(.5,.92,"Filled circle: first diagnostic pass   ·   Open square: fifth candidate",ha="center",fontsize=10)
    fig.subplots_adjust(bottom=.24,wspace=.12,left=.07,right=.98,top=.82)
    for ext in ("svg","png","pdf"):
        fig.savefig(report/("04-stopping-policy."+ext),dpi=220,bbox_inches="tight")
    plt.close(fig)


if __name__=="__main__":
    main()
