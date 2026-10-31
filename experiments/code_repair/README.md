# 反馈驱动的Python代码修复

HumanEval+ Mini 164题，两个Qwen模型，每个模型×题目共享一份初稿，四组各修改四轮。处理为独立重采样、自行检查、仅通过/失败、具体失败反例。后三组保留历史，只有基础诊断反馈可进入提示，保留集结果不反馈。

5,576条物理响应；共享初稿在逻辑组视图中复用，不增加调用数。当前版本通过率、配对区间和错误转移在reports/code_repair/full。规范物理表在data/processed/code_repair/responses.csv.gz，逻辑特征和事件在full/。

src提供参考预检、采集、沙箱执行和离线分析。统一采集入口scripts/acquisition/collect_code_repair.py默认打印计划，主动执行会在独立批次进行参考预检与模型采集。实际执行依赖macOS沙箱；离线分析只读取保存结果，不执行模型代码。
