# LENS 视觉与交互

当前视觉由 v5 生图参考与真实网页反馈共同确定：统一深蓝框架 #0b1f33、浅色主文字 #e8f0f7、辅助文字 #a7c4d6 与青色 #6dd1c4；数据图纸为 #f8fbff，文字为深蓝 #1e3a56、纸面强调 #0e7c7b。开场、页眉、导航及内容背景使用同组变量，科学模型/策略编码保持区分。UI 使用本地 Geist，英文展示和科学图采用 Times New Roman，中文标题使用已有 LENS Editorial 字体。品牌采用 Master 原生文字，保留可访问名称。首页恢复 Master 路径/地形插画关系，仅改装饰色，不更改研究内容。

五部分共用章节导航，桌面为左侧栏，窄屏为底栏。章节通过导航切换，长内容在当前面板内滚动。发现部分用结论、关键数字、主图和必要控件组织；完整案例、数据表及方法按需展开。

主图由app/src/story-charts.js读取冻结统计生成可编辑SVG。位置曲线连接九个实测位置，修复曲线连接初稿及四次修改；置信区间沿用保存结果。31提示全貌按任务和模型分别显示，热图支持鼠标或键盘选择条件，显示分数、Token与题目数。

URL保存发现和全貌筛选，支持刷新恢复。播放可暂停，SVG/CSV导出同当前条件。键盘焦点可见，动效遵循减少动态效果偏好。完整课程图形与匿名记录联动集中在explore.html。来源和实现说明见docs/design-sources.md。

共享视觉基础为 `app/site.css`；新版五部分展示用 `app/deck.css` 适配侧栏/底栏布局，图表库用 `app/styles.css`。两个页眉由模板生成，`app/src/story-motion.js`、`site-shell.js` 分别负责展示与图表库有限动效，`intro.js` 负责可重播/跳过的实时开场。迁移流程和完整验收见 `docs/visual-refinement-workflow.md`、`optimization/render-unification-v5/REPORT.md`。
