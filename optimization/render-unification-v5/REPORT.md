# Master 内容对齐、实际渲染检查与统一视觉 v5

本轮基线为已发布 `297d65e`。用户反馈首页图片/排版异常，明确要求“全篇和 Master 本来的内容对齐”。业务参照仍为 `dataAnalysis-vision/Master` 的 `35f7318`，本轮重新核对远端分支后确认未变。

## 本轮发现与修复

- 上一轮检查“有 SVG、无页面溢出”不能证明图已经完整显示。1366×768 原截图中，两级大标题、导航与留白将核心图表下半部推到屏外；限长图还因导出按钮独占第三排进一步下移。本轮压缩重复标题层级，把限长页排为标题/导出一排、筛选另一排，保留真实图表与原全部控件。
- 首轮 78 个普通动画状态及另外 12 个全貌截图未复现实际图片解码失败。本轮没有把这一点描述为已找到网络丢图根因；修复了能直接看到的版型问题，并新增图片解码、SVG 实际绘制、内部引用、透明度和滚动检查。
- 恢复 Master 的原路径/地形插画关系，移除旧版玻璃装饰对新版首页的替换。原始 `hero-orbit.svg` / `blue-field.svg` 保留原样；生产用颜色适配副本 `hero-master-v5.svg` / `field-master-v5.svg`，几何坐标逐字不变。装饰层使用正层级，正文独立在前，避免负层级叠放差异。
- 品牌保持 Master 的原生 LENS 字体与名称，旧生成图不再决定品牌是否可见。阻断装饰图加载后，原生品牌、正文、导航与科学 SVG 仍可用。
- 页面、导航、开场采用同组深蓝和青色，读数区保持浅色图纸。深色框架和浅色纸面分别规定文字、弱化文字、选中态、边框与焦点颜色，修正实际 axe 检出的交界处对比度问题。
- 开场继续纯代码实时绘制，沿用有限时长、跳过/重播、减少动态效果、超时回退与资源释放；Canvas 从共享 CSS 颜色读取粒子/光束，SVG 环与标题使用同一组变量，品牌落入新页眉时保持与真实页眉一致的浅色，不再中途变为深色字。

原始问题证据在 `before/`，第一版实现保留于 `iterations/round-1/`，最终截图、浏览器检查与录屏在 `after/`。测试过程发现的 Plotly 空 hover 图层单独标记为交互层，仍要求实际数据层有绘制内容；不把鼠标悬停层为空误报为科学图为空。

## 真正的内容对齐

`after/master-alignment.json` 使用独立构建的原 Master（8787）与当前页面（8788）逐项比较 **65 个首页状态**：研究问题、采集设计、数据处理、三方向所有模型/两视图、五发现及 36 个限长组合。

比较原正文、条件与选中状态，以及科学 SVG（仅归一化颜色字面量）。65/65 内容及图形比较通过。冻结数据、统计、原图稿、图表库业务模块和科研档案另做全部 2,189 个上游文件的保真检查。样式变化不改变研究结论、数据值、坐标、图形生成逻辑或 URL 筛选语义。

## 生图设计与执行

本轮使用内置 **image_gen**，以实际网页截图为输入，描述了每块内容、不能改变的数据、视口和容器尺寸：

- 桌面 1440×900，短屏 1366×768，手机 390×844。
- 桌面页眉 72 px / 左栏 184 px / 内容内边距 38 px；手机页眉 60 px / 底栏 72 px / 左右边距 20 px。
- 核心发现区采用紧凑的 30 px 章节标题、约 34 px 发现标题、270 px 证据说明，主图约 1100 px 宽；在短屏验证图形全部可见，手机长图在独立区域滚动，并明确提示。

生成 `design/direction-a.png`（浅色统一）和 `direction-b.png`（深蓝框架 + 浅色图纸）。选择 B：更接近 Master 原首页的深蓝身份，同时能让开场和页面连贯；图纸使用深字浅底，数据读数仍清楚。A 保留作为对照。

第一版代码真实截图后，再次调用生图模型生成 `design/homepage-revision.png`，要求严格保留 Master 原插画、首页文案、三项解释与 248,586。采用其更克制的标题和移动间距建议，未将参考图当作网页或数据图，也未使用模型虚构的新文字。完整提示词和输出文件见 `design/prompts.json`。

共同色板：深蓝 `#0b1f33`、主文字 `#e8f0f7`、辅助文字 `#a7c4d6`、青色 `#6dd1c4`；纸面 `#f8fbff`、纸面深字 `#1e3a56`、纸面强调 `#0e7c7b`。模型/策略的科学颜色保持区分，原本的原生 SVG/Canvas 没有变成图片。

