# Codex 实现交接单 · v6

## 输入与选择

- 内容源：Master `35f7318e45561da07c75eaf65374e4107004d5ec`；恢复检查点 `73a1e8c`。
- 第一轮输入：before/home-desktop.png、design-desktop.png、library-desktop.png。
- 完整提示：design/proposal-prompt.txt；实际生成稿：design/candidates-a-b.png。
- 选择 A：Warm Editorial Observatory。保留原有深蓝/暖纸双色结构；拒绝生成稿中给图表库额外添加侧栏的做法。
- 第二轮输入：实现后的首页/发现页桌面截图、首页/图表库手机截图；完整提示 design/iteration-prompt.txt；实际输出 design/screenshot-feedback.png。

## 实施范围

1. `app/refinement.css`：本地 Fraunces 标题、Geist 界面；深蓝 #071e30、纸色 #f5f2eb、铜色 #a34f36。首页字号、轨道安全区、标题间距；五部分内容维持原结构。图表库复用同一份呈现层，72px 深蓝顶栏、手机两行导航。
2. `app/src/refinement.js`：表格键盘滚动入口、手机图表提示、380ms 有限过渡。减少动态效果时取消；快速切换时取消旧动画，避免叠加。
3. `app/src/intro.js` / `intro.css`：复用已验证的纯代码引擎，迁移为独立 intro 配色变量；同步标题字体、顶栏落点及容器坐标，不引入旧版 site.css。
4. `app/index.html`：最小品牌包裹、重播按钮、可聚焦主容器、早期启动与1800ms故障揭幕保护。图库 `explore.html` 不能加载开场模块。
5. `app/src/narrative.js`：只给导航按钮绑定 data-section，避免 body 冒泡重置滚动。横向数据区域和开场期间不能被全局方向键抢走。
6. `scripts/system/build_web_app.py`：复制并指纹化新增 CSS/JS；原有数据与研究快照构建流程保留。

## 约束

不改数值、科研结论、数据快照、图表图形函数、系列配色和原有 URL 参数。不将生成稿变为整页截图网站，不将生成字形替换为不可访问的图片文字。所有字体、模块与授权文件放进仓库，线上没有字体 CDN 依赖。图表在手机内滚动，不压缩到无法阅读。

## 截图反馈的实际修改

第二轮保留已实现的文字与图表容器；将桌面轨道改为 contain 并留右侧安全边距，手机轨道放到下半部，避免穿过三个研究方向的说明；整理筛选器层级。生成稿的图表数值与几何不用于生产，继续使用 Master 原始图形。

## 验收

详见 docs/visual-refinement-workflow.md、scripts/run-review.py 和最终 CHECK-REPORT.md。先完成代码再测；浏览器检查时不重建 dist。帧率与 Lighthouse 独立顺序执行。必须核对线上发布提交与本地资源内容。
