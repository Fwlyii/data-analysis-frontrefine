# 知微答辩展示版交接

首页恢复深海蓝知微五气泡。五颗气泡进入研究问题、采集设计、数据处理、核心发现、总结与反思。正文只保留五章顶导航和上一段／下一段；可用左右方向键依序讲述。品牌返回五气泡首页。

## 展示结构

研究问题由总问题分到数学、文档、代码三任务，三组案例同时展示。采集页直接展示四维和31种真实策略。清洗页沿红色同义异名字段、映射规则、保存CSV关键字段展开；保留四字段切换与一个记录来源选择。

发现部分先展示四总体、三专项的静态结构，然后顺序进入七组证据：Token边际收益、模型规模、简洁表达、限长反弹、数学语言、文档位置、代码反馈。每组为结论标题、大图和旁侧解读，下接全部辅助对照。37张SVG全部保留。

正文不再放置“查看对应专项”、交叉推荐、每图SVG/CSV按钮、“设为主图”、格式切换、独立图册入口和探索按钮。图形来源与条件在图稿内保留，研究细节随正文阅读，不依赖多层展开。

## 文件与接口

| 内容 | 文件 |
|---|---|
| 首页五气泡 | `app/src/research-home.js`、`app/research-home.css` |
| 主壳、五章路由、12段顺序 | `app/index.html`、`app/src/research.js`、`app/research.css` |
| 三任务、31策略、清洗、总结 | `app/src/research-content.js`、`app/research-content.css` |
| 37张科学SVG与目录 | `app/assets/research/`、`app/data/research-charts.json` |
| 图稿生成器 | `scripts/figures/build_research_atlas.py` |
| 保留的完整探索 | `app/src/research-explorer.js`、`app/research-explorer.css` |
| 专项匿名记录模块与快照 | `app/src/research-special-records.js`、`app/data/special-records.json.gz` |

`renderHome()`返回首页HTML；`mountHome(container,{onNavigate})`返回清理函数。内容模块保留 `renderQuestion()`、`renderCollection()`、`renderCleaning(field,source)`、`renderConclusion()` 与 `bindContent(container,callbacks)`。离开模块前释放其事件。

图稿资源页通过 `?chapter=atlas` 直接访问，保留逐图SVG／CSV、完整图包与原有13类通用图、4个代码生成视图。该页面服务研究与素材准备，主答辩页面不摆额外按钮。专项匿名记录模块继续作为数据能力保留，未删除快照。

## 科研口径

- 248,586条是物理响应；9,176条专项记录已在其中。
- 四维是策略标签，31种是实际清单，不是完整笛卡尔组合。
- CSV（gzip压缩）为实际统一保存格式；清洗页展示同一21列CSV中的9个关键字段。完整行仍保留在数据对象及CSV helper中。
- 源字段片段由真实清洗代码重建所需字段视图，数值来自同条已保存记录；不冒充原API响应全文。
- 不混合任务评分。模型未知参数不填0，拟合线不改为实测线。
- 五次独立生成、反馈修复轮次、HTTP请求重试分别解释。共同修复初稿只计一次。

页面切换和动效可以继续美化；不得增加与答辩无关的导航或把图形重新藏进按钮。保留坐标、单位、范围、来源、点线形状和必要标注。新动效必须遵守减少动态偏好，触控与键盘仍可完整操作。

## 运行与核验

```bash
python3 app/launch.py --port 8770
python3 scripts/system/check_reconstruction.py
BASE_URL=http://127.0.0.1:8770/ node tests/browser/defense.mjs
```

使用 `python3 scripts/system/build_web_app.py` 重新构建。交接包用 `scripts/system/package_reconstruction.py --output /绝对路径/交接目录` 生成，含静态网站、可编辑ES模块、SVG生成器、冻结统计与独立启动器。
