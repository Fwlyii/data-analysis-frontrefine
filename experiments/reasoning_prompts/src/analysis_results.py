"""分析本次实验的本地结果，输出中文表格、复核清单及图像。"""

import csv
from pathlib import Path

import numpy as np
from scipy.stats import kendalltau, spearmanr

from result_io import PROTOCOL, atomic_json, fingerprint, read_json, result_path
from token_complexity import token_complexity
from prompt_styles import prompt_style


def ratio(numerator, denominator):
    """分母为零时留空，不向结果文件写入非标准数值。"""
    return float(numerator / denominator) if denominator else None


def summarize(grades, counts, prompt_ids, question_ids):
    """同时给出论文公式与旧代码口径，防止同名指标含义混淆。"""
    grades, counts = np.asarray(grades), np.asarray(counts)
    thresholds, fits, trivials = token_complexity(grades, counts)
    thresholds = np.asarray(thresholds)
    finite = np.isfinite(thresholds)
    n = len(question_ids)
    rows = []
    for prompt_id, grade, count in zip(prompt_ids, grades, counts):
        accuracy = float(grade.mean())
        predicted = float((count >= thresholds).mean())
        valid_correlation = finite.sum() >= 2 and len(np.unique(count[finite])) > 1 and len(np.unique(thresholds[finite])) > 1
        rows.append({
            "prompt_id": prompt_id, "accuracy": accuracy, "mean_tokens": float(count.mean()),
            "predicted_accuracy": predicted, "absolute_error": abs(predicted - accuracy),
            "relative_error_actual": ratio(abs(predicted - accuracy), accuracy),
            "relative_error_predicted_legacy": ratio(abs(predicted - accuracy), predicted),
            "spearman": float(spearmanr(count[finite], thresholds[finite]).statistic) if valid_correlation else None,
            "kendall": float(kendalltau(count[finite], thresholds[finite]).statistic) if valid_correlation else None,
            "correlation_n": int(finite.sum()),
        })
    finite_sum = float(thresholds[finite].sum())
    default = next((r["mean_tokens"] for r in rows if r["prompt_id"] == "DefaultCoT"), None)
    concise = next((r["mean_tokens"] for r in rows if r["prompt_id"] == "BeConcise"), None)
    errors = [r["relative_error_actual"] for r in rows if r["relative_error_actual"] is not None]
    # 理想分配曲线允许跳过题目且跳过成本为零，属于拟合模型内的参考曲线。
    oracle_cost = np.insert(np.cumsum(np.sort(thresholds[finite])), 0, 0) / n
    oracle_accuracy = np.arange(int(finite.sum()) + 1) / n
    return {
        "num_questions": n, "num_prompts": len(prompt_ids), "fit_accuracy": float(np.mean(fits)),
        "trivial_fraction": float(np.mean(trivials)), "finite_threshold_count": int(finite.sum()),
        "T_star_all_questions": finite_sum / n,
        "T_star_finite_only_legacy": ratio(finite_sum, int(finite.sum())),
        "mean_relative_error_actual": float(np.mean(errors)) if errors else None,
        "relative_error_defined_prompts": len(errors),
        "concise_compression_ratio": ratio(default, concise) if default is not None and concise is not None else None,
        "oracle_compression_ratio": ratio(default, finite_sum / n) if default is not None else None,
        "thresholds": [{"question_id": q, "threshold": float(t) if np.isfinite(t) else None,
                        "infinite": not bool(np.isfinite(t)), "fit_accuracy": f}
                       for q, t, f in zip(question_ids, thresholds, fits)],
        "prompts": rows, "oracle": {"mean_tokens": oracle_cost.tolist(), "accuracy": oracle_accuracy.tolist()},
    }


