# 脚本入口

- `acquisition/`：reasoning、document_qa、code_generation、document_positions、code_repair五个采集入口。默认不调用API。
- `cleaning/`：原始校验、基线解析、代码/位置/修复规范表、统一匿名特征、字段与缺失统计。
- `analysis/`：基线配对、提示变体、代码诊断与故事证据。专用位置/修复分析在experiments对应模块。
- `figures/`：出版SVG与五章主图。英文Times New Roman。
- `system/`：视图快照和标准库网页打包。
- `delivery/`：当前报告/答辩PDF、提交目录、归档与现行清单。build_baseline_*仅保留历史制作方法。
- `pipeline.py`：离线阶段入口，绝不调采集或代码执行。
- `reproduce_anonymous.py`：统一匿名表→全方向条件汇总。

输入、输出和完整命令见根目录PROJECT_SUMMARY.md与docs/reproducibility.md。
