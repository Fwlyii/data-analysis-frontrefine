from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT = ROOT / "data" / "processed"
reasoning_ZIP = ROOT / "data" / "raw" / "reasoning" / "responses_source.zip"
document_qa = ROOT / "data" / "raw" / "document_qa"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_bool(value: str | bool | None) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes"}:
        return True
    if s in {"0", "false", "no"}:
        return False
    raise ValueError(f"Invalid boolean: {value!r}")


def parse_int(value: str | int | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def parse_float(value: str | int | float | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def parse_json_cell(value: str, expected_type=None):
    obj = json.loads(value)
    if expected_type is not None and not isinstance(obj, expected_type):
        raise ValueError(f"Expected {expected_type}, got {type(obj)}")
    return obj


def json_cell(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json_cell(value)
    return str(value)


@contextmanager
def csv_sink(path: Path, fields: list[str], compressed: bool = True):
    path.parent.mkdir(parents=True, exist_ok=True)
    if compressed:
        stream = gzip.open(path, "wt", encoding="utf-8", newline="", compresslevel=6)
    else:
        stream = path.open("w", encoding="utf-8", newline="")
    try:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        yield writer
    finally:
        stream.close()


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reasoning_bool(value: str) -> bool:
    out = parse_bool(value)
    if out is None:
        raise ValueError("Required boolean is blank")
    return out


def normalize_reasoning(row: dict[str, str]) -> dict:
    options = parse_json_cell(row["选项JSON"], list)
    score = parse_int(row["当前评分"])
    if score not in (0, 1):
        raise ValueError(f"Invalid reasoning score {row['当前评分']!r} for {row['记录编号']}")
    model = row["模型标识"].strip()
    return {
        "record_id": row["记录编号"].strip(),
        "experiment_id": "compressed_cot_20261020",
        "model_id": model,
        "model_api_name": row["模型接口名称"].strip() or None,
        "benchmark": row["数据集"].strip().lower(),
        "question_id": row["题目编号"].strip(),
        "question_sha256": row["题目哈希"].strip().lower(),
        "prompt_id": row["提示词标识"].strip(),
        "prompt_text": row["提示词原文"],
        "question_text": row["题目原文"],
        "options_json": json_cell(options),
        "gold_answer": row["标准答案"].strip() or None,
        "response_text": row["回答原文"],
        "reasoning_text": row["推理字段原文"] or None,
        "extracted_answer": row["提取答案"] or None,
        "score_current": score,
        "grading_status": row["评分状态"].strip() or None,
        "score_revision_group": (
            "offline_rescore_exists_at_model_group_level" if model == "deepseek"
            else "source_snapshot_no_offline_rescore_reported"
        ),
        "output_tokens": parse_int(row["输出词元数"]),
        "input_tokens": parse_int(row["输入词元数"]),
        "reasoning_tokens": parse_int(row["推理词元数"]),
        "answer_tokens": parse_int(row["答案词元数"]),
        "response_status": row["响应状态"].strip().lower(),
        "finish_reason": row["结束原因"].strip() or None,
        "is_truncated": reasoning_bool(row["是否截断"]),
        "source_needs_review": reasoning_bool(row["原始待复核标记"]),
        "included_in_review": reasoning_bool(row["纳入复核清单"]),
        "review_trigger_reason": row["复核触发原因"].strip() or None,
        "latency_seconds": parse_float(row["耗时秒"]),
        "returned_model_name": row["返回模型名称"].strip() or None,
        "source_file": row["原始文件"].strip() or None,
        "source_record_hash": row["记录哈希"].strip().lower(),
    }


reasoning_FIELDS = [
    "record_id", "experiment_id", "model_id", "model_api_name", "benchmark", "question_id",
    "question_sha256", "prompt_id", "prompt_text", "question_text", "options_json", "gold_answer",
    "response_text", "reasoning_text", "extracted_answer", "score_current", "grading_status",
    "score_revision_group", "output_tokens", "input_tokens", "reasoning_tokens", "answer_tokens",
    "response_status", "finish_reason", "is_truncated", "source_needs_review", "included_in_review",
    "review_trigger_reason", "latency_seconds", "returned_model_name", "source_file", "source_record_hash",
]


def clean_reasoning():
    out = OUT / "reasoning"
    out.mkdir(parents=True, exist_ok=True)
    checksum_path = reasoning_ZIP.parent / "SHA256SUMS.txt"
    expected_hash = checksum_path.read_text(encoding="utf-8").split()[0].lower()
    actual_hash = sha256_file(reasoning_ZIP)
    if actual_hash != expected_hash:
        raise RuntimeError(f"reasoning source archive checksum mismatch: {actual_hash} != {expected_hash}")

    source_csv = "四模型回答数据_20261020/便于清洗/全部回答.csv"
    question_map = {}
    prompt_map = {}
    record_ids = set()
    hash_groups = defaultdict(list)
    distributions = Counter()
    model_counts = Counter()
    benchmark_counts = Counter()
    grading_status_counts = Counter()
    null_counts = Counter()
    count = review_count = trunc_count = source_review_count = extracted_null_count = 0

    with zipfile.ZipFile(reasoning_ZIP) as z, z.open(source_csv) as binary:
        text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        with csv_sink(out / "responses_clean.csv.gz", reasoning_FIELDS) as all_writer, \
             csv_sink(out / "review_queue_clean.csv.gz", reasoning_FIELDS) as review_writer:
            for source_row in reader:
                row = normalize_reasoning(source_row)
                count += 1
                rid = row["record_id"]
                if rid in record_ids:
                    raise RuntimeError(f"Duplicate reasoning record_id: {rid}")
                record_ids.add(rid)
                model_counts[row["model_id"]] += 1
                benchmark_counts[row["benchmark"]] += 1
                distributions[(row["model_id"], row["benchmark"], row["prompt_id"])] += 1
                grading_status_counts[row["grading_status"]] += 1
                hash_groups[row["source_record_hash"]].append(rid)
                if row["included_in_review"]:
                    review_count += 1
                    review_writer.writerow({k: csv_value(v) for k, v in row.items()})
                if row["is_truncated"]:
                    trunc_count += 1
                if row["source_needs_review"]:
                    source_review_count += 1
                if row["extracted_answer"] is None:
                    extracted_null_count += 1
                for f in ["reasoning_text", "reasoning_tokens", "answer_tokens", "review_trigger_reason"]:
                    if row[f] is None:
                        null_counts[f] += 1
                all_writer.writerow({k: csv_value(v) for k, v in row.items()})

                qkey = (row["benchmark"], row["question_id"])
                qval = {
                    "benchmark": row["benchmark"],
                    "question_id": row["question_id"],
                    "question_sha256": row["question_sha256"],
                    "question_text": row["question_text"],
                    "options_json": row["options_json"],
                    "gold_answer": row["gold_answer"],
                }
                if qkey in question_map and question_map[qkey] != qval:
                    raise RuntimeError(f"Inconsistent question metadata for {qkey}")
                question_map[qkey] = qval

                pkey = row["prompt_id"]
                pval = row["prompt_text"]
                if pkey in prompt_map and prompt_map[pkey] != pval:
                    raise RuntimeError(f"Inconsistent prompt text for {pkey}")
                prompt_map[pkey] = pval

    if count != 74400 or review_count != 3920 or trunc_count != 3309:
        raise RuntimeError(f"Unexpected reasoning totals: rows={count}, review={review_count}, truncated={trunc_count}")
    if len(question_map) != 600 or len(prompt_map) != 31:
        raise RuntimeError(f"Unexpected reasoning dimensions: questions={len(question_map)}, prompts={len(prompt_map)}")
    if set(model_counts.values()) != {18600} or set(benchmark_counts.values()) != {24800}:
        raise RuntimeError("Unexpected reasoning model/benchmark coverage")
    if len(distributions) != 4 * 3 * 31 or set(distributions.values()) != {200}:
        raise RuntimeError("Unexpected reasoning model x benchmark x prompt coverage")

    with csv_sink(out / "questions_clean.csv", ["benchmark", "question_id", "question_sha256", "question_text", "options_json", "gold_answer"], compressed=False) as w:
        for key in sorted(question_map):
            w.writerow({k: csv_value(v) for k, v in question_map[key].items()})
    prompt_counts = Counter()
    for (model, benchmark, prompt), n in distributions.items():
        prompt_counts[prompt] += n
    with csv_sink(out / "prompts_clean.csv", ["prompt_id", "prompt_text", "answer_records"], compressed=False) as w:
        for prompt in sorted(prompt_map):
            w.writerow({"prompt_id": prompt, "prompt_text": prompt_map[prompt], "answer_records": prompt_counts[prompt]})

    duplicate_groups = [(h, ids) for h, ids in hash_groups.items() if len(ids) > 1]
    with csv_sink(out / "repeated_hash_audit.csv", ["source_record_hash", "group_size", "record_ids_json", "handling"], compressed=False) as w:
        for h, ids in sorted(duplicate_groups):
            w.writerow({
                "source_record_hash": h,
                "group_size": len(ids),
                "record_ids_json": json_cell(ids),
                "handling": "retained_all_rows; repeated response hash across distinct experimental conditions is not a duplicate observation",
            })

    return {
        "source_archive": str(reasoning_ZIP.relative_to(ROOT)),
        "source_sha256": actual_hash,
        "source_expected_sha256": expected_hash,
        "rows": count,
        "unique_record_ids": len(record_ids),
        "unique_source_record_hashes": len(hash_groups),
        "repeated_hash_groups": len(duplicate_groups),
        "records_in_repeated_hash_groups": sum(len(ids) for _, ids in duplicate_groups),
        "models": dict(sorted(model_counts.items())),
        "benchmarks": dict(sorted(benchmark_counts.items())),
        "independent_questions": len(question_map),
        "questions_by_benchmark": {b: sum(1 for q in question_map if q[0] == b) for b in sorted({q[0] for q in question_map})},
        "prompt_strategies": len(prompt_map),
        "records_per_model_benchmark_prompt_group": 200,
        "review_included": review_count,
        "source_needs_review": source_review_count,
        "truncated": trunc_count,
        "extracted_answer_null": extracted_null_count,
        "null_counts_selected_fields": dict(null_counts),
        "grading_status_counts": dict(grading_status_counts),
        "score_caveat": "Current grades are preserved. The source package reports an offline rescore for the DeepSeek model group, while other model groups retain their source snapshot; these scores are not harmonized by this cleaning pass.",
        "output_tables": {
            "responses_clean.csv.gz": count,
            "review_queue_clean.csv.gz": review_count,
            "questions_clean.csv": len(question_map),
            "prompts_clean.csv": len(prompt_map),
            "repeated_hash_audit.csv": len(duplicate_groups),
        },
    }


document_qa_RESPONSE_FIELDS = [
    "record_id", "experiment_id", "source_run_id", "question_id", "scenario_id", "model_id", "task_type",
    "prompt_id", "strategy_scope", "document_count", "gold_position", "position_label", "gold_document_id",
    "question_text", "gold_answers_json", "prompt_sha256", "timestamp", "status", "http_status", "attempt_count",
    "latency_seconds", "request_model", "request_temperature", "request_max_tokens", "response_id", "response_model",
    "response_created_epoch", "system_fingerprint", "choice_count", "finish_reason", "response_text", "reasoning_text",
    "extracted_answer", "paper_firstline", "strict_final_em", "final_contains", "full_response_contains",
    "repaired_empty_marker", "is_truncated", "needs_review", "primary_metric_name", "input_tokens", "output_tokens",
    "total_tokens", "output_whitespace_words", "output_characters",
]


def clean_document_qa():
    out = OUT / "document_qa"
    out.mkdir(parents=True, exist_ok=True)
    checksums = json.loads((document_qa / "CHECKSUMS.json").read_text(encoding="utf-8"))
    inputs_to_verify = ["data/raw_responses.jsonl.gz", "data/scenarios.jsonl.gz", "data/attempt_log.jsonl.gz"]
    input_hashes = {}
    for rel in inputs_to_verify:
        p = document_qa / (rel.removeprefix("data/") if rel.startswith("data/") else rel.replace("derived/", "source_scores/", 1))
        expected = checksums[rel]["sha256"]
        actual = sha256_file(p)
        if actual != expected:
            raise RuntimeError(f"document_qa source checksum mismatch for {rel}: {actual} != {expected}")
        input_hashes[rel] = {"sha256": actual, "bytes": p.stat().st_size}

    # Load the compact final score table so each original response can be joined by its stable scenario/model key.
    score_map = {}
    with (document_qa / "source_scores" / "scores.csv").open("r", encoding="utf-8-sig", newline="") as f:
        for s in csv.DictReader(f):
            key = (s["scenario_id"], s["model"])
            if key in score_map:
                raise RuntimeError(f"Duplicate document_qa score key: {key}")
            score_map[key] = s

    # Normalize scenario definitions and validate that scenario prompt hashes match the retained full prompt text.
    scenario_meta = {}
    question_map = {}
    scenario_count = bad_prompt_hashes = 0
    scenario_fields = [
        "scenario_id", "experiment_id", "question_id", "question_text", "gold_answers_json", "task_type",
        "document_count", "gold_position", "position_label", "gold_document_id", "document_ids_json",
        "prompt_id", "strategy_text", "prompt_text", "prompt_sha256",
    ]
    with gzip.open(document_qa / "scenarios.jsonl.gz", "rt", encoding="utf-8") as source, \
         csv_sink(out / "scenarios_clean.csv.gz", scenario_fields) as writer:
        for line in source:
            s = json.loads(line)
            scenario_count += 1
            expected_hash = hashlib.sha256(s["prompt_text"].encode("utf-8")).hexdigest()
            if expected_hash != s["prompt_sha256"]:
                bad_prompt_hashes += 1
            scenario_id = s["scenario_id"]
            if scenario_id in scenario_meta:
                raise RuntimeError(f"Duplicate document_qa scenario_id: {scenario_id}")
            scenario_meta[scenario_id] = {
                "question_id": s["question_id"],
                "prompt_sha256": s["prompt_sha256"],
                "task_type": s["task_type"],
                "document_count": s["document_count"],
                "gold_position": s.get("gold_position"),
                "position_label": s["position_label"],
                "prompt_id": s["prompt_id"],
                "gold_answers_json": json_cell(s["answers"]),
            }
            qval = {
                "question_id": s["question_id"],
                "question_text": s["question"],
                "answers_json": json_cell(s["answers"]),
            }
            if s["question_id"] in question_map and question_map[s["question_id"]] != qval:
                raise RuntimeError(f"Inconsistent document_qa question metadata: {s['question_id']}")
            question_map[s["question_id"]] = qval
            outrow = {
                "scenario_id": scenario_id,
                "experiment_id": "lost_in_the_middle_nq_open",
                "question_id": s["question_id"],
                "question_text": s["question"],
                "gold_answers_json": json_cell(s["answers"]),
                "task_type": s["task_type"],
                "document_count": parse_int(s["document_count"]),
                "gold_position": parse_int(s.get("gold_position")),
                "position_label": s["position_label"],
                "gold_document_id": s.get("gold_document_id"),
                "document_ids_json": json_cell(s.get("document_ids", [])),
                "prompt_id": s["prompt_id"],
                "strategy_text": s["strategy_text"],
                "prompt_text": s["prompt_text"],
                "prompt_sha256": s["prompt_sha256"],
            }
            writer.writerow({k: csv_value(v) for k, v in outrow.items()})
    if bad_prompt_hashes:
        raise RuntimeError(f"document_qa scenario prompt hash mismatches: {bad_prompt_hashes}")
    if scenario_count != 37400 or len(question_map) != 200 or len(scenario_meta) != 37400:
        raise RuntimeError(f"Unexpected document_qa scenario/question counts: {scenario_count}/{len(question_map)}")

    question_source = json.loads((document_qa / "questions.json").read_text(encoding="utf-8"))
    question_rows = []
    for q in question_source:
        norm = question_map.get(q["question_id"])
        if norm is None or norm["question_text"] != q["question"] or parse_json_cell(norm["answers_json"], list) != q["answers"]:
            raise RuntimeError(f"document_qa questions.json disagrees with scenarios: {q['question_id']}")
        question_rows.append({
            "question_id": q["question_id"],
            "question_text": q["question"],
            "answers_json": json_cell(q["answers"]),
            "source_lines_json": json_cell(q.get("source_lines", {})),
            "gold_document_json": json_cell(q.get("gold_document", {})),
        })
    with csv_sink(out / "questions_clean.csv", ["question_id", "question_text", "answers_json", "source_lines_json", "gold_document_json"], compressed=False) as w:
        for row in question_rows:
            w.writerow(row)

    response_count = review_count = trunc_count = raw_score_joined = 0
    raw_keys = set()
    groups = Counter()
    model_counts = Counter()
    status_counts = Counter()
    score_mismatch_counts = Counter()
    prompt_request_mismatches = 0
    choice_counts = Counter()
    response_null_counts = Counter()
    run_id_by_key = {}
    review_fields = [
        "record_id", "question_id", "scenario_id", "model_id", "task_type", "prompt_id", "strategy_scope",
        "document_count", "position_label", "question_text", "gold_answers_json", "response_text", "extracted_answer",
        "paper_firstline", "strict_final_em", "final_contains", "full_response_contains", "is_truncated", "needs_review",
    ]
    with gzip.open(document_qa / "raw_responses.jsonl.gz", "rt", encoding="utf-8") as source, \
         csv_sink(out / "responses_clean.csv.gz", document_qa_RESPONSE_FIELDS) as writer, \
         csv_sink(out / "review_queue_clean.csv.gz", review_fields) as review_writer:
        for line in source:
            r = json.loads(line)
            key = (r["scenario_id"], r["model"])
            if key in raw_keys:
                raise RuntimeError(f"Duplicate document_qa raw response key: {key}")
            raw_keys.add(key)
            if key not in score_map:
                raise RuntimeError(f"Missing document_qa final score for {key}")
            s = score_map[key]
            raw_score_joined += 1
            if r["scenario_id"] not in scenario_meta:
                raise RuntimeError(f"Missing document_qa scenario: {r['scenario_id']}")
            sm = scenario_meta[r["scenario_id"]]
            if r["question_id"] != sm["question_id"] or r["prompt_sha256"] != sm["prompt_sha256"]:
                raise RuntimeError(f"Response/scenario identity mismatch: {key}")
            request = r.get("request") or {}
            messages = request.get("messages") or []
            prompt_from_request = messages[0].get("content") if messages else None
            # The full prompt lives once per scenario; verify every model request against it.
            if prompt_from_request is None or hashlib.sha256(prompt_from_request.encode("utf-8")).hexdigest() != r["prompt_sha256"]:
                prompt_request_mismatches += 1
            response = r.get("response") or {}
            choices = response.get("choices") or []
            choice_counts[len(choices)] += 1
            choice = choices[0] if choices else {}
            message = choice.get("message") or {}
            response_text = message.get("content")
            if response_text is None:
                response_null_counts["response_text"] += 1
                response_text = ""
            reasoning_text = message.get("reasoning_content")
            usage = response.get("usage") or {}
            score_metrics = {}
            for metric in ["paper_firstline", "strict_final_em", "final_contains", "full_response_contains"]:
                score_metrics[metric] = parse_float(s.get(metric))
                if score_metrics[metric] not in (0.0, 1.0):
                    score_mismatch_counts[f"invalid_{metric}"] += 1
            is_truncated = parse_bool(s["truncated"])
            needs_review = parse_bool(s["needs_review"])
            repaired = parse_bool(s["repaired_empty_marker"])
            finish_reason = choice.get("finish_reason")
            if is_truncated != (finish_reason == "length"):
                score_mismatch_counts["truncation_vs_finish_reason"] += 1
            input_tokens = parse_int(usage.get("prompt_tokens"))
            output_tokens = parse_int(usage.get("completion_tokens"))
            total_tokens = parse_int(usage.get("total_tokens"))
            if input_tokens != parse_int(s.get("input_tokens")):
                score_mismatch_counts["input_tokens_vs_scores"] += 1
            if output_tokens != parse_int(s.get("output_tokens")):
                score_mismatch_counts["output_tokens_vs_scores"] += 1
            if prompt_from_request is not None and sm["prompt_sha256"] == r["prompt_sha256"]:
                # Hash is authoritative for full prompt; prompt text equality is checked below from source scenario.
                pass
            record_id = r["run_id"]
            run_id_by_key[key] = record_id
            row = {
                "record_id": record_id,
                "experiment_id": "lost_in_the_middle_nq_open",
                "source_run_id": record_id,
                "question_id": r["question_id"],
                "scenario_id": r["scenario_id"],
                "model_id": r["model"],
                "task_type": r["task_type"],
                "prompt_id": r["prompt_id"],
                "strategy_scope": s["scope"],
                "document_count": parse_int(r.get("document_count")),
                "gold_position": parse_int(r.get("gold_position")),
                "position_label": r.get("position_label"),
                "gold_document_id": r.get("gold_document_id"),
                "question_text": r["question"],
                "gold_answers_json": json_cell(r["answers"]),
                "prompt_sha256": r["prompt_sha256"],
                "timestamp": r["timestamp"],
                "status": r["status"],
                "http_status": parse_int(r.get("http_status")),
                "attempt_count": parse_int(r.get("attempt_count")),
                "latency_seconds": parse_float(r.get("latency_s")),
                "request_model": request.get("model"),
                "request_temperature": parse_float(request.get("temperature")),
                "request_max_tokens": parse_int(request.get("max_tokens")),
                "response_id": response.get("id"),
                "response_model": response.get("model"),
                "response_created_epoch": parse_int(response.get("created")),
                "system_fingerprint": response.get("system_fingerprint") or None,
                "choice_count": len(choices),
                "finish_reason": finish_reason,
                "response_text": response_text,
                "reasoning_text": reasoning_text,
                "extracted_answer": s.get("extracted_answer") or None,
                **score_metrics,
                "repaired_empty_marker": repaired,
                "is_truncated": is_truncated,
                "needs_review": needs_review,
                "primary_metric_name": "paper_firstline",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "output_whitespace_words": len(response_text.split()),
                "output_characters": len(response_text),
            }
            writer.writerow({k: csv_value(v) for k, v in row.items()})
            response_count += 1
            model_counts[r["model"]] += 1
            status_counts[r["status"]] += 1
            groups[(r["task_type"], r["model"], r["prompt_id"], str(r.get("document_count")), r.get("position_label"))] += 1
            if needs_review:
                review_count += 1
                review_writer.writerow({k: csv_value(row.get(k)) for k in review_fields})
            if is_truncated:
                trunc_count += 1

    if prompt_request_mismatches:
        raise RuntimeError(f"document_qa request prompt hash mismatches: {prompt_request_mismatches}")
    if response_count != 74800 or raw_score_joined != 74800 or len(raw_keys) != 74800:
        raise RuntimeError(f"Unexpected document_qa response join totals: {response_count}/{raw_score_joined}")
    if set(score_map) != raw_keys:
        raise RuntimeError(f"document_qa raw/score key sets differ: raw={len(raw_keys)} scores={len(score_map)}")
    if len(model_counts) != 2 or set(model_counts.values()) != {37400}:
        raise RuntimeError(f"Unexpected document_qa model coverage: {dict(model_counts)}")
    if review_count != 20782 or trunc_count != 1074:
        raise RuntimeError(f"Unexpected document_qa review/truncation counts: {review_count}/{trunc_count}")
    if set(choice_counts) != {1}:
        raise RuntimeError(f"Unexpected document_qa response choice counts: {dict(choice_counts)}")
    if len(groups) != 374 or set(groups.values()) != {200}:
        raise RuntimeError(f"Unexpected document_qa group coverage: groups={len(groups)}, sizes={set(groups.values())}")

    attempt_count = 0
    attempt_fields = ["record_id", "model_id", "scenario_id", "attempt_number", "started_at", "ended_at", "latency_seconds", "http_status", "retry_after"]
    with gzip.open(document_qa / "attempt_log.jsonl.gz", "rt", encoding="utf-8") as source, \
         csv_sink(out / "attempts_clean.csv.gz", attempt_fields) as writer:
        seen_attempts = set()
        for line in source:
            a = json.loads(line)
            key = (a["scenario_id"], a["model"])
            dedupe_key = (*key, parse_int(a["attempt"]))
            if dedupe_key in seen_attempts:
                raise RuntimeError(f"Duplicate document_qa attempt key: {dedupe_key}")
            seen_attempts.add(dedupe_key)
            row = {
                "record_id": run_id_by_key.get(key, f"{a['model']}|{a['scenario_id']}"),
                "model_id": a["model"],
                "scenario_id": a["scenario_id"],
                "attempt_number": parse_int(a.get("attempt")),
                "started_at": a.get("started_at"),
                "ended_at": a.get("ended_at"),
                "latency_seconds": parse_float(a.get("latency_s")),
                "http_status": parse_int(a.get("http_status")),
                "retry_after": parse_float(a.get("retry_after")),
            }
            writer.writerow({k: csv_value(v) for k, v in row.items()})
            attempt_count += 1

    if attempt_count != 75229:
        raise RuntimeError(f"Unexpected document_qa attempt count: {attempt_count}")

    return {
        "source_experiment": str(document_qa.relative_to(ROOT)),
        "verified_input_hashes": input_hashes,
        "scores_csv_sha256": sha256_file(document_qa / "source_scores" / "scores.csv"),
        "response_rows": response_count,
        "unique_response_keys": len(raw_keys),
        "scores_joined": raw_score_joined,
        "models": dict(sorted(model_counts.items())),
        "statuses": dict(status_counts),
        "independent_questions": len(question_map),
        "scenarios": scenario_count,
        "groups": len(groups),
        "records_per_group": 200,
        "attempts": attempt_count,
        "needs_review": review_count,
        "truncated": trunc_count,
        "response_choice_counts": dict(choice_counts),
        "prompt_hash_mismatches": prompt_request_mismatches + bad_prompt_hashes,
        "score_consistency_diagnostics": dict(score_mismatch_counts),
        "selected_null_counts": dict(response_null_counts),
        "score_metrics_preserved": ["paper_firstline", "strict_final_em", "final_contains", "full_response_contains"],
        "manual_review_status": "The source README says the review queue has not been fully manually reviewed; needs_review is a flag, not a correctness label.",
        "output_tables": {
            "responses_clean.csv.gz": response_count,
            "review_queue_clean.csv.gz": review_count,
            "scenarios_clean.csv.gz": scenario_count,
            "questions_clean.csv": len(question_map),
            "attempts_clean.csv.gz": attempt_count,
        },
    }


def write_readme(report):
    z = report["reasoning"]
    f = report["document_qa"]
    content = f'''# 清洗后数据包

生成时间：{report['generated_at']}

## 范围与处理原则

- 清洗对象是已下载的 `reasoning` 与 `document_qa` 两个分支数据；main 分支只有课程题目和过程 PDF，没有另一套原始回答数据。
- 本次只读取本地文件，未调用 API。
- 原始文件都保留在各分支原目录。本目录是新增的清洗副本；没有覆盖原文件，也没有删除回答、重复测量条件或截断记录。
- 输出 CSV 使用 UTF-8、英文 snake_case 字段、标准 CSV 引号规则；布尔值写作 `true/false`，空值留空。JSON 数组/对象字段使用紧凑 JSON 字符串。所有 ID 和来源哈希保留。
- 评分只做类型和格式规范化，没有重判答案。不可比较的评分口径没有合并成一个分数。

## reasoning 分支

清洗后包含 {z['rows']:,} 条回答、{z['independent_questions']:,} 道独立题、{z['prompt_strategies']} 种提示词。`record_id` 唯一；每个模型 × 数据集 × 提示词组合 200 条。

- `reasoning/responses_clean.csv.gz`：全量逐条回答与评分快照。
- `reasoning/review_queue_clean.csv.gz`：源数据 `included_in_review=true` 的 {z['review_included']:,} 条记录。
- `reasoning/questions_clean.csv`、`reasoning/prompts_clean.csv`：拆分出的题目表和提示词表。
- `reasoning/repeated_hash_audit.csv`：{z['repeated_hash_groups']} 组重复 `source_record_hash`，全部保留。检查显示重复记录是不同提示词条件下同题同模型返回相同答案，属于有意义的重复测量结果。

空的独立推理字段规范为 null，不代表模型没有展示推理；缺失 token 数不填 0。当前评分原样保留。交付说明指出 DeepSeek 模型组存在离线重评分，而其他模型组使用源评分快照，所以跨模型汇总前仍需统一评分规则。

## document_qa 分支

清洗后包含 {f['response_rows']:,} 条回答、{f['scenarios']:,} 个场景、{f['independent_questions']:,} 道独立题和 {f['attempts']:,} 次请求尝试。

- `document_qa/responses_clean.csv.gz`：原始响应与最终离线评分按模型 × 场景合并，一条回答一行。
- `document_qa/scenarios_clean.csv.gz`：场景定义，保留完整 prompt、文档位置与提示词。
- `document_qa/questions_clean.csv`：200 道独立题及答案来源元数据。
- `document_qa/attempts_clean.csv.gz`：重试/请求尝试日志。
- `document_qa/review_queue_clean.csv.gz`：{f['needs_review']:,} 条 `needs_review=true` 记录。

保留四种不同评分列：`paper_firstline`、`strict_final_em`、`final_contains`、`full_response_contains`。主指标标识为 `paper_firstline`；四个指标含义不同，不能相互替代。{f['truncated']:,} 条截断记录和复核标记均保留。来源说明复核队列尚未全部人工复核。

## 清洗和校验

- 原始归档及 LFS 数据校验和与源清单一致。
- reasoning：回答记录数、唯一 ID、题目和提示词一致性、评分 0/1、布尔值、数字字段、覆盖数均已校验。
- document_qa：回答与最终评分按唯一键完整连接；场景 prompt 哈希与实际请求一致；请求 token 与评分表一致性及截断标志一致性已记录在 `quality_report.json`；回答、场景、复核、重试数量和分组覆盖均已校验。
- 详细计数、输入校验和、异常诊断和输出文件校验和见 `quality_report.json` 与 `SHA256SUMS.txt`。

## 建议读取顺序

分析模型表现时，先读各分支 `responses_clean.csv.gz`；人工复核时读对应 `review_queue_clean.csv.gz`；需要核对题目或完整 prompt 时，用 `question_id` / `scenario_id` 连接 `questions_clean.csv` / `scenarios_clean.csv.gz`。不要把两分支的行直接合并计算一个准确率：任务、评分和实验设计不同。
'''
    (OUT / "baseline_notes.md").write_text(content, encoding="utf-8")


def validate_output_tables(report):
    tables = {
        "reasoning.responses_clean": (OUT / "reasoning" / "responses_clean.csv.gz", report["reasoning"]["rows"]),
        "reasoning.review_queue_clean": (OUT / "reasoning" / "review_queue_clean.csv.gz", report["reasoning"]["review_included"]),
        "reasoning.questions_clean": (OUT / "reasoning" / "questions_clean.csv", report["reasoning"]["independent_questions"]),
        "reasoning.prompts_clean": (OUT / "reasoning" / "prompts_clean.csv", report["reasoning"]["prompt_strategies"]),
        "reasoning.repeated_hash_audit": (OUT / "reasoning" / "repeated_hash_audit.csv", report["reasoning"]["repeated_hash_groups"]),
        "document_qa.responses_clean": (OUT / "document_qa" / "responses_clean.csv.gz", report["document_qa"]["response_rows"]),
        "document_qa.review_queue_clean": (OUT / "document_qa" / "review_queue_clean.csv.gz", report["document_qa"]["needs_review"]),
        "document_qa.scenarios_clean": (OUT / "document_qa" / "scenarios_clean.csv.gz", report["document_qa"]["scenarios"]),
        "document_qa.questions_clean": (OUT / "document_qa" / "questions_clean.csv", report["document_qa"]["independent_questions"]),
        "document_qa.attempts_clean": (OUT / "document_qa" / "attempts_clean.csv.gz", report["document_qa"]["attempts"]),
    }
    dictionary = defaultdict(set)
    with (OUT / "data_dictionary.tsv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            dictionary[row["table"]].add(row["field"])
    counts, unique_counts, header_counts = {}, {}, {}
    for table, (path, expected) in tables.items():
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            unique = set()
            n = 0
            for row in reader:
                n += 1
                if table.startswith("reasoning.") and table.endswith("responses_clean") or table == "reasoning.review_queue_clean":
                    key = row["record_id"]
                    if key in unique:
                        raise RuntimeError(f"Duplicate output key in {table}: {key}")
                    unique.add(key)
                    if row["score_current"] not in {"0", "1"}:
                        raise RuntimeError(f"Invalid output score in {table}: {row['score_current']}")
                    for field in ["is_truncated", "source_needs_review", "included_in_review"]:
                        if row[field] not in {"true", "false"}:
                            raise RuntimeError(f"Invalid output boolean in {table}.{field}")
                elif table in {"document_qa.responses_clean", "document_qa.review_queue_clean"}:
                    key = row["record_id"]
                    if key in unique:
                        raise RuntimeError(f"Duplicate output key in {table}: {key}")
                    unique.add(key)
                    for field in ["paper_firstline", "strict_final_em", "final_contains", "full_response_contains"]:
                        if row[field] not in {"0.0", "1.0"}:
                            raise RuntimeError(f"Invalid output score in {table}.{field}")
                    for field in {"repaired_empty_marker", "is_truncated", "needs_review"} & set(fields):
                        if row[field] not in {"true", "false"}:
                            raise RuntimeError(f"Invalid output boolean in {table}.{field}")
                elif table == "document_qa.scenarios_clean":
                    key = row["scenario_id"]
                    if key in unique:
                        raise RuntimeError(f"Duplicate scenario_id: {key}")
                    unique.add(key)
                elif table == "document_qa.attempts_clean":
                    key = (row["model_id"], row["scenario_id"], row["attempt_number"])
                    if key in unique:
                        raise RuntimeError(f"Duplicate attempt key: {key}")
                    unique.add(key)
            if n != expected:
                raise RuntimeError(f"Unexpected output row count for {table}: {n} != {expected}")
            if set(fields) != dictionary[table]:
                raise RuntimeError(f"Data dictionary fields do not match output columns for {table}")
            counts[table] = n
            unique_counts[table] = len(unique) if unique else None
            header_counts[table] = len(fields)
    return {
        "passed": True,
        "tables_read_back": counts,
        "unique_key_counts": unique_counts,
        "column_counts": header_counts,
        "dictionary_covers_every_table_column": True,
    }


def write_data_dictionary():
    rows = []
    def add(table, items):
        for name, dtype, meaning in items:
            rows.append({"table": table, "field": name, "type": dtype, "meaning": meaning})
    add("reasoning.responses_clean", [
        ("record_id", "string", "Source stable answer-record ID; unique."),
        ("experiment_id", "string", "Experiment identifier."),
        ("model_id", "string", "Short model identifier used in the reasoning package."),
        ("model_api_name", "string/null", "API model name configured for this model group."),
        ("benchmark", "category", "mmlu, gsm8k, or math500."),
        ("question_id", "string", "Independent question identifier; repeats across prompts/models."),
        ("question_sha256", "string", "Source question content hash."),
        ("prompt_id", "string", "Prompt strategy identifier."),
        ("prompt_text", "string", "Verbatim prompt instruction."),
        ("question_text", "string", "Verbatim question text."),
        ("options_json", "JSON array", "Multiple-choice options; empty when not applicable."),
        ("gold_answer", "string", "Source accepted answer."),
        ("response_text", "string", "Verbatim model-visible answer."),
        ("reasoning_text", "string/null", "Independent platform reasoning field; blank source values normalized to null."),
        ("extracted_answer", "string/null", "Source-extracted final answer; not recomputed here."),
        ("score_current", "integer 0/1", "Current source grade; not harmonized or rejudged."),
        ("grading_status", "category", "Source grading status."),
        ("score_revision_group", "category", "Model-group provenance note from the delivery summary."),
        ("output_tokens", "integer/null", "Source API output tokens; null remains null."),
        ("input_tokens", "integer/null", "Source API input tokens; null remains null."),
        ("reasoning_tokens", "integer/null", "Source reasoning tokens; null remains null."),
        ("answer_tokens", "integer/null", "Source answer tokens; null remains null."),
        ("response_status", "category", "Source response status; success does not mean correct."),
        ("finish_reason", "string/null", "Source finish reason."),
        ("is_truncated", "boolean", "Source truncation flag."),
        ("source_needs_review", "boolean", "Original scorer review flag."),
        ("included_in_review", "boolean", "Source inclusion in review queue; may include truncation."),
        ("review_trigger_reason", "string/null", "Source review trigger."),
        ("latency_seconds", "number/null", "Source response latency in seconds."),
        ("returned_model_name", "string/null", "Model name reported by the API response."),
        ("source_file", "string", "Relative source record path in original package."),
        ("source_record_hash", "string", "Source response-record fingerprint; repeated hashes were audited and retained."),
    ])
    add("reasoning.questions_clean", [
        ("benchmark", "category", "Dataset/benchmark identifier."),
        ("question_id", "string", "Question key within the benchmark."),
        ("question_sha256", "string", "Source question content hash."),
        ("question_text", "string", "Verbatim source question."),
        ("options_json", "JSON array", "Options; empty when not applicable."),
        ("gold_answer", "string", "Source accepted answer."),
    ])
    add("reasoning.prompts_clean", [
        ("prompt_id", "string", "Prompt strategy identifier."),
        ("prompt_text", "string", "Verbatim prompt instruction."),
        ("answer_records", "integer", "Number of answer rows using this prompt."),
    ])
    add("reasoning.repeated_hash_audit", [
        ("source_record_hash", "string", "Repeated source record hash."),
        ("group_size", "integer", "Number of rows in the hash group."),
        ("record_ids_json", "JSON array", "All distinct record IDs sharing this hash."),
        ("handling", "string", "Audit note; these rows were retained."),
    ])
    add("document_qa.responses_clean", [
        ("record_id", "string", "Source run ID; unique response identifier."),
        ("experiment_id", "string", "Experiment identifier."),
        ("source_run_id", "string", "Original run ID from the raw collection record."),
        ("question_id", "string", "Independent question identifier; repeats across scenarios and models."),
        ("scenario_id", "string", "Question × document setup × position × prompt condition."),
        ("model_id", "string", "Full requested model ID."),
        ("task_type", "category", "document_qa main task or closedbook_control."),
        ("prompt_id", "category", "Prompt strategy identifier."),
        ("strategy_scope", "category", "Source strategy grouping."),
        ("document_count", "integer", "Number of context documents; 0 for control."),
        ("gold_position", "integer/null", "1-based support document position; null for control."),
        ("position_label", "category", "front/middle/back/none."),
        ("gold_document_id", "string/null", "ID of the support document containing the answer."),
        ("question_text", "string", "Verbatim English question."),
        ("gold_answers_json", "JSON array", "Official accepted answers."),
        ("prompt_sha256", "string", "Hash of the full prompt; full prompt is in scenarios_clean."),
        ("timestamp", "ISO 8601 string", "Source timestamp, timezone retained."),
        ("status", "category", "Collection status; success is not answer correctness."),
        ("http_status", "integer/null", "Last request HTTP status."),
        ("attempt_count", "integer", "Number of requests attempted for this response."),
        ("latency_seconds", "number", "Final request latency in seconds."),
        ("request_model", "string", "Model field in saved request."),
        ("request_temperature", "number/null", "Saved request temperature."),
        ("request_max_tokens", "integer/null", "Saved request output cap."),
        ("response_id", "string", "API response ID from saved response payload."),
        ("response_model", "string", "Model ID returned by API."),
        ("response_created_epoch", "integer/null", "API response creation epoch."),
        ("system_fingerprint", "string/null", "API system fingerprint if supplied."),
        ("choice_count", "integer", "Number of response choices; the source has one per row."),
        ("finish_reason", "string/null", "API finish reason."),
        ("response_text", "string", "Verbatim visible answer."),
        ("reasoning_text", "string/null", "Independent reasoning field if supplied; null is not interpreted as absence of reasoning."),
        ("extracted_answer", "string/null", "Source final-answer extraction."),
        ("paper_firstline", "number 0/1", "Official first-line score; designated primary metric."),
        ("strict_final_em", "number 0/1", "Strict normalized final-answer match."),
        ("final_contains", "number 0/1", "Official answer contained in extracted final answer."),
        ("full_response_contains", "number 0/1", "Official answer contained anywhere in full response."),
        ("repaired_empty_marker", "boolean", "Whether a fixed source rule recovered a short answer before an empty final marker."),
        ("is_truncated", "boolean", "Final score-table truncation flag; retained even if true."),
        ("needs_review", "boolean", "Source review flag; not a correctness label."),
        ("primary_metric_name", "category", "paper_firstline for the source primary comparison."),
        ("input_tokens", "integer/null", "Saved API prompt tokens."),
        ("output_tokens", "integer/null", "Saved API completion tokens."),
        ("total_tokens", "integer/null", "Saved API total tokens."),
        ("output_whitespace_words", "integer", "Recomputed whitespace-delimited word count from response_text."),
        ("output_characters", "integer", "Unicode character count of response_text."),
    ])
    add("document_qa.review_queue_clean", [
        ("record_id", "string", "Source response run ID."),
        ("question_id", "string", "Independent question identifier."),
        ("scenario_id", "string", "Question and experimental condition identifier."),
        ("model_id", "string", "Model ID."),
        ("task_type", "category", "Main document QA or closed-book control."),
        ("prompt_id", "string", "Prompt strategy identifier."),
        ("strategy_scope", "category", "Source strategy grouping."),
        ("document_count", "integer", "Number of context documents."),
        ("position_label", "category", "Position condition."),
        ("question_text", "string", "Verbatim English question."),
        ("gold_answers_json", "JSON array", "Official accepted answers."),
        ("response_text", "string", "Verbatim visible answer."),
        ("extracted_answer", "string/null", "Source final-answer extraction."),
        ("paper_firstline", "number 0/1", "Official first-line score."),
        ("strict_final_em", "number 0/1", "Strict normalized final-answer match."),
        ("final_contains", "number 0/1", "Official answer contained in extracted final answer."),
        ("full_response_contains", "number 0/1", "Official answer contained anywhere in the full response."),
        ("is_truncated", "boolean", "Source truncation flag."),
        ("needs_review", "boolean", "Filtered to true; a review flag, not a correctness label."),
    ])
    add("document_qa.scenarios_clean", [
        ("scenario_id", "string", "Unique scenario key."),
        ("experiment_id", "string", "Experiment identifier."),
        ("question_id", "string", "Independent question key."),
        ("question_text", "string", "Verbatim English question."),
        ("gold_answers_json", "JSON array", "Official accepted answers."),
        ("task_type", "category", "Main document QA or closed-book control."),
        ("document_count", "integer", "Number of provided context documents."),
        ("gold_position", "integer/null", "1-based gold document position."),
        ("position_label", "category", "Position condition."),
        ("gold_document_id", "string/null", "Gold support document key."),
        ("document_ids_json", "JSON array", "Ordered document IDs in the scenario."),
        ("prompt_id", "string", "Prompt strategy key."),
        ("strategy_text", "string", "Prompt instruction for the strategy."),
        ("prompt_text", "string", "Full actual prompt, including context."),
        ("prompt_sha256", "string", "SHA-256 of full prompt text."),
    ])
    add("document_qa.questions_clean", [
        ("question_id", "string", "Independent question identifier."),
        ("question_text", "string", "Verbatim English question."),
        ("answers_json", "JSON array", "Official accepted answer strings."),
        ("source_lines_json", "JSON object", "Source line identifiers by document setting."),
        ("gold_document_json", "JSON object", "Gold support document metadata from the benchmark."),
    ])
    add("document_qa.attempts_clean", [
        ("record_id", "string", "Response run ID associated with the attempt."),
        ("model_id", "string", "Model ID."),
        ("scenario_id", "string", "Scenario key."),
        ("attempt_number", "integer", "Retry attempt number."),
        ("started_at", "ISO 8601 string", "Request start time."),
        ("ended_at", "ISO 8601 string", "Request end time."),
        ("latency_seconds", "number/null", "Per-attempt latency."),
        ("http_status", "integer/null", "HTTP status if returned."),
        ("retry_after", "number/null", "Retry-After value if supplied."),
    ])
    # The reasoning review file is a filtered copy with the exact same columns as responses_clean.
    rows.extend(
        {**row, "table": "reasoning.review_queue_clean"}
        for row in list(rows)
        if row["table"] == "reasoning.responses_clean"
    )
    with (OUT / "data_dictionary.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["table", "field", "type", "meaning"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reasoning = clean_reasoning()
    document_qa = clean_document_qa()
    report = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "api_calls_made": 0,
        "source_files_modified": False,
        "principles": [
            "Retain all source observations and repeated-measure conditions.",
            "Keep raw inputs unchanged and place normalized copies in outputs/cleaned-data.",
            "Normalize field names, boolean/numeric/null representations, and preserve source IDs and hashes.",
            "Do not recompute or harmonize grades; retain separate source metrics and scoring provenance.",
        ],
        "reasoning": reasoning,
        "document_qa": document_qa,
    }
    write_data_dictionary()
    write_readme(report)
    report["output_validation"] = validate_output_tables(report)
    write_json(OUT / "quality_report.json", report)
    # Final deliverable checksums are written last and exclude themselves.
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            pass
    output_manifest = {
        str(p.relative_to(OUT)): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
        for p in sorted(OUT.rglob("*"))
        if p.is_file() and p.name != "SHA256SUMS.txt"
    }
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(f"{v['sha256']}  {name}\n" for name, v in output_manifest.items()), encoding="utf-8"
    )
    print(json.dumps({"reasoning": reasoning["rows"], "document_qa": document_qa["response_rows"], "output_files": len(output_manifest) + 1, "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
