# 设计与第三方来源

当前配色、品牌与光学装饰沿用已发布 LENS 视觉优化版本。下表保留 Master 原交付的设计溯源；本轮迁移不再沿用其中的深色/陶土配色。

| 来源 | 使用范围 | 本地许可或记录 |
|---|---|---|
| [Relay](https://relay-sage-sigma.vercel.app/) | 首屏色调、衬线标题、稀疏排版与统计节奏的视觉参考 | 本地纹理和路径为原创SVG，未引入站点代码或图片 |
| [AI Design Skills](https://github.com/elayadesign/ai-design-skills) | 字体层级、间距、焦点状态和窄屏检查 | MIT；app/templates/ai-design-skills-LICENSE.txt；参考版本4fdcdd52f15eda09da1257c303c860c13e0c879f |
| [Geist](https://github.com/google/fonts/tree/main/ofl/geist) | 本地UI字体400/500/600/700 | app/assets/fonts/Geist-OFL.txt |
| OpenWAM | 研究图形的表达参考 | 按本项目真实数据生成图形 |

主页结构、SVG主图和交互来自交付前端，已整合到统一构建。主图模块app/src/story-charts.js与课程图表库模块app/src/charts.js分别维护。

ECharts、D3、Vega-Lite、Plotly用于课程图表库。本地版本、校验和许可见app/assets/vendor/visualization-libraries.json。保留的Scrollama资源供模板溯源，当前主展示不加载它。字体与依赖均从本地读取。

## 当前视觉迁移

- 独立生成的光学装饰与 LENS 品牌艺术字复用上一版本，提示词和图稿见 `optimization/homepage-pilot/`、`optimization/type-motion-v2/`。本轮两方向及手机修订使用内置 image_gen，均为设计参考，不作为运行界面；见 `optimization/master-migration-v4/design/prompts.json`。
- 本地 Noto Serif CJK 子集的来源和制作记录见 `app/assets/visual/type-motion-manifest.json`、`site-manifest.json`、`intro-manifest.json`，SIL OFL 许可位于 `app/assets/fonts/Noto-CJK-OFL.txt`。
- Motion mini 14.9.0 复用已有本地资源，MIT 许可位于 `app/assets/vendor/motion-mini-14.9.0-LICENSE.txt`。章节、导航和弹层有限播放并尊重减少动态效果；开场的 Canvas/SVG/原生文字实时绘制，审阅录屏不随页面加载。

## v5 内容对齐与颜色统一

最新规范见 `docs/visual-refinement-workflow.md` 和 `optimization/render-unification-v5/REPORT.md`。本轮使用 image_gen 生成两套“页面 + 开场”设计板，再以真实首版首页截图做定向修订；提示词位于 `optimization/render-unification-v5/design/prompts.json`。选择深蓝框架、青色强调与浅色科学图纸。首页恢复 Master 原有路径/地形插画，生产颜色副本只改十六进制颜色字面量，坐标与形状保持原样，来源/哈希记录于 `app/assets/visual/v5-manifest.json`。品牌按 Master 使用原生文字，开场 Canvas 与 SVG 从共享颜色变量取色。