def load_group(directory, manifest, model, benchmark):
    """按固定题目身份校验各提示词的记录，拒绝错位比较。"""
    questions = manifest["datasets"][benchmark]["questions"]
    expected = {q["id"]: q for q in questions}
    order = list(expected)
    records_by_prompt, review, observed_models = {}, [], set()
    for prompt_id in manifest["prompts"]:
        path = result_path(directory, model, benchmark, prompt_id)
        result = read_json(path) if path.exists() else {"records": []}
        if path.exists() and any(result.get(k) != v for k, v in {
                "model": model, "benchmark": benchmark, "prompt_id": prompt_id,
                "manifest_hash": fingerprint(manifest)}.items()):
            raise ValueError("结果文件身份不匹配。")
        records = result["records"]
        ids = [r["question_id"] for r in records]
        if len(set(ids)) != len(ids) or any(q not in expected for q in ids) or ids != [q for q in order if q in ids]:
            raise ValueError("结果中存在重复、未知或顺序错位的题目。")
        valid = {}
        for record in records:
            qid = record["question_id"]
            if record["question_hash"] != expected[qid]["hash"]:
                raise ValueError("结果中的题目摘要不匹配。")
            count = record.get("token_count")
            if record.get("status") == "ok" and record.get("grade") in (0, 1) and isinstance(count, int) and count >= 0:
                valid[qid] = record
            if record.get("response_model"):
                observed_models.add(record["response_model"])
            if record.get("needs_review") or record.get("truncated") or record.get("status") != "ok":
                review.append({"model": model, "benchmark": benchmark, "prompt_id": prompt_id, **record})
        records_by_prompt[prompt_id] = valid
    if len(observed_models) > 1:
        raise ValueError(f"{model}/{benchmark} 返回了多个模型标识，不能混合统计；请检查服务路由。")
    complete_ids = [qid for qid in order if all(qid in records for records in records_by_prompt.values())]
    return records_by_prompt, complete_ids, review


