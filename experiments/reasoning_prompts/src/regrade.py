"""离线重新判分：保留最初评分及修订清单，不重新生成回答。"""

from pathlib import Path

from grading import grade_answer
from result_io import ROOT, atomic_json, exclusive_run, fingerprint, read_json, result_path

FIELDS = ("answer", "grade", "grading_status", "needs_review")


def regrade(directory):
    """修复解析规则后，对同一批原始回答统一重算并保留评分来源。"""
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    review_path = directory / "grading_reviews.json"
    reviews = read_json(review_path) if review_path.exists() else []
    review_map = {}
    for review in reviews:
        key = tuple(review[field] for field in ("model", "benchmark", "prompt_id", "question_id"))
        if key in review_map or type(review["grade"]) is not int or review["grade"] not in (0, 1):
            raise ValueError("逐条复核存在重复项或无效分数。")
        if not all(isinstance(review.get(field), str) and review[field].strip()
                   for field in ("question_hash", "response_hash", "reviewer", "reason")):
            raise ValueError("逐条复核必须包含题目与回答摘要、复核者及理由。")
        review_map[key] = review
    code = (ROOT / "grading.py").read_text(encoding="utf-8")
    revision = fingerprint({"grading_code": code, "reviews": reviews}) if reviews else fingerprint(code)
    audit = {"status": "running", "grading_revision": revision,
             "original_manifest_hash": fingerprint(manifest),
             "method": "仅根据已保存的回答和标准答案离线重算，原始评分保存在 original_grading",
             "answer_reviews": reviews, "reviewed_answers": 0, "changes": []}
    applied_reviews = set()
    with exclusive_run(directory):
        atomic_json(directory / "regrading.json", audit)
        for model in manifest["models"]:
            for benchmark, dataset in manifest["datasets"].items():
                questions = {q["id"]: q for q in dataset["questions"]}
                for prompt_id in manifest["prompts"]:
                    path = result_path(directory, model, benchmark, prompt_id)
                    if not path.exists():
                        continue
                    data = read_json(path)
                    if data.get("manifest_hash") != fingerprint(manifest):
                        raise ValueError("结果身份不一致，不能重新判分。")
                    for record in data["records"]:
                        if record.get("status") != "ok":
                            continue
                        question = questions[record["question_id"]]
                        if record["question_hash"] != question["hash"]:
                            raise ValueError("题目内容不一致，不能重新判分。")
                        original = record.setdefault("original_grading", {key: record.get(key) for key in FIELDS})
                        updated = grade_answer(record["text"], question["answer"], benchmark)
                        key = (model, benchmark, prompt_id, record["question_id"])
                        review = review_map.get(key)
                        if review:
                            if review["question_hash"] != question["hash"] or review["response_hash"] != fingerprint(record["text"]):
                                raise ValueError("逐条复核与实际题目或回答不一致，不能套用。")
                            updated.update(grade=review["grade"], grading_status="已按保存的逐条复核结论判分", needs_review=False)
                            record["grading_review"] = review
                            applied_reviews.add(key)
                        else:
                            record.pop("grading_review", None)
                        record.update(updated, grading_revision=revision)
                        audit["reviewed_answers"] += 1
                        if updated != original:
                            audit["changes"].append({"model": model, "benchmark": benchmark, "prompt_id": prompt_id,
                                                     "question_id": record["question_id"], "before": original, "after": updated})
                    atomic_json(path, data)
        if applied_reviews != set(review_map):
            raise ValueError("逐条复核包含不存在或未成功生成的回答。")
        audit["status"] = "complete"
        atomic_json(directory / "regrading.json", audit)
    print(f"离线判分完成：检查 {audit['reviewed_answers']} 个回答，更新 {len(audit['changes'])} 条评分记录，未调用模型。", flush=True)
    return audit
