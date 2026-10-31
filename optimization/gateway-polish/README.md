# 知微之门 · 光学材质与全屏研究页

这轮针对用户指出的两个问题：研究页面仍被导航栏占据，以及六球首页的视觉过于生硬。基线为上一版已发布的 `f44a54f93760a8c9a51c1762ace002834c3d670b`，本地备份分支为 `backup/before-gateway-polish-f44a54f`。原研究数据、图表和章节保留。

已推送 main 并部署至 GitHub Pages：[最新预览](https://fwlyii.github.io/data-analysis-frontrefine/?intro=1&v=optical-720f8e1)。222个线上文件逐字节核对和27项线上浏览器检查全部通过。

- [实际检查报告](REPORT.md)
- [生图调用及来源记录](design/provenance.json)
- [候选方向 A/B](design/directions.png)、[实现截图反馈](design/feedback.png)
- [完整优化流程](../../docs/visual-refinement-workflow.md)
- [真实浏览器录屏](after/gateway-demo-desktop.mp4)

首页通过五个真实链接进入 `#question`、`#collection`、`#cleaning`、`#landscape`、`#findings`。这五页的侧栏 DOM 已删除，顶栏隐藏，内容从视口左上角铺满屏幕；右上角仅保留轻量“返回入口”。发现章节、条件选择、表格和导出属于原有研究内容，继续保留。图表库可从首页原入口进入。

桌面采用大小和色调有差别的玻璃球体；手机使用五条完整的玻璃触摸入口。中央透镜、球体、图标和文字仍由 SVG/CSS/HTML 实时呈现。唯一新增运行时位图是独立生成、无文字的约31KB WebP 光学背景。

开场沿用原有5.95秒镜头和 Motion mini，同一组五个链接节点及同一个光学 SVG 完成衔接。搬移节点时显式保留材质色调；研究深链接的品牌落点改为实际可见的返回标记，并渐变为该标记的文字颜色。无需重新制作开场。

## 本地预览与复现

```sh
npm ci --prefix optimization/homepage-pilot/tools
python3 scripts/system/build_web_app.py
python3 -m http.server 8788 --bind 127.0.0.1 --directory app/dist
```

浏览器打开 `http://127.0.0.1:8788/?intro=1`，或使用 `?intro=0` 跳过。减少动态效果设置优先于强制播放参数。

检查需要另一个独立的上一版服务位于8793端口。本机已在修改前保存完整构建。其他机器可在独立工作树构建：

```sh
GIT_LFS_SKIP_SMUDGE=1 git worktree add --detach .git/polish-baseline f44a54f93760a8c9a51c1762ace002834c3d670b
cd .git/polish-baseline
python3 scripts/system/build_web_app.py
python3 -m http.server 8793 --bind 127.0.0.1 --directory app/dist
```

回到主工作目录运行 `python3 optimization/gateway-polish/scripts/run-review.py`。该脚本只进行本地构建、功能检查、独立性能测量、截图录屏和证据更新，不会推送。生图必须真实调用模型，脚本不能伪造；本轮三次调用的完整提示、输入、输出与 SHA-256 已归档。

不要在检查过程中重建应用。`after/` 的全部浏览器结果必须通过，且源文件指纹匹配，才能通过 Pages 发布门禁。性能诊断按顺序独立执行，截图或录屏不用于宣称帧率。
