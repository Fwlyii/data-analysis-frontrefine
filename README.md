# LENS · 模型行为研究

研究输出表达、资料位置与执行反馈如何影响大模型的任务表现。实验覆盖推理/选择题、文档问答与Python代码，共248,586条物理响应。项目采用课设题目二的**可视交互系统**形式。

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


## 当前 GitHub Pages 预览

本分支整合 `Fwlyii/dataAnalysis-vision` 的 `Master`（`35f7318`）与 LENS 前三轮视觉优化和纯代码电影开场。入口仍是 `app/index.html` 与 `app/explore.html`；保留最新英文展示内容、完整课程图表库、冻结研究数据及其交互。

- 构建：`python3 scripts/system/build_web_app.py`
- 本地预览：`python3 app/launch.py`
- 资源和数据绑定检查：`python3 scripts/system/check_web_snapshot.py --skip-build`
- 全站视觉证据门禁：`python3 scripts/system/check_visual_coverage.py`
- 流程与迁移报告：`docs/visual-refinement-workflow.md`、`optimization/master-migration-v4/REPORT.md`
- 公网：<https://fwlyii.github.io/data-analysis-frontrefine/>；每次推送 `main` 后由 Actions 构建发布。`?intro=1` 重播开场，`?intro=0` 直接进入系统，遵循减少动态效果偏好。

`app/runtime` 和 `app/dist` 可重复构建，无需提交。原始研究档案继续通过 `.lfsconfig` 引用源仓库的 Git LFS；页面所需的三个冻结 `.gz` 快照已按上游哈希校验，直接包含在 Git 中，因此 Pages 构建不依赖完整科研档案下载。需要完整档案时安装 Git LFS 后执行 `git lfs pull --include="data/**,reports/**,presentation/**,submission/**" --exclude=""`。

当前渲染修复与统一视觉版本见 `optimization/render-unification-v5/REPORT.md`：与 Master 实际内容/图形逐项比较，采用统一深蓝框架、青色与浅色数据图纸；开场与页面共享颜色。
