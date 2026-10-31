# LENS 第二轮：字体与动效

基线为已发布的 `2344eb5`，在 `visual/type-motion-v2-20261031` 分支完成。本轮保留上次 Pilot 的布局、研究内容、数据 SVG 与图表库，集中修正用户指出的字体与缺少可感知动画两个问题。沿用用户后续给出的远端发布授权，验收后通过现有 main → Actions → Pages 发布。

## 反思与流程补全

上一轮的主要问题：标题依赖系统字体回退，而截图环境装有 CJK 字体，这不能保证访问者看到相同排版；已有短暂的章节裁切过渡不够明显，截图测试又默认 `reducedMotion=reduce`，未单独验证普通模式的动态体验。不能以“截图好看、功能通过”代替字体一致性和动画验收。

已将可复用流程更新至 [前端视觉优化流程 v2](../../app/docs/visual-refinement-workflow.md)：基线 → 文字层级与真实字体 → 生图候选与独立素材 → GitHub 动画选型 → 原生实现 → 静态截图和动态录屏 → 功能/保真/可访问性/性能关卡 → 公网发布核验。新增可运行的动态检查、录屏、资源预算与综合验收脚本。

论文方法继续沿用首轮已核对的 Editable Visual Design、UI Remix、UI2Code-N：生图参考与独立素材、保留结构的局部改造、真实浏览器反馈。[原始阅读与工程适配](../homepage-pilot/research/method-notes.md) 保留。字体子集、动态模式、许可核对和发布关卡是本项目补充，不是三篇论文已经验证过的统一流程。

## 字体与实际生图

- 品牌艺术字使用内置 `image_gen` 实际生成 [候选 A](designs/wordmark-a.png) 和 [候选 B](designs/wordmark-b.png)，选择 A 的衬线轮廓、E 的青色切口与青色句点。[提示词及生成记录](designs/generation-manifest.json)、[选择理由](designs/selection.md)。工具未返回具体模型版本，不推断型号。
- 交付独立透明 `lens-wordmark.webp`，600×200，**12.8 KiB**。图片失败保留原生品牌文字；可访问名称由原生链接提供。没有把正文或数据转成图片。
- 中文标题使用 OFL 许可的 Noto Serif CJK SC SemiBold 子集，重命名为 **LENS Editorial**，随网站加载，**47.6 KiB / 174 个码点 / 当前标题无缺字**。配合 600 字重、字号、字距和行高调整。所有五章实际平台字体检查均为自定义字体。[覆盖与源文件哈希](assets/font-subset.json)；版权与 OFL 留在 `app/assets/fonts/`。
- 正文、导航、按钮、表单、动态研究标题和数值仍为原生可编辑文字；数据 SVG 保留原字体与原图稿。普通标题未来新增字符时需要重新做字体子集。

两份艺术字的实际风格差异小于提示词意图，因此不声称充分探索了所有设计方向。艺术字的识别度和整体协调性是本次定性视觉判断，没有用户偏好实验。

## GitHub 动画选型与实现

