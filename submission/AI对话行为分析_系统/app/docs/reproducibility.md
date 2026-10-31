# 复算说明

## 只运行系统

`python3 app/launch.py --port 8766`。标准库即可，构建使用已有JSON/SVG；不需要模型密钥、网络或npm。

## 全量数据管道

Python3.12环境安装`requirements/analysis.txt`和`requirements/documents.txt`。先运行`python3 scripts/pipeline.py all --plan`查看命令。分阶段为clean、analyze、figures、web、documents、submission；全部为离线数据操作，不触发采集，也不重新执行模型代码。

- clean：405个不可变源制品校验→原两方向解析→新三方向记录清洗→统一匿名表。
- analyze：保留原评分，做题目级配对比较和原定分组；文档位置与修复各自分析。
- figures：科学母版、代码图稿、五章主图；需合法Times New Roman。文档中文字体可用COURSE_CJK_FONT_FILE指定本地TrueType文件。
- web：标准库打包当前数据、主图和完整图表库。
- documents：当前10页报告与12页答辩PDF，原历史材料仍在archive。
- submission：生成课程目录树与匿名版系统。

`reproduce_baselines.py`保留原基线的匿名/全本地重算方式；它只覆盖原问答和独立代码生成，不冒充新增文档位置/修复的完整管道。

## 只有匿名提交数据

`python3 scripts/reproduce_anonymous.py`可从248,586条数值特征重算五方向全部条件汇总，输出reports/reproduced。加`--figures`可从保存CSV重绘五章SVG并构建系统。匿名数值不能重构全文、重新判断语义、重新跑代码或重新生成模型回答。

## 重新采集与重新评分

采集位于scripts/acquisition，默认计划/干跑；只有--execute才发送请求。文档位置和修复使用新批次，不改冻结数据。推理入口是根据保存材料重建的版本，原包没有交付历史采集器。

代码生成完整重测需要原CodePromptEval中34个项目的依赖环境；源评价脚本保留在experiments/code_generation/src，日常统计使用保存的target-function-ast-v2结果。代码修复的实际采集/执行依赖macOS沙箱，离线分析不调用该执行路径。新的API采样不属于本次整理。