方法沿用前三轮的“视觉参考 → 原生实现 → 真实渲染 → 定向反馈”，将论文启发与本轮工程检查区分；来源见 `../homepage-pilot/research/method-notes.md`。本轮新增实际绘制与 Master DOM/图形对齐，不声称这些工程门禁来自论文已验证的整体方案。

## 验收内容

最终结果见 `after/validation-summary.json`。新增标准包括：

- 92 个状态，320×740、390×844、768×960、1440×900；另完整检查 1366×768 的正常动画状态。
- 等待实际绘图完成；检查图片解码/自然尺寸、科学 SVG 非空绘制、内部 use 引用、嵌入图像解码、父级透明度；不能以按钮图标代替主图。
- 手机科学图独立滚动，桌面短屏检查整张主图初始可见；默认章节、选中控件、正文、导航、页眉和片区溢出同时核对。
- 原首页与图表库交互、数据/SVG 导出、400 行匿名记录、模态窗口、代码/修复播放、键盘热图与表格、快速切换与减少动画。
- 额外阻断装饰资源，确认原生正文、品牌与图表可用；快速导航、重播/跳过及落点阶段缩放后不能残留透明内容或 inert。
- 实时录屏与独立六档播放帧诊断；同主机/浏览器八次顺序 Lighthouse，对照已发布 297d65e。provided 节流不等同真实手机或弱网，不用单次分数宣称普遍加速。

构建与资源检查：

```bash
python3 scripts/system/build_web_app.py
python3 scripts/system/check_web_snapshot.py --skip-build
node optimization/render-unification-v5/scripts/coverage.mjs
node optimization/render-unification-v5/scripts/master-alignment.mjs
node optimization/render-unification-v5/scripts/home-interactions.mjs
node optimization/render-unification-v5/scripts/library-interactions.mjs
node optimization/render-unification-v5/scripts/intro-checks.mjs
node optimization/render-unification-v5/scripts/resilience.mjs
```

生产入口仍为两个 HTML。原提交包与历史优化成果只作为档案，不混入生产导航。生成的 runtime/dist 不提交，发布前需核对本轮源码指纹和真实证据。浏览器覆盖以 Chromium 为主，未声称穷尽所有真实设备、浏览器和数据组合。


## 最终实测结果

- 全站实际绘制与布局矩阵 462/462：首页/图表库 92 个状态 × 五档配置，包含普通动画短屏；保存 184 张桌面/手机状态截图与另外 8 张短屏截图。
- 原首页交互/无障碍 49/49，图表库交互/弹层 39/39，开场 86/86，Master 实际内容/科学图比较 65/65，图片故障/快速导航/落点缩放恢复 6/6。合计 707/707 通过。
- 上游 2,189 个文件全部保留并核对，2,176 个原样文件/已验证快照；13 个明确的展示/集成例外。数据、科学 SVG 生成坐标/数值逻辑不变。

| 页面 | 视口 | 性能 297d65e → v5 | v5 CLS |
| --- | --- | --- | --- |
| 首页 | 手机 | 100 → 100 | 0.000000 |
| 首页 | 桌面 | 100 → 100 | 0.000086 |
| 图表库 | 手机 | 100 → 100 | 0.000040 |
| 图表库 | 桌面 | 98 → 98 | 0.000007 |

八份报告的 accessibility 与 best-practices 均为 100。首页冷加载传输诊断减少约 18.8 KiB，图表库增加约 1.1 KiB。桌面首页 TBT 本次约 27.5 ms，其余为 0；这是同机单次诊断，不能据此宣称真实弱网/真实设备普遍提速。

六档实时开场完成于 5964–5970 ms，桌面约 54.9 FPS，手机约 30.0 FPS，4 倍 CPU 手机约 28.4 FPS；所有档位结束后 RAF=0、Canvas=1 像素。约 10.8 秒录屏来自 421 个真实浏览器帧，包含进入新版内容、位置滑块、重播及跳过。

## 预览

- [开场与新版首页](https://fwlyii.github.io/data-analysis-frontrefine/?intro=1#question)
- [直接进入首页](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0#question)
- [核心发现](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0&finding=concise#findings)
- [图表库](https://fwlyii.github.io/data-analysis-frontrefine/explore.html?mode=explore#case-1)

本会话此前已授权更新 main 与 Pages；本轮完成验收后发布，并在公网再次核对实际资源版本与页面，保留正常 Git 历史供回退。
