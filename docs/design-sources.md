# 设计与第三方来源

| 来源 | 使用范围 | 本地许可或记录 |
|---|---|---|
| [Relay](https://relay-sage-sigma.vercel.app/) | 首屏色调、衬线标题、稀疏排版与统计节奏的视觉参考 | 本地纹理和路径为原创SVG，未引入站点代码或图片 |
| [AI Design Skills](https://github.com/elayadesign/ai-design-skills) | 字体层级、间距、焦点状态和窄屏检查 | MIT；app/templates/ai-design-skills-LICENSE.txt；参考版本4fdcdd52f15eda09da1257c303c860c13e0c879f |
| [Geist](https://github.com/google/fonts/tree/main/ofl/geist) | 本地UI字体400/500/600/700 | app/assets/fonts/Geist-OFL.txt |
| OpenWAM | 研究图形的表达参考 | 按本项目真实数据生成图形 |

主页结构、SVG主图和交互来自交付前端，已整合到统一构建。主图模块app/src/story-charts.js与课程图表库模块app/src/charts.js分别维护。

ECharts、D3、Vega-Lite、Plotly用于课程图表库。本地版本、校验和许可见app/assets/vendor/visualization-libraries.json。保留的Scrollama资源供模板溯源，当前主展示不加载它。字体与依赖均从本地读取。

知微之门的玻璃球体、中央透镜、图标与文字由本项目的 HTML/CSS/SVG 实现，动画复用本地 Motion mini。`app/assets/visual/gateway-atmosphere.webp` 是通过 `image_gen.imagegen` 独立生成的无文字装饰背景，再用 ffmpeg 转为 WebP；不包含研究图表、数值或交互入口。三次实际生图的提示、输入与输出记录见 `optimization/gateway-polish/design/provenance.json`。生成稿只用于视觉参考，科研内容继续取自原系统。

## 2026-10-31 全站闭环

本轮素材、评分、逐页覆盖与发布验证收于 `optimization/fullsite-closed-loop-20261031/RESULT.md` 与 `gallery.html`。实际调用内置 image_gen 生成两套研究/分析/图表库视觉方向、首页桌面/手机参考、五个独立透明玻璃星球及真实实现截图反馈；原始提示、输入、输出及 SHA-256 在该目录 `design/provenance.json`。五个运行时装饰为 `app/assets/visual/planet-{question,collection,cleaning,landscape,findings}.webp`，真实 alpha、512px、静态图像；它们留在原五个链接节点内，普通文字与图标仍为原生。所有科学图表、数据、原科学绘制源码保持519文件保护清单中的字节。

继续实际复用本地 Motion mini 14.9.0 的 keyframe/WAAPI 动效驱动五个原链接轨迹与点击聚焦飞行。已从 [motiondivision/motion](https://github.com/motiondivision/motion/tree/7415b6cd14dfdb35d91dfc5b9758994444cc228b) 验证 v14.9.0 对应 commit `7415b6cd14dfdb35d91dfc5b9758994444cc228b` 与 MIT 许可，并归档官方 animateMini interruption 示例和许可，详见本轮 `assets/motion-source.json`。复用位置为 `app/src/gateway.js` 的 animate/sync/navigate/cancelIdle；新增透明素材随同一节点运动，没有新增依赖。


## 电脑录制版内容布局

当前布局来源及实现对照见 `optimization/content-layout-20261101/design/provenance.json` 和该目录 `gallery.html`。本轮5次真实内置生图分别覆盖问题页、方法与图表库、分析页、实际实现反馈、出版与更多发现。输入截图、提示和生成输出均固定SHA-256。新增布局层为`app/content-layout.css`；普通文字、分区、SVG图标和细线材质用代码实现，没有新增运行时生成位图，没有新增前端框架或动画依赖。现有Motion mini和五个静态透明装饰资产继续使用。

本轮以1920×1080电脑录屏为主，92个内容状态采用实际新布局，527个原有代码/数据/图稿/字体文件保护。模型改画的科研图、虚构页面或修改过的数据均未采用。实际实现与生成参考的差异、可读性量测及标准位置科学图形对照有独立记录。
