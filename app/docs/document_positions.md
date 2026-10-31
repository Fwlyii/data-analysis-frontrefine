# 文档位置实验

问题：相关证据的位置如何影响答案命中，模型优势是否随位置改变？

设计：同一批200题、20篇同样资料、NoCoT，两个Qwen模型，位置1、3、5、8、10、13、15、18、20。只移动唯一相关文档，其他内容和生成设置固定。共3,600条响应。

原始：data/raw/document_positions/no_cot_20_documents。清洗：data/processed/document_positions。分析：experiments/document_qa/src/analyze_document_positions.py。图稿及配对区间：reports/document_positions。

主指标为最终答案包含，其他三种匹配作敏感性口径。Qwen3相对Qwen2.5的首位优势16.5 pp、末位2.5 pp，首尾模型增益差14.0 pp，区间[5.5,23.0]。Qwen2.5呈浅U形，Qwen3主要表现为首位优势；曲线只连接真实测量点。

采集入口scripts/acquisition/collect_document_positions.py默认打印计划，主动执行写入独立批次。原文档提示实验与本协议分别保存；跨模型采集日期如实记录。
