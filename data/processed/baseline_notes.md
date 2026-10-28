# 清洗后数据包

生成时间：2026-10-28T20:23:34+08:00

## 范围与处理原则

- 清洗对象是已下载的 `reasoning` 与 `document_qa` 两个分支数据；main 分支只有课程题目和过程 PDF，没有另一套原始回答数据。
- 本次只读取本地文件，未调用 API。
- 原始文件都保留在各分支原目录。本目录是新增的清洗副本；没有覆盖原文件，也没有删除回答、重复测量条件或截断记录。
- 输出 CSV 使用 UTF-8、英文 snake_case 字段、标准 CSV 引号规则；布尔值写作 `true/false`，空值留空。JSON 数组/对象字段使用紧凑 JSON 字符串。所有 ID 和来源哈希保留。
- 评分只做类型和格式规范化，没有重判答案。不可比较的评分口径没有合并成一个分数。

## reasoning 分支

清洗后包含 74,400 条回答、600 道独立题、31 种提示词。`record_id` 唯一；每个模型 × 数据集 × 提示词组合 200 条。

- `reasoning/responses_clean.csv.gz`：全量逐条回答与评分快照。
- `reasoning/review_queue_clean.csv.gz`：源数据 `included_in_review=true` 的 3,920 条记录。
- `reasoning/questions_clean.csv`、`reasoning/prompts_clean.csv`：拆分出的题目表和提示词表。
- `reasoning/repeated_hash_audit.csv`：9 组重复 `source_record_hash`，全部保留。检查显示重复记录是不同提示词条件下同题同模型返回相同答案，属于有意义的重复测量结果。

空的独立推理字段规范为 null，不代表模型没有展示推理；缺失 token 数不填 0。当前评分原样保留。交付说明指出 DeepSeek 模型组存在离线重评分，而其他模型组使用源评分快照，所以跨模型汇总前仍需统一评分规则。

## document_qa 分支

清洗后包含 74,800 条回答、37,400 个场景、200 道独立题和 75,229 次请求尝试。

- `document_qa/responses_clean.csv.gz`：原始响应与最终离线评分按模型 × 场景合并，一条回答一行。
- `document_qa/scenarios_clean.csv.gz`：场景定义，保留完整 prompt、文档位置与提示词。
- `document_qa/questions_clean.csv`：200 道独立题及答案来源元数据。
- `document_qa/attempts_clean.csv.gz`：重试/请求尝试日志。
- `document_qa/review_queue_clean.csv.gz`：20,782 条 `needs_review=true` 记录。

保留四种不同评分列：`paper_firstline`、`strict_final_em`、`final_contains`、`full_response_contains`。主指标标识为 `paper_firstline`；四个指标含义不同，不能相互替代。1,074 条截断记录和复核标记均保留。来源说明复核队列尚未全部人工复核。

## 清洗和校验

- 原始归档及 LFS 数据校验和与源清单一致。
- reasoning：回答记录数、唯一 ID、题目和提示词一致性、评分 0/1、布尔值、数字字段、覆盖数均已校验。
- document_qa：回答与最终评分按唯一键完整连接；场景 prompt 哈希与实际请求一致；请求 token 与评分表一致性及截断标志一致性已记录在 `quality_report.json`；回答、场景、复核、重试数量和分组覆盖均已校验。
- 详细计数、输入校验和、异常诊断和输出文件校验和见 `quality_report.json` 与 `SHA256SUMS.txt`。

## 建议读取顺序

分析模型表现时，先读各分支 `responses_clean.csv.gz`；人工复核时读对应 `review_queue_clean.csv.gz`；需要核对题目或完整 prompt 时，用 `question_id` / `scenario_id` 连接 `questions_clean.csv` / `scenarios_clean.csv.gz`。不要把两分支的行直接合并计算一个准确率：任务、评分和实验设计不同。
