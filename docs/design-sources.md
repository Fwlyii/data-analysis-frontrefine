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
