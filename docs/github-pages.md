# GitHub Pages 发布

仓库：<https://github.com/Fwlyii/data-analysis-frontrefine>，发布分支 `main`。

预览：<https://fwlyii.github.io/data-analysis-frontrefine/>。

推送 main 后，`.github/workflows/pages.yml` 用 Python 构建 `app/dist`，检查绑定当前源码的全站审查证据，然后上传静态产物并发布。只有对应提交的工作流成功，网站才完成更新；刷新不会跳过构建和部署过程。

常用入口：

- `?intro=1`：强制查看开场，仍尊重系统“减少动态效果”。
- `?intro=0`：直接看首页。
- `explore.html?mode=explore#case-1`：图表库。

站点当前使用静态研究快照，没有常驻后端。页面字体、图标、图表库脚本全部随站点发布。审查录像和生图设计稿保留在源码仓库的 optimization 目录，不进入网页运行包。

详细更新和检查要求见 [视觉优化流程](visual-refinement-workflow.md)。
