# LENS · 知微

研究提示表达、证据位置和执行反馈如何影响模型表现。系统使用保存的匿名研究快照，包含五个研究章节、五项发现、13类图表及4个代码研究视图。

[在线预览](https://fwlyii.github.io/data-analysis-frontrefine/) · [项目与研究概述](docs/project-summary.md) · [目录说明](docs/repository-structure.md) · [录制提交指南](docs/submission.md)

## 启动系统

```bash
python3 app/launch.py --port 8770
```

在浏览器打开 `http://127.0.0.1:8770`。运行网站只需 Python 标准库，不需要 npm、API Key 或后端服务。首页可进入五章研究和图表库；支持真实条件筛选、记录查看、CSV/SVG导出及交互动效。

## 目录

```text
app/             网站源码、现用素材与匿名快照
configs/         实验协议与配置
data/           原始来源、清洗数据、质量与字段说明
experiments/     专项实验代码
reports/         科研统计、置信区间和科学图稿
scripts/         采集、清洗、分析、绘图、构建与文档生成
tests/          当前浏览器测试及必要的小型基线
docs/           使用、研究、部署和维护说明
report/          保留的参考报告（PDF与文稿）
presentation/    保留的参考PPT（PDF与讲稿）
requirements/    按用途划分的Python依赖
```

`reports/` 是科研证据，`report/` 是参考报告，两者用途不同。`app/runtime/`、`app/dist/`、`artifacts/` 是可重新生成的目录，不提交到Git。

## 检查与维护

```bash
python3 scripts/system/check_web_snapshot.py
python3 scripts/system/check_visual_coverage.py

# 自动浏览器测试才需要Node；首次安装测试依赖和浏览器
npm ci --prefix tests
npm run browser:install --prefix tests
python3 tests/run.py           # 发布前的93状态检查
python3 tests/run.py --full    # 全量交互与响应式回归
```

测试默认不录制视频、不保存截图。临时结果只写入 `artifacts/qa/`；需要临时截图时可设置 `QA_SCREENSHOTS=1`。更详细的说明见 [检查说明](docs/web-checks.md)与[前端维护流程](docs/visual-refinement-workflow.md)。

## 课程提交

最终人工录制并提交一个演示视频。报告和PPT留作参考，不再自动生成完整提交包，也不在仓库保存录像、旁白、字幕和历次优化截图。录制顺序见[录制提交指南](docs/submission.md)。

科研数据、图表、统计结果与现用前端素材继续保留。过往优化过程可从Git历史查询；整理前版本为 `c3d648a`，备份分支为 `backup/before-repository-cleanup-c3d648a`。
