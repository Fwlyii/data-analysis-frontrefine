# LENS 图表动态升级

基线 `7de85e836e8bc0f7c28c79188b71f1818c0aa234`，独立分支 `codex/lens-chart-motion`。保留 main、A、B 分支；本次不合并、不推送、不发布。

## 审计与实现边界

已读取任务指定的 interaction、refinement、charts、app、model、story、story-charts、code-study、code-interactions、narrative、libraries、gateway，以及维护流程、保护门禁、路由清单和浏览器测试。

- `interaction.js` 继续独占页面级场景调度。新 `chart-motion.js` 只管理图内效果，并由原场景和原图表注册入口调用；没有新研究工作台或侧栏。
- `app.js` 的原 render/dispose、异步记录版本守卫、筛选和记录面板保留。新层不能改写数据筛选。评分分歧路径新增的记录入口直接复用原匿名集合和导出面板。
- `charts.js` 的轴、聚合、分位数、排序、几何与普通样式保留。仅在统一挂载处调整原生动画及强调选项，注册精确高亮，并在导出前结束动画。
- `story-charts.js`、`model.js`、开场四文件和科研数据/素材全部建立不可变SHA基线。新增代码对照标记使用原匿名样例的真实行差，文本必须完全相同。
- 原独立采样、Vega框选、错误率联动和修复播放不是本次新成果；本次增强其反馈、生命周期与原位进度轨迹。
- 图表库的增强脚本同步放在原app脚本之前，保证首次原生绘图也能使用统一参数；Presentation保持原defer顺序。

## 各图表

| 类型 | 新增呈现与操作 | 保留的科学语义 |
|---|---|---|
| Model bar | 原生分批生长、标签渐显、数据项聚焦与键盘定位 | 原顺序、0–100轴、原评分/分母、原记录 |
| Radar | 原生中心展开、模型聚焦、五个真实维度的原tooltip | 原五轴定义，前三轴跨任务/位置的范围 |
| Heatmap | 原格渐显、同一实际行/列的外部细边强调、键盘巡检 | 原8/31策略、单元格数值、原记录 |
| Bubble | 原生缩放进入、实际气泡边缘光环与参考线 | 原token/参数轴与面积编码；不漂移 |
| Radial | 原扇区错峰显现、原tooltip/记录、原环/展开的有限视图过渡 | 原32条件、半径刻度及原两种布局 |
| Position | 原曲线/点绘制、真实点垂直参照、原tooltip | 原三位置与资料数；不添加中间测量 |
| Boxplot | 从原路径实际中位数处展开箱/须，原Plotly悬停与局部强调 | 直接使用原Q1/median/Q3/whisker路径，不重算 |
| Parallel | 真实轨迹错峰渐显、原生聚焦、按原轴显示真实值 | 原核心8策略、多维筛选、各轴独立单位 |
| Distribution | 原饼/堆叠原生形成、同一互斥状态跨图对应高亮 | 截断优先的原三分类及原分母 |
| Behavior | 原选中类别保留，右侧按原集合平滑更新、原键盘筛选 | 原格式/约束/结束状态及记录 |
| Timeline | 按真实请求时间排序延迟渐显、事件参照与原详情 | 不增加请求事件、不称反馈修复 |
| Tree | 原树按深度延迟展开，沿用原分支强调/折叠/漫游 | 原真实节点/运行数及初始深度 |
| Flow | 原真实带状路径渐显/逐段揭示、原生邻接强调、精确路径记录 | 原四类评分分歧计数、原流宽与空状态 |

原生图表初绘约720ms，更新约320ms，错峰最多280ms；科学SVG路径约680ms进入，测量点反馈约180ms。原生SVG/数据标签最终保持原样；临时效果清理后不写入科研导出。径向切换使用浏览器有限视图过渡，缺少该API时立即使用原两种布局。

## 五章与三种播放

研究问题沿原方向图标的真实路径描绘并保留原详情；采集设计的五个实际计数有限递增、原流程箭头按序出现；数据处理的原步骤/字段说明继续联动，点击后连接处仅播放一次光点；数据全景保留原模型/任务/矩阵，图内点和曲线分型进入；核心发现保留结论先行，五项原图均接入局部呈现与实际点定位。

九位置在原滑块旁加入紧凑播放键，按 `[1,3,5,8,10,13,15,18,20]` 每秒推进，暂停后继续、终点重播、拖动暂停、隐藏/离章/离屏停止；原评分、当前测量点及原区间同步，新增CI提示不增加读数行高。

