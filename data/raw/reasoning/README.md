# reasoning 固定来源输入

来源仓库：[Fwlyii/dataAnalysis-vision](https://github.com/Fwlyii/dataAnalysis-vision)。分支 `reasoning`，固定提交 `4133f88dfe9a9604a2e33098feeb32e8147024b3`；源目录为 [data/compressed-cot-20261020](https://github.com/Fwlyii/dataAnalysis-vision/tree/4133f88dfe9a9604a2e33098feeb32e8147024b3/data/compressed-cot-20261020)。

下载已有的 `responses_source.zip`，保留压缩包，不必解压。预期 SHA-256：

```text
b921ae2e9597d458dbd0778f29806b17635adc81031012591718a10abc301165
```

可以从固定目录的文件页下载，也可以在具备来源访问权限的机器上取得固定提交：

```bash
git clone --branch reasoning --single-branch https://github.com/Fwlyii/dataAnalysis-vision.git work/source-reasoning
git -C work/source-reasoning checkout 4133f88dfe9a9604a2e33098feeb32e8147024b3
```

原始 ZIP 最终放在 `data/raw/reasoning/responses_source.zip`。`cleaning/verify_source_inputs.py` 可接收整个来源 checkout 或下载的 ZIP；与 document_qa 一起准备的命令见 [document_qa/README.md](../document_qa/README.md)。脚本会先核验全部必需输入，校验失败则停止，且不会覆盖不同内容的原始文件。

原始快照为 74,400 条回答，四个模型、31 种提示策略、三组各 200 道题。当前分析保留源评分与复核状态。源说明把 `mmlu` 称为 MMLU-Pro 数学部分，但缺少可逐条核验的 subject 字段，因此应用只标注为 MMLU-Pro 选择题，不把数学子集当作已核实事实。历史说明与 [数据概况.json](数据概况.json) 保留为来源证据。

本路径只读取保存的实验结果；无需 API 密钥或重新采集。
