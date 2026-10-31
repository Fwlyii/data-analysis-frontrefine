# Master 重新开始 · 第六轮

本轮先重新克隆原仓库 Master，再恢复 main，重新完成全站截图、生图设计、Codex 实现、真实截图反馈和详细检查。

- [完整流程](../../docs/visual-refinement-workflow.md)
- [Codex 实现任务单](codex-implementation-brief.md)
- [本轮检查报告](CHECK-REPORT.md)
- [页面清单](site-inventory.json)
- [候选方案 A/B](design/candidates-a-b.png) 与 [实际截图反馈稿](design/screenshot-feedback.png)
- [第一次完整提示](design/proposal-prompt.txt) 与 [第二次完整提示](design/iteration-prompt.txt)
- `before/` 保存重新克隆的 Master 基线截图；`after/` 保存当前版本真实浏览器截图、导出文件和检查 JSON。

生产入口仅 `app/index.html` 和 `app/explore.html`。此目录是开发审查材料，不会作为产品内容上传到 Pages。

## 复现浏览器检查

安装 `optimization/homepage-pilot/tools/package-lock.json` 锁定的检查依赖：

```sh
npm ci --prefix optimization/homepage-pilot/tools
python3 scripts/system/build_web_app.py
python3 -m http.server 8788 --bind 127.0.0.1 --directory app/dist
```

准备并在另一个终端启动**独立构建的原 Master**：

```sh
python3 optimization/master-rebuild-v6/scripts/prepare-baseline.py
python3 -m http.server 8790 --bind 127.0.0.1 --directory .git/master-rebuild-v6/baseline/app/dist
```

脚本固定源提交 `35f7318e45561da07c75eaf65374e4107004d5ec`，核对三个网页用 LFS 数据集的 SHA-256 后构建。`fidelity.py` 读取 `.git/master-rebuild-v6/upstream` 中的重新克隆源码；部署门禁读取已经保存的结果，不依赖本地 `.git` 工作目录。不要在测试进行时重建基线或当前 dist。

本机使用 `/snap/bin/chromium`。其他环境需调整检查脚本的浏览器可执行路径。下载目录需在 Chromium 可写范围。运行：

```sh
python3 optimization/master-rebuild-v6/scripts/run-review.py
```

该命令依次构建、核对数据/原版、逐页检查、测试交互与开场、测性能、录制和生成证据清单。生图步骤需要真实调用 imagegen 技能，不能通过脚本伪造；完整输入、实际输出及选择记录已保存在本目录。`--functional-only` 只重跑功能，不替代完整发布审查。

`app/visual-coverage.json` 记录被审查源码的哈希。提交前运行 `python3 scripts/system/check_visual_coverage.py`。任何生产源码变动都需要重跑相关浏览器检查并重新生成清单。
