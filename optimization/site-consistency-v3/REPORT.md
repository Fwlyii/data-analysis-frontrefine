# LENS 全站一致性与布局优化 · 第三轮

本轮从已发布的 `a6c4c1f` 建立独立分支 `visual/site-consistency-v3-20261031`。修正“只优化默认首页、图表库仍用旧主题”的范围缺口；保留原数据、科学图、路由、筛选与记录联动。完成后沿用既有授权发布到 GitHub Pages。

## 流程为何会漏页，以及如何修正

前两轮以首页为 Pilot，图表库只验证过往返，未纳入视觉验收。文档甚至仍允许其独立沿用旧样式。现已更新 [全站流程 v3](../../app/docs/visual-refinement-workflow.md) 和 [视觉规范](../../app/docs/DESIGN.md)：

1. 先扫描生产入口、链接、模式、图种、章节和弹层，建立 [机器清单](site-inventory.json)。当前 **2 个入口 / 34 个状态 / 4 档宽度**；不是穷尽全部数据组合。
2. 先统一公共设计，再做页面布局；两入口共用 `site.css`、`templates/site-header.html` 与 `site-shell.js`。
3. 生图参与初始方向和真实实现后的修订；保留完整提示词与原图，而非仅让模型口头评价 CSS。
4. 核对实际标题、当前章节、所选图形和真实图表，不以网址或 HTTP 200 代替覆盖。扫描中发现 hash-only 导航复用旧文档，已修正工具并重新采集整站截图。
5. 发布前运行覆盖检查，将通过的浏览器记录绑定到源码指纹。新增入口、图形、章节、失败记录或过期证据会阻止上传；GitHub Actions 不会假装重新跑浏览器。

沿用首轮对 Editable Visual Design、UI Remix、UI2Code-N 的实际方法借鉴，详见 [既有阅读记录](../homepage-pilot/research/method-notes.md)。全站覆盖、模板、字体、动态与 CI 是本项目的工程适配，不称为论文验证过的统一方法。

## 三次实际生图与两轮实现

- 第一轮：[桌面 A](designs/direction-a.png)、[桌面 B](designs/direction-b.png)，输入真实图表库和首页截图。选择 A 的“标题—筛选面板—独立白色图纸”结构。[七维选择说明](designs/selection.md)。
- 实现第一版后，查看真实手机截图，发现标题和导出分行、筛选占用偏多。
- 第二轮：将第一版真实截图再次送入 image_gen，生成 [手机修订方案](designs/mobile-refinement.png)，再改为同一行标题/导出、全宽图形选择和其余四项两列布局；图表上沿从约 535px 提前至约 459px，选择框仍为 40px。
- [原始输出、输入角色、提示词及哈希](designs/generation-manifest.json)。使用内置 image_gen，三次成功调用；工具未返回具体模型版本。

生成图中不准确的字、模型图标、柱形渐变和数据没有进入生产图表。三个结果都作为参考保存在成果目录；页面仍由原生 HTML/CSS/JS/SVG 构成。沿用上一轮已生成的品牌字与透镜，不增加新的装饰下载。

## 跨页修改

| 范围 | 实际变化 |
|---|---|
| 两个入口 | 共用品牌、88/72px 页眉、五模式导航、蓝青变量、字体和外边距；图表库提供原有返回与全屏操作 |
| 13 种图形及空状态 | 筛选器成组、标签在上、选择框对齐；白图纸、统一图例/来源层次；宽图在自身区域滚动并可键盘聚焦 |
| 输出效率与资料位置 | 统一标题、工具条、科学图纸和浅青发现说明；修复两处原手机页面溢出 |
| 代码生成四视图 | 统一二级切换、过滤器、采样条、精确范围和评分抽屉；框选组补充可访问名称 |
| 更多发现五章 | 统一指标卡、图纸、图注和发现说明，保留原模型与条件交互 |
| 首页五章及任务变体 | 接入公共基础，保留原布局和操作，标题字体扩展至全站实际字符 |

共享标题字体为 **252 个码点 / 79,296 bytes**，OFL 许可、母版哈希与准备脚本保留；当前所有主标题实际平台字体均为 LENS Editorial。[字体记录](font-manifest.json)。正文仍采用系统无衬线栈，不保证不同操作系统像素完全一致。

原动画库 Motion mini 14.9.0 继续本地复用，未新增框架或 CDN。图表库增加模式入场、导航标记与详情抽屉反馈，支持减少动态效果、快速切换和旧目标清理。[约 12 秒真实跨页录屏](after/motion-preview.mp4) 来自 Chromium 的 283 帧，覆盖首页 → 图表库 → 热力图 → 位置记录 → 代码视图 → 返回首页，非生图视频。

