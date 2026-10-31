# 清洗与结构化数据

| 主表 | 记录数 | 说明 |
|---|---:|---|
| reasoning/responses_clean.csv.gz | 74,400 | 源评分、全文、Token、截断与复核标记分列 |
| document_qa/responses_clean.csv.gz | 74,800 | 四种评分、场景与耗时分别保留 |
| code_generation/responses.csv.gz | 90,210 | 独立样本、完整回答/代码、源测试结果；465条环境排除的passed为空 |
| document_positions/responses.csv.gz | 3,600 | 两模型文档位置，保留四种规则评分与真实响应 |
| code_repair/responses.csv.gz | 5,576 | 物理响应、父响应、真实反馈、基础/新增测试结果 |
| all_records.csv.gz | 248,586 | 匿名数值特征，可跨方向筛选，不能混合评分取总准确率 |
| record_lineage.csv.gz | 248,586 | 完整项目的源键映射，不进入匿名提交版 |

CSV空单元格表示null，布尔为true/false，JSON单元格为规范JSON，时间统一UTC。没有把缺失Token/耗时补0，没有将环境排除当作模型失败，也不重复加总共享初稿或pilot。

历史问答逐字段来源见 `data_dictionary.tsv`；统一与新增字段说明见 `../data_dictionary.md`，质量和缺失见 `../quality/`。