修复沿用原五版本控制器，支持暂停继续和重播，保留164题和共享初稿；进度轨迹与真实通过率同步。原公开样例只含一个真实前后修复对照，按真实行差强调，未虚构其他版本代码。

独立采样沿用原D3播放、整数滑块和Pass@k，加入五节点轨迹及当前采样点/读数反馈；第五次自动停止。使用193题和5次独立生成，始终与反馈修复分开。

## 生命周期、导出与保护

快速筛选会在新挂载前立即取消已移出DOM的短动画，专项测试同时断言 `detachedEffects === 0`。减少动态时直接呈现稳定结果；用户主动播放仍按有限离散步骤运行。偏好改变、隐藏、离屏和离开章节会停止播放/结束非必要效果。原生实例按原生命周期销毁，新增监听器逐项解绑，SVG临时样式恢复原值；外部光环、参考线和提示不进入SVG。

导出捕获阶段先完成新增效果、原生ZRender动画与原有页面转场，再暂停播放并调用原导出。CSV序列化未改。原31份导出golden与1100文件清单保持不变；源接入改动须由独立实际图形/像素/导出复核授权，不能只改哈希。

临时保护清单、真实截图与测试报告位于忽略目录 `artifacts/motion-audit/` 和 `artifacts/qa/`。最终测试记录见下方。

## 实际修改文件

- 图内增强：`app/src/chart-motion.js`、`app/chart-motion.css`。
- 原绘图/控件最小接入：`app/src/charts.js`、`app/src/app.js`、`app/src/story.js`、`app/src/code-interactions.js`、`app/src/interaction.js`。
- 真实入口及构建：`app/index.html`、`app/explore.html`、`scripts/system/build_web_app.py`。
- 门禁与认可维护：`app/visual-coverage.json`、`scripts/system/check_visual_coverage.py`、`scripts/system/record_chart_motion_review.py`、`tests/fixtures/chart-motion-ui-review.json`、`tests/fixtures/chart-motion-release.json`、`tests/fixtures/chart-motion-scientific-review.json`。
- 新增验收：`tests/browser/chart-motion-checks.mjs`、`tests/browser/chart-motion-science.mjs`、`tests/run.py`、`tests/browser/intro-checks.mjs`。
- 说明：本文件与 `docs/visual-refinement-workflow.md`。

`SVGElement` 的图内短动画使用原生 WAAPI，避免 SVG 属性残留；HTML 微交互继续复用 Motion mini。原生图表的首次 resize 保留应有的绘制时长，筛选更新保持约320ms。导出前另外清除原生 emphasis/blur 和 axisPointer，并将原D3悬停改动恢复为原属性文本，防止临时淡化、参考线或空样式混入科研 SVG。

## 本地查看与操作

当前功能分支目录：`/home/codex/fwl-temporay/coursework/lens-chart-motion`。8774预览服务在 `lens-previews` 的 `chart-motion` tmux窗口运行。VS Code机器设置已为8774添加自动转发；无需更改main。

- 首页与原开场：`http://127.0.0.1:8774/`。
- 九位置：`http://127.0.0.1:8774/index.html?intro=0#position`。
- 修复五版本：`http://127.0.0.1:8774/index.html?intro=0#repair`。
- 13类图表：`http://127.0.0.1:8774/explore.html?mode=explore&chart=heatmap`，使用原图形选择器切换。
- 独立采样：`http://127.0.0.1:8774/explore.html?codeView=sampling#code`。
- 真实框选联动：`http://127.0.0.1:8774/explore.html?codeView=tokens#code`。

图框可Tab聚焦，左右键巡检真实数据，Enter打开原有记录入口（适用图表），Escape清除临时聚焦。鼠标选择仍使用原数据筛选/匿名详情。不存在真实路径的Flow状态继续显示原空状态。

重启预览：

```bash
python3 scripts/system/build_web_app.py
python3 -m http.server 8774 --bind 127.0.0.1 --directory app/dist
```

验收命令：

```bash
python3 scripts/system/check_web_snapshot.py --skip-build
python3 scripts/system/check_visual_coverage.py
python3 tests/run.py
python3 tests/run.py --full
BASE_URL=http://127.0.0.1:8774/ MOTION_BASE_URL=http://127.0.0.1:8770/ node tests/browser/chart-motion-science.mjs
```

