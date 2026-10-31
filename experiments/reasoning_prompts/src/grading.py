"""本地判分：选择题按字母，数学题按数值或符号等价性；不调用第四个模型。"""

import re
from fractions import Fraction


def last_boxed(text):
    """读取最后一个完整方框，支持分式等嵌套花括号。"""
    answer = None
    for match in re.finditer(r"\\boxed\s*\{", text):
        start, depth = match.end(), 1
        for index in range(start, len(text)):
            depth += (text[index] == "{") - (text[index] == "}")
            if depth == 0:
                answer = text[start:index]
                break
    return answer


def extract_answer(text):
    """优先使用最后的答案标记，随后使用方框或独立的单行答案。"""
    # 标记与内容分开扫描，避免“最终答案：\nAnswer: ...”吞掉最后一个标记。
    markers = list(re.finditer(r"(?i)(?<![a-z])(?:final\s+answer|answer|ans|an|最终答案|答案)\s*\**\s*[:：]\s*\**\s*", text))
    if markers:
        tail = text[markers[-1].end():].strip()
        if not tail:
            return None
        answer = tail.splitlines()[0].strip().strip("*`").strip()
        return last_boxed(answer) or answer
    boxed = last_boxed(text)
    if boxed is not None:
        return boxed
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    # 不从长篇推导中捡取碰巧正确的中间数值。
    return lines[0] if len(lines) == 1 and len(lines[0]) <= 200 else None


def numeric_value(text):
    """严格识别独立数值、普通分数和百分数，拒绝夹杂解释的表达式。"""
    text = text.strip().strip("$ ")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    # 官方模板允许 ($NUMBER)：去掉括号后还须去掉货币符号。
    text = text.removeprefix(r"\$").strip("$ ").replace("−", "-")
    if "," in text:
        # 只去掉合法千位分隔符，不能把坐标 (1,2) 误读成数值 12。
        if not re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
            return None
        text = text.replace(",", "")
    text = re.sub(r"^\\(?:d?frac)\{(-?\d+)\}\{(-?\d+)\}$", r"\1/\2", text)
    percent = text.endswith("%")
    if percent:
        text = text[:-1]
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:/[+-]?\d+)?", text):
        return None
    try:
        return Fraction(text) / (100 if percent else 1)
    except (ValueError, ZeroDivisionError):
        return None


def grade_answer(text, gold, benchmark):
    """无法解析的标准答案留空待复核，不能误记为模型答错。"""
    answer = extract_answer(text)
    result = {"answer": answer, "grade": 0, "grading_status": "已判分", "needs_review": False}
    if answer is None:
        return {**result, "grading_status": "未提取到最终答案", "needs_review": True}
    if benchmark == "mmlu":
        match = re.fullmatch(r"\s*\(?\$?([A-J])\$?\)?[.。]?\s*", answer, re.I)
        if match:
            result["grade"] = int(match.group(1).upper() == gold.strip().upper())
        else:
            result.update(grading_status="选择题答案格式不明确", needs_review=True)
        return result
    gold_number, answer_number = numeric_value(gold), numeric_value(answer)
    if gold_number is not None and answer_number is not None:
        result["grade"] = int(gold_number == answer_number)
        return result
    from math_verify import LatexExtractionConfig, parse, verify

    def parse_math(value):
        # 候选已是提取出的最终答案；禁止字符串回退碰巧匹配。
        value = value.strip().strip("$")
        # 只规范化独立且无歧义的数值根式；含额外项的表达式仍交给解析器。
        radical = re.fullmatch(r"([+-]?(?:\d+(?:\.\d+)?|\.\d+)?)\s*√\s*(?:([0-9]+(?:\.[0-9]+)?)|\(([0-9]+(?:\.[0-9]+)?)\))", value)
        if radical:
            value = radical[1] + r"\sqrt{" + (radical[2] or radical[3]) + "}"
        return parse("$" + value + "$", extraction_config=[LatexExtractionConfig()],
                     fallback_mode="no_fallback", parsing_timeout=5)

    gold_parsed, answer_parsed = parse_math(gold), parse_math(answer)
    if not gold_parsed:
        result.update(grade=None, grading_status="标准答案无法自动解析", needs_review=True)
    elif not answer_parsed:
        result.update(grading_status="模型答案无法自动解析", needs_review=True)
    else:
        result["grade"] = int(verify(gold_parsed, answer_parsed, timeout_seconds=5))
    return result
