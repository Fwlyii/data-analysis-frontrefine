# LENS · 知微：实时电影开场本地验收

基线 `f353a18`，工作分支 `feat/cinematic-intro-20261031`。按本次任务要求只在本地实现、测试和留存提交，不合并、不推送、不修改线上部署。原任务保存在 [REQUEST.txt](REQUEST.txt)。

## 本地预览与操作

- [强制播放](http://127.0.0.1:8780/?intro=1)；[跳过开场查看系统](http://127.0.0.1:8780/?intro=0)。8780 是当前服务器上的本地预览服务，需要在该环境或转发该端口后访问。
- 启动：在仓库根目录执行 `python3 app/launch.py --port 8780 --no-open`。现有 8780 服务已经提供最新 dist；若另开服务可改端口。
- 页眉新增圆形播放/回转图标，悬停或读屏名称为“重播开场”。右上角“跳过片头”、Escape 均可结束；Tab 留在跳过按钮。
- 同会话正常返回/刷新不再自动播放；`intro=1` 覆盖会话记忆，`intro=0` 跳过。两者都尊重减少动态效果；该偏好启用时直接显示系统，重播按钮禁用并说明原因。
- [查看验收页](index.html)、[真实浏览器操作录屏](after/intro-demo-desktop.mp4)。录屏展示点击重播、完整开场、真实资料位置操作和再次重播后跳过。

**运行时没有视频、GIF、逐帧图片、Lottie 或整幅生成场景图。MP4 只保存在本目录供验收，构建不会将它复制到 app/dist。**

## 源码与模块

| 文件 | 职责 |
|---|---|
| [app/src/intro.js](../../app/src/intro.js) | 独立模块，五个类共用 performance.now + requestAnimationFrame 时间轴 |
| `IntroController` | 首访/强制/跳过/重播、键盘与 inert、会话记录、异常回退、尺寸和可见性、有限时长及清理 |
| `ParticleSystem` | 固定随机种子 `0x4c454e53`；深度投影、立方曲线运动、拖尾、流道、有限邻接线、程序化渐变光点和透视网格 |
| `LensScene` | SVG 同心环、绘制进度、弧线、96 刻线、半透明镜面和扫描线；聚焦光束由 Canvas 绘制 |
| `TitleReveal` | 原生 LENS. / 知微 / 副标题 / 标语，遮罩、轻字距和错峰揭示 |
| `PageTransition` | 一次测量中央文字与真实页眉，FLIP 移动/缩放；透明光圈扩大露出真实系统；复用 Motion mini，并由同一时间轴推进页面入场 |
| [app/intro.css](../../app/intro.css) | 完全限定的片头样式、空间层次、原生文字排版及四档响应式布局 |
| [app/index.html](../../app/index.html) | 提前捕获 intro 参数、深色首帧保护和缺失脚本兜底；intro 脚本排在数据脚本前，不等待片头结束才初始化数据 |
| `site-shell.js`、`story-motion.js` | 片头活动期间暂停各自的装饰动画，避免转场互相竞争；原数据与路由逻辑未改 |
| 构建器 | 从真实源码复制 intro.js、intro.css、字体并生成缓存标识；页眉重播入口也由真实构建配置提供 |
| `app/visual-coverage.json` 与覆盖检查 | 追加本轮真实验收、帧率与体积检查，继续保留全站覆盖规则 |

Motion mini 沿用已有本地 14.9.0，没有增加大型库。知微两字使用 Noto Serif CJK SC SemiBold 的合法衍生子集，**3,008 bytes**；其余文字复用现有系统字体。母版哈希、准备脚本与 [字体元数据](font-manifest.json) 留存，OFL 版权声明随字体目录交付。

## 时间轴与镜头衔接

| 时间 | 画面与连续运动 |
|---|---|
| 0–0.8s | 深色画面觉醒；不同深度、尺寸、透明度和速度的微光，透视网格逐渐显现 |
| 0.8–1.8s | 粒子从散乱漂移进入曲线速度场；两侧流道逐段显现，稀疏连线增强组织感 |
| 1.8–3.0s | 粒子继续汇聚，SVG 环线和刻度成形、转动后锁定，扫描和聚焦光束穿过透镜；环线从 1.55s 预先起笔，避免硬切 |
| 3.0–4.0s | 五项研究的抽象 SVG 意象错峰出现并收束，没有实验数值，也未改动真实曲线 |
| 4.0–5.06s | 原生 LENS.、知微、副标题和标语揭幕，品牌保持可读停留 |
| 5.06–5.95s | 光圈从焦点打开，透镜向观察者扩大；洞中是实际可操作页面，品牌飞入真实页眉，导航、发现标题与主图依次到位 |

[机器可读时间轴](timeline.json)。转场不是切换两张画面：背景层的圆形透明遮罩逐渐扩大，原首页在其下照常运行；原生品牌通过 getBoundingClientRect 的 First/Last 坐标映射至真实页眉。品牌飞行时根据光圈已露出的背景调整字色，避免在深色边缘变暗。示例锚点进入时保留原滚动位置，品牌使用该位置下实际测得的页眉坐标。

## 实际视觉迭代与截图

第一版已在真实浏览器完整播放并留存于 `iterations/round-1/`，没有用概念图代替网页截图。观察到流动组织感较弱、飞行文字在暗处偏暗、自动聚焦使跳过按钮出现明显轮廓。

第二版增加被逐段揭示的曲线流道、提高粒子的可见度；让字色随光圈露出的纸面变化；初始聚焦对话框，仅键盘导航时显示按钮焦点。性能迭代将 Canvas 延迟到实际播放时创建，结束后释放为 1×1，且将只用于“知微”的字体从 40,976 bytes 减为 3,008 bytes。

- 桌面：[觉醒](after/1440-awakening.png)、[汇聚](after/1440-flow.png)、[透镜](after/1440-lens.png)、[五项意象](after/1440-insights.png)、[品牌](after/1440-brand.png)、[穿越](after/1440-transfer.png)、[真实首页](after/1440-complete.png)。
- 平板：[品牌](after/768-brand.png)、[穿越](after/768-transfer.png)。
- 手机：[品牌](after/390-brand.png)、[穿越](after/390-transfer.png)、[完成](after/390-complete.png)。
- 窄屏：[品牌](after/320-brand.png)、[穿越](after/320-transfer.png)、[完成](after/320-complete.png)。
- [录屏](after/intro-demo-desktop.mp4)：1440×900，约 10 秒，采集 400 个实际 Chromium 帧，未生成/插值视频帧。[录制动作与元数据](after/video-manifest.json)。录屏有采集开销，不作为帧率结论。

已逐阶段检查真实截图，并检查录屏中的实际中间帧。未发现整屏闪白/闪黑、转场后封面残留、内容被永久遮挡或停止后仍运行粒子的问题；片头之外的原科学图保持原生。

## 浏览器与功能验收

| 检查 | 结果与证据 |
|---|---|
| 片头专项 | [82/82](after/intro-checks.json)：四宽度完整五阶段、真实粒子运动、字体、测量坐标、透明光圈、时长、释放、重播与固定种子 |
| 交互与回退 | 同一专项覆盖首访、会话返回/刷新、intro=1/0、深链接、浏览器历史、跳过/Escape、连续重播、两类 resize、偏好变化、键盘、存储拒绝、Canvas 故障和脚本缺失兜底 |
| 示例锚点 | [1/1](after/deep-link-check.json)：强制片头后仍是 position/example、位置 20、CI 开启，示例停在约 132px，未重置 URL 或滚动位置 |
| 全站回归 | [278/278](after/site-checks.json)：34 个状态 × 320/390/768/1440；对应 68 张桌面/手机真实页面截图，均无页面横向溢出 |
| 首页原功能 | [82/82](after/home-regression/regression.json)，含章节、筛选、位置/CI、修复播放、CSV/SVG 与图表库往返 |
| 原字体与动态 | [50/50](after/home-regression/motion-checks.json) |
| 数据与研究保真 | [79 个文件逐字节一致](after/content-fidelity.json)，包含原数据、原科学 SVG、业务渲染、统计与快照 |
| 构建与覆盖检查 | 源码构建、资产哈希、来源指纹、全站/片头证据及新增资源预算均通过 |

合计 **493 条检查通过**。可访问性在普通活动对话框、减少动态效果系统及原有代表性页面/弹层检查通过。可见性取消使用模拟 hidden 状态事件测试；没有把这项模拟描述成真实操作系统切换测试。

## 性能结果与限制

[独立帧率诊断](after/frame-performance.json) 在没有截图或录屏干扰时，顺序运行六个真实播放场景。以下为本机无界面 Chromium，不是实体设备/GPU 保证。JS 绘制耗时不含 GPU/合成器的全部成本。

| 视口/条件 | 平均绘制 FPS | P95 JS 绘制 | 数据主图已初始化 | Canvas 像素上限实测 |
|---|---:|---:|---:|---:|
| 1440×900 | 56.8 | 2.3ms | 99ms | 1,296,000 |
| 768×1024 | 58.3 | 2.3ms | 74ms | 786,432 |
| 390×844 | 30.0 | 1.6ms | 72ms | 329,160 |
| 320×740 | 29.9 | 1.5ms | 59ms | 236,800 |
| 手机视口 / DPR 3 | 29.8 | 1.5ms | 84ms | 740,610 |
| 手机视口 / CPU 4× | 29.1 | 3.6ms | 252ms | 329,160 |

所有场景约 5.95–5.98 秒结束，空闲 RAF=0、Canvas 缓冲=1 像素。桌面没有达到每帧严格 60 FPS；在当前软件渲染环境接近目标，仍需真实设备确认。普通手机策略为 30 FPS、92 粒子；桌面为 176 粒子。高 DPI 限制 Canvas 分辨率，原生文字和 SVG 保持清晰。负载较高时降低粒子数量，不延长镜头时间轴。

新增源 JS **24,178 bytes**、CSS **5,315 bytes**、字体 **3,008 bytes**，合计约 **31.7 KiB**；首页冷加载实际增量约 **33.6 KiB**（含 HTML/请求开销）。没有新增大型引擎。

[八次配对 Lighthouse](after/performance-summary.json) 是同机无网络/CPU 节流的诊断：用 `intro=0` 比较原系统的加载，首页两视口均保持 100，图表库为移动 100 / 桌面 99，CLS 全部为 0。该分数不代表首次带片头立即可交互：首访有明确设计的约六秒观看时间，可随时跳过；图表数据在这段时间照常初始化。原图表库大快照与弱网问题仍保持原状。

## 复查、修改列表与本地留存

```sh
PYTHONDONTWRITEBYTECODE=1 python3 app/pipeline/scripts/system/build_web_app.py
node optimization/cinematic-intro/scripts/intro-checks.mjs
node optimization/cinematic-intro/scripts/deep-link-check.mjs
node optimization/cinematic-intro/scripts/site-capture.mjs after
node optimization/cinematic-intro/scripts/site-checks.mjs
node optimization/cinematic-intro/scripts/home-regression.mjs regression
node optimization/cinematic-intro/scripts/home-motion.mjs
node optimization/cinematic-intro/scripts/frame-performance.mjs
node optimization/cinematic-intro/scripts/record-intro.mjs
node optimization/cinematic-intro/scripts/performance.mjs
PYTHONDONTWRITEBYTECODE=1 python3 optimization/cinematic-intro/scripts/finalize-review.py
python3 app/pipeline/scripts/system/check_visual_coverage.py
```

需要当前环境的 Chromium 和 FFmpeg，浏览器工具沿用 `optimization/homepage-pilot/tools`。8785 为 f353a18 的原样基线预览。字体准备脚本依赖 fontTools 4.60.1 / brotli 1.2.1，仅用于重新制备资产；生产构建仍只需 Python 标准库。

实际修改：`app/index.html`、`app/src/intro.js`、`app/intro.css`、两个旧展示控制器、构建器、覆盖检查、`app/visual-coverage.json`、新增字体/元数据、流程说明，以及对应 runtime/dist 构建产物。没有改科学数据、评分、统计、实验结论或原业务路由代码。

实现依据核对了 [requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)、[inert](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/inert)、[CSS mask-image](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/mask-image) 的浏览器文档。真实样例和脚本留存在本目录，原优化成果不覆盖。
