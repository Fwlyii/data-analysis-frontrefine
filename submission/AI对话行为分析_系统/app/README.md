# LENS 可视交互系统

在项目根目录执行：

```bash
python3 app/launch.py --port 8770
```

启动器用Python标准库构建本地快照并提供HTTP服务。构建后也可直接打开app/index.html或app/dist/index.html离线演示。

主页包括Research Question、Collection Design、Data Pipeline、Data Landscape、Core Findings。主展示使用英文；图表库保留中文研究内容。五发现覆盖两低维、两多维和一异常，支持条件切换、九位置选择、五版本播放、实际案例及SVG/CSV导出。全貌页覆盖推理372、文档问答186、代码生成93个提示条件。

| 文件 | 用途 |
|---|---|
| index.html / story.css | 主展示结构与样式 |
| src/narrative.js | 研究设计、清洗与31提示全貌 |
| src/story.js | 五发现、案例、版本控制及导出 |
| src/story-charts.js | 从冻结统计生成可编辑SVG主图 |
| explore.html / styles.css | 课程图表库 |
| src/charts.js及其他模块 | 图表库、匿名记录和交互联动 |
| data/ | 冻结特征、分组证据与精选案例 |
| assets/ | 字体、图标、图稿与本地依赖 |
| runtime/ / dist/ | 从源码生成的运行文件 |

修改src后执行python3 scripts/system/build_web_app.py或重新启动服务。runtime由构建生成；story-charts.js与图表库的charts.js分别维护。

```bash
python3 scripts/system/check_web_snapshot.py
```

检查会重建快照、验证本地资源与三个任务31提示的数据接入。系统启动只需Python；若已安装Node，还会检查JS语法和SVG数值绑定。设计来源和许可证见../docs/design-sources.md。
