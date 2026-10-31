# 文档问答与证据位置

研究模型、提示、文档数和相关证据位置与答案命中的关系。源响应和评分在data/raw/document_qa，位置实验在data/raw/document_positions，规范表在data/processed对应目录。

采集入口：scripts/acquisition/collect_document_qa.py、collect_document_positions.py。基础问答复用保存的完整场景，位置实验只移动相关文档。原始问答采集实现保存在method_source/collector.py供方法溯源，其凭据读取已改为环境变量；运行入口采用统一配置和冻结场景。

离线分析：src/analyze_document_positions.py。四种源评分独立保留，模型比较按同题配对。20篇文档的证据位置为1、3、5、8、10、13、15、18、20。
