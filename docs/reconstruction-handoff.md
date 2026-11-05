# 知微答辩展示版交接

首页恢复深海蓝知微五气泡。五颗气泡进入研究问题、采集设计、数据处理、核心发现、总结与反思。正文只保留五章顶导航，页底翻页与左右键跳章均已删除。品牌返回五气泡首页。

## 展示结构

研究问题由总问题分到数学、文档、代码三任务，三组案例同时展示。采集页直接展示四维和31种真实策略。清洗页为完整静态Figure：A两来源字段，B四组映射规则，C两条统一保存记录，D统一21列CSV格式与保存原则。所有部分同时可见，没有按钮、选择框或折叠。

核心发现是一个连续长页面，先展示四总体、三专项的静态结构，然后向下阅读七组证据：Token边际收益、模型规模、简洁表达、限长反弹、数学语言、文档位置、代码反馈。每组为结论标题、大图和旁侧解读，下接全部辅助对照。37张SVG全部保留。

代码反馈补充批次完整发布后，直接接在该专项内继续向下阅读。六张新批次图分别呈现强测试初稿／终稿、公开五版轨迹、修复／回退、Token代价、初始错误支持数及离线强测五版轨迹；历史Mini→完整强测另有一图。补充结果与原37张图分别保存，不替换旧实验、不把新旧样本合算。未完成或合成快照不进入主展示。

正文不再放置“查看对应专项”、交叉推荐、每图SVG/CSV按钮、“设为主图”、格式切换、独立图册入口和探索按钮。图形来源与条件在图稿内保留，研究细节随正文阅读，不依赖多层展开。

## 文件与接口

| 内容 | 文件 |
|---|---|
| 首页五气泡 | `app/src/research-home.js`、`app/research-home.css` |
| 主壳、五章路由、发现长页 | `app/index.html`、`app/src/research.js`、`app/research.css` |
| 三任务、31策略、清洗、总结 | `app/src/research-content.js`、`app/research-content.css` |
| 37张科学SVG与目录 | `app/assets/research/`、`app/data/research-charts.json` |
| 图稿生成器 | `scripts/figures/build_research_atlas.py` |
| 保留的完整探索 | `app/src/research-explorer.js`、`app/research-explorer.css` |
| 专项匿名记录模块与快照 | `app/src/research-special-records.js`、`app/data/special-records.json.gz` |
| 补充批次静态章节 | `app/src/research-feedback-extension.js`、`app/research-feedback-extension.css` |
| 已发布补充快照与图 | `app/data/code-feedback-extension.json`、`app/assets/research-extension/`，发布后才存在 |
| 补充图包 | `app/assets/research-feedback-svg.zip`，与原图包分开 |
| 新批与旧批重绘器 | `experiments/code_repair_v2/src/analyze.py`、`experiments/code_repair_v2/analysis/redraw_legacy.py` |

`renderHome()`返回首页HTML；`mountHome(container,{onNavigate})`返回清理函数。内容模块保留 `renderQuestion()`、`renderCollection()`、`renderCleaning()`、`renderConclusion()` 与 `bindContent(container,callbacks)`。离开模块前释放其事件。

图稿资源页通过 `?chapter=atlas` 直接访问，保留逐图SVG／CSV、完整图包与原有13类通用图、4个代码生成视图。该页面服务研究与素材准备，主答辩页面不摆额外按钮。专项匿名记录模块继续作为数据能力保留，未删除快照。

补充模块接口为 `renderFeedbackExtension(evidence, figures, legacyEvidence?, {prefix?})`，返回静态HTML。`figures`接新批目录的数组；旧批为 `{checks, summary, figures?}`。默认图路径为 `assets/research-extension/`，旧图在其 `legacy/` 子目录。仅真实且完整的快照可展示，代码与实际反馈按文本转义。正文没有按钮、折叠或悬停依赖；窄屏图表区域可水平滚动并由键盘聚焦。

## 科研口径

- 248,586条是物理响应；9,176条专项记录已在其中。
- 四维是策略标签，31种是实际清单，不是完整笛卡尔组合。
- CSV（gzip压缩）为实际统一保存格式；清洗页同时展示两条21列CSV记录的关键字段与统一类型。完整行仍保留在数据对象及CSV helper中。
- 源字段片段由真实清洗代码重建所需字段视图，数值来自同条已保存记录；不冒充原API响应全文。
- 不混合任务评分。模型未知参数不填0，拟合线不改为实测线。
- 五次独立生成、反馈修复轮次、HTTP请求重试分别解释。共同修复初稿只计一次。
- 补充实验按完整题目配对，重复初稿不增加独立题数。六条策略共享初稿，公开测试负责反馈，强保留结果不交给模型。
- 公开五版曲线与离线强测五版曲线分开呈现。强曲线仅使用所有模型、重复、策略、版本都完成强测的共同题目；子队列必须写明分母。
- 净提升按题目分簇估计95%配对区间；区间包含0，不宣称稳定提升。初错修复和初对回退使用各自分母，按模型报告。
- 历史Mini强复测只重执行已保存代码，不重新生成。公开重执行变化与旧超时未复现单列，不把这些变化全归因于更多测试。

页面切换和动效可以继续美化；不得增加与答辩无关的导航或把图形重新藏进按钮。保留坐标、单位、范围、来源、点线形状和必要标注。新动效必须遵守减少动态偏好，触控与键盘仍可完整操作。

## 运行与核验

```bash
python3 app/launch.py --port 8770
python3 scripts/system/check_reconstruction.py
BASE_URL=http://127.0.0.1:8770/ node tests/browser/defense.mjs
```

使用 `python3 scripts/system/build_web_app.py` 重新构建。交接包用 `scripts/system/package_reconstruction.py --output /绝对路径/交接目录` 生成，含静态网站、可编辑ES模块、SVG生成器、冻结统计与独立启动器。

补充批次只从已发布构建中打包。默认在 `reports/code_repair_extension/<batch_id>/` 查找聚合报告，可用 `--extension-report` 指定同批目录。原图包输出为 `知微科研SVG图包.zip`；补充包输出为 `知微代码反馈SVG图包.zip`，两者保持独立。包内 `代码反馈源图/`采用文件白名单，仅保存匿名 `app-evidence.json`、公开CSV、复核摘要及两个重绘器；不复制运行目录、原始请求、逐程序评测、oracle或凭证。

在交付包内执行 `python3 重建代码反馈图.py`，可由冻结聚合结果更新六张新图、一张旧图及补充ZIP。该命令只使用Python标准库；调整配色和标注后可直接重绘。若修改样本、指标或统计，需回原仓库重新核验并发布完整快照。源码中的两个独立命令见[README](../README.md)，完整口径见[分析说明](../experiments/code_repair_v2/ANALYSIS.md)。