def draw_figures(group, directory, title):
    """按官方提示词样式绘制双面板图；图例放在数据区外。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "Noto Sans CJK JP", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"
    rows = group["prompts"]
    styles = {r["prompt_id"]: prompt_style(r["prompt_id"]) for r in rows}
    legend_rows = int(np.ceil((len(rows) + 1) / 4))
    legend_height = 0.34 * legend_rows + 0.7
    height = 4.8 + legend_height
    figure, axes = plt.subplots(1, 2, figsize=(14, height))
    figure.subplots_adjust(left=0.06, right=0.98, bottom=legend_height / height,
                           top=1 - 0.7 / height, wspace=0.22)
    handles = {}
    # 大点先画、小点后画，尽量显露重叠点；不改变数据坐标。
    for row in sorted(rows, key=lambda r: styles[r["prompt_id"]]["size"], reverse=True):
        style = styles[row["prompt_id"]]
        options = {"s": style["size"], "marker": style["marker"], "color": style["color"],
                   "alpha": 0.8, "linewidths": 0.7, "zorder": 3, "label": style["label"]}
        if style["marker"] not in ("x", "+"):
            options["edgecolors"] = "black"
        handles[row["prompt_id"]] = axes[0].scatter(row["mean_tokens"], row["accuracy"], **options)
        axes[1].scatter(row["accuracy"], row["predicted_accuracy"], **options)
    oracle, = axes[0].plot(group["oracle"]["mean_tokens"], group["oracle"]["accuracy"],
                           "--", color="orchid", label="拟合阈值下的理想分配", zorder=1)
    # 给较大的官方标记留边距，避免准确率为 0 或 1 时点形被边界裁切。
    axes[0].set(xlabel="每题平均输出词元数", ylabel="准确率", ylim=(-0.06, 1.06))
    axes[1].plot([0, 1], [0, 1], "--", color="gray")
    axes[1].set(xlabel="实际准确率", ylabel="样本内预测准确率", xlim=(-0.06, 1.06), ylim=(-0.06, 1.06))
    axes[0].set_title("（甲）输出长度与准确率", fontsize=11, pad=12)
    axes[1].set_title("（乙）实际与预测准确率", fontsize=11, pad=12)
    figure.suptitle(title, y=1 - 0.16 / height, fontsize=14)
    figure.legend(handles=[handles[r["prompt_id"]] for r in rows] + [oracle],
                  loc="lower center", bbox_to_anchor=(0.5, 0.52 / height), ncol=4,
                  fontsize=9, frameon=False, markerscale=0.65, labelspacing=1.25,
                  handletextpad=0.7, columnspacing=2.8)
    figure.text(0.5, 0.22 / height,
                "颜色和点形区分提示词类别，点大小区分限制值；相同坐标的提示词可能重叠。",
                ha="center", va="center", fontsize=9)
    figure.savefig(directory / "对比图.png", dpi=300)
    figure.savefig(directory / "对比图.pdf")
    figure.savefig(directory / "对比图.svg")
    atomic_json(directory / "提示词样式.json", {
        "source": "https://github.com/Compressed-CoT/compressed-cot/blob/096f6e9/plots.py",
        "encoding": "同类别共用颜色与点形；数值限制按官方离散档位映射点面积。",
        "prompts": [styles[r["prompt_id"]] for r in rows],
    })
    plt.close(figure)


def analyze(directory, allow_incomplete=False, figures=True):
    """默认要求完整结果；显式允许不完整时，仅统计各提示词共同完成的题。"""
    directory = Path(directory)
    manifest = read_json(directory / "manifest.json")
    if manifest.get("protocol") != PROTOCOL:
        raise ValueError("实验协议不同，请使用与该运行对应的代码分析。")
    regrading = read_json(directory / "regrading.json") if (directory / "regrading.json").exists() else None
    if regrading and regrading["status"] != "complete":
        raise ValueError("离线重新判分尚未完成，请先完成重算，避免混合不同评分规则。")
    output = directory / ("analysis_partial" if allow_incomplete else "analysis")
    groups, coverage, review = {}, [], []
    for model in manifest["models"]:
        for benchmark in manifest["datasets"]:
            records, ids, items = load_group(directory, manifest, model, benchmark)
            if regrading and any(r.get("grading_revision") != regrading["grading_revision"] for group in records.values() for r in group.values()):
                raise ValueError("评分规则版本不一致，请重新完成离线判分。")
            review.extend(items)
            expected = len(manifest["datasets"][benchmark]["questions"])
            coverage.append({"model": model, "benchmark": benchmark, "expected": expected,
                             "common_complete": len(ids), "excluded": expected - len(ids)})
            groups[(model, benchmark)] = (records, ids)
    atomic_json(output / "coverage.json", coverage)
    atomic_json(output / "review.json", review)
    if not allow_incomplete and any(row["excluded"] for row in coverage):
        raise ValueError("结果尚未完整或存在待判分题；已写入完成情况与复核清单。重跑原命令可续跑接口失败项。")
    summary = {"protocol": PROTOCOL, "mode": manifest["mode"], "partial": allow_incomplete,
               "grading_revision": regrading["grading_revision"] if regrading else None,
               "interpretation": "阈值与预测均在同一批数据上拟合；试跑结果仅用于检查流程。",
               "coverage": coverage, "groups": {}}
    csv_rows = []
    for (model, benchmark), (records, ids) in groups.items():
        if not ids:
            continue
        prompt_ids = list(manifest["prompts"])
        grades = [[records[p][qid]["grade"] for qid in ids] for p in prompt_ids]
        counts = [[records[p][qid]["token_count"] for qid in ids] for p in prompt_ids]
        group = summarize(grades, counts, prompt_ids, ids)
        group["truncated_answers"] = sum(records[p][qid].get("truncated", False) for p in prompt_ids for qid in ids)
        summary["groups"][f"{model}/{benchmark}"] = group
        folder = output / model / benchmark
        atomic_json(folder / "statistics.json", group)
        if figures:
            stage = {"smoke": "流程试跑", "full": "完整配置", "custom": "自定义实验", "test": "软件测试"}.get(manifest["mode"], "实验")
            if allow_incomplete:
                stage += "（仅共同完成题目）"
            draw_figures(group, folder, f"{stage} · {manifest['models'][model]['label']} · {benchmark} · {len(ids)} 题")
        for row in group["prompts"]:
            csv_rows.append({"模型": model, "数据集": benchmark, "题数": len(ids), "提示词": row["prompt_id"],
                             "准确率": row["accuracy"], "平均输出词元数": row["mean_tokens"],
                             "样本内预测准确率": row["predicted_accuracy"], "斯皮尔曼相关": row["spearman"],
                             "肯德尔相关": row["kendall"], "相对误差（实际准确率作分母）": row["relative_error_actual"]})
    atomic_json(output / "summary.json", summary)
    if csv_rows:
        with (output / "提示词对比.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
            writer.writeheader()
            writer.writerows(csv_rows)
    print(f"统计和复核清单已保存：{output}；待查看记录 {len(review)} 条。", flush=True)
    return summary
