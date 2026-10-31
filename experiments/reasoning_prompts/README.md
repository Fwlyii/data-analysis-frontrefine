# 推理提示实验

GSM8K、MATH500、MMLU三个benchmark，每项200题，四个模型、31种提示，共74,400条回答。研究分步/简洁模板、输出语言与字母/词/Token/步骤限制。

原始源包：data/raw/reasoning/responses_source.zip。规范表：data/processed/reasoning。统计：reports/baseline、reports/prompt_variants、reports/story。

统一采集入口：scripts/acquisition/collect_reasoning.py，默认只显示计划。其协议reconstructed-reasoning-v1由保存题目和提示构造；源包未提供历史采集器，因此不标注为历史采集程序。src保留源评分、结果IO与阈值分析方法。源评分版本及缺失解释随数据保留，不覆盖为统一语义标签。
