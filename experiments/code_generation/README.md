# Python代码生成实验

CodePromptEval经题意和参考实现审查保留194题，三模型、31条适配提示，每条件五次独立生成，共90,210条。统一排除1道环境不稳定题，保留全部原始回答，89,745条进入性能统计。

数据：data/raw/code_generation，源评分在source_scores，规范表在data/processed/code_generation。指标：Pass@k、独立采样覆盖、Prompt差异、错误类别、输出开销。

src保留随数据交付的采集、功能评价、分析、汇总与绘图实现。统一采集入口：scripts/acquisition/collect_code_generation.py。日常离线分析读取保存的target-function-ast-v2结果，不执行模型代码；完整重测需要原CodePromptEval的34个项目环境。

固定来源提交：9dfc5923d3e0e099accca7a709c420c0d531a58b。五次生成不携带前次答案或测试反馈，与反馈代码修复实验分别解释。
