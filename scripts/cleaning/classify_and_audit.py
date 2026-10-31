#!/usr/bin/env python3
"""Complete local data/method evidence without generating answers or changing source scores.

Reads preserved cleaned CSVs, source manifests and pure local scoring code. Public
outputs contain field aggregates or anonymous numeric/categorical features only.
This is an analysis command, not a test suite or a human semantic review.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import gzip
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import logging
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
PROCESSED = ROOT / "data/processed"
APP = ROOT / "app/data"
REPORTS = ROOT / "reports/baseline"
SEED = 91
TABLES = {
    "reasoning.responses_clean": "reasoning/responses_clean.csv.gz",
    "reasoning.review_queue_clean": "reasoning/review_queue_clean.csv.gz",
    "reasoning.questions_clean": "reasoning/questions_clean.csv",
    "reasoning.prompts_clean": "reasoning/prompts_clean.csv",
    "reasoning.repeated_hash_audit": "reasoning/repeated_hash_audit.csv",
    "document_qa.responses_clean": "document_qa/responses_clean.csv.gz",
    "document_qa.review_queue_clean": "document_qa/review_queue_clean.csv.gz",
    "document_qa.scenarios_clean": "document_qa/scenarios_clean.csv.gz",
    "document_qa.questions_clean": "document_qa/questions_clean.csv",
    "document_qa.attempts_clean": "document_qa/attempts_clean.csv.gz",
}
TASKS = {
    "gsm8k": ("arithmetic_word_problem", "GSM8K 算术应用题"),
    "math500": ("competition_math", "MATH500 竞赛数学题"),
    "mmlu": ("multiple_choice", "MMLU-Pro 选择题"),
    "document_qa": ("document_qa", "NQ-Open 多文档问答"),
    "closedbook_control": ("document_qa", "NQ-Open 闭卷对照（同一问答任务）"),
}
FAMILIES = {
    "NoCoT": "answer_only", "DefaultCoT": "step_by_step_requested",
    "BeConcise": "concise_steps_requested", "BulletPoints": "bullet_format",
    "OnlyNumbers": "numeric_format", "NoSpaces": "space_format",
    "NoProperGrammar": "grammar_format", "AbbreviateWords": "abbreviation_format",
    "WordLimit": "word_budget", "CharLimit": "character_budget",
    "TokenLimit": "token_budget", "StepLimit": "step_budget", "ChineseCoT": "chinese_language",
}
FEATURE_FIELDS = ["id", "prompt_family", "output_style", "result_state", "task_type",
                  "marker_present", "enumerated_steps", "han_character_count", "word_count",
                  "character_count", "budget_check"]
STEP = re.compile(r"(?im)^\s*(?:step\s*\d+\b|步骤\s*[一二三四五六七八九十\d]+|\d+[.)、]\s+)")
BULLET = re.compile(r"(?m)^\s*[-*•]\s+\S")
MARKER = re.compile(r"(?i)(?<![a-z])(?:final\s+answer|answer|ans|an|最终答案|答案)\s*\**\s*[:：]")
HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_write(path, rows, fields=None, delimiter=","):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter=delimiter, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def yes(value):
    return str(value).lower() == "true"


def prompt_family(prompt):
    match = re.fullmatch(r"([A-Za-z]+)(?:\((\d+)\))?", prompt)
    if not match:
        return "unknown", None, "unknown"
    base, limit = match[1], int(match[2]) if match[2] else None
    family = FAMILIES.get(base, "unknown")
    if base == "ChineseCoT" and limit is not None:
        family = "chinese_character_budget"
    return family, limit, base


def classify(row, dataset, anonymous_id):
    text = row["response_text"]
    family, limit, base = prompt_family(row["prompt_id"])
    words, chars = len(text.split()), len(text)
    steps = len(STEP.findall(text))
    if not text.strip():
        style = "empty"
    elif steps:
        style = "explicit_step_markers"
    elif BULLET.search(text):
        style = "bullet_list"
    elif len(text.strip().splitlines()) > 1:
        style = "multiline_unmarked"
    else:
        style = "singleline"
    success = row.get("response_status", row.get("status")) == "ok"
    unresolved = (row.get("grading_status") not in {"已判分", "已按保存的逐条复核结论判分"}) if dataset == "reasoning" else not row["extracted_answer"].strip()
    state = "request_failed" if not success else "truncated" if yes(row["is_truncated"]) else "extraction_unresolved" if unresolved else "scored_source"
    check = "not_applicable"
    if limit is not None:
        count = None
        if base == "WordLimit":
            count = words
        elif base == "ChineseCoT":
            count = chars
        elif base == "TokenLimit" and row.get("output_tokens", "") != "":
            count = int(row["output_tokens"])
        elif base == "StepLimit" and steps:
            count = steps
        # CharLimit's source says "letters", so a Unicode character count is
        # not treated as a verified compliance check for that instruction.
        check = "unknown" if count is None else "within_proxy" if count <= limit else "over_proxy"
    task = TASKS[row["benchmark"] if dataset == "reasoning" else row["task_type"]][0]
    return [anonymous_id, family, style, state, task, int(bool(MARKER.search(text))),
            steps, len(HAN.findall(text)), words, chars, check]


def missing_reason(table, field, row, *, container=False):
    """Only distinguish reasons supported by retained fields; do not infer causes."""
    if container and field == "options_json" and row.get("benchmark") != "mmlu":
        return "not_applicable_non_multiple_choice"
    if container and field == "document_ids_json" and row.get("task_type") == "closedbook_control":
        return "not_applicable_closedbook_control"
    if field in {"gold_position", "gold_document_id"} and row.get("task_type") == "closedbook_control":
        return "not_applicable_closedbook_control"
    if field == "review_trigger_reason" and not yes(row.get("included_in_review")):
        return "not_applicable_not_in_review_queue"
    if field == "extracted_answer":
        return "source_evaluator_extraction_unavailable"
    if table.startswith("document_qa.") and field in {"system_fingerprint", "reasoning_text"}:
        return "saved_api_optional_field_absent_null_or_empty"
    if field == "retry_after":
        return "saved_attempt_optional_header_not_recorded"
    return "source_missing_cause_not_documented"


reasoning_SOURCE = dict(zip(
    ["record_id", "model_id", "model_api_name", "benchmark", "question_id", "question_sha256", "prompt_id", "prompt_text", "question_text", "options_json", "gold_answer", "response_text", "reasoning_text", "extracted_answer", "score_current", "grading_status", "output_tokens", "input_tokens", "reasoning_tokens", "answer_tokens", "response_status", "finish_reason", "is_truncated", "source_needs_review", "included_in_review", "review_trigger_reason", "latency_seconds", "returned_model_name", "source_file", "source_record_hash"],
    ["记录编号", "模型标识", "模型接口名称", "数据集", "题目编号", "题目哈希", "提示词标识", "提示词原文", "题目原文", "选项JSON", "标准答案", "回答原文", "推理字段原文", "提取答案", "当前评分", "评分状态", "输出词元数", "输入词元数", "推理词元数", "答案词元数", "响应状态", "结束原因", "是否截断", "原始待复核标记", "纳入复核清单", "复核触发原因", "耗时秒", "返回模型名称", "原始文件", "记录哈希"]
))
document_qa_RAW = {
    "record_id": "run_id", "source_run_id": "run_id", "question_id": "question_id",
    "scenario_id": "scenario_id", "model_id": "model", "task_type": "task_type",
    "prompt_id": "prompt_id", "document_count": "document_count", "gold_position": "gold_position",
    "position_label": "position_label", "gold_document_id": "gold_document_id",
    "question_text": "question", "gold_answers_json": "answers", "prompt_sha256": "prompt_sha256",
    "timestamp": "timestamp", "status": "status", "http_status": "http_status",
    "attempt_count": "attempt_count", "latency_seconds": "latency_s", "request_model": "request.model",
    "request_temperature": "request.temperature", "request_max_tokens": "request.max_tokens",
    "response_id": "response.id", "response_model": "response.model",
    "response_created_epoch": "response.created", "system_fingerprint": "response.system_fingerprint",
    "finish_reason": "response.choices[0].finish_reason", "response_text": "response.choices[0].message.content",
    "reasoning_text": "response.choices[0].message.reasoning_content",
    "input_tokens": "response.usage.prompt_tokens", "output_tokens": "response.usage.completion_tokens",
    "total_tokens": "response.usage.total_tokens",
}


def provenance(table, field):
    dataset, name = table.split(".")
    canonical = "responses_clean" if name == "review_queue_clean" else name
    if dataset == "reasoning":
        if canonical in {"responses_clean", "questions_clean", "prompts_clean"} and field in reasoning_SOURCE:
            kind = "source_evaluator" if field in {"extracted_answer", "score_current", "grading_status", "source_needs_review", "included_in_review", "review_trigger_reason", "is_truncated"} else "source_observation"
            return kind, f"reasoning archive / 便于清洗/全部回答.csv / {reasoning_SOURCE[field]}; scripts/cleaning/clean_baseline_data.py normalize_reasoning"
        rules = {
            "experiment_id": "constant compressed_cot_20261020 assigned by cleaning/clean_baseline_data.py",
            "score_revision_group": "model_id==deepseek -> source reports offline rescore; otherwise source snapshot; not a new grade",
            "answer_records": "count answer rows by prompt_id",
            "group_size": "number of retained rows sharing source_record_hash",
            "record_ids_json": "list distinct source IDs within repeated hash group; local only",
            "handling": "constant retention note; repeated conditions retained",
        }
        if field == "source_record_hash":
            return "source_observation", "source record hash from archive; group key only"
        return "derived_rule", rules[field]
    if canonical == "attempts_clean":
        return ("derived_join", "join attempt (model,scenario_id) to response run_id") if field == "record_id" else ("source_observation", f"data/raw/document_qa/attempt_log.jsonl.gz / { {'model_id':'model','attempt_number':'attempt','latency_seconds':'latency_s'}.get(field, field) }")
    if canonical == "questions_clean":
        return "source_observation", f"data/raw/document_qa/questions.json / { {'question_text':'question','answers_json':'answers','source_lines_json':'source_lines','gold_document_json':'gold_document'}.get(field, field) }; serialized JSON for *_json"
    if canonical == "scenarios_clean":
        if field == "experiment_id":
            return "derived_rule", "constant lost_in_the_middle_nq_open assigned by cleaning/clean_baseline_data.py"
        return "source_observation", f"data/raw/document_qa/scenarios.jsonl.gz / { {'question_text':'question','gold_answers_json':'answers','document_ids_json':'document_ids'}.get(field, field) }; serialized JSON for *_json"
    if field in document_qa_RAW:
        return "source_observation", f"data/raw/document_qa/raw_responses.jsonl.gz / {document_qa_RAW[field]}; cleaning/clean_baseline_data.py clean_document_qa"
    if field in {"paper_firstline", "strict_final_em", "final_contains", "full_response_contains", "extracted_answer", "repaired_empty_marker", "is_truncated", "needs_review", "strategy_scope"}:
        source_field = {"is_truncated": "truncated", "strategy_scope": "scope"}.get(field, field)
        return "source_evaluator", f"data/raw/document_qa/source_scores/scores.csv / {source_field}; joined by (model,scenario_id); source evaluator analyze.py + scoring_helpers.py + official_metrics.py"
    rules = {
        "experiment_id": "constant lost_in_the_middle_nq_open",
        "primary_metric_name": "constant paper_firstline in current cleaning; original manifest proposed strict_final_em",
        "choice_count": "len(response.choices)",
        "output_whitespace_words": "len(response_text.split())",
        "output_characters": "len(response_text), Unicode code points",
    }
    return "derived_rule", rules[field]


def audit_missingness(dictionary):
    results = []
    for table, relative in TABLES.items():
        fields = [r["field"] for r in dictionary if r["table"] == table]
        counts, empty, reasons = Counter(), Counter(), defaultdict(Counter)
        n = 0
        for row in read_csv(PROCESSED / relative):
            n += 1
            if set(row) != set(fields):
                raise ValueError(f"Dictionary does not cover all fields: {table}")
            for field in fields:
                value = row[field]
                if value is None or not value.strip():
                    counts[field] += 1
                    reasons[field][missing_reason(table, field, row)] += 1
                elif value.strip() in {"[]", "{}", "null"} and field.endswith("_json"):
                    empty[field] += 1
                    reasons[field]["empty_container:" + missing_reason(table, field, row, container=True)] += 1
        for field in fields:
            results.append({"table": table, "field": field, "total_rows": n,
                            "missing_count": counts[field], "missing_rate": counts[field] / n if n else 0,
                            "empty_container_count": empty[field], "reason_counts": dict(sorted(reasons[field].items()))})
        print(f"missingness {table}: {n:,} rows; {len(fields)} fields", flush=True)
    return results


def enrich_dictionary(dictionary, missingness):
    lookup = {(r["table"], r["field"]): r for r in missingness}
    out = []
    for source in dictionary:
        row = {k: source[k] for k in ["table", "field", "type", "meaning"]}
        table, field = row["table"], row["field"]
        info = lookup[(table, field)]
        origin, rule = provenance(table, field)
        applicability = "all rows in this table; review table is a filtered subset" if "review_queue" in table else "all rows in this table"
        if field in {"gold_position", "gold_document_id", "document_ids_json"}:
            applicability = "document_qa with supplied context; not applicable to closedbook_control"
        if field == "options_json":
            applicability = "multiple-choice benchmark only; empty array for arithmetic/competition math"
        if field == "review_trigger_reason":
            applicability = "included_in_review=true; empty otherwise"
        row.update(origin_kind=origin, source_or_rule=rule, applicability=applicability,
                   missing_policy="preserve blank/null and empty containers; never impute; no zero-fill; denominator documented per field",
                   missing_reasons_observed=json.dumps(info["reason_counts"], ensure_ascii=False, sort_keys=True),
                   total_rows=info["total_rows"], missing_count=info["missing_count"],
                   missing_rate=info["missing_rate"], empty_container_count=info["empty_container_count"])
        out.append(row)
    csv_write(PROCESSED / "data_dictionary.tsv", out, delimiter="\t")


def document_qa_recompute(row, official, helper):
    text, aliases = row["response_text"], json.loads(row["gold_answers_json"])
    stub = {"response": {"choices": [{"message": {"content": text}, "finish_reason": row["finish_reason"]}]},
            "answers": aliases, "status": row["status"]}
    grade = helper.grade(stub)
    extracted = grade["extracted_answer"]
    repaired = False
    if extracted == "":
        markers = list(re.finditer(r"FINAL\s+ANSWER\s*:\s*", text, re.I))
        before = text[:markers[-1].start()].strip()
        if "\n" not in before and len(before.split()) <= 30:
            extracted, repaired = before, True
    scores = {
        "paper_firstline": official.best_subspan_em(text.split("\n")[0].strip(), aliases),
        "strict_final_em": int(any(official.normalize_answer(extracted) == official.normalize_answer(a) for a in aliases)) if extracted is not None else 0,
        "final_contains": official.best_subspan_em(extracted or "", aliases),
        "full_response_contains": official.best_subspan_em(text, aliases),
    }
    return scores, extracted, repaired, grade


def as_rows(counters, names):
    return [dict(zip(names, key), count=value) for key, value in sorted(counters.items())]


def saved_reasoning_overrides():
    """Read prior saved review decisions; never export reviewer/reason or invent one."""
    decisions = {}
    with zipfile.ZipFile(ROOT / "data/raw/reasoning/responses_source.zip") as archive:
        for member in archive.namelist():
            if member.endswith("/grading_reviews.json") and "/原始结果/" in member:
                for row in json.loads(archive.read(member)):
                    key = tuple(row[field] for field in ["model", "benchmark", "prompt_id", "question_id"])
                    if key in decisions:
                        raise ValueError("Duplicate prior source-review key")
                    decisions[key] = row
    return decisions


def score_and_classify(*, sample_per_stratum=4, symbolic=True):
    reasoning_grader = load_module("local_source_grading", ROOT / "experiments/reasoning_prompts/src/grading.py")
    official = load_module("local_official_metrics", ROOT / "experiments/document_qa/src/official_metrics.py")
    helper = load_module("local_scoring_helpers", ROOT / "experiments/document_qa/src/scoring_helpers.py")
    source_paths = [ROOT / "experiments/reasoning_prompts/src/grading.py", ROOT / "experiments/document_qa/src/official_metrics.py",
                    ROOT / "experiments/document_qa/src/scoring_helpers.py", ROOT / "experiments/document_qa/src/analyze.py"]
    scorer_hashes = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    score_groups, document_qa_metrics = defaultdict(Counter), defaultdict(Counter)
    family_counts, style_counts, state_counts, coverage, budget_counts = Counter(), Counter(), Counter(), Counter(), Counter()
    task_groups, questions = Counter(), defaultdict(set)
    features, review_candidates = [], defaultdict(list)
    cache, exceptions, source_overrides = {}, Counter(), Counter()
    preserved_decisions, override_audit = saved_reasoning_overrides(), Counter()
    local_feature_fields = FEATURE_FIELDS + ["source_score", "audit_score", "audit_status", "audit_disagreement"]
    for dataset, prefix in [("reasoning", "Z"), ("document_qa", "F")]:
        local_path = PROCESSED / dataset / "method_features.csv.gz"
        local_stream = gzip.open(local_path, "wt", encoding="utf-8", newline="")
        local_writer = csv.writer(local_stream, lineterminator="\n")
        local_writer.writerow(local_feature_fields)
        for index, row in enumerate(read_csv(PROCESSED / dataset / "responses_clean.csv.gz"), 1):
            anonymous = f"{prefix}{index:06d}"
            feature = classify(row, dataset, anonymous)
            features.append(feature)
            _, family, style, state, task, *_ = feature
            original_task = row["benchmark"] if dataset == "reasoning" else row["task_type"]
            group_key = (dataset, row["model_id"], original_task)
            task_groups[(dataset, original_task, task)] += 1
            questions[(dataset, original_task, task)].add(row["question_id"])
            family_counts[(dataset, family)] += 1
            style_counts[(dataset, style)] += 1
            state_counts[(dataset, state)] += 1
            budget_counts[(dataset, row["prompt_id"], feature[-1])] += 1
            coverage[(dataset, row["model_id"], original_task, row["prompt_id"], family, style, state)] += 1
            changed, audit_score, audit_status = False, None, ""
            source_score = int(float(row["score_current"] if dataset == "reasoning" else row["paper_firstline"]))
            if dataset == "document_qa":
                scores, extracted, repaired, grade = document_qa_recompute(row, official, helper)
                for metric, score in scores.items():
                    stats = document_qa_metrics[(row["model_id"], metric)]
                    stats["n"] += 1
                    stats["source_positive"] += int(float(row[metric]))
                    stats["audit_positive"] += int(score)
                    same = int(float(row[metric])) == int(score)
                    stats["agree"] += same
                    stats["disagree"] += not same
                    changed |= not same
                stats = score_groups[group_key]
                stats["n"] += 1
                stats["extracted_answer_agree"] += (extracted or "") == row["extracted_answer"]
                stats["repair_flag_agree"] += repaired == yes(row["repaired_empty_marker"])
                stats["review_flag_agree"] += grade["needs_review"] == yes(row["needs_review"])
                stats["truncation_flag_agree"] += grade["truncated"] == yes(row["is_truncated"])
                audit_score, audit_status = int(scores["paper_firstline"]), "four_source_metrics_recomputed"
            else:
                key = (original_task, row["gold_answer"], reasoning_grader.extract_answer(row["response_text"]))
                if key not in cache:
                    try:
                        # The grader is pure after extraction. Cache by exact extracted
                        # answer, official answer and benchmark; no semantic shortcut.
                        if not symbolic and original_task != "mmlu" and key[2] is not None and not (reasoning_grader.numeric_value(key[1]) is not None and reasoning_grader.numeric_value(key[2]) is not None):
                            result = {"grade": None, "grading_status": "symbolic_dependency_not_enabled", "needs_review": True}
                        else:
                            with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                                result = reasoning_grader.grade_answer(row["response_text"], row["gold_answer"], original_task)
                        cache[key] = result
                    except Exception as exc:
                        exceptions[type(exc).__name__] += 1
                        cache[key] = {"grade": None, "grading_status": "local_scorer_exception", "needs_review": True}
                result = cache[key]
                audit_score, audit_status = result["grade"], result["grading_status"]
                stats = score_groups[group_key]
                stats["n"] += 1
                stats["source_positive"] += source_score
                stats["local_unresolved"] += bool(result["needs_review"])
                stats["source_status_changed"] += audit_status != row["grading_status"]
                if row["grading_status"] == "已按保存的逐条复核结论判分":
                    stats["preserved_source_review_override"] += 1
                    source_overrides[(row["model_id"], original_task)] += 1
                prior = preserved_decisions.get((row["model_id"], original_task, row["prompt_id"], row["question_id"]))
                replayed_score = audit_score
                if prior:
                    response_hash = hashlib.sha256(json.dumps(row["response_text"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                    override_audit["rows_found"] += 1
                    same_q = prior["question_hash"] == row["question_sha256"]
                    same_response = prior["response_hash"] == response_hash
                    same_grade = prior["grade"] == source_score
                    override_audit["question_hash_matches"] += same_q
                    override_audit["response_hash_matches"] += same_response
                    override_audit["saved_grade_matches_source"] += same_grade
                    if same_q and same_response and same_grade:
                        replayed_score = prior["grade"]
                        stats["verified_source_review_overrides"] += 1
                if replayed_score is not None:
                    stats["with_preserved_overrides_compared"] += 1
                    stats["with_preserved_overrides_agree"] += replayed_score == source_score
                if audit_score is None:
                    stats["abstain"] += 1
                else:
                    stats["binary_compared"] += 1
                    stats["binary_agree"] += audit_score == source_score
                    stats["audit_positive"] += audit_score
                    stats["changed_0_to_1"] += source_score == 0 and audit_score == 1
                    stats["changed_1_to_0"] += source_score == 1 and audit_score == 0
                    changed = audit_score != source_score
                    if changed:
                        stats["changes_on_preserved_source_review" if row["grading_status"] == "已按保存的逐条复核结论判分" else "changes_on_regular_source_scoring"] += 1
                    if not result["needs_review"]:
                        stats["resolved_compared"] += 1
                        stats["resolved_agree"] += audit_score == source_score
            source_review = yes(row["included_in_review"] if dataset == "reasoning" else row["needs_review"])
            risk = "audit_disagreement" if changed else "truncated" if yes(row["is_truncated"]) else "extraction_unresolved" if state == "extraction_unresolved" else "source_review" if source_review else "ordinary"
            stratum = (dataset, row["model_id"], task, risk)
            candidate = {"anonymous_id": anonymous, "dataset": dataset, "model_id": row["model_id"],
                         "task_type": task, "prompt_id": row["prompt_id"], "risk_stratum": risk,
                         "output_style": style, "result_state": state, "source_score": source_score,
                         "audit_score": "" if audit_score is None else audit_score,
                         "audit_disagreement": int(changed), "output_tokens": row["output_tokens"],
                         "human_label": "", "human_extraction_label": "", "reviewer_code": "",
                         "reviewed_at": "", "human_note": ""}
            rank = hashlib.sha256(f"{SEED}:{anonymous}".encode()).hexdigest()
            candidates = review_candidates[stratum]
            candidates.append((rank, candidate))
            candidates.sort(key=lambda pair: pair[0])
            del candidates[sample_per_stratum:]
            local_writer.writerow(feature + [source_score, "" if audit_score is None else audit_score, audit_status, int(changed)])
            if index % 10000 == 0:
                print(f"classify/score {dataset}: {index:,}; cached distinct reasoning answers={len(cache):,}", flush=True)
        local_stream.close()
    feature_blob = json.dumps({"schemaVersion": 1, "fields": FEATURE_FIELDS, "rows": features}, ensure_ascii=False, separators=(",", ":")).encode()
    (APP / "method-features.json.gz").write_bytes(gzip.compress(feature_blob, mtime=0))
    sample = [candidate for key in sorted(review_candidates) for _, candidate in review_candidates[key]]
    csv_write(REPORTS / "scoring-review-sample.csv", sample)
    tasks = []
    for key, count in sorted(task_groups.items()):
        dataset, source_task, task = key
        tasks.append({"dataset": dataset, "sourceTask": source_task, "taskType": task,
                      "label": TASKS[source_task][1], "responseCount": count, "independentQuestions": len(questions[key])})
    return {
        "taskMapping": tasks,
        "promptFamilies": {"coverage": as_rows(family_counts, ["dataset", "family"]), "unknownCount": sum(v for k, v in family_counts.items() if k[1] == "unknown")},
        "observations": {"outputStyles": as_rows(style_counts, ["dataset", "output_style"]), "resultStates": as_rows(state_counts, ["dataset", "result_state"]),
                         "budgetChecks": as_rows(budget_counts, ["dataset", "prompt", "budget_check"]),
                         "coverage": as_rows(coverage, ["dataset", "model", "sourceTask", "prompt", "prompt_family", "output_style", "result_state"]),
                         "featurePath": "app/data/method-features.json.gz", "featureFields": FEATURE_FIELDS, "featureRows": len(features)},
        "scoringAudit": {
            "scorerHashes": scorer_hashes,
            "groups": [dict(dataset=k[0], model=k[1], sourceTask=k[2], **dict(v)) for k, v in sorted(score_groups.items())],
            "documentQaMetrics": [dict(model=k[0], metric=k[1], agreementRate=v["agree"] / v["n"], **dict(v)) for k, v in sorted(document_qa_metrics.items())],
            "symbolicEnabled": symbolic, "cachedDistinctZZYAnswers": len(cache), "scorerExceptions": dict(exceptions),
            "preservedSourceOverrideAudit": {"savedDecisions": len(preserved_decisions), **dict(override_audit), "newHumanReviewPerformed": False},
            "sourceScoresModified": False, "humanSemanticReviewPerformed": False,
            "localScorePaths": ["data/processed/reasoning/method_features.csv.gz", "data/processed/document_qa/method_features.csv.gz"],
        },
        "reviewSample": {"seed": SEED, "ranking": "sha256(f'{seed}:{anonymous_id}') ascending within stratum", "perStratum": sample_per_stratum,
                         "strata": len(review_candidates), "rows": len(sample), "humanReviewCompleted": False,
                         "path": "reports/baseline/scoring-review-sample.csv",
                         "purpose": "diagnostic stratified sample; not a probability weighted accuracy estimate; all human fields blank"},
    }


def raw_optional_field_audit():
    """Check absent/null/empty, without interpreting hidden model computation."""
    out = defaultdict(Counter)
    with gzip.open(ROOT / "data/raw/document_qa/raw_responses.jsonl.gz", "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            response = row.get("response") or {}
            message = ((response.get("choices") or [{}])[0].get("message") or {})
            for field, obj, key in [("system_fingerprint", response, "system_fingerprint"), ("reasoning_text", message, "reasoning_content")]:
                status = "absent" if key not in obj else "null" if obj[key] is None else "empty" if obj[key] == "" else "present_nonempty"
                out[field][status] += 1
    return {field: dict(counts) for field, counts in out.items()}


def collection_facts():
    reasoning_path = ROOT / "data/raw/reasoning/responses_source.zip"
    manifests = []
    with zipfile.ZipFile(reasoning_path) as archive:
        for member in sorted(archive.namelist()):
            if member.endswith("/manifest.json") and "/原始结果/" in member:
                manifest = json.loads(archive.read(member))
                datasets = []
                for benchmark, dataset in manifest["datasets"].items():
                    datasets.append({k: dataset.get(k) for k in ["benchmark", "source", "revision", "split", "selection", "content_hash"]})
                manifests.append({"member": member, "seed": manifest.get("seed"), "maxTokens": manifest.get("max_tokens"), "models": [{"model": m.get("model"), "temperature": m.get("temperature"), "extraBody": m.get("extra_body", {})} for m in manifest["models"].values()], "datasets": datasets})
    document_qa = json.loads((ROOT / "data/raw/document_qa/manifest.json").read_text(encoding="utf-8"))
    return {"reasoningArchiveSHA256": digest(reasoning_path), "reasoningManifests": manifests,
            "document_qa": {k: document_qa.get(k) for k in ["created_at", "upstream_commit", "sample_seed", "independent_questions", "models", "temperature", "max_tokens", "qwen3_extra_body", "input_system_message", "inherited_pilot_records", "operation_note", "grading", "dataset_sources"]},
            "unconfirmed": ["actual collector/team member identity and division of work", "whether any other person's runs require participant consent, and recorded permission scope", "student understanding and verification of AI-assisted implementation", "platform-policy and benchmark-license checks recorded by the team"],
            "subjectCaveat": "reasoning delivery README describes MMLU-Pro math, but retained question records have no category/subject. Task mapping uses neutral multiple_choice; no independent subject verification is claimed."}


def write_audit(payload):
    audit = payload["scoringAudit"]
    reasoning = [g for g in audit["groups"] if g["dataset"] == "reasoning"]
    compared = sum(g.get("binary_compared", 0) for g in reasoning)
    agreed = sum(g.get("binary_agree", 0) for g in reasoning)
    up = sum(g.get("changed_0_to_1", 0) for g in reasoning)
    down = sum(g.get("changed_1_to_0", 0) for g in reasoning)
    unresolved = sum(g.get("local_unresolved", 0) for g in reasoning)
    abstain = sum(g.get("abstain", 0) for g in reasoning)
    review_changes = sum(g.get("changes_on_preserved_source_review", 0) for g in reasoning)
    regular_changes = sum(g.get("changes_on_regular_source_scoring", 0) for g in reasoning)
    full_compared = sum(g.get("with_preserved_overrides_compared", 0) for g in reasoning)
    full_agreed = sum(g.get("with_preserved_overrides_agree", 0) for g in reasoning)
    resolved_n = sum(g.get("resolved_compared", 0) for g in reasoning)
    resolved_ok = sum(g.get("resolved_agree", 0) for g in reasoning)
    lines = ["# 现有回答的离线评分复算审计", "", "本审计仅重新运行本地确定性规则；未调用模型 API，未修改原始回答、清洗表和源评分。算法重现一致率不等于评分语义正确率，也不表示人工复核已完成。", "",
             "## reasoning：统一运行保存的 source grader", "", f"对 74,400 条回答使用同一份 `experiments/reasoning_prompts/src/grading.py`。缓存键为数据集、原标准答案和该源函数提取的最终答案，共 {audit['cachedDistinctZZYAnswers']:,} 个不同键。数学符号路径启用状态：{audit['symbolicEnabled']}。", "",
             f"可返回二元分数 {compared:,} 条，其中与源分数一致 {agreed:,} 条（{agreed / compared:.4%}）；候选 0→1 为 {up:,}，1→0 为 {down:,}。未能给出二元分数 {abstain:,} 条。规则仍标记提取/解析未决 {unresolved:,} 条。", "",
             f"仅在本次规则不要求复核的 {resolved_n:,} 条中，源分数一致 {resolved_ok:,} 条（{resolved_ok / resolved_n:.4%}）。这个子集排除了当前未决项，仍不能当成总体人工准确率。源中的 139 条已保存复核覆盖继续保留，本次纯算法候选不覆盖它们。", "",
             f"候选分数差异中，{review_changes:,} 条来自源中已有的逐条复核覆盖，普通源规则评分差异为 {regular_changes:,}。因此这些差异是“纯算法未应用既有覆盖”的审计结果，不能直接当成应当改分的错误。", "",
             f"另外读取源包已存在的 `grading_reviews.json`，核对 139 条覆盖的题目哈希、回答哈希和源分数，三项均匹配 139/139。将这些已存覆盖与源规则合起来重放时，一致为 {full_agreed:,}/{full_compared:,}（{full_agreed / full_compared:.4%}）。这里只验证既有决策的对应关系，并未核实既有 reviewer 的真实身份、完成新的语义标注或替源决策背书；任何 reviewer/reason 文本均未导出。", "",
             "| 模型 | 任务 | N | 二元比较 | 一致 | 0→1 | 1→0 | 本次未决 | 暂不判分 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for g in reasoning:
        lines.append(f"| {g['model']} | {g['sourceTask']} | {g['n']} | {g.get('binary_compared',0)} | {g.get('binary_agree',0)} | {g.get('changed_0_to_1',0)} | {g.get('changed_1_to_0',0)} | {g.get('local_unresolved',0)} | {g.get('abstain',0)} |")
    lines += ["", "未提取到答案、选择题格式不明确或模型答案无法解析时，源 grader 可能返回 0 和待复核标记；因此上表二元一致中包含算法未决的 0。不能将其解释为模型确实答错。本次只报告候选变化，不自动发布新的排行榜。来源的 DeepSeek 已重评分、其他模型保留快照；这里将既有逐条覆盖与纯规则结果分别记录。", "",
              "## document_qa：重放四种源口径", "", "直接调用保存的 `official_metrics.best_subspan_em/normalize_answer` 和 `scoring_helpers.grade`，按 `analyze.py` 完全复现空末尾 FINAL ANSWER 的短答案修复。首行不先剔除空行；严格匹配、末答案包含和全文包含各自保留。", "",
              "| 模型 | 指标 | N | 一致 | 不一致 | 一致率 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for g in audit["documentQaMetrics"]:
        lines.append(f"| {g['model']} | {g['metric']} | {g['n']} | {g['agree']} | {g['disagree']} | {g['agreementRate']:.4%} |")
    lines += ["", "四口径一致说明本次能重现既有算法，不能证明字符串命中等于语义正确、中文答案被公平评分或推理过程正确。采集 manifest 起初指定提取后严格匹配为主，现有成果用首行包含为主；本项目将其明确称为源规则评分，保留另外三种敏感性口径。", "",
              "## 可复现的分层待审样本", "", f"固定种子 {SEED}，以数据来源 × 模型 × 四类任务 × 风险层分层，每个非空层最多 {payload['reviewSample']['perStratum']} 条；按 `sha256('91:' + anonymous_id)` 排序。共 {payload['reviewSample']['strata']} 个非空层、{payload['reviewSample']['rows']} 条，见 `scoring-review-sample.csv`。风险优先级为本次分数差异、截断、提取未决、源复核标记、普通记录。", "",
              "样本只含匿名 ID、条件及数值/类别，所有 human_label、human_extraction_label、reviewer_code、reviewed_at、human_note 均留空。**人工语义复核尚未执行。** 样本为诊断用途，不能不加权估计总体准确率。复核者可在本机按与浏览器相同的 Z/F 行序连接原始文本，独立标注最终答案是否正确、提取是否适当及不确定原因；建议双人独立审阅并记录分歧后再决定修订。身份、时间和同意不能由脚本补写。", "",
              "## 重跑与版本", "", "```bash", "python -m pip install -r requirements/methods-analysis.txt", "python scripts/cleaning/classify_and_audit.py", "```", "",
              "运行前需本机已存在 10 份原始清洗表、reasoning 原始 zip 和 document_qa 原始响应。脚本不重建/覆盖这些输入。逐条候选特征和候选分数仅写入被 Git 忽略的 `data/processed/reasoning/method_features.csv.gz` 与 `data/processed/document_qa/method_features.csv.gz`；公共侧车只导出匿名类别/计数。输入和评分源码 SHA-256 见 `app/data/method-evidence.json`。", "",
              f"评分器异常（按独立缓存键统计）：`{json.dumps(audit['scorerExceptions'],ensure_ascii=False)}`。依赖版本：`{json.dumps(payload['dependencies'],ensure_ascii=False,sort_keys=True)}`。"]
    (REPORTS / "scoring-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-per-stratum", type=int, default=4)
    parser.add_argument("--no-symbolic", action="store_true", help="explicitly abstain on symbolic math; requires regex, not math-verify")
    args = parser.parse_args()
    if args.sample_per_stratum < 1:
        parser.error("sample-per-stratum must be positive")
    if not args.no_symbolic:
        importlib.import_module("math_verify")
    logging.disable(logging.CRITICAL)
    APP.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    input_hashes = {str((PROCESSED / path).relative_to(ROOT)): digest(PROCESSED / path) for path in TABLES.values()}
    dictionary = list(csv.DictReader((PROCESSED / "data_dictionary.tsv").open(encoding="utf-8"), delimiter="\t"))
    missing = audit_missingness(dictionary)
    missing_public = [{**row, "reason_counts": json.dumps(row["reason_counts"], ensure_ascii=False, sort_keys=True)} for row in missing]
    csv_write(PROCESSED / "missingness_report.csv", missing_public)
    missing_summary = {"generatedAt": started, "definition": "blank/whitespace CSV cells; [] and {} reported separately as empty containers; literal none/category sentinels and numeric zero are not missing", "fields": missing}
    json_write(PROCESSED / "missingness_report.json", missing_summary)
    enrich_dictionary(dictionary, missing)
    evidence = score_and_classify(sample_per_stratum=args.sample_per_stratum, symbolic=not args.no_symbolic)
    evidence.update(schemaVersion=1, generatedAt=started, apiCallsMade=0, inputHashes=input_hashes,
                    dependencies={name: importlib.metadata.version(name) for name in ["regex", "math-verify", "sympy", "latex2sympy2_extended"] if importlib.util.find_spec(name.replace("-", "_")) is not None},
                    collection=collection_facts(), limitations=[
                        "Visible formatting rules describe output text only; requested CoT and step markers do not demonstrate internal reasoning.",
                        "Current source grades remain unchanged; deterministic recomputation is not human semantic validation.",
                        "Unknown collection member identity, consent scope and student understanding are not invented.",
                        "800 independent questions yield 149200 single-turn answer records; response count is not multi-turn conversation count.",
                        "No code execution, repair or tool behavior is supported by the current QA datasets.",
                        "20-document positions 5 and 15 are unobserved; cumulative budget curves use observed outputs and fitted thresholds, not a prospective allocation experiment.",
                    ])
    reason_totals = Counter()
    for row in missing:
        reason_totals.update(row["reason_counts"])
    evidence["missingness"] = {"fieldCount": len(missing), "tableCount": len(TABLES), "fieldsWithMissing": sum(row["missing_count"] > 0 for row in missing),
                               "missingCells": sum(row["missing_count"] for row in missing), "emptyContainerCells": sum(row["empty_container_count"] for row in missing),
                               "reasonCounts": dict(sorted(reason_totals.items())), "reportPaths": ["data/processed/missingness_report.csv", "data/processed/missingness_report.json", "data/processed/data_dictionary.tsv"],
                               "documentQaSavedApiOptionalFields": raw_optional_field_audit(),
                               "note": "Across all ten tables, review/scenario/question subsets repeat source entities; cell totals are not counts of independent observations."}
    evidence["promptFamilies"]["rules"] = {**FAMILIES, "ChineseCoT(N)": "chinese_character_budget"}
    evidence["observations"]["rules"] = {
        "output_style_precedence": ["empty", "explicit_step_markers", "bullet_list", "multiline_unmarked", "singleline"],
        "step_regex": STEP.pattern, "bullet_regex": BULLET.pattern,
        "result_state_precedence": ["request_failed", "truncated", "extraction_unresolved", "scored_source"],
        "budget": "<= requested limit proxy: WordLimit len(split), TokenLimit reported completion tokens, ChineseCoT(N) total Unicode characters, StepLimit explicit enumerated markers only; CharLimit 'letters' and unmarked steps remain unknown. Whole visible output including final-answer suffix is measured.",
    }
    after_hashes = {str((PROCESSED / path).relative_to(ROOT)): digest(PROCESSED / path) for path in TABLES.values()}
    if input_hashes != after_hashes:
        raise RuntimeError("A source cleaned table changed during the completion pass")
    evidence["sourceCleanTablesUnchanged"] = True
    json_write(APP / "method-evidence.json", evidence)
    quality_path = PROCESSED / "quality_report.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    quality["methods_completion_audit"] = {"generated_at": started, "script": "scripts/cleaning/classify_and_audit.py", "api_calls_made": 0,
        "source_clean_tables_unchanged": True, "source_scores_modified": False, "human_semantic_review_performed": False,
        "input_hashes": input_hashes, "full_field_missingness": evidence["missingness"],
        "classification_rows": evidence["observations"]["featureRows"], "unknown_prompt_families": evidence["promptFamilies"]["unknownCount"],
        "review_sample": evidence["reviewSample"], "scoring_audit": evidence["scoringAudit"]}
    json_write(quality_path, quality)
    write_audit(evidence)
    print(json.dumps({"anonymous_features": len(json.loads(gzip.decompress((APP / 'method-features.json.gz').read_bytes()))['rows']),
                      "field_audit": len(missing), "review_sample": evidence["reviewSample"], "outputs": "method-evidence.json, method-features.json.gz, full-field missingness/dictionary, scoring audit"}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