## 真实截图与验收

- 图表库：[优化前桌面](before/chart-model-desktop.png) / [优化后桌面](after/chart-model-desktop.png)，[优化前手机](before/chart-model-mobile.png) / [优化后手机](after/chart-model-mobile.png)。
- 其他代表页：[位置矩阵](after/position-matrix-desktop.png)、[代码开销](after/code-tokens-desktop.png)、[更多发现](after/discovery-5-mobile.png)、[手机记录详情](after/dialog-record-mobile.png)。
- 两版各 **68 张**对应截图，覆盖 34 状态的桌面和手机；[最终截图审计](after/page-audit.json) 中实际选中项全部匹配，页面均无横向溢出。
- [全站检查](after/site-checks.json) **278/278**：34 状态 × 四宽度、真实字体、公共品牌与导航，以及筛选、刷新、记录、400 行集合导出、联动、采样播放、范围刷选、评分详情和动态。
- [首页原功能](after/home-regression/regression.json) **82/82**；[首页字体与动态](after/home-regression/motion-checks.json) **50/50**。
- [六个代表性页面/弹层的 axe 检查](after/accessibility.json)：**0 个已确认违规**；全站操作未出现未捕获异常或失败资源。不声称全部图种都做过完整可访问性审计。
- [79 个受保护文件](after/content-fidelity.json)：原数据、原科学 SVG、业务渲染和研究快照保持一致；代码框选只增加一行可访问名称，比较时明确去除这项展示注释；品牌解码从旧首页控制器移至公共脚本。
- [迭代及失败修正记录](iterations/review.md)：保留首轮失败结果，修复颜色对比度、滚动聚焦和框选名称；纠正测试对当前三行模型汇总 CSV 的错误预期，未改动导出数据。

源码指纹允许 HTML 构建缓存标识和 CSS 行尾空白的无视觉差异规范化；检查时的原始指纹保留在结果中。当前部署检查已在本地运行通过。

## 性能与边界

[完整性能汇总及原始报告](after/performance-summary.json)。本轮在同机、同浏览器、同视口顺序做两个入口的八次冷加载诊断，**不模拟弱网和 CPU 节流**。基线为直接提取的 `a6c4c1f`。这些分数不能与第二轮使用 DevTools 节流的 77 分直接比较，也不能推断真实手机提速。

| 入口 / 视口 | 性能 前→后 | LCP 前→后 | CLS 后 | 冷加载增量 |
|---|---:|---:|---:|---:|
| 首页 / 手机视口 | 100 → 100 | 199 → 186ms | 0 | 37.6 KiB |
| 首页 / 桌面 | 100 → 100 | 211 → 200ms | 0 | 37.6 KiB |
| 图表库 / 手机视口 | 100 → 100 | 782 → 784ms | 0 | 113.5 KiB |
| 图表库 / 桌面 | 99 → 99 | 806 → 811ms | 0 | 113.5 KiB |

共享字体、CSS、脚本分别在 90/8/8 KiB 预算内。图表库原有头部仍加载约 14 MiB 的未压缩资源；本轮保持其加载架构，弱网表现仍有较大优化空间。科学图在窄屏使用可聚焦的区域横滚，未将所有宽图重画成手机专版；未穷尽浏览器、真实设备与全部数据组合。

## 复查与回退

当前页面由 8780 提供，`a6c4c1f` 原样基线由 8784 提供。开发工具沿用首轮 tools，Chromium/FFmpeg 路径按当前环境设置；生产构建与 CI 检查只需 Python 标准库。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 app/pipeline/scripts/system/build_web_app.py
node optimization/site-consistency-v3/scripts/inventory.mjs
node optimization/site-consistency-v3/scripts/capture.mjs before
node optimization/site-consistency-v3/scripts/capture.mjs after
node optimization/site-consistency-v3/scripts/site-checks.mjs
node optimization/site-consistency-v3/scripts/home-regression.mjs regression
node optimization/site-consistency-v3/scripts/home-motion.mjs
node optimization/site-consistency-v3/scripts/record-motion.mjs
node optimization/site-consistency-v3/scripts/performance.mjs
PYTHONDONTWRITEBYTECODE=1 python3 optimization/site-consistency-v3/scripts/finalize-review.py
python3 app/pipeline/scripts/system/check_visual_coverage.py
```

预览沿用 [研究首页](https://fwlyii.github.io/data-analysis-frontrefine/) 和 [图表库](https://fwlyii.github.io/data-analysis-frontrefine/explore.html?mode=explore#case-1)。发布后另行核对公网版本与实际跨页操作。修改保存在独立提交，可通过正常 revert 回退，不强制重置历史。
