# 数据字典

## 统一匿名特征表

`processed/all_records.csv.gz` 共 248,586 条物理响应。CSV 空单元格表示 null；布尔为 true/false；时间为 UTC。不同任务的评分规则由 metric_name 区分，不计算跨任务总准确率。

| 字段 | 类型 | 含义 | 缺失原因 / 规则 |
|---|---|---|---|
| record_id | string | Anonymous unique identity within this released project | never missing |
| experiment_id | category | Experiment direction; identifies the unit and protocol | never missing |
| model_id | category | Canonical model family identifier | never missing |
| benchmark | category | Benchmark/task family; not a score scale | never missing |
| question_key | string | Experiment-scoped SHA-256 pseudonym of the source question ID | never missing |
| prompt_id | category/null | Named prompt strategy | not applicable to repair baseline |
| timestamp | UTC datetime/null | Recorded response timestamp normalized to UTC | not recorded in historical reasoning/code-generation sources |
| input_tokens | integer/null | Provider input token count | provider/source did not record it |
| output_tokens | integer/null | Provider output token count | provider/source did not record it |
| latency_seconds | float/null | Recorded request elapsed seconds | source did not record it |
| finish_reason | category/null | Provider completion stop reason | provider/source did not return it |
| is_truncated | boolean/null | True only when the recorded finish reason indicates length | unknown when source finish reason absent |
| metric_name | category | Native primary scoring rule; different tasks are not pooled | never missing |
| metric_value | float/null | Native 0/1 observation under the named score | environment exclusion or unresolved source result; never filled with zero |
| environment_excluded | boolean | Common code benchmark environment exclusion | false for experiments without this exclusion |
| document_count | integer/null | Number of supplied reference documents | not applicable outside document QA |
| evidence_position | integer/null | One-based relevant-document position | not applicable outside document QA |
| independent_sample | integer/null | Index of an independent generation; not a repair turn | not applicable outside code-generation repetitions |
| revision_round | integer/null | Number of code revisions after the shared seed; seed is 0 | not applicable outside code repair |
| feedback_type | category/null | seed/resample/self_review/pass_fail/counterexample | not applicable outside code repair |
| parent_record_key | string/null | Pseudonym of the preceding physical repair response | no previous response or not applicable |

## 分实验清洗表

原题、完整回答、原始 ID 和代码只在完整项目的各实验表中保留。匿名提交版仅包含统一数值特征及原有匿名视图快照。

### reasoning — 74,400 条

`data/processed/reasoning/responses_clean.csv.gz`

| 字段 | 来源 / 说明 |
|---|---|
| record_id | Anonymous unique identity within this released project |
| experiment_id | Experiment direction; identifies the unit and protocol |
| model_id | Canonical model family identifier |
| model_api_name | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| benchmark | Benchmark/task family; not a score scale |
| question_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| question_sha256 | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| prompt_id | Named prompt strategy |
| prompt_text | Recorded task-adapted prompt text. |
| question_text | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| options_json | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| gold_answer | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| response_text | Saved model response; preserved text, not re-generated. |
| reasoning_text | Provider field, nullable; absence does not prove absence of reasoning. |
| extracted_answer | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| score_current | Original source grading snapshot; not a harmonized semantic judge. |
| grading_status | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| score_revision_group | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| output_tokens | Provider output token count |
| input_tokens | Provider input token count |
| reasoning_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| answer_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| response_status | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| finish_reason | Provider completion stop reason |
| is_truncated | True only when the recorded finish reason indicates length |
| source_needs_review | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| included_in_review | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| review_trigger_reason | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| latency_seconds | Recorded request elapsed seconds |
| returned_model_name | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| source_file | Canonical raw-file path. |
| source_record_hash | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
### document_qa — 74,800 条

`data/processed/document_qa/responses_clean.csv.gz`

