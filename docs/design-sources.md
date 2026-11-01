# 设计与第三方来源

| 来源 | 使用范围 | 本地许可或记录 |
|---|---|---|
| [Relay](https://relay-sage-sigma.vercel.app/) | 首屏色调、衬线标题、稀疏排版与统计节奏的视觉参考 | 本地纹理和路径为原创SVG，未引入站点代码或图片 |
| [AI Design Skills](https://github.com/elayadesign/ai-design-skills) | 字体层级、间距、焦点状态和窄屏检查 | MIT；app/templates/ai-design-skills-LICENSE.txt；参考版本4fdcdd52f15eda09da1257c303c860c13e0c879f |
| [Geist](https://github.com/google/fonts/tree/main/ofl/geist) | 本地UI字体400/500/600/700 | app/assets/fonts/Geist-OFL.txt |
| OpenWAM | 研究图形的表达参考 | 按本项目真实数据生成图形 |

主页结构、SVG主图和交互来自交付前端，已整合到统一构建。主图模块app/src/story-charts.js与课程图表库模块app/src/charts.js分别维护。

ECharts、D3、Vega-Lite、Plotly用于课程图表库。本地版本、校验和许可见app/assets/vendor/visualization-libraries.json。保留的Scrollama资源供模板溯源，当前主展示不加载它。字体与依赖均从本地读取。

## 当前原创素材与动效

知微之门的中央透镜、图标、文字和开场由原生代码实现，交互复用本地 Motion mini 14.9.0。许可与版本记录位于 `app/assets/vendor/`。

`app/assets/visual/gateway-atmosphere.webp` 和五个 `planet-*.webp` 为先前实际调用生图模型制作的静态装饰素材，不包含科研数据或交互文字。必要来源记录保留在[素材来源](provenance/README.md)；完整旧设计迭代可从Git提交 `c3d648a` 查询。

现有电脑布局使用 `app/content-layout.css`，统一配色使用 `app/palette.css`，新交互使用 `app/interaction.css` 与 `app/src/interaction.js`。真实科研图由原组件与冻结快照绘制，始终不采用模型改画的数值、坐标或结论。历史截图、视频及未采用设计稿按用户要求清理，运行时素材与第三方许可证原样保留。
