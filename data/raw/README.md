# 完整原始数据

本完整项目包含源响应、场景、题库、保存评分和参考缓存。源文件内容未改写，405个不可变源制品与原文件SHA-256相同；权威外层文件清单见 `../inventory/raw_files.json`。

| 目录 | 内容 |
|---|---|
| reasoning | 原始四模型三benchmark提示实验ZIP，内部格式完整保留 |
| document_qa | 原始响应、完整场景、请求尝试、题目、提示及源评分 |
| code_generation | 194题、31提示、三模型原始响应及source_scores/中的已保存测试结果 |
| document_positions | 九位置补采、场景、运行信息与探测结果 |
| code_repair | HumanEval+ Mini、完整响应、执行结果、事件、参考预检和缓存 |

上游manifest/CHECKSUMS的内部相对路径按原样保留；本仓库外层命名应查当前inventory。整理只复制与改外层文件名，不覆盖源内容。源ZIP内部已有的名称也不重写。

新采集默认只打印计划；主动启用后写入各实验 `collections/<新批次>/`，不会覆盖本快照。密钥不随数据或代码分发。
