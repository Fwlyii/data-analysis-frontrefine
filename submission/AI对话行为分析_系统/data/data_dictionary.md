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


## 质量与来源

逐实验缺失率见processed/metadata/missingness.csv，质量与评分规则见processed/metadata/quality_report.json。原始文件校验见raw/source_checksums.json。提交数据不含全文或源ID映射。
