# 课程提交

运行 `python3 scripts/delivery/build_submission.py` 生成 `submission/AI对话行为分析_系统/`。

```text
README.md
app/                        可运行系统、pipeline脚本与统计图稿
data/
  raw/                      来源与校验
  processed/                匿名特征及质量元数据
  data_dictionary.md
report/
  案例报告.pdf
presentation/
  答辩PPT.pdf
  汇报演示_1080P.mp4
```

结构对应课程PDF系统组示例。外层名称可按学校要求填写学号姓名。无子Git仓库、无嵌套的第二套项目；app/pipeline是从统一代码基底生成的脚本副本。

系统：`python3 app/launch.py --port 8766`。匿名统计：`python3 app/pipeline/scripts/reproduce_anonymous.py`。图稿重绘加`--figures`，需分析依赖和Times New Roman；文档重绘另需documents.txt。

两条低维、两条多维和一条异常的证据见PROJECT_SUMMARY.md与案例报告。完整原始响应保存在完整项目，匿名提交目录只带数据特征、代码、统计和图形。
