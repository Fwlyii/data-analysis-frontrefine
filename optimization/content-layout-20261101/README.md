# 内容布局详细优化 · 电脑录制版

本轮由用户明确指出上一轮内容页字号小、留白失衡、布局单调而启动。用户随后明确：最终使用电脑录制，主要优化电脑端。主目标为1920×1080，另外检查1440×900、2560×1440、1600×900与1366×768。

上一轮按布局类型给原版较高预设分，导致184个内容状态/设备组合保留原布局。这个方法没有有效识别阅读问题。本轮不再用高预设分作为不改版的理由：全部92个内容状态采用真正的布局与字体改造，入口与开场继续保留。

## 实现与证据

- [详细报告](REPORT.md)、[进度](STATUS.md)、[逐页前后与设计稿账本](coverage-table.json)、[对照画廊](gallery.html)
- [真实生图来源与完整提示](design/provenance.json)、[设计评审与实际差异](design/visual-review.json)
- [实际字号与操作边界](after/readability-checks.json)、[1080p/QHD专项](after/desktop-recording-checks.json)
- [科学图形对照](after/chart-render-preservation.json)、[源文件保护](after/preservation.json)、[实际导出](after/export-checks.json)
- [全电脑演示录屏](after/intro-demo.mp4)

`app/content-layout.css` 是本轮共享的内容布局层，源码入口和构建流程已接入并做缓存指纹；不直接编辑dist。研究页不恢复原侧栏或顶栏。图表源码、数据、字体文件、科学配色和SVG几何保留，控制区与文字在图形外围重新组织。新增三条研究维度的解释性文案，原标签、说明与统计文字继续保留。

## 运行与复现

```sh
python3 scripts/system/build_web_app.py
python3 -m http.server 8828 --bind 127.0.0.1 --directory app/dist
```

打开 `http://127.0.0.1:8828/?intro=0#question` 直接检查用户指出的问题页。完整开场仍可通过 `?intro=1` 观看。

完整审查依赖另一个冻结基线服务在8829端口。本轮基线为860eb9c2a56a0c5051988efee3c76d9a77d2a899。当前机器的冻结产物在 `.git/content-layout/baseline-dist/`；其他机器可用独立工作树构建该提交。不要在浏览器检查过程中重建当前dist。

浏览器工具使用 `optimization/homepage-pilot/tools` 中锁定的Playwright/Axe/Lighthouse依赖，Chromium为 `/snap/bin/chromium`，诊断裁剪/压缩使用FFmpeg。所有生产页面只需要静态HTTP服务器和原有本地数据，不加载这些检查依赖或录屏。

```sh
python3 optimization/content-layout-20261101/scripts/run-review.py
```

该脚本只做本地审查，不推送。真实生图调用不能由截图脚本替代；五次调用的输入和输出已保存。已有手机回归检查仅用于兼容性保障，本轮设计、新增截图、可读性、图形对照与录制验收均以电脑为主。
