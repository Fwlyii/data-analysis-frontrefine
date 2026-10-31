# 最新 Master 功能与 LENS 视觉迁移

业务基线：[dataAnalysis-vision / Master / 35f7318](https://github.com/Fwlyii/dataAnalysis-vision/tree/35f7318e45561da07c75eaf65374e4107004d5ec)。视觉基线：当前 Pages 仓库 `a1cd05a`。用户本轮明确授权克隆、迁移、更新当前 `main` 并推送发布；源仓库 `Master` 不作修改。

## 合并结果

保留最新五部分英文展示：研究问题、采集设计、数据处理、数据全貌、核心发现；保留最新动态 SVG、31 提示全貌的三任务方向、模型切换、热图键盘选择、五个发现、原始示例、表格、方法、SVG/CSV、位置和修复播放、查询参数与章节历史。图表库五模式、13 图形及匿名记录联动延续 Master 的实现。

迁入前几轮的 `#f4f8fa` 浅蓝背景、白色图纸、`#203b50` 深蓝文字、`#147b7b` 青色、共享字体与品牌、独立生成的 LENS 艺术字和光学素材、卡片边框/阴影、焦点、弹层、有限章节/图形过渡和导航移动标记。电影开场继续使用实时 Canvas + SVG + 原生文字，约 5.95 秒；光圈露出真实新首页，品牌按实际测量飞入新版顶栏。支持会话内一次、强制播放/跳过、重播、Esc、减少动态效果、错误回退和播放后释放 Canvas。

主入口仍为 `app/index.html` 与 `app/explore.html`，新增 `app/deck.css` 只适配新版五部分布局。没有以旧首页覆盖新业务，也没有把设计稿或录屏当作网页运行内容。

## 设计闭环与取舍

沿用前三轮对 Editable Visual Design、UI Remix、UI2Code-N 的阅读：先视觉想象，再按原结构原生实现，以真实渲染图反馈并作局部修订。研究方法与工程补充的区分、来源与限制见 `../homepage-pilot/research/method-notes.md`；本次是工程迁移，未复现模型训练或宣称论文验证了这一组合流程。

- 真实基线：`before/` 中两个入口及五部分的桌面/手机截图，共 12 张。
- 两份真实生图：`design/direction-a.png`、`design/direction-b.png`，调用内置 `image_gen`，输入新站真实截图及上一已发布视觉截图。完整提示词与输入角色见 `design/prompts.json`。
- 第一版真实实现：`iterations/round-1/`，保持新站侧栏、顶栏、内容与参数。
- 第二次生图反馈：`design/mobile-revision.png`，以第一版真实手机截图和方向 A 为输入，要求压缩流程图纵向占用并改善间距。
- 最终真实实现：`after/deck-*.png`、`after/landscape-*.png`、`after/story-*.png` 与图表库各状态截图。

| 比较维度 | 方向 A | 方向 B |
| --- | --- | --- |
| 审美与视觉层次 | 光学素材与留白建立焦点，内容直接落在浅蓝底上 | 外层整纸容器更规整，但边框与内容图纸容易重复 |
| 风格一致性 | 延续既有浅蓝青身份、品牌与透明光学素材 | 保留配色，但引入额外大容器 |
| 可读性 | 深色原生标题与柔和装饰分离 | 标题同样清晰，右上光学弧较接近文字 |
| 原布局保留 | 顶栏、侧栏、主文案和计数关系保持 | 新增包围主屏的容器，需要更多尺寸调整 |
| 实现可行性 | 复用现有独立素材和 CSS | 需要处理大卡片内外双层滚动和边界 |
| 响应式适配 | 手机自然堆叠，保留可用宽度 | 手机外层边距会进一步压缩内容 |

选择 A。不照搬生成图中的文字绘制或任何数据图。手机修订图未满足紧凑流程要求，还把 Document QA / Code generation 错改成其他任务名称，因此拒绝这些内容与布局，保留原始数据和文案，以代码实现三列紧凑流程；只参考其图标对齐、圆角与间距。生图提供了配色、材质和主次关系的可视参考，不能替代真实响应式与数据验收。

## 局部修复与兼容

- Master 原来的 `[data-section]` 点击绑定包含 `body`；所有内容点击冒泡后会重复切换章节、重置面板滚动并提前终止入场效果。限定为 `button[data-section]`，保留原章节与参数语义，新增真实滚动和导航回归。
- 手机图表库长英文返回文字挤出全屏按钮：显示简短的 Research，保留完整可访问名称；模式标签缩短并保留语义。
- 手机采集流程改为三列；数据表、位置滑块、图注与区间开关留在可达宽度，宽科学图仍在自己的区域滚动。只裁切装饰图的越界部分，不隐藏数据或操作控件。
- 清理数据管线列表的重复编号，调整代码示例卡片内部间距。强调文字改用更深青色，消除实际测得 4.45:1 的对比度失败。
- 滚动数据表、提示定义和示例代码可键盘聚焦；在这些区域按方向键不误切章节。
- 保留 Master 固定视口/面板内滚动方式；开场后恢复可操作状态，并将焦点交给可见展示主区，重播后恢复触发按钮。

## 内容与依赖保真

`after/content-fidelity.json` 对上游全部 **2,189 个文件**逐一检查。除明确列出的 13 个集成/展示文件外，2,176 个文件或快照保持上游内容。三个 `app/data/*.gz` 从 LFS 指针还原为实际字节，分别核对 SHA-256 和大小；冻结统计、SVG 原稿、其他业务模块和科研档案保持原样。`story-charts.js` 去除颜色字面量后与 Master 逐字相同，图形坐标/数值代码未改；`story.js` 只增加展示回调与滚动区域可访问性。

七项已有字体、品牌、装饰、Motion mini、开场 CSS 与图表库样式逐字复用上一版本。没有引入新的运行框架或远端 CDN。Geist 使用 Master 已有本地字体；艺术字保留原生可访问品牌和图片失败回退。现有字体与 Motion 的许可继续随资源提供。

原匿名包的 `app/pipeline/`、`app/results/`、`app/docs/` 等目录由 Master 根目录规范替代。历史优化成果保留，生成的 `app/runtime` / `app/dist` 不再入 Git。上游科研档案共约 1 GiB，保留其 LFS 指针及[Git LFS 支持的自定义源仓库端点](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-config.adoc)；生产所需三个小型快照直接存入当前 Git，构建无需下载完整档案。`submission/` 保留上游历史包原样，不属于生产导航。

清理旧目录曾误删复用资源，已由 Git 快照恢复，并在完整构建后重新执行最终浏览器验收；没有把中间版本推送上线。

公网首轮冷加载发现原有 1.8 秒引导兜底会抑制迟到的强制播放请求；显式 `intro=1` 现在允许脚本稍后抵达时正常播放，普通迟到访问仍直接显示系统。新增 2.2 秒模块延迟、完整播放和普通回退三个真实浏览器断言。

## 验收与复现

最终结果由 `after/validation-summary.json` 汇总。状态清单见 `site-inventory.json`，覆盖 **92 个状态 × 320 / 390 / 768 / 1440 四档宽度**，保存 184 张真实桌面/手机状态截图。清单包含全貌所有方向/模型/两种视图、36 个模型/任务/限长组合、全部发现与图表库，不只检查 HTTP 状态码或默认首页。

检查内容包括实际选中视图、可见标题、真实 SVG、页面及面板溢出、共同品牌/配色/导航、原生筛选与刷新、热图键盘选择、方法和记录详情、400 行记录 CSV、SVG 导出、修复/代码播放、有限动效与减少动态效果、重播/跳过/异常回退、控制台和资源错误。axe 检查主要视图、五个发现展开内容与图表库弹层，报告保留 `incomplete` 项，不声称覆盖所有浏览器或所有筛选组合。

运行：

```bash
python3 scripts/system/build_web_app.py
python3 scripts/system/check_web_snapshot.py --skip-build
python3 -m http.server 8788 --bind 127.0.0.1 --directory app/dist
node optimization/master-migration-v4/scripts/inventory.mjs
node optimization/master-migration-v4/scripts/coverage.mjs
node optimization/master-migration-v4/scripts/home-interactions.mjs
node optimization/master-migration-v4/scripts/library-interactions.mjs
node optimization/master-migration-v4/scripts/intro-checks.mjs
python3 optimization/master-migration-v4/scripts/fidelity.py
```

浏览器工具使用仓库既有 `optimization/homepage-pilot/tools` 依赖与 `/snap/bin/chromium`。基线服务器 8787 对应独立克隆的 Master 构建；当前服务器 8788。性能工具及录屏脚本在同一 `scripts/` 目录。

性能采用同主机、同浏览器、同视口的八次顺序 Lighthouse 前后对照，使用 provided 节流（不模拟弱网/CPU），首页显式跳过开场，以比较真实主系统。开场另做六档视口/DPR/CPU实时播放；测帧时不截图、不录屏、不同时执行其他浏览器任务。录屏由真实 CDP 帧编码，只存于审阅成果，不进入 `app/dist`。这些是单机诊断，不能视为真实手机或弱网保证；图表库已有较大的数据快照仍然保留。


### 最终实测结果

- 全站矩阵：370/370；首页交互与可访问性：49/49；图表库交互与弹层：39/39；开场生命周期：86/86。合计 **544/544 通过**，最终源码与浏览器证据指纹一致。
- 基线与当前均保持每方向 31 提示完整数据绑定：推理 372、文档问答 186、代码生成 93 个条件；32 个直接资源通过 HTTP 检查，模块与运行副本一致。

| 页面 | 视口 | Lighthouse 性能：Master → 合并后 | 合并后 CLS |
| --- | --- | --- | --- |
| 首页 | 手机 | 100 → 100 | 0.000000 |
| 首页 | 桌面 | 94 → 100 | 0.000088 |
| 图表库 | 手机 | 100 → 100 | 0.000040 |
| 图表库 | 桌面 | 98 → 99 | 0.000007 |

公网强制加载分支修正后重新执行全站矩阵和开场回归；首页性能诊断显式使用 `intro=0`，播放时间线也未更改，因此沿用上述同条件性能结果。八份报告中的 accessibility 和 best-practices 均为 100。首页冷加载资源诊断增加约 184.6 KiB，图表库增加约 113.7 KiB；前者包含完整开场和品牌资源，后者不加载开场。评分与毫秒受本机状态影响，不能将单次对照宣称为普遍提速。

六档实时开场全部正常完成，时长 5954–5979 ms；普通桌面约 54.9 FPS、平板约 59.5 FPS、手机约 29.8 FPS，手机 4 倍 CPU 节流约 28.4 FPS。完成后所有档位 RAF=0、Canvas=1 像素，数据在开场期间已初始化。真实录屏约 10.7 秒，包含完整开场、新版章节、位置滑块、重播与跳过。

从 Git 暂存树额外提取一份干净副本，独立构建、资源/数据绑定与发布门禁全部通过，证据见 `after/fresh-build.json`。

## 发布与预览

GitHub Actions 使用 `scripts/system/build_web_app.py` 与 `scripts/system/check_visual_coverage.py`。门禁核对全站图谱、真实截图、检查结果、当前源码指纹、数据保真、性能与开场清理，再上传 `app/dist`。

- [完整预览，显式播放开场](https://fwlyii.github.io/data-analysis-frontrefine/?intro=1#question)
- [直接预览新版五部分展示](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0#question)
- [核心发现](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0&finding=concise#findings)
- [完整图表库](https://fwlyii.github.io/data-analysis-frontrefine/explore.html?mode=explore#case-1)

发布后以 Actions 成功、资源哈希与真实公网浏览器结果为准。新提交保留当前仓库历史并纳入 Master 祖先，可正常 revert；不强制推送、不改写历史。
