# 知微重构版交接

## 当前内容

五个一级模块为研究问题、采集设计、数据处理、核心发现、总结与反思。研究问题采用“提示词总问题 → 数学、文档、代码三任务 → 专项变量”；核心发现采用“四总体＋三专项”：

- 总体：Token—成功率log关系、模型规模、简洁表达、限长反弹。
- 专项：数学语言模板、文档证据位置、代码执行反馈。

系统包含37张可编辑SVG、13类通用交互图、4个代码独立生成视图。专项匿名快照有9,176条记录，即3,600条位置记录和5,576条反馈修复物理响应；它们已包含在总计248,586条中。

## 启动、生成与检查

在仓库根目录运行：

```bash
python3 app/launch.py --port 8770

# 需要单独更新图形或静态产物时
python3 scripts/figures/build_research_atlas.py
python3 scripts/system/build_web_app.py
```

启动后在另一个终端执行新界面回归：

```bash
npm ci --prefix tests
npm run browser:install --prefix tests
BASE_URL=http://127.0.0.1:8770/ node tests/browser/reconstruction.mjs
```

可用 `CHROMIUM_PATH` 指定浏览器。回归结果位于 `artifacts/qa/reconstruction/report.json`。旧 `tests/run.py` 和93状态清单属于旧门户基线，不作为新主界面的状态数量承诺。

## 修改入口与接口

| 模块 | 文件与作用域 |
|---|---|
| 主壳、章节路由、主题图册 | `app/src/research.js`、`app/research.css` |
| 中文章节、四维策略、字段映射 | `app/src/research-content.js`、`app/research-content.css`，`.rc-*` |
| 通用图表与代码生成探索 | `app/src/research-explorer.js`、`app/research-explorer.css`，`.r-explorer-*` |
| 专项匿名记录 | `app/src/research-special-records.js`，`.rs-*` |
| 图形目录与数值 | `app/data/research-charts.json` |
| SVG与成套下载 | `app/assets/research/*.svg`、`app/assets/research-svg.zip` |

内容模块导出 `researchContent`、`renderQuestion()`、`renderCollection()`、`renderCleaning()`、`renderConclusion()`、`bindContent()`和`cleaningSampleCSV()`。`bindContent(container, {onNavigate, onTaskChange, onFieldChange})`返回清理函数，替换章节前调用。

图表目录的主题ID为 `budget`、`scale`、`concise`、`limits`、`language`、`position`、`feedback`。每图包含标题、条件、来源、SVG路径和数值行；主图、辅助图与导出均以此目录为依据。

## 字段标红与统一保存

来源字段视图来自实际读取代码，数值来自已保存匿名记录：

| 统一字段 | 推理源表格 | 文档问答API层级 |
|---|---|---|
| `output_tokens` | `输出词元数` | `response.usage.completion_tokens` |
| `input_tokens` | `输入词元数` | `response.usage.prompt_tokens` |
| `finish_reason` | `结束原因` | `response.choices[0].finish_reason` |
| `model_id` | `模型标识` | `model`，再经规范模型字典映射 |

红色表示同义异名字段；点选后，来源字段、映射规则和统一保存项同步突出。示例仅展示映射所需字段及匿名数值，省略原始问答全文。读取规则见 `scripts/cleaning/clean_baseline_data.py`，统一结构见 `scripts/cleaning/build_unified_features.py`。

实际保存为gzip压缩的CSV；JSON是同一记录的阅读视图。空单元格为null，布尔为true/false，缺失Token不补0。不同任务评分由 `metric_name`区分，不计算跨任务总准确率。31种策略是实际清单，四维为可重叠标签，不代表完整笛卡尔积。

## 后续页面美化的边界

可以调整页面布局、导航表现、整体切换、进出场和图形呈现节奏。以下内容须随研究证据保留：

- 科学数字、坐标范围、单位、编码含义、图例、来源与适用条件。
- 观测点与拟合线的区别；未知模型规模不补0、不按名称猜测。
- 图中统计、筛选、记录数量与CSV导出的同一数据集合。
- URL恢复、有效筛选、图表下钻、分页、真实CSV与SVG导出。
- 键盘入口、焦点恢复、减少动态效果、播放暂停与离章清理。
- HTTP请求重试与代码修复的区别；独立生成与多轮反馈的区别。
- 共享修复初稿只计一次；465条代码环境排除保留为空评分。

替换动效或页面结构后，先跑新回归，再检查1440级电脑窗口和窄屏。报告、讲稿、截图与PPT复用系统中的中文主旨、图形和范围说明。
