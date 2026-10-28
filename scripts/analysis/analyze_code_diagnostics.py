"""Analyze saved code generations and scores. No API calls or code execution."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import textwrap
import warnings

import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT = ROOT / "reports/code_diagnostics"
REGULAR = ["DefaultCoT", "BeConcise", "BulletPoints", "StepLimit(1)", "StepLimit(2)", "StepLimit(5)"]
MODELS = {"deepseek-flash": "deepseek", "qwen2.5-7b-instruct-cloud": "qwen", "qwen3-8b-cloud": "qwen3"}


def write_csv(name, rows):
    with (OUT / name).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def body_fingerprint(code, function_name):
    if not code:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(textwrap.dedent(code))
    except (SyntaxError, ValueError, TypeError):
        return None
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    target = next((n for n in functions if n.name == function_name), None)
    if target is None and len(functions) == 1:
        target = functions[0]
    if target is None:
        return None
    body = list(target.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    normalized = ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)
    return hashlib.sha256(normalized.encode()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(ROOT / "app/data/code-features.json.gz", "rt") as f:
        data = json.load(f)
    rows = [dict(zip(data["fields"], row)) for row in data["rows"]]
    rows = [r for r in rows if r["passed"] is not None and not r["environment_excluded"]]
    groups = defaultdict(list)
    for r in rows:
        groups[r["model"], r["question"], r["prompt"]].append(r)
    for group in groups.values():
        group.sort(key=lambda r: r["sample"])
        if len(group) != 5:
            raise ValueError("Expected five saved independent samples")
    questions = sorted({r["question"] for r in rows})
    idx = np.random.default_rng(20261026).integers(0, len(questions), (5000, len(questions)))
    retries, errors = [], []
    for model in MODELS.values():
        for scope, prompts in [("DefaultCoT", ["DefaultCoT"]), ("regular6", REGULAR)]:
            per_question, selected = [], []
            for q in questions:
                chosen = [groups[model, q, p] for p in prompts]
                first_fail = sum(not a[0]["passed"] for a in chosen)
                recovered = sum(not a[0]["passed"] and any(r["passed"] for r in a[1:]) for a in chosen)
                per_question.append((first_fail, recovered))
                selected.extend(chosen)
            a = np.asarray(per_question, dtype=float)
            denominator = a[:, 0].sum()
            boot = a[idx].sum(axis=1)
            low, high = np.nanquantile(np.divide(boot[:, 1], boot[:, 0], out=np.full(len(boot), np.nan), where=boot[:, 0] > 0), [.025, .975])
            retries.append({"model": model, "scope": scope, "questions": len(questions),
                            "conditions": len(selected), "first_failure_conditions": int(denominator),
                            "recovered_in_next_four": int(a[:, 1].sum()),
                            "conditional_recovery_pct": a[:, 1].sum() / denominator * 100,
                            "ci_low_pct": low * 100, "ci_high_pct": high * 100,
                            "all_five_fail_conditions": sum(not any(r["passed"] for r in g) for g in selected)})
            failure_rows = [r for g in selected for r in g if not r["passed"]]
            counts = Counter(r["error"] for r in failure_rows)
            for error, count in counts.most_common():
                errors.append({"model": model, "scope": scope, "error": error, "count": count,
                               "failure_records": len(failure_rows), "all_records": len(selected) * 5,
                               "share_of_failures_pct": count / len(failure_rows) * 100,
                               "share_of_all_records_pct": count / (len(selected) * 5) * 100})
    write_csv("first-failure-recovery.csv", retries)
    write_csv("failure-composition.csv", errors)

    source = ROOT / "data/raw/code_generation"
    with gzip.open(source / "source_scores/scores.csv.gz", "rt") as f:
        scores = list(csv.DictReader(f))
    task_map = {q: f"T{i+1:03d}" for i, q in enumerate(dict.fromkeys(r["task_id"] for r in scores))}
    fingerprints = {}
    for source_model, model in MODELS.items():
        with gzip.open(source / f"raw_{source_model}.jsonl.gz", "rt") as f:
            for line in f:
                r = json.loads(line)
                if r["compression_prompt_id"] not in REGULAR:
                    continue
                key = model, task_map[r["task_id"]], r["compression_prompt_id"], int(r["turn_id"])
                fingerprints[key] = body_fingerprint(r["generated_code"], r["function_name"])
    repetition = []
    for model in MODELS.values():
        for scope, prompts in [("DefaultCoT", ["DefaultCoT"]), ("regular6", REGULAR)]:
            for outcome in ["all_five_fail", "all_five_pass", "mixed"]:
                chosen, parsed, identical = [], 0, 0
                for q in questions:
                    for p in prompts:
                        g = groups[model, q, p]
                        total = sum(r["passed"] for r in g)
                        kind = "all_five_fail" if total == 0 else "all_five_pass" if total == 5 else "mixed"
                        if kind != outcome:
                            continue
                        chosen.append(g)
                        hashes = [fingerprints[model, q, p, int(r["sample"])] for r in g]
                        if all(h is not None for h in hashes):
                            parsed += 1
                            identical += len(set(hashes)) == 1
                repetition.append({"model": model, "scope": scope, "outcome": outcome,
                                   "conditions": len(chosen), "all_five_bodies_parsed": parsed,
                                   "identical_function_body_conditions": identical,
                                   "identical_pct_all_conditions": identical / len(chosen) * 100 if chosen else None,
                                   "identical_pct_parsed_conditions": identical / parsed * 100 if parsed else None})
    write_csv("function-body-repetition.csv", repetition)
    manifest = {"source_commit": "code-generation@9dfc592", "eligible_questions": len(questions),
                "eligible_responses": len(rows), "api_calls": 0, "candidate_code_executed": False,
                "bootstrap_unit": "question", "bootstrap_resamples": 5000, "bootstrap_seed": 20261026,
                "body_fingerprint": "Target function body AST; omit its leading docstring and source positions; comments and whitespace disappear on parsing. No claim of semantic equivalence.",
                "scope": "Six ordinary prompts; saved independent samples, not feedback repair."}
    (OUT / "analysis-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    names={"deepseek":"DeepSeek", "qwen":"Qwen2.5", "qwen3":"Qwen3"}
    report=["# 代码任务：贴近实际使用场景的发现", "",
            "2026-10-26；固定来源 code-generation@9dfc592。193 道共同可评题，三个模型、31 提示、每条件五次独立生成；temperature=0.2。主分析使用 DefaultCoT、BeConcise、BulletPoints、StepLimit(1/2/5) 六种常规提示。", "",
            "只读取保存回答和测试结果。本轮 API 调用为 0，没有执行生成代码。", "",
            "## 1. 初次失败后，同提示独立重试四次约九成仍失败", "",
            "固定 DefaultCoT，按照保存次序统计首次失败的题：", "",
            "| 模型 | 首次失败题数 | 后四次至少一次通过 | 翻盘比例 |", "|---|---:|---:|---:|"]
    for r in retries:
        if r["scope"]=="DefaultCoT":
            report.append(f"| {names[r['model']]} | {r['first_failure_conditions']} | {r['recovered_in_next_four']} | {r['conditional_recovery_pct']:.2f}% |")
    report += ["", "扩展到六种常规提示，翻盘比例分别为 " + "、".join(f"{r['conditional_recovery_pct']:.2f}%" for r in retries if r["scope"]=="regular6") + "。每次生成看不到前次答案和测试报错，代表保持原提示点重新生成的情形。", "",
               "五份函数体均可解析的五连败条件中，五次函数体结构完全相同的比例分别为 " + "、".join(f"{r['identical_pct_parsed_conditions']:.2f}%" for r in repetition if r["scope"]=="regular6" and r["outcome"]=="all_five_fail") + "；其余约 93%–94% 出现结构变化。函数体结构变化表示写法不同，未对算法语义作新的人工分类。", "",
               "## 2. 失败主要集中在功能和接口语义，语法错误占比较小", "",
               "分母为六种常规提示下的失败回答。每模型共有 5,790 条可评回答。", "",
               "| 模型 | 失败回答 | 断言/属性/类型三类占失败 | 语法错误占失败 |", "|---|---:|---:|---:|"]
    for model in MODELS.values():
        group=[r for r in errors if r["model"]==model and r["scope"]=="regular6"]
        major=sum(r["count"] for r in group if r["error"] in ["assertion_failure","attribute_error","type_error"])
        syntax=next(r["count"] for r in group if r["error"]=="syntax_error")
        total=group[0]["failure_records"]
        report.append(f"| {names[model]} | {total} | {major/total*100:.2f}% | {syntax/total*100:.2f}% |")
    report += ["", "原文例子 T005：任务要求提取命令行参数标记，参考函数取 action.option_strings；一份 Qwen2.5 回答取 action.dest，并加入额外类型检查。这是字段与接口语义的差异，代码块排版和语法检查无法代替功能测试。", "",
               "## 3. 独立函数题上，模型间的成功频率差距大于成功集合差距", "",
               "下表使用全部 31 提示、每提示五次的结果。覆盖定义为某题在该模型的 155 份保存回答中至少通过一次。", "",
               "| 模型 | 30 道独立函数题平均 Pass@1 | 曾成功覆盖 |", "|---|---:|---:|"]
    with (ROOT/"reports/prompt_variants/code-dependency-levels.csv").open() as f:
        levels=list(csv.DictReader(f))
    for model in MODELS.values():
        r=next(r for r in levels if r["model"]==model and r["scope"]=="all31" and r["level"]=="self_contained")
        report.append(f"| {names[model]} | {float(r['pass1_pct']):.2f}% | {r['ever_solved_questions']}/30 |")
    report += ["", "三模型曾成功的都是同一组 23 题；仅七种常规提示时覆盖为 21/21/20，交集为 20 题。独立函数组中，更高得分主要体现为更稳定地生成能通过测试的答案。", "",
               "21 道项目依赖题的三模型 Pass@1 为 11.92%/11.86%/12.20%；其中 16 题的 465 份回答全部未通过。该类别对照使用不同题目组，描述固定函数说明、签名和包信息输入下的结果。", "",
               "## 4. 隐含业务约定可以让很短的函数成为共同失败题", "",
               "T042/base_config：提示列出 tls、authentication、authorization、etcd、docs、log 六类配置和函数签名；参考实现还包含固定嵌套结构、证书占位路径、认证策略和默认布尔值。模型各自生成了不同配置，这些约定没有在实际输入中完整提供。", "",
               "T136/_replace_register：提示写入 flow_params[register_number]，参考实现实际写入 'reg{:d}'.format(register_number)。例如数字 4 对应测试需要的字符串键 reg4。实际输入未交代这个前缀约定。", "",
               "两题均属于原数据的 self_contained 标签，均在 31×5×3=465 份回答下未通过。该标签描述运行依赖层级，题意仍可能包含项目约定。以上是直接阅读保存提示、参考实现和回答得到的案例解释，没有重评或修改原分数。", "",
               "## 5. 固定五次调用，提示多样性提供额外覆盖", "",
               "六提示池同上。比较随机固定一种提示的五次回答，与随机选五种不同提示各一次；两者单次提示边际分布相同，期望返回 Token 相同。下面是保存回答的离线组合期望。", "",
               "| 模型 | 同提示五次 | 五种提示各一次 | 增益及 95% 区间 |", "|---|---:|---:|---:|"]
    with (ROOT/"reports/prompt_variants/code-prompt-diversity.csv").open() as f:
        diversity=list(csv.DictReader(f))
    for r in diversity:
        if r["scope"]=="regular6_without_NoCoT":
            report.append(f"| {names[r['model']]} | {float(r['same_prompt_five_pct']):.2f}% | {float(r['distinct_prompts_five_pct']):.2f}% | +{float(r['difference_pp']):.2f} pp [{float(r['ci_low_pp']):.2f}, {float(r['ci_high_pp']):.2f}] |")
    report += ["", "## 证据与口径", "",
               "新表：first-failure-recovery.csv、failure-composition.csv、function-body-repetition.csv。覆盖与多样性表复用 ../deeper-findings-20261026/ 下的保存分析结果。", "",
               "区间按题目为簇做 5,000 次 bootstrap。原始 194 题中一题统一环境排除；这里使用 193 题、89,745 条可评记录。覆盖按题统计，Pass@1 按回答成功频率统计，两者分母不同。测试通过表示通过保存测试。"]
    (OUT/"findings.md").write_text("\n".join(report)+"\n")
    print(json.dumps({"retry_results": retries, "body_repetition": [r for r in repetition if r["outcome"] == "all_five_fail"], "manifest": manifest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
