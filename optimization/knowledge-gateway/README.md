# LENS · 知微之门

本轮在已完成的开场上开发默认导航首页。本地验收完成后，用户已明确授权将本版推送到 main 并通过 GitHub Pages 预览；Pages 已部署成功，221个线上文件比对和22项线上交互检查全部通过。

## 线上预览

[完整开场与知微之门](https://fwlyii.github.io/data-analysis-frontrefine/?intro=1&v=knowledge-gateway) · [直接看主页](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0&v=knowledge-gateway)。线上截图及验证结果见 [REPORT.md](REPORT.md#发布与线上复核)。

## 本地预览

```sh
python3 scripts/system/build_web_app.py
python3 -m http.server 8788 --bind 127.0.0.1 --directory app/dist
```

打开 `http://127.0.0.1:8788/?intro=1` 看开场及接续；`?intro=0` 直接看导航空间。系统减少动态效果设置优先于强制开场。浏览器需能访问开发服务器；远程开发时可通过 SSH 将服务器8788端口转发到本机。

## 真实路由映射

| 球体 | 原有入口 | 路由 |
| --- | --- | --- |
| 研究问题 | Research Question，原首页的研究问题内容 | `#question` |
| 采集设计 | Collection Design | `#collection` |
| 数据处理 | Data Pipeline | `#cleaning` |
| 数据全景 | Data Landscape | `#landscape` |
| 核心发现 | Core Findings | `#findings` |

新增 `#gateway` 只承载导航空间，空 hash 默认进入该空间。五个原入口及研究深链接保持有效。图表库继续使用 `explore.html`，页眉保留图表库、重播和全屏。内部研究页保留原五章导航，并提供返回知微之门的按钮。

## 连续性实现

`gateway.js` 在开场开始时借用首页**同一组五个真实链接 DOM 节点**，将它们放到开场覆盖层。它们从五个研究意象附近的微光汇聚成五个点，在5.06–5.95秒沿连续轨迹展开为球体，最后放回各自首页位置。链接节点没有被图片、克隆或另一套加载动画替代。

中央沿用原开场的**同一个 `.intro-optics` SVG 元素**及其96个刻度。只调整原开场最后的落点：导航首页落入中央透镜，研究深链接仍使用原来的页眉品牌转场。开场结束时将该 SVG 移交给首页；重播时再还给原 LensScene。早期跳过会将光环补到完整状态，失败时保留静态 SVG 回退。

首页微幅椭圆漂移由已存在的 Motion mini 驱动；悬停/键盘聚焦暂停对应球体的漂移并增强高光。点击时移动同一个链接到中央焦点，等待有限动画完成后调用真实 `LENS_GO_TO`。原生 href 保留修饰键新开页面及脚本不可用时的链接语义。用户离开首页、切换标签或启用减少动态效果后停止背景运动。

手机布局采用独立双列网格和第五个居中入口，透镜置顶；小屏可以纵向滚动，入口不被强行缩小。Tab、Enter、方向键及 Home/End 支持键盘访问。

## 文件

- `app/src/gateway.js` / `app/gateway.css`：共享场景、五球导航、材质与响应式布局。
- `app/index.html`：真实链接、中央透镜回退、辅助入口；原研究内容保留。
- `app/src/intro.js`：接入共享场景，原电影镜头、时间轴与降级逻辑继续使用。
- `app/src/narrative.js` / `app/src/story.js`：新增默认 gateway 路由及返回入口，保留五个研究入口和旧深链接。
- `scripts/system/build_web_app.py`：复制与指纹化新增模块和样式。
- `app/visual-coverage.json` / `scripts/system/check_visual_coverage.py`：93状态的更新证据和门禁。

## 检查

浏览器工具沿用仓库锁定依赖 `optimization/homepage-pilot/tools`，使用本机 `/snap/bin/chromium`。`before/intro-audit.json` 是修改前真实播放审查；`after/` 是本轮截图、录屏与测试结果。历史优化目录保持原样。

完整测试与修改说明见 [REPORT.md](REPORT.md)。源码对照、65个原有演示状态的图形/文字对照、93状态×5尺寸渲染、交互、可访问性及开场异常路径分别保存为 JSON。测试时不重建 dist，帧率与 Lighthouse 单独顺序运行。

`scripts/run-review.py` 会顺序执行整套本地检查并刷新发布门禁证据，不执行任何远程写入。比较前需独立提供旧版基线到8792端口；本轮基线是开始修改前保存的 aa3116d 构建。新机器可建立本地 worktree 复现：

```sh
git worktree add --detach .git/gateway-baseline aa3116d
cd .git/gateway-baseline
python3 scripts/system/build_web_app.py
python3 -m http.server 8792 --bind 127.0.0.1 --directory app/dist
```

回到当前工作区，确保8788端口服务当前 app/dist 后，执行：

```sh
python3 optimization/knowledge-gateway/scripts/run-review.py
```

这些步骤会清理并重建可再生成的 runtime/dist，不应在另一轮浏览器检查进行时运行。原数据、源码和参考截图均不应手工改动来使检查通过。