核对 [Motion 官方 GitHub](https://github.com/motiondivision/motion) 与 [animate 文档](https://motion.dev/docs/animate)，并比较 Animate.css、Anime.js 后，选用 MIT 许可的 **motion/mini@14.9.0**。打包后的本地脚本为 **8.6 KiB（未 gzip）**，不加载外部 CDN、不增加 React。[来源、许可及选择说明](research/animation-selection.md)。

新增 `app/src/story-motion.js`，在原渲染器中仅插入一个展示钩子：

- 标题与图纸轻入场，摘要和结论错开几十毫秒呈现。
- 主题导航下划线平滑移动到当前章节。
- 条件切换后图表容器短淡入；原有修复播放的版本更新有轻微反馈。
- 证据区首次滚入视口时轻入场；按钮增加悬停和按压反馈。
- 尊重系统“减少动态效果”，切换偏好时立即结束装饰动画；快速触发替换前一个动画，页面隐藏时结束，重渲染时清理观察器。

只改变 transform/opacity，不插值实验数据，不重画原 SVG 曲线。全部效果为有限时长，没有装饰循环。静态内容默认可见，不依赖隐藏后再播放。一次主要视觉实现后，浏览器审查修正动画替换时的跟踪清理与中等宽度导航标记对齐。

## 真实页面与验收

| 内容 | 证据 |
|---|---|
| 上一版真实页面 | [桌面](before/desktop.png)、[手机](before/mobile.png) |
| 本轮真实页面 | [桌面](after/desktop.png)、[桌面全页](after/desktop-full.png)、[手机](after/mobile.png)、[手机全页](after/mobile-full.png) |
| 正常模式真实录屏 | [motion-preview.mp4](after/motion-preview.mp4)，约 12.4 秒；285 帧来自实际 Chromium，非生图视频，[录制记录](after/video-manifest.json) |
| 功能回归 | [82/82](after/regression.json)：四宽度×五章、选择、URL、下载、位置/CI、修复播放、图表库往返等 |
| 字体和动态专项 | [50/50](after/motion-checks.json)：正常/减少动态效果、动画终止、快速连点、四宽度标记、逐章真实字体、图片失败回退 |
| 可访问性 | [axe](after/accessibility.json)：0 个已确认违规；回归中无未捕获异常或失败资源 |
| 数据与原逻辑保真 | [73/73 文件校验](after/content-fidelity.json)：数据、原 SVG、其他源文件逐字节一致；story.js 除一个展示钩子外一致；CSV 与上版相同 |
| 综合预算与验收 | [自动关卡](after/acceptance.json)，涵盖字体、素材哈希、体积、功能结果、保真、录屏和性能诊断 |

静态截图在减少动态效果模式下稳定采集；动画专项和录屏使用普通模式。它们是两套不同证据，不能互相代替。未穷尽真实手机和全部浏览器。

## 性能与代价

使用同机 Chromium、同视口和实际 DevTools 节流，顺序执行四次 Lighthouse；基线 dist 直接提取自 `2344eb5`。下表为单次诊断，不能解释为稳定提速或多机统计结果。[汇总及原始报告路径](after/performance-summary.json)。

| 设备/版本 | 性能 | 可访问性 | 最佳实践 | FCP | LCP | TBT | CLS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 手机/上一版 | 79 | 100 | 100 | 1.47s | 5.42s | 64ms | 0 |
| 手机/本轮 | 77 | 100 | 100 | 1.67s | 5.87s | 77ms | 0 |
| 桌面/上一版 | 100 | 100 | 100 | 0.14s | 0.24s | 0ms | 0 |
| 桌面/本轮 | 100 | 100 | 100 | 0.10s | 0.19s | 0ms | 0 |

两端冷加载资源均增加约 **76.1 KiB**。主要新增为标题字体、艺术字和本地 Motion 加控制层。新增资源在字体 60 KiB、艺术字 20 KiB、库 12 KiB、控制层 8 KiB、合计 90 KiB 的预算内。

手机端有可测的加载代价，性能分下降 2 分、LCP 增加约 0.45s；没有把这个结果描述为提速。本轮没有新增布局位移。原有约 0.72 MiB 的展示数据/脚本冷加载仍是移动端慢网限制，后续可另做按需加载优化，保持证据和功能一致。

## 复查、部署与回退

```sh
# Pages 构建只用 Python 标准库，不需要 npm 或字体准备依赖
PYTHONDONTWRITEBYTECODE=1 python3 app/pipeline/scripts/system/build_web_app.py

# 开发检查依赖，沿用首轮浏览器工具
npm ci --prefix optimization/homepage-pilot/tools --ignore-scripts
npm ci --prefix optimization/type-motion-v2/tools --ignore-scripts

# 默认 8780 提供当前 app/dist，8783 提供 2344eb5 的 dist
node optimization/homepage-pilot/scripts/browser.mjs capture ../type-motion-v2/after
node optimization/homepage-pilot/scripts/browser.mjs regression ../type-motion-v2/after
node optimization/type-motion-v2/scripts/motion-checks.mjs
node optimization/type-motion-v2/scripts/record-motion.mjs
node optimization/type-motion-v2/scripts/performance.mjs
python3 optimization/type-motion-v2/scripts/acceptance.py
```

浏览器脚本使用当前环境的 `/snap/bin/chromium`；录屏需要 FFmpeg。`bundle-motion.mjs` 可重新打包锁定的 Motion，实际验证输出哈希与交付脚本相同。字体准备单独使用 fontTools 4.60.1 与 brotli 1.2.1，生产构建直接校验已提交的 WOFF2/图片哈希；许可与来源一起交付。大字体母版、node_modules、录屏中间帧和凭据不进入仓库。

线上预览沿用 [GitHub Pages 首页](https://fwlyii.github.io/data-analysis-frontrefine/)。发布后另行核对工作流与公网资产版本。保留独立提交，需要回退时可以针对本轮提交做 `git revert` 并正常发布，无需强制重置历史。
