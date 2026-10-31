# LENS · 模型行为研究

研究输出表达、资料位置与执行反馈如何影响大模型的任务表现。实验覆盖推理/选择题、文档问答与Python代码，共248,586条物理响应。项目采用课设题目二的**可视交互系统**形式。

[线上预览](https://fwlyii.github.io/data-analysis-frontrefine/) · [电脑录制版布局与截图](optimization/content-layout-20261101/README.md) · [全站优化流程](docs/visual-refinement-workflow.md)

## 运行

```bash
python3 app/launch.py --port 8770
```

标准库即可启动，使用本地数据和SVG，不需要API Key、网络或npm。首页按研究问题、采集设计、数据清洗、数据全貌、五项发现组织。五项发现依次为简洁作答、中文数学、资料位置、反馈修复、限长反弹；“图表库”提供课程图形和联动探索。

前端源码与构建说明见[系统说明](app/README.md)。运行`python3 scripts/system/check_web_snapshot.py`可检查快照、本地资源及三类任务的数据接入。

## 内容

```text
app/                         可视化系统与匿名视图快照
configs/                     实验协议与模型配置
scripts/
  acquisition/               数据采集
  cleaning/                  数据清洗与质量审计
  analysis/                  统计与配对分析
  figures/                   科学图稿
  system/                    网页数据导出与构建
  delivery/                  报告、答辩与提交目录
experiments/                 专用采集、评分和分析实现
requirements/                分阶段依赖
data/
  raw/                       完整原始数据，内容冻结
  processed/                 清洗表与统一匿名特征
  quality/                   质量与缺失报告
  inventory/                 原始校验与现行文件清单
  data_dictionary.md         字段、来源、单位及缺失原因
reports/                     统计CSV、区间、发现和图稿源数据
report/                      案例报告
presentation/                答辩PDF、汇报视频与制作材料
docs/                       课程原文、研究方法与复算说明
PROJECT_SUMMARY.md            实验、结论与六类材料索引
submission/                  独立生成的课程匿名提交目录
```

实验规模、主要结论、数据与脚本入口见 [项目概述](PROJECT_SUMMARY.md)。

## 数据管道

```bash
# 从匿名数值特征复算所有实验的条件统计
python3 scripts/reproduce_anonymous.py

# 查看全离线流程；不执行采集
python3 scripts/pipeline.py all --plan

# 重新清洗完整原始数据
python3 scripts/pipeline.py clean
```

分析和绘图依赖`requirements/analysis.txt`，文档生成另需`requirements/documents.txt`。图形指定Times New Roman。采集脚本单独放在`scripts/acquisition/`，默认不请求模型，只有`--execute`才采集。密钥从环境变量读取，空模板见`.env.example`。

## GitHub与课程提交

本目录是同一GitHub仓库新分支的完整项目内容，包含原始数据、清洗表和全部代码。大压缩数据、ZIP、缓存及视频使用`.gitattributes`中的Git LFS规则；上传前应启用Git LFS。

```bash
python3 scripts/delivery/build_submission.py
```

生成`submission/AI对话行为分析_系统/`：顶层为README、app、data、report、presentation，与课设系统组示例一致。提交版只含匿名特征、统计、图稿和代码；完整原始数据保留在本项目。提交版由同一套脚本生成，作为独立提交目录一并收录。

最新电脑录制版的详细布局重设计、逐页截图和测量见 `optimization/content-layout-20261101/REPORT.md`、`optimization/content-layout-20261101/gallery.html`。 原图表、数据及科研绘制源码保持；首页采用五个真实生成的静态透明装饰资产，原生链接、文字和开场交接连续性保留。
