# LENS 视觉与交互

当前版本沿用已发布 LENS 浅蓝青视觉：全站背景 #f4f8fa、白色图纸、深蓝正文 #203b50、青色强调 #147b7b；深海蓝仅用于约 5.95 秒纯代码电影开场。UI 使用本地 Geist，英文标题和科学图采用 Times New Roman，中文展示标题提供本地 LENS Editorial 字体，代码使用系统等宽字体。独立生成的品牌艺术字与透明光学装饰保持为非信息素材；控件、文案和数据图全部原生可编辑。

五部分共用章节导航，桌面为左侧栏，窄屏为底栏。章节通过导航切换，长内容在当前面板内滚动。发现部分用结论、关键数字、主图和必要控件组织；完整案例、数据表及方法按需展开。

主图由app/src/story-charts.js读取冻结统计生成可编辑SVG。位置曲线连接九个实测位置，修复曲线连接初稿及四次修改；置信区间沿用保存结果。31提示全貌按任务和模型分别显示，热图支持鼠标或键盘选择条件，显示分数、Token与题目数。

URL保存发现和全貌筛选，支持刷新恢复。播放可暂停，SVG/CSV导出同当前条件。键盘焦点可见，动效遵循减少动态效果偏好。完整课程图形与匿名记录联动集中在explore.html。来源和实现说明见docs/design-sources.md。

共享视觉基础为 `app/site.css`；新版五部分展示用 `app/deck.css` 适配侧栏/底栏布局，图表库用 `app/styles.css`。两个页眉由模板生成，`app/src/story-motion.js`、`site-shell.js` 分别负责展示与图表库有限动效，`intro.js` 负责可重播/跳过的实时开场。迁移流程和完整验收见 `docs/visual-refinement-workflow.md`、`optimization/master-migration-v4/REPORT.md`。
