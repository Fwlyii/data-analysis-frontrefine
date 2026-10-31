"""沿用官方绘图的提示词配色、点形和面积，补充中文图例名称。

来源：Compressed-CoT/compressed-cot 的 096f6e9 提交，plots.py。
同类提示词共用颜色与点形，长度或步数限制通过点面积区分。
"""

import re


# 每项依次为中文名称、颜色、点形；颜色按官方字典实际生效的值保留。
STYLES = {
    "NoCoT": ("只给答案", "limegreen", "d"),
    "DefaultCoT": ("普通思维链", "black", "*"),
    "BeConcise": ("简洁思维链", "pink", "s"),
    "BulletPoints": ("项目符号", "gray", "x"),
    "OnlyNumbers": ("只用数字或公式", "green", "D"),
    "NoSpaces": ("去掉空格", "magenta", "v"),
    "NoProperGrammar": ("省略正规语法", "blueviolet", "d"),
    "AbbreviateWords": ("缩写单词", "gray", "+"),
    "WordLimit": ("单词限制", "darkorange", "."),
    "CharLimit": ("字母限制", "yellowgreen", "h"),
    "TokenLimit": ("词元限制", "blue", "^"),
    "StepLimit": ("步骤限制", "lightsteelblue", ">"),
    "ChineseCoT": ("中文回答", "darkblue", "o"),
    "ChineseCoTLimit": ("中文字符限制", "deepskyblue", "p"),
}

# 原代码按离散档位映射面积；保留未在本次 31 种提示词中出现的档位。
SIZE_RULES = {
    "WordLimit": ([1, 5, 10, 15, 25, 50, 100], 200, 500),
    "CharLimit": ([1, 10, 20, 50, 100, 500], 50, 300),
    "TokenLimit": ([1, 10, 20, 50, 100, 500], 100, 300),
    "StepLimit": ([1, 2, 5], 100, 300),
    "ChineseCoTLimit": ([10, 50, 100, 500], 100, 300),
}


def prompt_style(prompt_id):
    """固定按提示词身份取样式，避免顺序或数据集变化导致颜色变化。"""
    match = re.fullmatch(r"(\w+)\((\d+)\)", prompt_id)
    category, value = (match[1], int(match[2])) if match else (prompt_id, None)
    if category == "ChineseCoT" and value is not None:
        category = "ChineseCoTLimit"
    if category not in STYLES:
        raise ValueError(f"提示词 {prompt_id} 尚无绘图样式，请先补充映射。")
    label, color, marker = STYLES[category]
    size = 300
    if value is not None:
        bins, minimum, maximum = SIZE_RULES[category]
        index = min(range(len(bins)), key=lambda i: abs(bins[i] - value))
        size = minimum + index / (len(bins) - 1) * (maximum - minimum)
        label += f"（{value}）"
    return {"prompt_id": prompt_id, "category": category, "label": label,
            "color": color, "marker": marker, "size": size}
