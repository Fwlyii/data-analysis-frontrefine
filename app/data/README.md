# 应用数据快照

代码生成已接入 `code-generation@9dfc592`：完整源快照仅本机 `data/raw/code_generation/`；匿名特征 `app/data/code-features.json.gz`，统计 `code-evidence.json`；主字典和缺失报告合计 185 字段。[方法](../../docs/code-generation.md)。

`summary.json` 包含 746 个实验条件汇总、按题配对比较、请求重试序列和数据来源哈希。`features.json.gz` 包含 149,200 条匿名数值/分类特征，仅供本地记录详情探索。

这里不包含原始问题、回答、推理文本、个人信息、原始响应 ID 或代码。匿名编号 Z/F 表示响应，Z/C 表示独立题目；同一道题在不同条件下保留同一个匿名题号。真实请求重试记录与模型修复代码的事件严格区分。

它们由仓库根目录的 `python3 scripts/system/export_baseline_features.py` 从本地清洗副本生成。运行该脚本不会调用 API。已附匿名特征快照，因此启动界面无需重新下载原始大文件或安装 Python 分析库。

数据特征可按课程规范随代码提交；来源授权与团队的知情同意仍需在最终提交前核实。原始文本保存在本地且被 Git 忽略。
