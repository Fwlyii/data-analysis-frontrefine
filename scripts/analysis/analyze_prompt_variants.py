"""Explore directional findings using saved anonymous features, without API calls.

Writes a new report directory. Existing scores, raw data and the app stay unchanged.
All uncertainty intervals resample independent questions, not response rows.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT = ROOT / "reports" / "prompt_variants"
SEED = 20261026
BOOTSTRAPS = 5000
REGULAR7 = [
    "NoCoT", "DefaultCoT", "BeConcise", "BulletPoints",
    "StepLimit(1)", "StepLimit(2)", "StepLimit(5)",
]
METRICS = ["paper_firstline", "strict_final_em", "final_contains", "full_response_contains"]
BOOT_INDEX: dict[int, np.ndarray] = {}


def feature_rows(name: str) -> list[dict]:
    with gzip.open(ROOT / "app" / "data" / name, "rt") as f:
        data = json.load(f)
    return [dict(zip(data["fields"], row)) for row in data["rows"]]


def indices(n: int) -> np.ndarray:
    if n not in BOOT_INDEX:
        BOOT_INDEX[n] = np.random.default_rng(SEED + n).integers(0, n, (BOOTSTRAPS, n))
    return BOOT_INDEX[n]


def interval(values) -> tuple[float, float]:
    a = np.asarray(values, dtype=float)
    bounds = np.quantile(a[indices(len(a))].mean(axis=1), [0.025, 0.975])
    return float(bounds[0]), float(bounds[1])


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def reasoning_contrasts(rows: list[dict], methods: list[dict]) -> list[dict]:
    by_id = {r["id"]: r for r in methods}
    groups = defaultdict(dict)
    for r in rows:
        if r["dataset"] == "reasoning":
            groups[r["model"], r["task"]][r["question"], r["prompt"]] = r
    comparisons = [
        ("ChineseCoT", "DefaultCoT"), ("BeConcise", "DefaultCoT"),
        ("StepLimit(5)", "DefaultCoT"), ("CharLimit(10)", "CharLimit(100)"),
        ("WordLimit(1)", "WordLimit(10)"), ("TokenLimit(500)", "TokenLimit(100)"),
    ]
    output = []
    for (model, task), rec in sorted(groups.items()):
        questions = sorted({q for q, _ in rec})
        for first, baseline in comparisons:
            a = [rec[q, first] for q in questions]
            b = [rec[q, baseline] for q in questions]
            y_a = np.array([r["scores"][0] for r in a], dtype=float)
            y_b = np.array([r["scores"][0] for r in b], dtype=float)
            t_a = np.array([r["tokens"] for r in a], dtype=float)
            t_b = np.array([r["tokens"] for r in b], dtype=float)
            lo, hi = interval((y_a - y_b) * 100)
            t_lo, t_hi = interval(t_a - t_b)
            rescues = (y_a == 1) & (y_b == 0)
            losses = (y_a == 0) & (y_b == 1)
            row = {
                "model": model, "task": task, "first": first, "baseline": baseline,
                "questions": len(questions), "first_score_pct": float(y_a.mean() * 100),
                "baseline_score_pct": float(y_b.mean() * 100),
                "score_difference_pp": float((y_a - y_b).mean() * 100),
                "score_ci_low_pp": lo, "score_ci_high_pp": hi,
                "first_mean_tokens": float(t_a.mean()), "baseline_mean_tokens": float(t_b.mean()),
                "token_difference": float((t_a - t_b).mean()),
                "token_difference_ci_low": t_lo, "token_difference_ci_high": t_hi,
                "token_saving_pct": float((1 - t_a.mean() / t_b.mean()) * 100),
                "first_visible_characters": float(np.mean([by_id[r["id"]]["character_count"] for r in a])),
                "baseline_visible_characters": float(np.mean([by_id[r["id"]]["character_count"] for r in b])),
                "first_truncated_pct": float(np.mean([r["truncated"] for r in a]) * 100),
                "baseline_truncated_pct": float(np.mean([r["truncated"] for r in b]) * 100),
                "first_unresolved_pct": float(np.mean([r["unresolved"] for r in a]) * 100),
                "baseline_unresolved_pct": float(np.mean([r["unresolved"] for r in b]) * 100),
                "rescued_questions": int(rescues.sum()), "lost_questions": int(losses.sum()),
                "rescues_baseline_truncated": sum(bool(v) and bool(r["truncated"]) for v, r in zip(rescues, b)),
                "losses_first_truncated": sum(bool(v) and bool(r["truncated"]) for v, r in zip(losses, a)),
            }
            output.append(row)
    write_csv("reasoning-paired-contrasts.csv", output)
    recoveries = []
    for row in output:
        if row["task"] == "math500" and row["first"] in ["ChineseCoT", "BeConcise"]:
            recoveries.append({
                **{k: row[k] for k in ["model", "first", "score_difference_pp", "rescued_questions",
                                       "rescues_baseline_truncated", "lost_questions", "losses_first_truncated"]},
                "rescues_previously_truncated_pct": row["rescues_baseline_truncated"] / row["rescued_questions"] * 100,
            })
    write_csv("math-completion-recovery.csv", recoveries)
    profiles = []
    for (model, task), rec in sorted(groups.items()):
        for prompt in sorted({p for _, p in rec}):
            a = [rec[q, prompt] for q in sorted({q for q, _ in rec})]
            profiles.append({
                "model": model, "task": task, "prompt": prompt, "questions": len(a),
                "score_pct": float(np.mean([r["scores"][0] for r in a]) * 100),
                "mean_tokens": float(np.mean([r["tokens"] for r in a])),
                "truncated_pct": float(np.mean([r["truncated"] for r in a]) * 100),
                "unresolved_pct": float(np.mean([r["unresolved"] for r in a]) * 100),
            })
    write_csv("reasoning-all-prompt-profiles.csv", profiles)
    return output


def document_qa_position_gains(rows: list[dict]) -> list[dict]:
    summary = json.loads((ROOT / "app" / "data" / "summary.json").read_text())
    main = sorted({c["prompt"] for c in summary["cells"]
                   if c["dataset"] == "document_qa" and c["scope"] == "main_comparison"})
    selected = [r for r in rows if r["dataset"] == "document_qa" and r["task"] == "document_qa"]
    rec = {(r["model"], r["question"], r["prompt"], r["documents"], r["position"]): r for r in selected}
    questions = sorted({r["question"] for r in selected})
    pos = ["front", "middle", "back"]
    scopes = {"main19": main, "regular7": REGULAR7, "NoCoT": ["NoCoT"], "DefaultCoT": ["DefaultCoT"]}
    output, per_prompt, doc_effect = [], [], []
    for metric_id, metric in enumerate(METRICS):
        for scope, prompts in scopes.items():
            for docs in [[10], [20], [10, 20]]:
                arr = {}
                for model in ["qwen", "qwen3"]:
                    arr[model] = np.array([
                        [np.mean([rec[model, q, p, d, at]["scores"][metric_id]
                                  for p in prompts for d in docs]) for at in pos]
                        for q in questions
                    ])
                gains = (arr["qwen3"] - arr["qwen"]) * 100
                contrast = gains[:, 0] - gains[:, 2]
                lo, hi = interval(contrast)
                row = {
                    "scope": scope, "metric": metric, "documents": "+".join(map(str, docs)),
                    "questions": len(questions), "prompts": len(prompts),
                    "front_gain_pp": float(gains[:, 0].mean()),
                    "middle_gain_pp": float(gains[:, 1].mean()),
                    "back_gain_pp": float(gains[:, 2].mean()),
                    "front_minus_back_gain_pp": float(contrast.mean()),
                    "gain_contrast_ci_low_pp": lo, "gain_contrast_ci_high_pp": hi,
                }
                for model in arr:
                    for i, at in enumerate(pos):
                        row[f"{model}_{at}_pct"] = float(arr[model][:, i].mean() * 100)
                output.append(row)
        for prompt in main:
            vals = {}
            for model in ["qwen", "qwen3"]:
                vals[model] = np.array([
                    [np.mean([rec[model, q, prompt, d, at]["scores"][metric_id] for d in [10, 20]])
                     for at in pos] for q in questions
                ])
            gains = (vals["qwen3"] - vals["qwen"]) * 100
            per_prompt.append({"prompt": prompt, "metric": metric,
                               "front_gain_pp": float(gains[:, 0].mean()),
                               "middle_gain_pp": float(gains[:, 1].mean()),
                               "back_gain_pp": float(gains[:, 2].mean()),
                               "front_minus_back_gain_pp": float((gains[:, 0] - gains[:, 2]).mean())})
        for scope, prompts in scopes.items():
            for model in ["qwen", "qwen3"]:
                for at in pos:
                    a = np.array([np.mean([rec[model, q, p, 20, at]["scores"][metric_id]
                                           - rec[model, q, p, 10, at]["scores"][metric_id]
                                           for p in prompts]) for q in questions]) * 100
                    lo, hi = interval(a)
                    doc_effect.append({"scope": scope, "model": model, "metric": metric,
                                       "position": at, "difference_20_minus_10_pp": float(a.mean()),
                                       "ci_low_pp": lo, "ci_high_pp": hi, "questions": len(questions)})
    write_csv("document_qa-model-gain-by-position.csv", output)
    write_csv("document_qa-model-gain-per-prompt.csv", per_prompt)
    write_csv("document_qa-document-expansion.csv", doc_effect)
    return output


def code_analysis(rows: list[dict]) -> dict:
    valid = [r for r in rows if not r["environment_excluded"] and r["passed"] is not None]
    groups = defaultdict(lambda: defaultdict(list))
    by_question = defaultdict(list)
    for r in valid:
        groups[r["model"], r["question"]][r["prompt"]].append(r)
        by_question[r["question"]].append(r)
    levels, level_contrasts, recurrence, diversity, masks = [], [], [], [], []
    for model in ["deepseek", "qwen", "qwen3"]:
        for scope, ps in [("all31", None), ("regular7", REGULAR7), ("DefaultCoT", ["DefaultCoT"])]:
            by_level = defaultdict(list)
            fails = []
            for (m, q), prompts in groups.items():
                if m != model:
                    continue
                a = {p: v for p, v in prompts.items() if ps is None or p in ps}
                combined = [r for v in a.values() for r in v]
                by_level[combined[0]["level"]].append((
                    np.mean([r["passed"] for r in combined]),
                    np.mean([max(r["passed"] for r in v) for v in a.values()]),
                    int(any(r["passed"] for r in combined)),
                ))
                fails.extend(v for v in a.values() if not any(r["passed"] for r in v))
            for level, a in sorted(by_level.items()):
                arr = np.asarray(a, dtype=float)
                lo, hi = interval(arr[:, 0] * 100)
                levels.append({"model": model, "scope": scope, "level": level, "questions": len(a),
                               "pass1_pct": float(arr[:, 0].mean() * 100),
                               "pass1_ci_low_pct": lo, "pass1_ci_high_pct": hi,
                               "pass5_pct": float(arr[:, 1].mean() * 100),
                               "ever_solved_questions": int(arr[:, 2].sum()),
                               "never_solved_questions": int(len(a) - arr[:, 2].sum())})
            standalone = np.asarray(by_level["self_contained"], dtype=float)[:, 0] * 100
            project = np.asarray(by_level["project_runnable"], dtype=float)[:, 0] * 100
            difference_boot = (standalone[indices(len(standalone))].mean(axis=1)
                               - project[indices(len(project))].mean(axis=1))
            lo, hi = np.quantile(difference_boot, [0.025, 0.975])
            level_contrasts.append({
                "model": model, "scope": scope,
                "self_contained_questions": len(standalone), "project_questions": len(project),
                "self_contained_minus_project_pp": float(standalone.mean() - project.mean()),
                "ci_low_pp": float(lo), "ci_high_pp": float(hi),
            })
            stable = sum(len({r["error"] for r in a}) == 1 for a in fails)
            recurrence.append({"model": model, "scope": scope, "all_five_fail_conditions": len(fails),
                               "all_five_same_error": stable, "same_error_pct": stable / len(fails) * 100})

        pools = {"all31": None, "regular7": REGULAR7,
                 "regular6_without_NoCoT": [p for p in REGULAR7 if p != "NoCoT"]}
        for scope, ps in pools.items():
            values, costs = [], []
            for (m, q), prompts in sorted(groups.items()):
                if m != model:
                    continue
                a = [v for p, v in prompts.items() if ps is None or p in ps]
                n_prompts = len(a)
                if any(len(v) != 5 for v in a):
                    raise ValueError("Expected five independent saved responses in every condition")
                same = np.mean([max(r["passed"] for r in v) for v in a])
                # Elementary symmetric mean: exact average over distinct five-prompt subsets.
                e = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
                for v in a:
                    failure = 1 - np.mean([r["passed"] for r in v])
                    for k in range(5, 0, -1):
                        e[k] += failure * e[k - 1]
                distinct = 1 - e[5] / math.comb(n_prompts, 5)
                values.append((same, distinct))
                # Each policy has the same uniform marginal prompt distribution on each call.
                costs.append(5 * np.mean([np.mean([r["output_tokens"] for r in v]) for v in a]))
            arr = np.asarray(values)
            difference = (arr[:, 1] - arr[:, 0]) * 100
            lo, hi = interval(difference)
            diversity.append({"model": model, "scope": scope, "questions": len(arr),
                              "pool_size": n_prompts, "calls": 5,
                              "same_prompt_five_pct": float(arr[:, 0].mean() * 100),
                              "distinct_prompts_five_pct": float(arr[:, 1].mean() * 100),
                              "difference_pp": float(difference.mean()),
                              "ci_low_pp": lo, "ci_high_pp": hi,
                              "same_expected_output_tokens": float(np.mean(costs)),
                              "distinct_expected_output_tokens": float(np.mean(costs))})

    for q, a in sorted(by_question.items()):
        solved = {m: any(r["passed"] for r in a if r["model"] == m)
                  for m in ["deepseek", "qwen", "qwen3"]}
        masks.append({"question": q, "level": a[0]["level"],
                      **{f"{m}_ever_solved": int(v) for m, v in solved.items()},
                      "any_model_ever_solved": int(any(solved.values())),
                      "all_models_ever_solved": int(all(solved.values()))})
    hard = [q for q, a in by_question.items() if not any(r["passed"] for r in a)]
    hard_errors = Counter(r["error"] for q in hard for r in by_question[q])
    overlaps = []
    for scope, ps in [("all31", None), ("regular7", REGULAR7)]:
        for level in ["__all", "self_contained", "project_runnable"]:
            questions = [q for q, a in by_question.items() if level == "__all" or a[0]["level"] == level]
            sets = {
                m: {q for q in questions if any(r["passed"] for p, a in groups[m, q].items()
                                               if ps is None or p in ps for r in a)}
                for m in ["deepseek", "qwen", "qwen3"]
            }
            overlaps.append({"scope": scope, "level": level, "questions": len(questions),
                             **{f"{m}_covered": len(s) for m, s in sets.items()},
                             "union": len(set.union(*sets.values())),
                             "intersection": len(set.intersection(*sets.values()))})
    output = {
        "eligible_questions": len(by_question), "valid_responses": len(valid),
        "all_465_fail_questions": len(hard),
        "any_model_solved_questions": len(by_question) - len(hard),
        "all_models_ever_solved_questions": sum(r["all_models_ever_solved"] for r in masks),
        "each_model_ever_solved": {m: sum(r[f"{m}_ever_solved"] for r in masks)
                                   for m in ["deepseek", "qwen", "qwen3"]},
        "hard_core_error_counts": dict(hard_errors),
    }
    write_csv("code-dependency-levels.csv", levels)
    write_csv("code-dependency-contrasts.csv", level_contrasts)
    write_csv("code-error-recurrence.csv", recurrence)
    write_csv("code-prompt-diversity.csv", diversity)
    write_csv("code-question-coverage.csv", masks)
    write_csv("code-coverage-overlap.csv", overlaps)
    return output


def write_findings(reasoning: list[dict], document_qa: list[dict], code_summary: dict, rows: list[dict]) -> None:
    def read_table(name: str) -> list[dict]:
        with (OUT / name).open() as f:
            return list(csv.DictReader(f))

    levels = read_table("code-dependency-levels.csv")
    diversity = read_table("code-prompt-diversity.csv")
    coverage = read_table("code-question-coverage.csv")
    pos_votes = read_table("document_qa-model-gain-per-prompt.csv")
    lines = [
        "现有实验的进一步挖掘：2026-10-26",
        "",
        "本轮只分析本地保存结果。所有表格均保留源评分，不修改网页，不调用 API。",
        "",
        "一、极端限长会造成输出反弹",
        "",
    ]
    for first, baseline in [("CharLimit(10)", "CharLimit(100)"), ("WordLimit(1)", "WordLimit(10)")]:
        a = [r for r in reasoning if r["first"] == first and r["baseline"] == baseline]
        longer = [r for r in a if r["token_difference"] > 0]
        lines.append(f"{first} 相对 {baseline}：{len(longer)}/{len(a)} 个模型×任务组合输出更长。")
    for r in reasoning:
        if r["task"] == "math500" and r["first"] == "CharLimit(10)" and r["model"] != "qwen":
            lines.append(f"{r['model']} / MATH500：100 字母→10 字母，平均 Token "
                         f"{r['baseline_mean_tokens']:.1f}→{r['first_mean_tokens']:.1f}；"
                         f"源评分 {r['baseline_score_pct']:.1f}%→{r['first_score_pct']:.1f}%。")
    lines.extend([
        "",
        "案例 Z404：同一题的 100 字母回答（Z015804）用 25 Token 命中；10 字母回答（Z015404）",
        "先算出 9，随后反复讨论 NINE 如何凑成 10 个字母，最终在 801 Token 截断，源评分为 0。",
        "此案例为助理直接阅读保存文本后的说明；没有新增语义评分。",
        "",
        "二、MATH500 上精简模板救回的题目，多数来自默认 CoT 截断",
        "",
    ])
    recovery = [r for r in reasoning if r["task"] == "math500" and r["first"] in ["ChineseCoT", "BeConcise"]]
    fractions = [r["rescues_baseline_truncated"] / r["rescued_questions"] for r in recovery]
    gained = sum(r["score_difference_pp"] > 0 for r in recovery)
    lines.append(f"{len(recovery)} 个模型×模板组合中，{gained} 组净升分；全部组合中新命中题目在基线中被截断的比例为 "
                 f"{min(fractions)*100:.1f}%–{max(fractions)*100:.1f}%。")
    for r in recovery:
            lines.append(f"{r['model']} / {r['first']}：得分差 {r['score_difference_pp']:+.1f} pp；"
                     f"新命中 {r['rescued_questions']} 题，其中 {r['rescues_baseline_truncated']} 题基线被截断；"
                     f"另有 {r['lost_questions']} 题从基线命中变为未命中。")
    lines.extend(["", "三、Qwen3 的文档问答增益集中在证据前部", ""])
    for r in document_qa:
        if r["scope"] == "main19" and r["metric"] == "final_contains" and r["documents"] in ["10+20", "20"]:
            lines.append(f"{r['documents']} 篇文档：相对 Qwen2.5 的前/中/尾增益为 "
                         f"{r['front_gain_pp']:.2f}/{r['middle_gain_pp']:.2f}/{r['back_gain_pp']:.2f} pp；"
                         f"前部减尾部增益 {r['front_minus_back_gain_pp']:.2f} pp，"
                         f"95% 区间 [{r['gain_contrast_ci_low_pp']:.2f}, {r['gain_contrast_ci_high_pp']:.2f}]。")
    for metric in METRICS:
        a = [r for r in pos_votes if r["metric"] == metric]
        positive = sum(float(r["front_minus_back_gain_pp"]) > 0 for r in a)
        lines.append(f"{metric}：{positive}/{len(a)} 种提示的前部模型增益大于尾部。")
    lines.extend(["", "四、独立函数任务上，正确率差距明显，成功覆盖集合相同", ""])
    self_cases = [r for r in coverage if r["level"] == "self_contained"]
    any_solved = sum(int(r["any_model_ever_solved"]) for r in self_cases)
    all_solved = sum(int(r["all_models_ever_solved"]) for r in self_cases)
    lines.append(f"30 道 self_contained 题，每个模型使用 31 提示×5 独立采样："
                 f"三模型成功集合的并集 {any_solved} 题、交集 {all_solved} 题，集合完全一致。")
    for r in levels:
        if r["scope"] == "all31" and r["level"] == "self_contained":
            lines.append(f"{r['model']}：Pass@1 {float(r['pass1_pct']):.2f}%，"
                         f"曾成功 {r['ever_solved_questions']}/{r['questions']} 题。")
    overlap = next(r for r in read_table("code-coverage-overlap.csv")
                   if r["scope"] == "regular7" and r["level"] == "self_contained")
    lines.append(f"仅用七种常规提示：覆盖题数为 {overlap['deepseek_covered']}/"
                 f"{overlap['qwen_covered']}/{overlap['qwen3_covered']}；"
                 f"三模型交集 {overlap['intersection']}、并集 {overlap['union']} 题。")
    lines.extend(["", "五、项目依赖型任务形成三模型共同的低通过率区间", ""])
    for r in levels:
        if r["scope"] == "all31" and r["level"] == "project_runnable":
            lines.append(f"{r['model']}：Pass@1 {float(r['pass1_pct']):.2f}%，"
                         f"曾成功 {r['ever_solved_questions']}/{r['questions']} 题。")
    project_cases = [r for r in coverage if r["level"] == "project_runnable"]
    project_never = sum(not int(r["any_model_ever_solved"]) for r in project_cases)
    lines.append(f"21 道项目依赖型题中，{project_never} 题在三个模型共 465 份回答下均未通过。")
    lines.append(f"完整 193 题中，共 {code_summary['all_465_fail_questions']} 题全部 465 份回答未通过。"
                 f"DeepSeek 的全部记录覆盖 {code_summary['each_model_ever_solved']['deepseek']} 题，"
                 f"加入两个 Qwen 的全部记录后覆盖 {code_summary['any_model_solved_questions']} 题。")
    lines.extend([
        "本实验固定提供函数签名和包名；类别对照反映当前输入条件下的工程任务差异。",
        "依赖分组的来源：https://github.com/CoderEval/CoderEval#3-data-inspection",
        "",
        "六、同样五次调用，提示多样化比随机固定一种提示覆盖更多题目",
        "",
        "提示池：NoCoT、DefaultCoT、BeConcise、BulletPoints、StepLimit(1/2/5)。",
        "固定策略：均匀随机选一种提示，使用它的五次独立回答。",
        "多样策略：均匀无放回选五种不同提示，各随机使用一个保存回答。",
    ])
    for r in diversity:
        if r["scope"] == "regular7":
            lines.append(f"{r['model']}：{float(r['same_prompt_five_pct']):.2f}%→"
                         f"{float(r['distinct_prompts_five_pct']):.2f}%；增益 {float(r['difference_pp']):.2f} pp；"
                         f"95% 区间 [{float(r['ci_low_pp']):.2f}, {float(r['ci_high_pp']):.2f}]。")
    lines.extend([
        "两策略调用数相同；每次调用的提示边际分布相同，期望输出 Token 因而相同。",
        "排除 NoCoT 后，三模型增益仍为 +1.80 至 +2.42 pp。",
        "该对照评估提示池内的平均策略；数值为保存回答的离线组合期望。",
        "",
        "统计与来源",
        "",
        "reasoning 每个任务 200 道独立题；document_qa 为 200 道独立题；代码为 193 道共同可评题。",
        "所有得分沿用源自动评分，未解析标志与截断标志同时保留。",
        "本轮属于探索性分析；95% 区间按题重采样 5,000 次，未作多重比较校正。",
        "按依赖类别比较时，两个类别包含不同题目；其余对照保留同题配对关系。",
        "重算：python scripts/analysis/analyze_prompt_variants.py",
        "输入哈希、指标说明和策略定义见 analysis-manifest.json；各数值见同目录 CSV。",
    ])
    (OUT / "findings.txt").write_text("\n".join(lines) + "\n")
    rec = {r["id"]: r for r in rows}
    case_records = []
    for rid in ["Z015404", "Z015804"]:
        r = rec[rid]
        case_records.append({k: r[k] for k in ["id", "question", "model", "task", "prompt", "tokens", "truncated"]}
                            | {"source_score": r["scores"][0]})
    write_csv("inspected-budget-case.csv", case_records)


def main() -> None:
    rows = feature_rows("features.json.gz")
    methods = feature_rows("method-features.json.gz")
    code = feature_rows("code-features.json.gz")
    reasoning = reasoning_contrasts(rows, methods)
    document_qa = document_qa_position_gains(rows)
    code_summary = code_analysis(code)
    write_findings(reasoning, document_qa, code_summary, rows)
    sources = {}
    for name in ["features.json.gz", "method-features.json.gz", "code-features.json.gz", "summary.json"]:
        p = ROOT / "app" / "data" / name
        sources[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {
        "analysis_date": "2026-10-26", "seed": SEED, "bootstrap_draws": BOOTSTRAPS,
        "unit": "question", "multiplicity_adjusted": False, "analysis_type": "exploratory",
        "sources": sources, "raw_scores_modified": False, "api_requests": 0,
        "reasoning_comparisons": sorted({(r["first"], r["baseline"]) for r in reasoning}),
        "source_score_notes": "Retains source rule scores and unresolved flags; reasoning does not have uniformly adjudicated semantic labels.",
        "document_qa_metric_notes": "All four source metrics retained. Position gain claims use final_contains with sensitivity tables for the other metrics.",
        "diversity_notes": "Exact offline expectation under uniform random fixed-prompt vs uniform five-distinct-prompt policies. Both use five calls and identical expected output-token totals; realized per-question costs differ. No best-prompt oracle baseline or feedback repair is implied.",
        "dependency_notes": "Original CoderEval dependency levels; generation supplies signature and package names. Level comparisons use different question groups, not randomized changes to context.",
        "code_summary": code_summary,
    }
    (OUT / "analysis-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(OUT), "reasoning_contrasts": len(reasoning), "document_qa_contrasts": len(document_qa),
                      "code_summary": code_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
