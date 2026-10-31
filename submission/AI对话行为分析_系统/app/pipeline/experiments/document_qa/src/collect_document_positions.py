#!/usr/bin/env python3
"""Opt-in position collection. `prepare` is offline; only `collect` calls the API.

Keys are read from an environment variable or a user-supplied project PDF in
memory. Headers and keys are never persisted. Raw outputs remain in the existing
git-ignored document_qa data directory. The original experiment is never overwritten.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import signal
import threading
import time
import urllib.error
import urllib.request

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
DEFAULT_CONFIG = ROOT / "configs/document_positions.json"


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def prepare(config):
    """Reposition the same gold document, preserving all distractors and text."""
    originals = {}
    with gzip.open(ROOT / config["source"], "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["document_count"] == config["document_count"] and row["prompt_id"] in config["prompts"]:
                originals[row["question_id"], row["prompt_id"], row["gold_position"]] = row
    template = (Path(__file__).parent / "qa.prompt").read_text().rstrip("\n")
    after_documents = template.split("{search_results}")[1]
    questions = sorted({key[0] for key in originals})
    if len(questions) != config["questions"]:
        raise ValueError("Source question count differs from the frozen plan")
    jobs, matched_anchors = [], 0
    for qid in questions:
        for prompt in config["prompts"]:
            source = originals[qid, prompt, 1]
            text = source["prompt_text"]
            tail = after_documents.format(question=source["question"])
            if not text.endswith(tail):
                raise ValueError("Source prompt does not match its saved template")
            first = text.index("Document [1](Title: ")
            prefix = text[:first]
            body = text[first:-len(tail)]
            matches = list(re.finditer(r"(?m)^Document \[\d+\]\(Title: ", body))
            if len(matches) != config["document_count"]:
                raise ValueError("Unexpected document boundary count")
            blocks = []
            for i, match in enumerate(matches):
                piece = body[match.start():(matches[i+1].start() if i+1 < len(matches) else len(body))]
                # Remove only the single join separator; source document text
                # can itself end with newlines that must remain byte-identical.
                blocks.append(piece.removesuffix("\n") if i+1 < len(matches) else piece)
            gold, distractors = blocks[0], blocks[1:]
            gold_id, distractor_ids = source["document_ids"][0], source["document_ids"][1:]
            if gold_id != source["gold_document_id"]:
                raise ValueError("Gold-document identity mismatch")
            for position in config["positions_1_based"]:
                docs, ids = list(distractors), list(distractor_ids)
                docs.insert(position - 1, gold)
                ids.insert(position - 1, gold_id)
                docs = [re.sub(r"^Document \[\d+\]", f"Document [{i+1}]", block)
                        for i, block in enumerate(docs)]
                new_text = prefix + "\n".join(docs) + tail
                prompt_hash = digest(new_text.encode())
                anchor = originals.get((qid, prompt, position))
                if anchor:
                    if prompt_hash != anchor["prompt_sha256"] or ids != anchor["document_ids"]:
                        raise ValueError("Reconstructed anchor differs from the source")
                    matched_anchors += 1
                jobs.append({**{k: source[k] for k in ["question_id", "question", "answers", "task_type", "document_count", "gold_document_id", "prompt_id", "strategy_text"]},
                    "scenario_id": f"{qid}-d20-p{position:02d}-{prompt}",
                    "gold_position": position, "position_label": f"p{position:02d}",
                    "document_ids": ids, "prompt_text": new_text, "prompt_sha256": prompt_hash})
    out = ROOT / config["raw_output"]
    out.mkdir(parents=True, exist_ok=True)
    blob = b"".join((json.dumps(j, ensure_ascii=False) + "\n").encode() for j in jobs)
    scenario_path = out / "scenarios.jsonl.gz"
    if scenario_path.exists():
        with gzip.open(scenario_path, "rb") as handle:
            if handle.read() != blob:
                raise ValueError("Refusing to replace a different prepared scenario set")
    else:
        with gzip.open(scenario_path, "wb") as handle:
            handle.write(blob)
    manifest = {"batch_id": config["batch_id"], "prepared_at": timestamp(), "config": config,
                "config_sha256": digest(json.dumps(config, sort_keys=True).encode()),
                "scenarios_uncompressed_sha256": digest(blob), "scenarios": len(jobs),
                "matched_historical_prompt_anchors": matched_anchors,
                "credential_values_persisted": False}
    existing = out / "manifest.json"
    if existing.exists():
        old = json.loads(existing.read_text())
        if old["config_sha256"] != manifest["config_sha256"]:
            operational = {"max_concurrency", "initial_tpm_per_credential_model", "maximum_tpm_per_credential_model", "operational_model_limits"}
            old_protocol = {k:v for k,v in old["config"].items() if k not in operational}
            new_protocol = {k:v for k,v in config.items() if k not in operational}
            if old_protocol != new_protocol:
                raise ValueError("Existing batch uses another frozen experimental protocol")
            revisions = old.get("operational_revisions", [])
            revisions.append({"timestamp": timestamp(), "previous_config_sha256": old["config_sha256"],
                              "previous_settings": {k:v for k,v in old["config"].items() if k in operational},
                              "reason": "Observed RPM/TPM limits; pool models separately and share each model budget across credential slots"})
            manifest["operational_revisions"] = revisions
            manifest["prepared_at"] = old["prepared_at"]
            dump(existing, manifest)
    else:
        dump(existing, manifest)
    return jobs, out, matched_anchors


def load_keys(_unused=None):
    key = os.getenv("SILICONFLOW_API_KEY")
    if not key:
        raise ValueError("Set SILICONFLOW_API_KEY in the environment.")
    return [key]


class Lane:
    """Shared model budget across keys; keys are not assumed to add account quota."""
    def __init__(self, initial, maximum, stop, initial_rpm=600, maximum_rpm=2000):
        self.budget, self.maximum, self.stop = initial, maximum, stop
        self.rpm, self.maximum_rpm = initial_rpm, maximum_rpm
        self.recent = deque()
        self.request_times = deque()
        self.next_request = 0.0
        self.lock = threading.Condition()
        self.cooldown = 0.0
        self.last_adjusted = time.monotonic()
        self.ratio = 0.28
        self.ratelimits = 0

    def acquire(self, prompt):
        with self.lock:
            while not self.stop.is_set():
                now = time.monotonic()
                while self.recent and now - self.recent[0][0] >= 61:
                    self.recent.popleft()
                while self.request_times and now - self.request_times[0] >= 61:
                    self.request_times.popleft()
                if now - self.last_adjusted >= 62 and now >= self.cooldown:
                    self.budget = min(self.maximum, int(self.budget * 1.35))
                    self.rpm = min(self.maximum_rpm, max(self.rpm+1, int(self.rpm*1.35)))
                    self.last_adjusted = now
                estimate = min(self.budget, max(1000, int(len(prompt) * self.ratio) + 800))
                if now >= max(self.cooldown, self.next_request) and len(self.request_times) < self.rpm and sum(r[1] for r in self.recent) + estimate <= self.budget:
                    entry = [now, estimate]
                    self.recent.append(entry)
                    self.request_times.append(now)
                    self.next_request = now + 61/self.rpm
                    return entry
                self.lock.wait(timeout=0.5)
        return None

    def observe(self, entry, usage, status, error):
        with self.lock:
            if usage.get("total_tokens"):
                entry[1] = usage["total_tokens"]
            if status == 429:
                self.ratelimits += 1
                now = time.monotonic()
                if now >= self.cooldown:
                    if "RPM" in (error or ""):
                        self.rpm = max(1, int(self.rpm * 0.65))
                    else:
                        self.maximum = max(10000, min(self.maximum, int(self.budget * 0.9)))
                        self.budget = max(10000, int(self.budget * 0.65))
                    self.cooldown = now + 61
                    self.last_adjusted = now
            self.lock.notify_all()


def collect(config, jobs, out, keys, selected_models=None):
    lock_handle = (out / ".collection.lock").open("w")
    fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    stop = threading.Event()
    for sig in [signal.SIGINT, signal.SIGTERM]:
        signal.signal(sig, lambda *_: stop.set())
    done = set()
    raw_path = out / "raw_responses.jsonl"
    if raw_path.exists():
        with raw_path.open() as handle:
            for line in handle:
                r = json.loads(line)
                identity = r["model"], r["scenario_id"]
                if identity in done:
                    raise ValueError("Duplicate successful output in resume log")
                done.add(identity)
    active_models = selected_models or config["models"]
    active_expected = len(jobs)*len(active_models)
    work = [(m, j) for m in active_models for j in jobs if (m, j["scenario_id"]) not in done]
    random.Random(config["job_shuffle_seed"]).shuffle(work)
    lanes = {model: Lane(limits["initial_tpm"], limits["maximum_tpm"], stop,
                         limits["initial_rpm"], limits["maximum_rpm"])
             for model, limits in config["operational_model_limits"].items() if model in active_models}
    # Preserve the rolling window on resume: restarting a process must not
    # pretend the account's recent requests and token usage have disappeared.
    prior_attempts = out / "attempts.jsonl"
    if prior_attempts.exists():
        now_wall, now_mono = dt.datetime.now(dt.timezone.utc), time.monotonic()
        for line in prior_attempts.read_text().splitlines():
            event = json.loads(line)
            lane = lanes.get(event["model"])
            age = (now_wall-dt.datetime.fromisoformat(event["timestamp"])).total_seconds()
            if lane is not None and 0 <= age < 61:
                lane.recent.append([now_mono-age,(event.get("usage") or {}).get("total_tokens") or 4000])
                lane.request_times.append(now_mono-age)
                if event["http_status"] == 429:
                    lane.cooldown = max(lane.cooldown,now_mono+61-age)
    io_lock = threading.Lock()
    slot_lock, dispatch_counts = threading.Lock(), Counter()
    counts = Counter(model for model, sid in done)
    attempt_counts, usage_totals = Counter(), Counter()
    errors, durations = Counter(), []
    started = time.monotonic()
    raw_handle = raw_path.open("a", encoding="utf-8")
    attempt_handle = (out / "attempts.jsonl").open("a", encoding="utf-8")

    def clean(value):
        text = str(value)
        for key in keys:
            text = text.replace(key, "[REDACTED]")
        return re.sub(r"sk-[A-Za-z0-9_-]{20,}", "[REDACTED]", text)

    def worker(model, job, slot):
        lane = lanes[model]
        payload = {"model": model, "messages": [{"role": "user", "content": job["prompt_text"]}],
                   "temperature": config["temperature"], "max_tokens": config["max_tokens"], "stream": False}
        if "Qwen3" in model:
            payload["enable_thinking"] = config["qwen3_enable_thinking"]
        for attempt in range(1, config["max_attempts_per_job"] + 1):
            entry = lane.acquire(job["prompt_text"])
            if entry is None:
                return False
            with slot_lock:
                slot = dispatch_counts[model] % len(keys)
                dispatch_counts[model] += 1
            t = time.monotonic()
            status, response, error, trace = None, None, None, None
            try:
                req = urllib.request.Request(config["endpoint"], data=json.dumps(payload).encode(),
                    headers={"Authorization": "Bearer " + keys[slot], "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as result:
                    status = result.status
                    response = json.load(result)
                    trace = result.headers.get("x-siliconcloud-trace-id")
                choices = response.get("choices") or []
                if response.get("model") != model or not choices or not choices[0].get("message", {}).get("content"):
                    error = "Unexpected model identity, choices, or empty content"
            except urllib.error.HTTPError as exc:
                status, error = exc.code, clean(exc.read().decode("utf-8", "replace"))[:1000]
            except Exception as exc:
                error = type(exc).__name__
            elapsed = time.monotonic() - t
            usage = response.get("usage", {}) if response else {}
            lane.observe(entry, usage, status, error)
            success = status == 200 and error is None
            event = {"timestamp": timestamp(), "model": model, "scenario_id": job["scenario_id"],
                     "credential_slot": slot + 1, "attempt": attempt, "http_status": status,
                     "latency_s": round(elapsed, 4), "success": success, "error": error,
                     "trace_id": trace, "usage": usage}
            with io_lock:
                attempt_handle.write(json.dumps(event, ensure_ascii=False) + "\n")
                attempt_handle.flush()
                attempt_counts[str(status)] += 1
                if success:
                    record = {**{k: job[k] for k in job if k not in ["document_ids", "prompt_text", "strategy_text"]},
                              "batch_id": config["batch_id"], "model": model, "timestamp": event["timestamp"],
                              "status": "ok", "http_status": status, "credential_slot": slot + 1,
                              "attempt_count": attempt, "latency_s": event["latency_s"], "trace_id": trace,
                              "request": payload, "response": response}
                    serialized = json.dumps(record, ensure_ascii=False)
                    if any(key in serialized for key in keys):
                        stop.set()
                        raise RuntimeError("Credential detected in output; refused to persist it")
                    raw_handle.write(serialized + "\n")
                    raw_handle.flush()
                    counts[model] += 1
                    usage_totals.update({k: usage.get(k, 0) or 0 for k in ["prompt_tokens", "completion_tokens", "total_tokens"]})
                    durations.append(elapsed)
                else:
                    errors[str(status) if status else error] += 1
            if success:
                return True
            if status in [400, 401, 402, 403, 404]:
                stop.set()
                return False
            if attempt < config["max_attempts_per_job"]:
                stop.wait(min(30, 2 ** attempt))
        return False

    def progress(state):
        with io_lock:
            result = {"batch_id": config["batch_id"], "state": state, "updated_at": timestamp(),
                      "successful": sum(counts.values()), "expected": config["expected_successful_responses"],
                      "active_models": active_models, "active_successful": sum(counts[m] for m in active_models),
                      "active_expected": active_expected,
                      "by_model": dict(counts), "http_attempts_this_process": dict(attempt_counts),
                      "usage_this_process": dict(usage_totals), "elapsed_s": round(time.monotonic() - started, 1),
                      "max_concurrency": config["max_concurrency"], "credential_slots": len(keys),
                      "mean_request_latency_s": round(sum(durations) / len(durations), 3) if durations else None,
                      "lanes": [{"model": model, "tpm_budget": lane.budget, "rpm_budget": lane.rpm,
                                  "rate_limits": lane.ratelimits} for model, lane in lanes.items()]}
            dump(out / "progress.json", result)
            print(json.dumps(result, ensure_ascii=False), flush=True)

    progress("running")
    pending = set()
    # Separate pools prevent a rate-limited model from occupying the other
    # model's worker slots while waiting for its budget to replenish.
    pools = {model: ThreadPoolExecutor(max_workers=max(1,config["max_concurrency"]//len(active_models))) for model in active_models}
    try:
        for i, (model, job) in enumerate(work):
            pending.add(pools[model].submit(worker, model, job, i % len(keys)))
        last = time.monotonic()
        while pending:
            finished, pending = wait(pending, timeout=5, return_when=FIRST_COMPLETED)
            for future in finished:
                try:
                    future.result()
                except Exception as exc:
                    stop.set()
                    print(json.dumps({"fatal_type": type(exc).__name__}), flush=True)
            if time.monotonic() - last >= 30:
                progress("stopping" if stop.is_set() else "running")
                last = time.monotonic()
    finally:
        for pool in pools.values():
            pool.shutdown(wait=True)
    state = "complete" if sum(counts.values()) == config["expected_successful_responses"] else ("selected_models_complete" if sum(counts[m] for m in active_models) == active_expected else "incomplete")
    progress(state)
    raw_handle.close()
    attempt_handle.close()
    lock_handle.close()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "collect"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", action="append", choices=["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen3-8B"], help="Collect only the selected model(s); preserve all other saved outputs")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    jobs, out, anchors = prepare(config)
    print(json.dumps({"prepared_scenarios": len(jobs), "matched_historical_anchors": anchors,
                      "planned_generations": config["expected_successful_responses"]}), flush=True)
    if args.mode == "collect":
        state = collect(config, jobs, out, load_keys(None), args.model)
        raise SystemExit(0 if state in ["complete", "selected_models_complete"] else 2)


if __name__ == "__main__":
    main()
