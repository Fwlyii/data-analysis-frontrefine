#!/usr/bin/env python3
"""Offline scoring and figures for a frozen position-extension batch. No API calls."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

import numpy as np

from official_metrics import best_subspan_em, normalize_answer
from scoring_helpers import grade

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
METRICS = ["final_contains", "strict_final_em", "paper_firstline", "full_response_contains"]
MODEL_NAMES = {"Qwen/Qwen2.5-7B-Instruct": "Qwen2.5-7B-Instruct", "Qwen/Qwen3-8B": "Qwen3-8B"}
COLORS = {"Qwen/Qwen2.5-7B-Instruct": "#315B8A", "Qwen/Qwen3-8B": "#208378"}


def truth(value):
    return str(value).lower() in ["1", "1.0", "true"]


def summarize_record(record, question_aliases):
    g = grade(record)
    text, extracted = g["text"], g["extracted_answer"]
    if extracted == "":
        marker = list(re.finditer(r"FINAL\s+ANSWER\s*:\s*", text, re.I))[-1]
        before = text[:marker.start()].strip()
        if "\n" not in before and len(before.split()) <= 30:
            extracted = before
    aliases = record["answers"]
    usage = record["response"].get("usage", {})
    details = usage.get("completion_tokens_details") or {}
    return {"batch_id": record["batch_id"], "model": record["model"],
            "question": question_aliases[record["question_id"]],
            "position": record["gold_position"],
            "final_contains": int(best_subspan_em(extracted or "", aliases)),
            "strict_final_em": int(any(normalize_answer(extracted) == normalize_answer(a) for a in aliases)) if extracted is not None else 0,
            "paper_firstline": int(best_subspan_em(text.split("\n")[0].strip(), aliases)),
            "full_response_contains": int(best_subspan_em(text, aliases)),
            "truncated": int(g["truncated"]), "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"), "reasoning_tokens": details.get("reasoning_tokens"),
            "reasoning_content_nonempty": int(bool(record["response"]["choices"][0]["message"].get("reasoning_content"))),
            "latency_s": record["latency_s"], "credential_slot": record["credential_slot"]}


def write_csv(path, rows):
    if not rows:
        return
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def paired_stat(vector, indices):
    means = vector[indices].mean(axis=1)
    lo, hi = np.quantile(means, [.025, .975])
    return {"difference_pp": float(vector.mean()*100), "ci_low_pp": float(lo*100), "ci_high_pp": float(hi*100)}


def figures(summary, out, config):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    font = "Times New Roman" if "Times New Roman" in installed else "DejaVu Serif"
    plt.rcParams.update({"font.family": font, "font.size": 12, "axes.labelsize": 14,
                         "axes.titlesize": 16, "svg.fonttype": "none", "axes.linewidth": .8,
                         "xtick.direction": "out", "ytick.direction": "out"})
    fig, axes = plt.subplots(1, len(config["models"]), figsize=(6.4*len(config["models"]), 4.8), sharex=True, sharey=True, squeeze=False)
    axes = axes[0]
    rates = [r for r in summary if r["metric"] == config["primary_metric"]]
    low = max(0, np.floor(min(r["ci_low"]*100 for r in rates)/5)*5-5)
    high = min(100, np.ceil(max(r["ci_high"]*100 for r in rates)/5)*5+5)
    for ax, model in zip(axes, config["models"]):
        group = sorted((r for r in rates if r["model"] == model), key=lambda r:r["position"])
        x = [r["position"] for r in group]
        y = np.array([r["rate"] for r in group])*100
        lo = np.array([r["ci_low"] for r in group])*100
        hi = np.array([r["ci_high"] for r in group])*100
        color = COLORS[model]
        ax.fill_between(x, lo, hi, color=color, alpha=.095, linewidth=0)
        ax.errorbar(x, y, yerr=[y-lo, hi-y], color=color, lw=1.8, marker="o", markersize=5.5,
                    markerfacecolor="white", markeredgewidth=1.5, capsize=2.2, elinewidth=.7)
        for pos, rate, upper in zip(x, y, hi):
            ax.annotate(f"{rate:.1f}", (pos, upper), xytext=(0, 6), textcoords="offset points",
                        ha="center", color=color, fontsize=10.5)
        ax.set_title(MODEL_NAMES[model], pad=15, loc="left")
        ax.set_xticks(config["positions_1_based"])
        ax.set_xlim(.4, 20.6)
        ax.set_ylim(low, high)
        ax.set_xlabel("Position of the answer-bearing document")
        ax.grid(axis="y", color="#DEE3E8", lw=.55)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Final-answer containment (%)")
    fig.subplots_adjust(left=.11 if len(config["models"])==1 else .075, right=.985, bottom=.26, top=.85, wspace=.12)
    fig.text(.075, .975, "Evidence position in a 20-document context", fontsize=19, va="top")
    fig.text(.075, .105, "200 paired questions per position; 20 documents; NoCoT.", fontsize=10.5, color="#4C535B")
    fig.text(.075, .06, "Error bars and shading: pointwise question-bootstrap 95% intervals.", fontsize=9.7, color="#4C535B")
    fig.text(.075, .015, "Lines connect the nine measured positions; no smoothing.", fontsize=9.7, color="#4C535B")
    fig.savefig(out/"position-profile.svg")
    fig.savefig(out/"position-profile.png", dpi=240)
    plt.close(fig)


def analyze(config_path, output, selected_model=None):
    config = json.loads(config_path.read_text())
    frozen_config_sha256 = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    original_models = list(config["models"])
    if selected_model:
        if selected_model not in original_models:
            raise ValueError("Selected model is absent from the frozen experiment")
        config["models"] = [selected_model]
    batch = ROOT/config["raw_output"]
    source = (batch/"raw_responses.jsonl").read_bytes()
    if not source.endswith(b"\n"):
        raise ValueError("Raw output ends in an incomplete record")
    all_records = [json.loads(line) for line in source.splitlines()]
    records = [r for r in all_records if r["model"] in config["models"]]
    expected = config["questions"]*len(config["positions_1_based"])*len(config["prompts"])*len(config["models"])
    if len(records) != expected:
        raise ValueError(f"Batch incomplete: {len(records)}/{expected}; final report not produced")
    identities = {(r["model"],r["question_id"],r["gold_position"],r["prompt_id"]) for r in records}
    if len(identities) != expected:
        raise ValueError("Duplicate or missing experimental conditions")
    with gzip.open(batch/"scenarios.jsonl.gz","rb") as handle:
        scenario_source=handle.read()
    scenarios={r["scenario_id"]:r for line in scenario_source.splitlines() if (r:=json.loads(line))}
    for record in records:
        scenario=scenarios[record["scenario_id"]]
        request=record["request"]
        if any(record[key]!=scenario[key] for key in ["question_id","gold_position","document_count","prompt_id","answers","prompt_sha256"]):
            raise ValueError("Saved response metadata differs from its prepared scenario")
        if request["messages"]!=[{"role":"user","content":scenario["prompt_text"]}]:
            raise ValueError("Saved request text differs from its prepared scenario")
        if request["model"]!=record["model"] or request["temperature"]!=config["temperature"] or request["max_tokens"]!=config["max_tokens"]:
            raise ValueError("Saved generation settings differ from the frozen protocol")
        if "Qwen3" in record["model"] and request.get("enable_thinking")!=config["qwen3_enable_thinking"]:
            raise ValueError("Saved Qwen3 thinking setting differs from the frozen protocol")
        if record["response"].get("model")!=record["model"]:
            raise ValueError("Provider returned a different model identity")
    # Reuse the canonical C001... question identities from the existing
    # system/export_baseline_features.py encounter order, rather than invent a new map.
    question_aliases, old = {}, {}
    with gzip.open(ROOT/"data/processed/document_qa/responses_clean.csv.gz","rt",encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            source_question = r["question_id"]
            if source_question not in question_aliases:
                question_aliases[source_question] = f"C{len(question_aliases)+1:03d}"
            if r["document_count"]=="20" and r["prompt_id"]=="NoCoT":
                old[r["model_id"],question_aliases[source_question],int(r["gold_position"])] = {k:r[k] for k in METRICS}
    rows = [summarize_record(r,question_aliases) for r in records]
    rows.sort(key=lambda r:(r["model"],r["question"],r["position"]))
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output/"anonymous-scores.csv.gz", rows)
    questions = sorted({r["question"] for r in rows})
    if len(questions) != config["questions"]:
        raise ValueError("Unexpected independent question count")
    lookup = {(r["model"],r["question"],r["position"]):r for r in rows}
    positions = config["positions_1_based"]
    indices = np.random.default_rng(config["bootstrap"]["seed"]).integers(0,len(questions),(5000,len(questions)))
    summary, contrasts, matrices = [], [], {}
    for model in config["models"]:
        for metric in METRICS:
            mat = np.array([[lookup[model,q,p][metric] for p in positions] for q in questions],dtype=float)
            matrices[model,metric] = mat
            for i, p in enumerate(positions):
                column = mat[:,i]
                lo, hi = np.quantile(column[indices].mean(axis=1),[.025,.975])
                group = [lookup[model,q,p] for q in questions]
                summary.append({"model":model,"position":p,"metric":metric,"questions":len(questions),
                                "successes":int(column.sum()),"rate":float(column.mean()),"ci_low":float(lo),"ci_high":float(hi),
                                "mean_output_tokens":float(np.mean([r["output_tokens"] for r in group])),
                                "truncations":sum(r["truncated"] for r in group)})
            center = mat[:,[positions.index(p) for p in [8,10,13]]].mean(axis=1)
            front = mat[:,[positions.index(p) for p in [1,3,5]]].mean(axis=1)
            back = mat[:,[positions.index(p) for p in [15,18,20]]].mean(axis=1)
            vectors = {"position1-position10":mat[:,positions.index(1)]-mat[:,positions.index(10)],
                       "position20-position10":mat[:,positions.index(20)]-mat[:,positions.index(10)],
                       "front_band-center_band":front-center,"back_band-center_band":back-center}
            for name, vector in vectors.items():
                contrasts.append({"model":model,"metric":metric,"comparison":name,"questions":len(questions),**paired_stat(vector,indices)})
    write_csv(output/"position-summary.csv",summary)
    write_csv(output/"paired-position-contrasts.csv",contrasts)
    model_comparisons=[]
    if len(config["models"])==2:
        baseline_model,comparison_model=config["models"]
        for metric in METRICS:
            gain=matrices[comparison_model,metric]-matrices[baseline_model,metric]
            front_gain=gain[:,[positions.index(p) for p in [1,3,5]]].mean(axis=1)
            back_gain=gain[:,[positions.index(p) for p in [15,18,20]]].mean(axis=1)
            vectors={f"model_gain_at_position{p:02d}":gain[:,i] for i,p in enumerate(positions)}
            vectors["model_gain_over_all_positions"]=gain.mean(axis=1)
            vectors["front_band_gain-minus-back_band_gain"]=front_gain-back_gain
            vectors["gain_position1-minus-position20"]=gain[:,positions.index(1)]-gain[:,positions.index(20)]
            for name,vector in vectors.items():
                model_comparisons.append({"baseline_model":baseline_model,"comparison_model":comparison_model,
                                          "metric":metric,"comparison":name,"questions":len(questions),
                                          **paired_stat(vector,indices)})
        write_csv(output/"paired-model-position-contrasts.csv",model_comparisons)
    pattern_summary, patterns = [], []
    for (model,metric),mat in matrices.items():
        totals = mat.sum(axis=1).astype(int)
        for count in range(len(positions)+1):
            pattern_summary.append({"model":model,"metric":metric,"correct_positions":count,
                                    "positions_measured":len(positions),"questions":int((totals==count).sum()),
                                    "fraction":float((totals==count).mean())})
        for q,row,total in zip(questions,mat,totals):
            patterns.append({"model":model,"question":q,"metric":metric,"correct_positions":int(total),
                             "positions_measured":len(positions),"pattern":"".join(str(int(v)) for v in row)})
    write_csv(output/"question-pattern-summary.csv",pattern_summary)
    write_csv(output/"anonymous-position-patterns.csv.gz",patterns)
    anchors=[]
    for model in config["models"]:
        for metric in METRICS:
            for p in [1,10,20]:
                past = np.array([int(truth(old[model,q,p][metric])) for q in questions],dtype=float)
                current = matrices[model,metric][:,positions.index(p)]
                anchors.append({"model":model,"position":p,"metric":metric,"questions":len(questions),
                                "historical_rate":float(past.mean()),"new_rate":float(current.mean()),
                                "old_hit_new_miss":int(((past==1)&(current==0)).sum()),
                                "new_hit_old_miss":int(((past==0)&(current==1)).sum()),
                                "score_disagreement_pct":float((past!=current).mean()*100),
                                **paired_stat(current-past,indices)})
    write_csv(output/"historical-anchor-comparison.csv",anchors)
    attempts=[r for line in (batch/"attempts.jsonl").read_text().splitlines() if (r:=json.loads(line))["model"] in config["models"]]
    attempt_status={str(code):sum(a["http_status"]==code for a in attempts) for code in {a["http_status"] for a in attempts}}
    manifest={"batch_id":config["batch_id"],"records":len(rows),"raw_records_in_snapshot":len(all_records),
              "analyzed_models":config["models"],"full_planned_models":original_models,"full_two_model_batch_complete":len(all_records)==config["expected_successful_responses"],
              "independent_questions":len(questions),
              "positions":positions,"models":config["models"],"prompt":"NoCoT","document_count":20,
              "collection_dates_utc_by_model":{model:dict(sorted(Counter(r["timestamp"][:10] for r in records if r["model"]==model).items())) for model in config["models"]},
              "raw_sha256":hashlib.sha256(source).hexdigest(),"config_sha256":frozen_config_sha256,
              "scenarios_uncompressed_sha256":hashlib.sha256(scenario_source).hexdigest(),
              "validated_prepared_requests":len(records),"request_protocol_validation_passed":True,
              "bootstrap":config["bootstrap"],"primary_metric":config["primary_metric"],
              "request_attempts":len(attempts),"http_status_counts":attempt_status,
              "truncations":sum(r["truncated"] for r in rows),
              "nonempty_reasoning_content":sum(r["reasoning_content_nonempty"] for r in rows),
              "reported_reasoning_tokens":sum(r["reasoning_tokens"] for r in rows if r["reasoning_tokens"] is not None) if any(r["reasoning_tokens"] is not None for r in rows) else None,
              "reasoning_token_reporting_records":sum(r["reasoning_tokens"] is not None for r in rows),
              "reasoning_token_missing_records":sum(r["reasoning_tokens"] is None for r in rows),
              "input_tokens":sum(r["input_tokens"] for r in rows),"output_tokens":sum(r["output_tokens"] for r in rows),
              "model_position_comparisons":"Exploratory paired question contrasts; provider collection dates are recorded in raw data and models were not collected simultaneously" if model_comparisons else None,
              "api_calls_during_analysis":0,"historical_anchor_observations_pooled":False}
    (output/"analysis-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    figures(summary,output,config)
    report=["# Lost in the Middle: nine-position extension","", "## Frozen protocol","",
            f"200 identical questions, 20 identical documents per question, nine measured positions, NoCoT; {len(config['models'])} analyzed model(s), {expected:,} fresh responses. Historical anchors are compared separately, never pooled into the curve.","",
            "Primary metric: extracted final-answer containment; strict final exact match, first-line containment, and full-response containment are sensitivity analyses. None is a new human semantic adjudication.","",
            "## Position profile","", "| Position | "+" | ".join(MODEL_NAMES[m] for m in config["models"])+" |",
            "| --- | "+" | ".join("---:" for m in config["models"])+" |"]
    for p in positions:
        rates=[next(r["rate"] for r in summary if r["position"]==p and r["model"]==m and r["metric"]==config["primary_metric"]) for m in config["models"]]
        report.append(f"| {p} | "+" | ".join(f"{rate*100:.1f}%" for rate in rates)+" |")
    report.extend(["", "## Prespecified paired contrasts","", "| Model | Contrast | Difference (pp) | 95% interval (pp) |", "| --- | --- | ---: | ---: |"])
    for r in contrasts:
        if r["metric"]==config["primary_metric"]:
            report.append(f"| {MODEL_NAMES[r['model']]} | {r['comparison']} | {r['difference_pp']:+.2f} | [{r['ci_low_pp']:.2f}, {r['ci_high_pp']:.2f}] |")
    if model_comparisons:
        report.extend(["","## Exploratory model-by-position comparisons","",
                       f"{MODEL_NAMES[comparison_model]} minus {MODEL_NAMES[baseline_model]}; resample the same question across both models and all positions. Models were collected on separate dates, with identical saved prompts and generation settings. Historical three-position results are not pooled into these contrasts.","",
                       "| Comparison | Difference (pp) | 95% interval (pp) |","| --- | ---: | ---: |"])
        for r in model_comparisons:
            if r["metric"]==config["primary_metric"]:
                report.append(f"| {r['comparison']} | {r['difference_pp']:+.2f} | [{r['ci_low_pp']:.2f}, {r['ci_high_pp']:.2f}] |")
    report.extend(["", "## 中文结论与解释", ""])
    transitions=[]
    for model in config["models"]:
        mat=matrices[model,config["primary_metric"]]
        a,b=mat[:,positions.index(1)],mat[:,positions.index(10)]
        front_only=int(((a==1)&(b==0)).sum())
        middle_only=int(((a==0)&(b==1)).sum())
        totals=mat.sum(axis=1)
        all_hit=int((totals==len(positions)).sum())
        all_miss=int((totals==0).sum())
        mixed=len(questions)-all_hit-all_miss
        edges=[r for r in contrasts if r["model"]==model and r["metric"]==config["primary_metric"] and r["comparison"] in ["position1-position10","position20-position10"]]
        supports_endpoints=all(r["ci_low_pp"]>0 for r in edges)
        first_edge=next(r for r in edges if r["comparison"]=="position1-position10")
        last_edge=next(r for r in edges if r["comparison"]=="position20-position10")
        report.append(f"### {MODEL_NAMES[model]}")
        report.append("")
        if supports_endpoints:
            report.append("端点比较支持首尾均优于中间，九点轮廓与双端优势一致。预设的分段比较另见上表。")
        elif first_edge["ci_low_pp"]>0:
            report.append(f"九点轮廓体现明确的首位优势：第 1 位相对第 10 位高 {first_edge['difference_pp']:.2f} 个百分点，95% 区间 [{first_edge['ci_low_pp']:.2f}, {first_edge['ci_high_pp']:.2f}]；第 20 位相对第 10 位为 {last_edge['difference_pp']:+.2f} 个百分点。")
        else:
            report.append(f"第 1、10、20 位的最终答案包含率分别为 {mat[:,positions.index(1)].mean()*100:.1f}%、{mat[:,positions.index(10)].mean()*100:.1f}%、{mat[:,positions.index(20)].mean()*100:.1f}%。九点轮廓的起伏及预设配对区间见上表。")
        report.append("")
        report.append(f"首位与第 10 位之间，{front_only+middle_only}/{len(questions)} 道题的二元评分不同（{(front_only+middle_only)/len(questions)*100:.1f}%）：{front_only} 道仅首位命中，{middle_only} 道仅中位命中。两类变化的净平均差为 {(a-b).mean()*100:+.2f} 个百分点。逐题统计同时记录了两个方向的变化。")
        report.append("")
        report.append(f"文档位置全部命中的题目 {all_hit} 道，全部未命中 {all_miss} 道，至少发生一次评分变化 {mixed} 道（{mixed/len(questions)*100:.1f}%），反映位置变动下的成功集合更替。")
        anchor_rows=[r for r in anchors if r["model"]==model and r["metric"]==config["primary_metric"]]
        flips=sum(r["old_hit_new_miss"]+r["new_hit_old_miss"] for r in anchor_rows)
        anchor_n=sum(r["questions"] for r in anchor_rows)
        report.append("")
        report.append(f"新旧批次三个相同提示锚点的评分一致 {anchor_n-flips}/{anchor_n}（{(anchor_n-flips)/anchor_n*100:.2f}%）。")
        for pa,pb in [(1,10),(20,10),(1,20)]:
            x,y=mat[:,positions.index(pa)],mat[:,positions.index(pb)]
            transitions.append({"model":model,"metric":config["primary_metric"],"first_position":pa,"second_position":pb,
                                "questions":len(questions),"first_only_hit":int(((x==1)&(y==0)).sum()),
                                "second_only_hit":int(((x==0)&(y==1)).sum()),"both_hit":int(((x==1)&(y==1)).sum()),
                                "both_miss":int(((x==0)&(y==0)).sum())})
        report.append("")
    write_csv(output/"paired-score-transitions.csv",transitions)
    report.extend(["", "## Interpretation limits","",
                   "Confidence intervals resample the 200 questions as paired clusters, preserving all positions. Intervals are pointwise/exploratory and not adjusted for multiplicity. Nine positions improve horizontal resolution but do not increase independent question count. The same provider model ID does not guarantee unchanged weights across dates. U-shape claims require both front and back advantages over the center; a front advantage alone is insufficient.","",
                   "See `historical-anchor-comparison.csv` for batch drift and `position-summary.csv` for all four scoring rules. SVG labels use Times New Roman when installed; lines only connect observed positions."])
    (output/"findings.md").write_text("\n".join(report)+"\n")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",type=Path,default=ROOT/"configs/document_positions.json")
    parser.add_argument("--output",type=Path,default=ROOT/"reports/document_positions")
    parser.add_argument("--model",choices=list(MODEL_NAMES),help="Report only a completed model; all its positions must be complete")
    args=parser.parse_args()
    analyze(args.config,args.output,args.model)


if __name__=="__main__":
    main()
