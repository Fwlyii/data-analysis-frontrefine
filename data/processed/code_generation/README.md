# 代码生成匿名特征

`data_dictionary.tsv` 说明 14 个字段；同样的字段已合并进上一级统一字典和缺失报告。匿名输入位于 `app/data/code-features.json.gz`，统计证据位于 `app/data/code-evidence.json`。

90,210 条、194 道题、31 提示、3 模型、每条件 5 次独立生成。共同环境排除题对应 465 个 `passed=null`，性能只使用其余 89,745 条。其余公开字段没有空值；不以 0 填充 null。

不公开题目、回答、代码、源 ID、错误原文和个人路径。[完整方法](../../../docs/code-generation.md)。
