# 现有数据分析

[发现与课设写法](findings.md)包含证据、适用范围和评分局限；正式交付见[案例 PDF](../../report/baseline_case_report.pdf)/[正文](../../report/baseline_case_report.md)与[答辩 PPTX](../../presentation/baseline_defense_slides.pptx)/[PDF](../../presentation/baseline_defense_slides.pdf)。本目录包含聚合结果、审计和匿名待审样本，不包含逐条回答原文。

## 汇总表

| 文件 | 内容 |
| --- | --- |
| `reasoning_prompt_summary.csv` | 模型、benchmark、提示的评分、token、截断和未解析情况 |
| `reasoning_paired_contrasts.csv` | 指定提示对照、按题区间及未解析记录极端重判敏感性 |
| `reasoning_grading_status.csv` | 源评分状态计数 |
| `reasoning_token_instruction_compliance.csv` | 提示 token 数与实际返回 token 的差异 |
| `document_qa_prompt_summary.csv` | 四种评分、返回 token、截断和复核比例 |
| `document_qa_paired_contrasts.csv` | 同题位置、文档数、提示、模型和有无资料的比较 |
| `document_qa_position_summary.csv` | NoCoT、原指定 core8、常规 main19 的位置汇总 |
| `document_qa_control_summary.csv` | 无资料对照 |
| `document_qa_scoring_diagnostics.csv` | 评分分歧和复核计数 |
| `document_qa_truncation_outcomes.csv` | 按策略与截断状态拆分评分 |
| `scoring-audit.md` | 源规则、四口径和既有 139 条覆盖的离线重放；不改源分数 |
| `scoring-review-sample.csv` | 固定种子分层的 170 条匿名待审样本；所有人工标签为空 |
| `anonymous_reproduction.json` | 匿名复算输入/排序哈希、环境与保留快照的边界 |

评分率字段为 0–1；`difference_pp` 和区间字段为百分点。`token_saving_pct` 为相对第二个条件的平均返回 token 减少百分比，负值表示返回量增加。`pairs` 是场景配对数，独立题数见 `independent_questions`，两者不能替代。

`core8` 来自采集 manifest 的 `primary_strategy_ids`。`main19` 来自清洗表的 `strategy_scope=main_comparison`，排除了翻译和压力策略。四种评分各自保留，来源清单和后续清洗表的主指标标注不一致，不能仅选一种有利口径。

`unresolved_sensitivity_low_pp/high_pp` 不是置信区间：它们在假定已解析评分有效时，对未解析记录作极端判定，展示结论对提取失败的敏感性。普通 95% bootstrap 区间未作多重比较校正，全部用于探索性描述。

## 复现

公开匿名路径为 `python3 scripts/reproduce_baselines.py --mode anonymous`，完整本地路径为 `--mode full-local`；依赖、字体与不能从匿名特征重算的字段见[复现说明](../../docs/reproducibility.md)。有本地清洗输入时也可单独运行 `python scripts/analysis/analyze_baselines.py`。输入哈希、版本、样本量与 bootstrap 设置保存在清单中；不需要 API Key 或新模型调用。

分类标签覆盖全部 149,200 条响应，31 提示映射 14 类要求，页面已实现要求×可见格式→状态→匿名记录联动。标签和规则保存在 `app/data/method-features.json.gz` 与 `method-evidence.json`，完整字段审计见 `data/processed/missingness_report.csv/.json`。MMLU-Pro 中性标签为选择题，保留学科元数据不足以独立确认数学子集。
