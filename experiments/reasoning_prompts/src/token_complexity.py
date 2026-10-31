"""根据输出长度与正确性，拟合每道题的词元阈值。"""

import numpy as np


def token_complexity(all_grades, all_token_counts):
    """输入形状为[提示词数,题数]，返回阈值、拟合准确率、全对全错标记。

    预测规则为“输出长度 >= 阈值”。候选阈值为实际出现的不同长度与正无穷。
    相同长度不能被划到阈值两侧；多个阈值并列最优时选较小者。
    全对题取观测最短长度，全错题取正无穷。这是样本内拟合，不是因果估计。
    """
    grades, counts = np.asarray(all_grades), np.asarray(all_token_counts)
    if grades.ndim != 2 or grades.shape != counts.shape or 0 in grades.shape:
        raise ValueError("评分与词元数必须是形状相同的非空二维数组。")
    if not np.isin(grades, [0, 1]).all():
        raise ValueError("评分必须为 0 或 1，缺失回答不能参与阈值拟合。")
    if not np.isfinite(counts).all() or (counts < 0).any() or (counts != np.floor(counts)).any():
        raise ValueError("词元数必须是非负整数。")
    thresholds, accuracies, trivials = [], [], []
    for grade, count in zip(grades.T, counts.T):
        candidates = np.append(np.unique(count), np.inf)
        scores = ((count[None, :] >= candidates[:, None]) == grade[None, :]).mean(axis=1)
        best = int(np.argmax(scores))
        threshold = float("inf") if not grade.any() else float(candidates[best])
        thresholds.append(threshold)
        accuracies.append(float(scores[best]))
        trivials.append(int(np.all(grade == grade[0])))
    return thresholds, accuracies, trivials
