#!/usr/bin/env python3
"""Rebuild the offline coursework deliverable without model or network requests.

snapshot/app-only: standard-library build using committed anonymous snapshots.
anonymous: recompute QA and code statistics from anonymous saved features.
full-local: clean already downloaded source files, then recompute all evidence.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
FEATURES = ROOT / "app/data/features.json.gz"
SUMMARY = ROOT / "app/data/summary.json"
QUESTION_ORDER = ROOT / "app/data/question-cluster-order.json"
MODEL_SOURCE = {"qwen": "Qwen/Qwen2.5-7B-Instruct", "qwen3": "Qwen/Qwen3-8B"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(script, *args):
    print(f"[offline] {script}", flush=True)
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    interpreter_flags = ["-S"] if sys.flags.no_site else []
    subprocess.run([sys.executable, *interpreter_flags, str(ROOT / "scripts" / script), *args], cwd=ROOT, env=env, check=True)


def load_snapshot():
    packed = json.loads(gzip.decompress(FEATURES.read_bytes()))
    required = {"id", "question", "dataset", "model", "task", "prompt", "documents", "position",
                "scores", "tokens", "truncated", "unresolved", "review", "finish", "latency", "attempts"}
    if set(packed["fields"]) != required:
        raise ValueError("Anonymous feature schema differs from the documented snapshot.")
    if any(len(row) != len(packed["fields"]) for row in packed["rows"]):
        raise ValueError("An anonymous feature row has a different width from the schema.")
    rows = [dict(zip(packed["fields"], row)) for row in packed["rows"]]
    counts = {name: sum(r["dataset"] == name for r in rows) for name in ("reasoning", "document_qa")}
    if counts != {"reasoning": 74400, "document_qa": 74800} or len({r["id"] for r in rows}) != 149200:
        raise ValueError(f"Unexpected anonymous response counts or duplicate anonymous IDs: {counts}")
    return rows, json.loads(SUMMARY.read_text(encoding="utf-8"))


def build_question_order():
    """Retain only the source sort rank needed to replay bootstrap exactly."""
    rows, _summary = load_snapshot()
    orders = {}
    sources = {}
    for dataset, folder in (("reasoning", "reasoning"), ("document_qa", "document_qa")):
        path = ROOT/"data/processed"/folder/"responses_clean.csv.gz"
        source_to_anonymous = {}
        exported = [r for r in rows if r["dataset"] == dataset]
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            count = 0
            for source, feature in itertools.zip_longest(csv.DictReader(stream), exported):
                if source is None or feature is None:
                    raise ValueError("Source and anonymous feature row counts differ.")
                count += 1
                if source["question_id"] in source_to_anonymous and source_to_anonymous[source["question_id"]] != feature["question"]:
                    raise ValueError("Question mapping is inconsistent with the anonymous export order.")
                source_to_anonymous[source["question_id"]] = feature["question"]
        orders[dataset] = {source_to_anonymous[q]: i for i, q in enumerate(sorted(source_to_anonymous))}
        sources[str(path.relative_to(ROOT))] = digest(path)
    QUESTION_ORDER.write_text(json.dumps({"schema_version": "anonymous-question-order-v1",
        "feature_sha256": digest(FEATURES), "source_clean_sha256": sources,
        "purpose": "Numeric sort ranks only; reproduces source question-cluster bootstrap order without source IDs or text.",
        "datasets": orders}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def anonymous_statistics(rows, summary):
    """Use retained features only; source-only diagnostics remain frozen evidence."""
    import numpy as np
    import pandas as pd

    spec = importlib.util.spec_from_file_location("current_analysis", ROOT / "scripts/analysis/analyze_baselines.py")
    analysis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis)
    analysis.OUT.mkdir(parents=True, exist_ok=True)
    analysis.FIG.mkdir(parents=True, exist_ok=True)
    order = json.loads(QUESTION_ORDER.read_text(encoding="utf-8"))
    if order["feature_sha256"] != digest(FEATURES):
        raise ValueError("Anonymous question order belongs to a different feature snapshot.")
    ranks = order["datasets"]
    z = pd.DataFrame([{
        "model_id": r["model"], "benchmark": r["task"], "question_id": ranks["reasoning"][r["question"]],
        "prompt_id": r["prompt"], "score_current": r["scores"][0], "output_tokens": r["tokens"],
        "is_truncated": bool(r["truncated"]), "unresolved": bool(r["unresolved"]),
        "included_in_review": bool(r["review"]),
    } for r in rows if r["dataset"] == "reasoning"])
    scopes = {c["prompt"]: c["scope"] for c in summary["cells"] if c["dataset"] == "document_qa"}
    f = pd.DataFrame([{
        "model_id": MODEL_SOURCE[r["model"]], "question_id": ranks["document_qa"][r["question"]], "task_type": r["task"],
        "prompt_id": r["prompt"], "strategy_scope": scopes[r["prompt"]],
        "document_count": r["documents"], "position_label": r["position"],
        **dict(zip(analysis.METRICS, r["scores"])), "output_tokens": r["tokens"],
        "is_truncated": bool(r["truncated"]), "needs_review": bool(r["review"]),
    } for r in rows if r["dataset"] == "document_qa"])
    if z.duplicated(["model_id", "benchmark", "question_id", "prompt_id"]).any():
        raise ValueError("Duplicate reasoning experimental key in anonymous snapshot.")
    if f.duplicated(["model_id", "question_id", "task_type", "prompt_id", "document_count", "position_label"]).any():
        raise ValueError("Duplicate document_qa experimental key in anonymous snapshot.")

    # This is the numerical portion of analyze_reasoning. No per-row grading_status
    # is reconstructed: that source field was deliberately not exported.
    zs = z.groupby(["model_id", "benchmark", "prompt_id"]).agg(
        responses=("score_current", "size"), questions=("question_id", "nunique"),
        current_score_rate=("score_current", "mean"), mean_output_tokens=("output_tokens", "mean"),
        median_output_tokens=("output_tokens", "median"), truncation_rate=("is_truncated", "mean"),
        unresolved_rate=("unresolved", "mean"), review_rate=("included_in_review", "mean")).reset_index()
    analysis.write_table("reasoning_prompt_summary", zs)
    contrasts = []
    chosen = [("DefaultCoT", "NoCoT"), ("BeConcise", "DefaultCoT"), ("WordLimit(25)", "DefaultCoT"),
              ("WordLimit(50)", "DefaultCoT"), ("WordLimit(100)", "DefaultCoT"),
              ("StepLimit(2)", "DefaultCoT"), ("TokenLimit(10)", "DefaultCoT")]
    for (model, benchmark), group in z.groupby(["model_id", "benchmark"]):
        for first, second in chosen:
            stat = analysis.paired(group, ["question_id"], "prompt_id", first, second, "score_current")
            a = group[group.prompt_id == first].set_index("question_id").sort_index()
            b = group[group.prompt_id == second].set_index("question_id").sort_index()
            if not a.index.equals(b.index) or len(a) != 200:
                raise ValueError("Incomplete matched-question reasoning contrast.")
            a_low = a.score_current.where(~a.unresolved, 0).mean()
            a_high = a.score_current.where(~a.unresolved, 1).mean()
            b_low = b.score_current.where(~b.unresolved, 0).mean()
            b_high = b.score_current.where(~b.unresolved, 1).mean()
            contrasts.append({"model_id": model, "benchmark": benchmark, "first": first, "second": second,
                **stat, "first_mean_tokens": float(a.output_tokens.mean()),
                "second_mean_tokens": float(b.output_tokens.mean()),
                "token_saving_pct": float((1-a.output_tokens.mean()/b.output_tokens.mean())*100),
                "first_truncation_rate": float(a.is_truncated.mean()),
                "second_truncation_rate": float(b.is_truncated.mean()),
                "first_unresolved_rate": float(a.unresolved.mean()),
                "second_unresolved_rate": float(b.unresolved.mean()),
                "unresolved_sensitivity_low_pp": float((a_low-b_high)*100),
                "unresolved_sensitivity_high_pp": float((a_high-b_low)*100)})
    zc = analysis.write_table("reasoning_paired_contrasts", contrasts)
    budget = z[z.prompt_id.str.match(r"TokenLimit\(\d+\)")].copy()
    budget["requested_tokens"] = budget.prompt_id.str.extract(r"\((\d+)\)").astype(int)
    budget["exceeds_requested_tokens"] = budget.output_tokens > budget.requested_tokens
    analysis.write_table("reasoning_token_instruction_compliance", budget.groupby(
        ["model_id", "benchmark", "prompt_id", "requested_tokens"]).agg(
        responses=("output_tokens", "size"), mean_output_tokens=("output_tokens", "mean"),
        median_output_tokens=("output_tokens", "median"),
        exceeds_requested_rate=("exceeds_requested_tokens", "mean")).reset_index())
    fs, fc, fp = analysis.analyze_document_qa(f)
    analysis.plots(zc, fs, fc, fp)
    for name, table in (("reasoning", zc), ("document_qa", fc)):
        converted = json.loads(table.to_json(orient="records", double_precision=15))
        for row in converted:
            row["model_id"] = {value: key for key, value in MODEL_SOURCE.items()}.get(row["model_id"], row["model_id"])
        summary["comparisons"][name] = converted
    # Rebuild aggregate cells, keeping source protocol metadata (scope, prompts,
    # grading status totals, and request retry histories) as explicit snapshots.
    cells = {}
    for r in rows:
        key = (r["dataset"], r["model"], r["task"], r["prompt"], r["documents"], r["position"])
        if key not in cells:
            cells[key] = dict(zip(("dataset", "model", "task", "prompt", "documents", "position"), key))
            cells[key].update(scope=scopes.get(r["prompt"], "") if r["dataset"] == "document_qa" else "",
                              n=0, questions=set(), scores=[0, 0, 0, 0], tokens=0, token_n=0,
                              truncated=0, unresolved=0, review=0, disagreement=[0, 0, 0, 0])
        c = cells[key]
        c["n"] += 1
        c["questions"].add(r["question"])
        for i, score in enumerate(r["scores"]):
            if score is not None:
                c["scores"][i] += score
        if r["tokens"] is not None:
            c["tokens"] += r["tokens"]
            c["token_n"] += 1
        for name in ("truncated", "unresolved", "review"):
            c[name] += r[name]
        if r["dataset"] == "document_qa":
            c["disagreement"][r["scores"][0]*2+r["scores"][2]] += 1
    for c in cells.values():
        c["questions"] = len(c["questions"])
    summary["cells"] = list(cells.values())
    summary["provenance"]["anonymous_recomputation"] = {
        "feature_sha256": digest(FEATURES), "api_calls_made": 0,
        "frozen_fields": ["prompts", "core_prompts", "grading_statuses", "attempts", "model metadata", "source hashes"],
        "bootstrap_note": "Anonymous numeric source-sort ranks reproduce source question-cluster resampling order exactly.",
        "question_order_sha256": digest(QUESTION_ORDER)}
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")
    frozen = ["reports/baseline/reasoning_grading_status.csv", "reports/baseline/analysis_manifest.json",
              "data/processed/quality_report.json", "data/processed/data_dictionary.tsv",
              "data/processed/missingness_report.csv", "data/processed/missingness_report.json",
              "reports/baseline/scoring-audit.md", "reports/baseline/scoring-review-sample.csv",
              "app/data/method-evidence.json", "app/data/method-features.json.gz"]
    manifest = {"mode": "anonymous", "api_calls_made": 0, "network_requests_made": 0,
        "input": {"path": "app/data/features.json.gz", "sha256": digest(FEATURES), "responses": len(rows)},
        "question_order": {"path": "app/data/question-cluster-order.json", "sha256": digest(QUESTION_ORDER)},
        "versions": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__},
        "bootstrap": {"seed": analysis.SEED, "resamples": analysis.BOOTSTRAPS, "unit": "anonymous question"},
        "frozen_evidence": {name: digest(ROOT/name) for name in frozen if (ROOT/name).is_file()},
        "boundary": "Raw-field missingness, answer extraction/regrading, grading-status labels and request retry metadata need local source records; frozen artifacts retain their source provenance."}
    (analysis.OUT/"anonymous_reproduction.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Recomputed 746 cells and paired statistics from {len(rows):,} anonymous records.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("snapshot", "app-only", "anonymous", "full-local"), default="snapshot")
    parser.add_argument("--font-file", type=Path, help="Licensed local Times New Roman font file for figure regeneration")
    parser.add_argument("--with-report", action="store_true", help="Also rebuild the case-report PDF; requires requirements/report.txt and local fonts")
    parser.add_argument("--cjk-font", type=Path, help="Local Chinese TrueType font for the optional PDF report")
    args = parser.parse_args()
    if args.font_file:
        font = args.font_file.expanduser().resolve()
        if not font.is_file():
            parser.error("--font-file must name an existing local font file")
        os.environ["COURSE_FIGURE_FONT_FILE"] = str(font)
    if args.cjk_font:
        font = args.cjk_font.expanduser().resolve()
        if not font.is_file():
            parser.error("--cjk-font must name an existing local font file")
        os.environ["COURSE_CJK_FONT_FILE"] = str(font)
    if args.mode == "full-local":
        run("cleaning/verify_source_inputs.py", "--check-only")
        run("cleaning/clean_baseline_data.py")
        run("analysis/analyze_baselines.py")
        run("system/export_baseline_features.py")
        build_question_order()
        run("cleaning/classify_and_audit.py")
    rows, summary = load_snapshot()
    if args.mode == "anonymous":
        anonymous_statistics(rows, summary)
    if args.mode in ("anonymous", "full-local"):
        run("analysis/build_research_evidence.py")
        run("figures/plot_baseline_figures.py")
    code_features=ROOT/"app/data/code-features.json.gz"
    if args.mode in ("anonymous","full-local") and code_features.exists():
        run("cleaning/import_code_generation.py", *(["--anonymous"] if args.mode=="anonymous" else []))
        run("figures/plot_code_generation.py")
    run("system/build_web_app.py")
    if args.with_report:
        run("delivery/build_baseline_report.py")
    print("Ready: app/index.html, or python3 app/launch.py --no-open", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, ImportError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Offline reproduction stopped: {exc}\nSee docs/reproducibility.md for the required input/dependency path.") from exc
