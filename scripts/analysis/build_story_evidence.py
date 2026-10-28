"""Prepare local classroom narratives: saved examples, descriptive fits and SVGs.

This script reads saved data only; it never calls a model or executes generated code.
"""
from pathlib import Path
import csv
import gzip
import hashlib
import json
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT = ROOT / "reports" / "story"
DEEP = ROOT / "reports" / "prompt_variants"
NAMES = {"deepseek": "DeepSeek", "hy4": "HY4", "qwen": "Qwen2.5", "qwen3": "Qwen3"}
COLORS = {"deepseek": "#355F8C", "hy4": "#A67438", "qwen": "#84709F", "qwen3": "#287D76"}


def table(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def fit_profiles():
    rows = table(ROOT / "reports/baseline/reasoning_prompt_summary.csv")
    output = []
    for model in NAMES:
        for task in ["gsm8k", "math500", "mmlu"]:
            for scope in ["all31", "WordLimit"]:
                a = [r for r in rows if r["model_id"] == model and r["benchmark"] == task
                     and (scope == "all31" or r["prompt_id"].startswith("WordLimit("))]
                x = np.log([float(r["mean_output_tokens"]) for r in a])
                y = np.array([float(r["current_score_rate"]) * 100 for r in a])
                design = np.c_[np.ones(len(a)), x]
                intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
                r2 = 1 - np.sum((y - design @ [intercept, slope]) ** 2) / np.sum((y - y.mean()) ** 2)
                output.append({"model": model, "task": task, "scope": scope, "points": len(a),
                               "intercept": intercept, "log_token_slope": slope, "in_sample_r2": r2})
    write_csv("log-fit-diagnostics.csv", output)
    chinese = []
    for model in NAMES:
        for task in ["gsm8k", "math500", "mmlu"]:
            a = next(r for r in rows if r["model_id"] == model and r["benchmark"] == task and r["prompt_id"] == "ChineseCoT")
            b = next(r for r in rows if r["model_id"] == model and r["benchmark"] == task and r["prompt_id"] == "DefaultCoT")
            chinese.append({"model": model, "task": task,
                            "default_tokens": float(b["mean_output_tokens"]), "chinese_tokens": float(a["mean_output_tokens"]),
                            "token_saving_pct": (1-float(a["mean_output_tokens"])/float(b["mean_output_tokens"]))*100,
                            "default_score_pct": float(b["current_score_rate"])*100,
                            "chinese_score_pct": float(a["current_score_rate"])*100,
                            "score_difference_pp": (float(a["current_score_rate"])-float(b["current_score_rate"]))*100,
                            "default_truncation_pct": float(b["truncation_rate"])*100,
                            "chinese_truncation_pct": float(a["truncation_rate"])*100})
    write_csv("chinese-template-comparison.csv", chinese)
    return rows, output


def extract_examples():
    zids = {"Z006587", "Z006787", "Z012672", "Z012872", "Z015404", "Z015804",
            "Z049851", "Z054851", "Z049873", "Z054873"}
    examples = {"reasoning": [], "positions": [], "code": [], "prompt_specs": {}}
    with gzip.open(ROOT / "data/processed/reasoning/responses_clean.csv.gz", "rt") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            rid = f"Z{i:06d}"
            if r["prompt_id"] in ["DefaultCoT", "BeConcise", "ChineseCoT", "CharLimit(10)", "CharLimit(100)"]:
                examples["prompt_specs"][r["prompt_id"]] = r["prompt_text"]
            if rid in zids:
                examples["reasoning"].append({"id": rid, "model": r["model_id"], "task": r["benchmark"],
                                        "prompt": r["prompt_id"], "question": r["question_text"],
                                        "gold": r["gold_answer"], "response": r["response_text"],
                                        "tokens": int(r["output_tokens"]), "score": int(r["score_current"]),
                                        "finish": r["finish_reason"], "extracted_answer": r["extracted_answer"],
                                        "grading_status": r["grading_status"]})
    aliases = {}
    with gzip.open(ROOT / "data/processed/document_qa/responses_clean.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            if r["question_id"] not in aliases:
                aliases[r["question_id"]] = f"C{len(aliases)+1:03d}"
    scores = [r for r in table_gzip(ROOT / "reports/document_positions/anonymous-scores.csv.gz") if r["model"] == "Qwen/Qwen2.5-7B-Instruct"]
    score_lookup = {(r["question"], int(r["position"])): int(r["final_contains"]) for r in scores}
    with (ROOT / "data/raw/document_positions/no_cot_20_documents/raw_responses.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            alias = aliases[r["question_id"]]
            if r["model"] == "Qwen/Qwen2.5-7B-Instruct" and alias in ["C007", "C001"] and r["gold_position"] in [1, 10, 20]:
                examples["positions"].append({"question_alias": alias, "question": r["question"],
                                              "gold_aliases": r["answers"], "position": r["gold_position"],
                                              "response": r["response"]["choices"][0]["message"]["content"],
                                              "final_contains": score_lookup[alias, r["gold_position"]]})
    source = ROOT / "data/raw/code_generation"
    scores = table_gzip(source / "source_scores/scores.csv.gz")
    taskmap = {q: f"T{i+1:03d}" for i, q in enumerate(dict.fromkeys(r["task_id"] for r in scores))}
    records = {(r["analysis_model"], r["task_id"], r["analysis_prompt_id"], int(r["analysis_turn_id"])): (i, r)
               for i, r in enumerate(scores, 1)}
    examples["code_sample_patterns"] = []
    for m in ["deepseek-flash", "qwen2.5-7b-instruct-cloud", "qwen3-8b-cloud"]:
        a = [r for r in scores if taskmap[r["task_id"]] == "T005" and r["analysis_model"] == m
             and r["analysis_prompt_id"] == "DefaultCoT"]
        examples["code_sample_patterns"].append({"question": "T005", "model": m,
            "passed_samples": [int(r["analysis_passed"] == "True") for r in sorted(a, key=lambda x:int(x["analysis_turn_id"]))]})
    for filename, model in [("raw_deepseek-flash.jsonl.gz", "deepseek-flash"),
                            ("raw_qwen3-8b-cloud.jsonl.gz", "qwen3-8b-cloud")]:
        with gzip.open(source / filename, "rt") as f:
            for line in f:
                r = json.loads(line)
                if r["function_name"] == "is_none_string" and r["turn_id"] == 1 and r["compression_prompt_id"] in ["NoCoT", "DefaultCoT"]:
                    i, score = records[model, r["task_id"], r["compression_prompt_id"], r["turn_id"]]
                    examples["code"].append({"id": f"Y{i:06d}", "question_alias": taskmap[r["task_id"]],
                                             "model": model, "prompt": r["compression_prompt_id"],
                                             "question": r["zero_shot_prompt"], "function": r["function_name"],
                                             "response": r["complete_response"], "tokens": r["output_tokens"],
                                             "passed": score["analysis_passed"] == "True",
                                             "error": score["analysis_error_category"]})
    examples["code_prompt_specs"] = json.loads((source / "prompts.json").read_text())
    (OUT / "saved-examples.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 课堂案例原文", "", "从保存结果摘录，未重写模型回答。匿名 ID 对应现有特征快照。", ""]
    for r in examples["reasoning"]:
        lines += [f"## {r['id']} · {r['model']} / {r['task']} / {r['prompt']}", "",
                  f"问题：{r['question']}", "", f"标准答案：`{r['gold']}`；Token：{r['tokens']}；"
                  f"源评分：{r['score']}；结束：`{r['finish']}`。", "", "~~~text", r["response"], "~~~", ""]
    for r in examples["positions"]:
        lines += [f"## {r['question_alias']} · 证据第 {r['position']} 位", "", r["question"], "",
                  f"标准别名：{', '.join(r['gold_aliases'])}；最终包含：{r['final_contains']}。", "",
                  "~~~text", r["response"], "~~~", ""]
    for r in examples["code"]:
        lines += [f"## {r['id']} · {r['model']} / {r['prompt']}", "", r["question"], "",
                  f"通过：{r['passed']}；错误类别：{r['error']}。", "", "~~~text", r["response"], "~~~", ""]
    (OUT / "案例原文.md").write_text("\n".join(lines))


def table_gzip(path):
    with gzip.open(path, "rt") as f:
        return list(csv.DictReader(f))


def style():
    plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11, "axes.labelsize": 12,
                         "axes.titlesize": 14, "svg.fonttype": "none", "axes.linewidth": .7,
                         "xtick.direction": "out", "ytick.direction": "out", "figure.facecolor": "white"})


def clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E4E7EB", lw=.5)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / (name + ".svg"), bbox_inches="tight")
    fig.savefig(OUT / (name + ".png"), bbox_inches="tight", dpi=210)
    plt.close(fig)


def figures(profiles, fits):
    style()
    # A measured budget family followed by the paired intervention.
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.2), gridspec_kw={"width_ratios": [1, 1.12]})
    ax = axes[0]
    a = [r for r in profiles if r["model_id"] == "qwen" and r["benchmark"] == "gsm8k" and r["prompt_id"].startswith("WordLimit(")]
    a.sort(key=lambda r:float(r["mean_output_tokens"]))
    x = [float(r["mean_output_tokens"]) for r in a]; y = [float(r["current_score_rate"]) * 100 for r in a]
    fit = next(r for r in fits if r["model"] == "qwen" and r["task"] == "gsm8k" and r["scope"] == "WordLimit")
    xx = np.linspace(min(x), max(x), 250)
    ax.plot(xx, fit["intercept"] + fit["log_token_slope"] * np.log(xx), color="#8B969F", ls="--", lw=1.2)
    ax.scatter(x, y, s=30, color="#73808C", label="Seven word-limit settings", zorder=3)
    for p, color, marker in [("DefaultCoT", "#355F8C", "s"), ("BeConcise", "#B05A3E", "D")]:
        r = next(r for r in profiles if r["model_id"] == "qwen" and r["benchmark"] == "gsm8k" and r["prompt_id"] == p)
        px, py = float(r["mean_output_tokens"]), float(r["current_score_rate"]) * 100
        ax.scatter(px, py, s=55, marker=marker, color=color, zorder=4)
        ax.annotate(p, (px, py), xytext=(0, -19 if p == "DefaultCoT" else 8), textcoords="offset points", ha="center", color=color)
    ax.text(.04, .82, f"Word-limit fit: $R^2$ = {fit['in_sample_r2']:.2f}", transform=ax.transAxes, color="#4D5963")
    ax.set(xlabel="Mean returned tokens", ylabel="Source score (%)", xlim=(-5, 285), ylim=(0, 105), title="(a) Budget trend and concise output")
    clean(ax)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax = axes[1]
    z = table(DEEP / "reasoning-paired-contrasts.csv")
    points = [{"model": r["model"], "task": r["task"], "saving": float(r["token_saving_pct"]), "delta": float(r["score_difference_pp"]), "direction": "Reasoning / MCQA"}
              for r in z if r["first"] == "BeConcise"]
    f = table(ROOT / "reports/baseline/document_qa_prompt_summary.csv")
    for m, source in [("qwen", "Qwen/Qwen2.5-7B-Instruct"), ("qwen3", "Qwen/Qwen3-8B")]:
        a = next(r for r in f if r["model_id"] == source and r["prompt_id"] == "BeConcise")
        b = next(r for r in f if r["model_id"] == source and r["prompt_id"] == "DefaultCoT")
        points.append({"model": m, "task": "Document QA", "direction": "Document QA", "saving": (1-float(a['mean_output_tokens'])/float(b['mean_output_tokens']))*100,
                       "delta": (float(a['final_contains'])-float(b['final_contains']))*100})
    c = table(ROOT / "reports/code_generation/conditions.csv")
    for m in ["deepseek", "qwen", "qwen3"]:
        a = next(r for r in c if r["model"] == m and r["prompt"] == "BeConcise")
        b = next(r for r in c if r["model"] == m and r["prompt"] == "DefaultCoT")
        points.append({"model":m,"task":"Code","direction":"Code","saving":(1-float(a['mean_output_tokens'])/float(b['mean_output_tokens']))*100,
                       "delta":(float(a['pass_1'])-float(b['pass_1']))*100})
    write_csv("concise-cross-task-points.csv", points)
    markers = {"Reasoning / MCQA": "o", "Document QA": "s", "Code": "^"}
    for r in points:
        ax.scatter(r["saving"], r["delta"], color=COLORS[r["model"]], marker=markers[r["direction"]], s=55, edgecolor="white", lw=.5)
    ax.axhline(0, color="#727E88", lw=.8, ls="--")
    ax.set(xlabel="Mean token reduction (%)", ylabel="Paired score difference (pp)", xlim=(0, 64), ylim=(-2.8, 14), title="(b) BeConcise vs. DefaultCoT")
    for label, marker in markers.items():
        ax.scatter([], [], color="#4B5862", marker=marker, s=38, label=label)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    ax.text(.03,.95,"17 groups; all use fewer tokens",va="top",transform=ax.transAxes,fontsize=10)
    clean(ax)
    handles=[plt.Line2D([],[],marker='o',lw=0,color=COLORS[m],label=NAMES[m]) for m in NAMES]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,-.025),ncol=4,frameon=False,fontsize=10)
    fig.tight_layout(w_pad=3,rect=(0,.07,1,1))
    save(fig, "01-budget-and-concise")

    # All seven actual WordLimit settings; no invented intermediate observations.
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
    limits = [1, 5, 10, 15, 25, 50, 100]
    for ax, task in zip(axes, ["gsm8k", "math500"]):
        for m in NAMES:
            a = [next(r for r in profiles if r["model_id"]==m and r["benchmark"]==task and r["prompt_id"]==f"WordLimit({n})") for n in limits]
            ax.plot(limits, [float(r["mean_output_tokens"]) for r in a], marker="o", ms=4, lw=1.5, color=COLORS[m], label=NAMES[m])
        ax.set_xscale("log")
        ax.set_xticks(limits, [str(n) for n in limits])
        ax.set(xlabel="Requested word limit (log-spaced axis)", ylabel="Mean returned tokens", title=task.upper(), ylim=(0,None))
        clean(ax)
    axes[1].legend(frameon=False, fontsize=9)
    fig.tight_layout(w_pad=2)
    save(fig,"02-extreme-limit-rebound")

    fig, axes = plt.subplots(1, 2, figsize=(10.6, 3.8))
    pos = table(DEEP / "document_qa-model-gain-by-position.csv")
    for ax, docs in zip(axes, ["10", "20"]):
        r=next(r for r in pos if r['scope']=='main19' and r['metric']=='final_contains' and r['documents']==docs)
        for m in ["qwen","qwen3"]:
            y=[float(r[f'{m}_{p}_pct']) for p in ['front','middle','back']]
            ax.plot([0,1,2],y,color=COLORS[m],marker='o',lw=1.7,label=NAMES[m])
        ax.set(xticks=[0,1,2],xticklabels=['Front','Middle','Back'],ylim=(48,72),ylabel='Final-answer containment (%)',title=f'{docs} documents · 19 regular prompts')
        clean(ax)
    axes[1].legend(frameon=False)
    fig.tight_layout(w_pad=2)
    save(fig,'03-position-model-gain')

    fig, axes=plt.subplots(1,2,figsize=(10.7,3.9))
    lv=table(DEEP/'code-dependency-levels.csv')
    for ax,level in zip(axes,['self_contained','project_runnable']):
        for i,m in enumerate(['deepseek','qwen','qwen3']):
            r=next(r for r in lv if r['scope']=='all31' and r['level']==level and r['model']==m)
            values=[float(r['pass1_pct']),int(r['ever_solved_questions'])/int(r['questions'])*100]
            ax.plot([0,1],values,color=COLORS[m],marker='o',lw=1.6,label=NAMES[m])
        ax.set(xticks=[0,1],xticklabels=['Mean Pass@1','Ever passed in 155 samples'],xlim=(-.15,1.15),ylim=(0,90),ylabel='Tasks / responses passing (%)',title='30 standalone tasks' if level=='self_contained' else '21 project-dependent tasks')
        clean(ax)
    axes[1].legend(frameon=False,fontsize=9)
    fig.tight_layout(w_pad=2)
    save(fig,'04-code-reliability-coverage')

    fig,axes=plt.subplots(1,2,figsize=(10.8,3.9))
    code=table(ROOT/'reports/code_generation/conditions.csv')
    r=next(r for r in code if r['model']=='deepseek' and r['prompt']=='DefaultCoT')
    values=[float(r[f'pass_{k}'])*100 for k in range(1,6)]
    axes[0].plot(range(1,6),values,color=COLORS['deepseek'],marker='o',lw=1.7)
    axes[0].set(xticks=range(1,6),xlabel='Independent samples, k',ylabel='Pass@k (%)',
                title='DeepSeek · DefaultCoT · 193 tasks',ylim=(27,39))
    for k,value in enumerate(values,1):
        axes[0].annotate(f'{value:.2f}',(k,value),xytext=(0,8),textcoords='offset points',ha='center',fontsize=10)
    clean(axes[0])
    div=table(DEEP/'code-prompt-diversity.csv')
    for i,m in enumerate(['deepseek','qwen','qwen3']):
        r=next(r for r in div if r['model']==m and r['scope']=='regular6_without_NoCoT')
        a,b=float(r['same_prompt_five_pct']),float(r['distinct_prompts_five_pct'])
        axes[1].plot([a,b],[i,i],color=COLORS[m],lw=2)
        axes[1].scatter([a],[i],marker='o',s=44,facecolor='white',edgecolor=COLORS[m],zorder=3)
        axes[1].scatter([b],[i],marker='o',s=44,color=COLORS[m],zorder=3)
        axes[1].text(a-.15,i-.18,f'{a:.2f}',ha='right',fontsize=10)
        axes[1].text(b+.15,i+.05,f'{b:.2f}',ha='left',fontsize=10)
    axes[1].set(yticks=[0,1,2],yticklabels=['DeepSeek','Qwen2.5','Qwen3'],xlabel='Expected success coverage (%)',
                title='Five calls · six regular prompts',xlim=(30.5,40.5),ylim=(-.65,2.65))
    axes[1].scatter([],[],s=35,facecolor='white',edgecolor='#4B5862',label='One random prompt, five samples')
    axes[1].scatter([],[],s=35,color='#4B5862',label='Five distinct prompts, one each')
    axes[1].legend(frameon=False,fontsize=8.8,loc='upper left')
    axes[1].invert_yaxis()
    clean(axes[1])
    fig.tight_layout(w_pad=3)
    save(fig,'05-sampling-and-prompt-diversity')

    # Language-template effects are shown as their own evidence panel.
    language=table(OUT/'chinese-template-comparison.csv')
    fig,axes=plt.subplots(1,3,figsize=(11.8,4.2),sharey=True)
    specs=[('tokens','Mean returned tokens',(0,620)),
           ('score_pct','Source score (%)',(50,92)),
           ('truncation_pct','Truncated responses (%)',(0,40))]
    for ax,(key,label,limits) in zip(axes,specs):
        for i,m in enumerate(NAMES):
            r=next(r for r in language if r['model']==m and r['task']=='math500')
            a,b=float(r[f'default_{key}']),float(r[f'chinese_{key}'])
            ax.plot([a,b],[i,i],color='#A3ADB5',lw=1.5,zorder=1)
            ax.scatter(a,i,color='#355F8C',s=40,zorder=3)
            ax.scatter(b,i,color='#B05A3E',s=40,zorder=3)
            for value,dy,color in [(a,-13,'#355F8C'),(b,11,'#B05A3E')]:
                ax.annotate(f'{value:.1f}',(value,i),xytext=(0,dy),textcoords='offset points',ha='center',color=color,fontsize=9)
        ax.set(xlabel=label,xlim=limits,yticks=range(4),yticklabels=[NAMES[m] for m in NAMES],ylim=(3.5,-.5))
        clean(ax)
    fig.suptitle('MATH500: Chinese template reduces tokens; three of four models score higher',fontsize=15,y=1.015)
    handles=[plt.Line2D([],[],marker='o',lw=0,color=c,label=l) for c,l in [('#355F8C','DefaultCoT'),('#B05A3E','ChineseCoT')]]
    fig.legend(handles=handles,loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,-.015))
    fig.tight_layout(w_pad=2,rect=(0,.06,1,1))
    save(fig,'06-chinese-math')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    profiles,fits=fit_profiles()
    extract_examples()
    figures(profiles,fits)
    inputs=[ROOT/'app/data/features.json.gz',ROOT/'reports/baseline/reasoning_prompt_summary.csv',
            DEEP/'analysis-manifest.json',ROOT/'reports/document_positions/analysis-manifest.json']
    manifest={'date':'2026-10-26','api_calls':0,'generated_code_executed':False,
              'fit':'Unweighted descriptive OLS: source_score_pct = a + b * ln(mean returned tokens). In-sample fit, not validation.',
              'examples':'Saved model outputs; examples intentionally chosen to illustrate mechanisms. Aggregate evidence uses all stated conditions.',
              'inputs_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    (OUT/'evidence-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'directory':str(OUT),'fits':len(fits),'figures':6,'api_calls':0},ensure_ascii=False))


if __name__=='__main__':
    main()