同一份dist被多个浏览器验收读取时，先完成一次构建，再用 `python3 tests/run.py --full --skip-build`。`--skip-build` 只避免重复生成正在读取的文件，不跳过任何测试；默认命令仍自动构建。不要并行重建同一个dist。

科学图对照要求8770服务来自指定基线提交的独立工作树，不能用新版页面冒充before。测试会先打开空白文档，保证每个科学对照都从指定URL恢复初始条件，并等待原清单中应有的全部科学图；特别包含More Findings第4页的两幅图。`MOTION_SCIENCE_KEYS`、`MOTION_EXPORT_KEYS`仅供定位失败项，部分运行的报告不能通过完整认可门禁。

限制：未新增外部服务、依赖或位图。缺少View Transition API时径向布局切换采用原布局直接更新；禁用Motion库时保留原生WAAPI/原图表库降级。公开修复样例只提供一个真实前后对照，因此仅高亮这个样例的实际改行，不生成其他轮次的虚构代码。系统减少动态时不自动播放；用户主动播放仍按有限真实测量步骤推进。

开场测试仅将偏好重置后的固定30ms等待改为等待真实matchMedia事件及重播按钮启用状态，原断言保留；四个开场源码文件未修改。


## 最终验收（2026-11-03）

全部结果来自最终冻结源码，未沿用失效的旧PASS。完整运行日志、截图与下载文件留在忽略目录 `artifacts/motion-audit/`、`artifacts/qa/`。

| 检查 | 实际结果 |
|---|---|
| 正式源码构建、快照检查 | 通过；44个本地资源，源码/运行时同步，0个在线API |
| 93状态预览 smoke | 460 / 460 |
| 全量浏览器回归 | 2,003 / 2,003：原1,793项完整保留，新增210项 |
| 5种电脑宽度 | 1366、1440、1600、1920、2560；467项解码、绘制和布局检查全部通过 |
| 紧凑屏幕专项 | 768、390、320；13图及关键章节/播放器的60项控件和进度位置检查通过 |
| 原始科学图对照 | 184状态、188幅图；DOM结构、计算样式、规范化像素和位置全部一致 |
| 正常动画最终状态 | 13类图表全部与main一致；原生/图内短动画按时结束 |
| 真实下载 | 31项CSV/SVG与main一致；包含悬停/键盘高亮后的导出清理 |
| 原保护契约 | 原1,100文件清单及31份导出golden未改写；门禁通过 |
| 扩展不可变清单 | 1,141份科研资料、算法、图稿、素材、开场及原科学SVG绘图模块逐字节一致 |
| main工作树 | 1,289份原跟踪文件逐字节一致，工作区干净 |
| 资源与异常 | 最终完整回归没有普通资源请求失败和浏览器异常 |

原1,100文件保护范围中有4个控制器需要接入新交互：app、charts、story、code-interactions。其余1,096份仍逐字节一致；这4份以明确的可逆补丁、原源码指纹、184状态实际科学图对照及31项实际下载审核。`model.js`、`story-charts.js`、科研数据/算法/图稿和四个开场文件均未改动。

专项验证包括：13图真实运行的图内动画；移出DOM的动画立即清理；热力图真实提示卡及行列强调；Plotly多任务定位；Flow真实评分路径记录；原匿名详情/筛选/框选；九位置播放/暂停/继续/重播；五版本修复及真实代码改行；五次独立采样；隐藏、离章、减少动态、快速切换和销毁。

已修复的验收问题：首次resize提前终止绘图、异步两图页面漏等、D3悬停残留属性、原生blur和axisPointer污染导出、提示卡被清理隐藏，以及Sankey重绘替换路径产生的失效短动画。科学图对照从空白文档恢复真实URL条件并等齐原清单要求的图形；全部断言保留。开场偏好重置只修正测试等待方式，不改开场源码。

最终全量命令使用 `python3 tests/run.py --full --skip-build --port 8851`，与普通 `--full` 执行完全相同的10个测试套件；前置构建已单独完成，避免其他科学图审核读取dist时重复生成文件。通过记录：`full-final-proof.log`、`science-final-proof.log`、`smoke-final-proof.log`、`gate-final-proof.log`、`snapshot-final-proof.log`。

只提交源码、说明和必要的小型认可清单/科学图摘要；完整临时测试报告、截图、下载和旧失败日志均不提交。未制作或提交录屏，未合并、推送或发布。
