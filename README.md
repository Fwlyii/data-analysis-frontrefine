# LENS · 知微

中文模型行为研究与可视化系统。首页保留知微五气泡，进入研究问题、采集设计、数据处理、核心发现、总结与反思五章。五章各自直接阅读，核心发现为包含七主题、37张图的完整长页面；正文不设置前后翻页。

核心发现采用**四个总体主题＋三个任务专项**：Token与成功率的log关系、模型规模、简洁表达、限长反弹，以及数学语言模板、文档证据位置、代码执行反馈。

当前保留 **37张可编辑SVG、13类通用交互图和4个代码独立生成视图**。主展示直接呈现主图、辅助对照与结论，移除跨章推荐和逐图工具按钮。清洗页为无控件的完整静态Figure，两种来源、四组字段映射及两条统一保存记录同时展示。完整交互、图稿导出留在独立的 `?chapter=atlas` 图稿页，答辩主线不摆放额外入口。位置与反馈修复的9,176条匿名记录快照继续保留，属于总计248,586条响应的子集。

[研究概述](docs/project-summary.md) · [内容与美化交接](docs/reconstruction-handoff.md) · [目录说明](docs/repository-structure.md) · [录制指南](docs/submission.md)

## 启动

在仓库根目录运行：

```bash
python3 app/launch.py --port 8770
```

浏览器打开 `http://127.0.0.1:8770`。运行与构建只用Python标准库，使用已保存的匿名网页快照，不需要npm、模型密钥或常驻后端。请通过本地HTTP服务打开，避免直接双击HTML。

## 图表与静态构建

```bash
# 从冻结统计生成37张SVG和图表目录
python3 scripts/figures/build_research_atlas.py

# 打包主系统、探索模块、快照及SVG/CSV图包
python3 scripts/system/build_web_app.py

# 检查图包、真实记录与1100项科研文件保护
python3 scripts/system/check_reconstruction.py
```

- `app/assets/research/*.svg`：可编辑科学图。
- `app/data/research-charts.json`：图表主题、条件、来源与数值。
- `app/assets/research-svg.zip`：完整SVG图包及各图CSV。
- `app/dist/`：生成后的静态网站，可由HTTP静态服务提供。

## 浏览器回归

先启动上面的本地服务，在另一个终端运行：

```bash
npm ci --prefix tests
npm run browser:install --prefix tests
BASE_URL=http://127.0.0.1:8770/ node tests/browser/defense.mjs
```

已有Chrome等浏览器时，可用 `CHROMIUM_PATH` 指定其可执行文件。当前回归检查五气泡首页、五章答辩路径、无多余按钮、字段映射、七主题37图、响应式与可访问性；结果写入 `artifacts/qa/defense/report.json`。

`tests/run.py`和 `tests/browser/reconstruction.mjs` 保留此前界面的基线，不代表当前精简后的控件数量，不能替代上述回归。

## 源码入口

| 内容 | 入口 |
|---|---|
| 主页面、路由、主题图册 | `app/index.html`、`app/src/research.js`、`app/research.css` |
| 五气泡首页 | `app/src/research-home.js`、`app/research-home.css` |
| 中文章节、策略与清洗演示 | `app/src/research-content.js`、`app/research-content.css` |
| 通用图表、代码生成探索 | `app/src/research-explorer.js`、`app/research-explorer.css` |
| 位置与反馈专项记录 | `app/src/research-special-records.js`、`app/data/special-records.json.gz` |
| SVG生成与目录 | `scripts/figures/build_research_atlas.py`、`app/data/research-charts.json` |
| 冻结数据、清洗、统计 | `data/`、`scripts/cleaning/`、`scripts/analysis/`、`reports/` |
| 参考报告与答辩材料 | `report/`、`presentation/` |

`app/dist/`、`app/runtime/`和`artifacts/`为生成或临时目录。后续页面切换、动效与布局的修改边界见[交接说明](docs/reconstruction-handoff.md)。

向队友提供可运行网站及图稿源文件，可运行 `python3 scripts/system/package_reconstruction.py --output /绝对路径/交接目录`。它保留网页模块源码、离线数据、SVG生成器与冻结统计，并附独立启动器；目标目录已存在时会停止，避免覆盖队友修改。

## 数据复算与课程演示

完整分析表通过Git LFS管理。要重算统一匿名表的条件汇总，先取回该表：

```bash
git lfs install --local
git lfs pull --include='data/processed/all_records.csv.gz' --exclude=''
python3 scripts/reproduce_anonymous.py
```

完整离线流程见[复算说明](docs/reproducibility.md)。网页浏览不要求下载完整问答全文。专项网页快照可用 `python3 scripts/system/export_special_records.py` 从已取回的统一表更新。

报告与PPT作为参考，最终演示视频由人工录制并提交；不在仓库保存成片。系统、演讲稿、报告和PPT应使用同一套图形、数据范围与结论。
