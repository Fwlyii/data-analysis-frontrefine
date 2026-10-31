# 多轮代码修复匿名特征

由 `experiments/code_repair/src/analyze.py` 从本机完整记录生成。每行是模型 × 题目 × 组别 × 轮次；初稿共享，分析视图复用四次，不能将其当作四次独立生成。

| 字段 | 含义 |
|---|---|
| model / task_id / arm | 模型、公开题目编号和组别 |
| round | 0 为初稿，1–4 为后续生成 |
| full_pass | 同时通过诊断和隐藏测试 |
| diagnostic_pass / hidden_pass | 两套测试分别是否通过 |
| initial_full_pass | 共享初稿的完整通过状态 |
| input_tokens / output_tokens / total_tokens | 平台真实 usage |
| cumulative_tokens | 本组截至当前轮的累计 Token，含共享初稿一次 |
| code_changed_from_previous | AST 是否变化；首轮为空 |
| code_text_changed_from_previous | 提取代码的文本是否变化；首轮为空 |
| public_error_type | 诊断首个失败的异常类型，或 pass |
| finish_reason | 平台生成终止原因 |
| evaluation_seconds | 本地隔离评测耗时 |
| physical_record_id / shared_seed | 实际生成记录键、是否复用初稿 |

`events.csv` 保存实际发生的 API、修改、测试和请求错误事件，包含时间、模型、题目、组别、轮次和对应数值；不适用的字段留空，不推造事件。

数据中没有密钥、完整题目、模型回答或隐藏用例。原始记录只保存在本机 `data/raw/code_repair/`；原 CodePromptEval 匿名特征继续存于原目录。