| 字段 | 来源 / 说明 |
|---|---|
| record_id | Anonymous unique identity within this released project |
| experiment_id | Experiment direction; identifies the unit and protocol |
| source_run_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| question_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| scenario_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| model_id | Canonical model family identifier |
| task_type | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| prompt_id | Named prompt strategy |
| strategy_scope | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| document_count | Number of supplied reference documents |
| gold_position | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| position_label | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| gold_document_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| question_text | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| gold_answers_json | Reference aliases serialized as JSON. |
| prompt_sha256 | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| timestamp | Recorded response timestamp normalized to UTC |
| status | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| http_status | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| attempt_count | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| latency_seconds | Recorded request elapsed seconds |
| request_model | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| request_temperature | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| request_max_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| response_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| response_model | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| response_created_epoch | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| system_fingerprint | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| choice_count | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| finish_reason | Provider completion stop reason |
| response_text | Saved model response; preserved text, not re-generated. |
| reasoning_text | Provider field, nullable; absence does not prove absence of reasoning. |
| extracted_answer | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| paper_firstline | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| strict_final_em | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| final_contains | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| full_response_contains | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| repaired_empty_marker | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| is_truncated | True only when the recorded finish reason indicates length |
| needs_review | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| primary_metric_name | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| input_tokens | Provider input token count |
| output_tokens | Provider output token count |
| total_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| output_whitespace_words | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| output_characters | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
### code_generation — 90,210 条

`data/processed/code_generation/responses.csv.gz`

| 字段 | 来源 / 说明 |
|---|---|
| record_id | Anonymous unique identity within this released project |
| experiment_id | Experiment direction; identifies the unit and protocol |
| model_id | Canonical model family identifier |
| task_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| prompt_id | Named prompt strategy |
| sample_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| sampling_mode | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| prompt_text | Recorded task-adapted prompt text. |
| response_text | Saved model response; preserved text, not re-generated. |
| generated_code | Code extracted in the source experiment; no execution during cleaning. |
| passed | Saved test result; null for environment exclusion. |
| environment_excluded | Common code benchmark environment exclusion |
| error_type | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| input_tokens | Provider input token count |
| output_tokens | Provider output token count |
| total_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| latency_seconds | Recorded request elapsed seconds |
| finish_reason | Provider completion stop reason |
| scorer | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| function_name | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| source_file | Canonical raw-file path. |
### document_positions — 3,600 条

`data/processed/document_positions/responses.csv.gz`

| 字段 | 来源 / 说明 |
|---|---|
| record_id | Anonymous unique identity within this released project |
| experiment_id | Experiment direction; identifies the unit and protocol |
| model_id | Canonical model family identifier |
| question_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| scenario_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| prompt_id | Named prompt strategy |
| document_count | Number of supplied reference documents |
| gold_position | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| question_text | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| gold_answers_json | Reference aliases serialized as JSON. |
| response_text | Saved model response; preserved text, not re-generated. |
| timestamp | Recorded response timestamp normalized to UTC |
| input_tokens | Provider input token count |
| output_tokens | Provider output token count |
| total_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| latency_seconds | Recorded request elapsed seconds |
| finish_reason | Provider completion stop reason |
| final_contains | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| strict_final_em | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| paper_firstline | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| full_response_contains | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| is_truncated | True only when the recorded finish reason indicates length |
### code_repair — 5,576 条

`data/processed/code_repair/responses.csv.gz`

| 字段 | 来源 / 说明 |
|---|---|
| record_id | Anonymous unique identity within this released project |
| experiment_id | Experiment direction; identifies the unit and protocol |
| model_id | Canonical model family identifier |
| task_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| arm | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| revision_round | Number of code revisions after the shared seed; seed is 0 |
| parent_record_id | Previous physical response, not an independently sampled answer. |
| shared_seed_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| feedback_source_id | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| feedback_text | Actual external feedback passed to that revision. |
| response_text | Saved model response; preserved text, not re-generated. |
| generated_code | Code extracted in the source experiment; no execution during cleaning. |
| timestamp | Recorded response timestamp normalized to UTC |
| input_tokens | Provider input token count |
| output_tokens | Provider output token count |
| total_tokens | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| latency_seconds | Recorded request elapsed seconds |
| finish_reason | Provider completion stop reason |
| diagnostic_passed | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| heldout_passed | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| full_pass | Both diagnostic/base and held-out mini tests passed. |
| diagnostic_error_json | Saved first diagnostic failure; null on no failure. |
| evaluation_seconds | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |
| sandboxed | Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema. |

## 原始字段与评分说明

历史问答字段的逐字段来源、缺失数量和处理依据见 `processed/data_dictionary.tsv`。新增实验的原始字段见 `raw/code_generation/data_dictionary.tsv` 与 `experiments/code_repair/README.md`。全量缺失统计见 `quality/missingness.csv`，逐表 SHA-256 见 `inventory/processed_tables.json`。
