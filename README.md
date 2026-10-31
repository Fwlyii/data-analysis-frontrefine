# AI对话行为分析 · 可视交互系统

研究输出表达、资料位置与执行反馈对模型表现的影响。五条发现覆盖两条低维、两条多维和一条异常。

```text
README.md
app/                       可运行系统
  launch.py                标准库启动入口
  src/                     前端代码
  pipeline/                采集、清洗、分析、绘图与生成脚本
  results/                 聚合统计与科学图稿
  docs/                    方法、来源与依赖说明
data/
  raw/                     来源与校验清单
  processed/               248,586条匿名物理响应及质量元数据
  data_dictionary.md       字段、单位与缺失原因
report/
  案例报告.pdf
presentation/
  答辩PPT.pdf
  汇报演示_1080P.mp4
```

## 运行系统

`python3 app/launch.py --port 8766`。无API调用、无密钥、无npm，使用本地数据与SVG。预构建运行时也支持直接打开app/index.html。

## GitHub Pages 在线访问

仓库已提供 `.github/workflows/pages.yml`。仓库管理员首次在 **Settings → Pages → Build and deployment → Source** 选择 **GitHub Actions**，然后推送到 `main` 或在 **Actions → Deploy visualization to GitHub Pages → Run workflow** 手动运行。

工作流使用 Python 标准库重新构建网页，只发布 `app/dist/`。部署成功后，网址由 Actions 的部署结果给出；对于当前远程仓库，默认网址预计为 `https://fwlyii.github.io/data-analysis-frontrefine/`。此地址在首次部署成功前不代表已上线。

后续修改 `app/src/`、CSS 或网页数据并推送到 `main`，GitHub 会重新构建和发布；等待工作流成功后刷新同一网址。只修改本地文件不会更新线上页面。Pages 托管的是静态网页，Python 数据分析和模型采集程序不在网站上运行。

账号与仓库可见性需要符合 GitHub Pages 的使用条件；部署过程不会修改仓库的公开/私有设置。配置和排查步骤见 [部署说明](app/docs/github-pages.md)。

## 复算

`python3 app/pipeline/scripts/reproduce_anonymous.py`，从匿名数值表重算五类实验的条件汇总。加`--figures`重绘主图，需安装app/pipeline/requirements/analysis.txt和Times New Roman。文档重绘另需documents.txt。

系统支持条件切换、九个证据位置选择、版本播放、完整图表库与匿名记录联动。CSV/SVG可下载。不同任务评分按metric_name分别解释；修复共享初稿只计一次。

原始全文和源ID映射不进入本匿名目录，完整项目保留这些材料。外层文件夹可按学校要求填写真实学号姓名。
