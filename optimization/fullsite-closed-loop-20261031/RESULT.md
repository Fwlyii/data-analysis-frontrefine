# 知微之门至图表库：全站视觉闭环结果

已完成发布与线上复核。

基线为 `f751c3fe2db5a977f63d394ca185d09bc3ef8132`。未使用子代理，未调用需要API Key的替代生图流程；未修改运行器和独立完成校验器。

## 交付与实际范围

从真实源码重新提取93个路由状态，覆盖入口、3个介绍/方法页、18个数据全景条件、44个发现条件、4个论文图状态、4个代码视图、5个发现章节、13类图表及1个有意空状态。每路由桌面1440×900和手机390×844均有本轮前后截图，共186行逐页账本；另外在320、768、1366宽度检查。共有157组配对展开/长内容状态，含抽屉、真实案例、方法、数据表、导出菜单和中/底部滚动。

[可筛选前/参考/后画廊](gallery.html) · [逐页评分与采用/保留原因](coverage-table.json) · [详细分项和还原评审](design/visual-scores.json) · [展开状态清单](overlays.json) · [全部文件清单](changed-files.json)

## 生图、选择与落地

实际调用内置 `image_gen.imagegen` 14次。两套方向覆盖研究、分析及图表库各布局；另有入口桌面/手机稿、五个独立透明资产以及真实实现截图反馈。所有提示、输入、实际生成输出、运行资源及SHA-256见[生图来源](design/provenance.json)，候选量表与拒绝理由见[候选评分](design/candidate-scores.json)。没有用HTML截图或旧稿冒充模型输出。

采用A的深蓝、象牙白、铜色和光学玻璃语言。B的冷白青色、无衬线标题与额外手机菜单破坏既有品牌，因此拒绝。科研内容页的生成稿未比原版高至少5分，保留原布局与原图形，只统一外围眉题细线、控件边框/焦点、说明展开态和抽屉材质。184行明确标记 `kept_with_reason`；只把入口两设备标记为 `improved`。没有声称全站所有页面都进行了结构重设计。

评分为AI主观视觉判断，使用PLAN六项100分权重，不是客观测量或用户偏好保证。完整逐页结果在账本；入口采用结果如下：

| 入口 | 原版 | 选中生成稿 | 实现 | 还原度 |
| --- | ---: | ---: | ---: | ---: |
| 桌面 | 82.8 | 93.45 | 92.65 | 93.1 |
| 手机 | 84.7 | 94.15 | 93.0 | 91.3 |

两轮实际实现截图分别存于 `iterations/round-1/`、`iterations/round-2/`。第一轮发现原背景抢眼、中央纹理干扰品牌；第二轮暗化背景并遮罩中央纹理。实际第二轮桌面、手机、内容页及图表库图像又交给生图工具，保存了独立输入和反馈图。最终保留原生中央SVG和图标，中央金色流体细节不完全复制稿件，手机透镜按原154px规范；这些差异已计入主观还原评分。

## 五个透明资产与连续开场

五个资产均由本轮单独真实生成，FFmpeg只做512px缩放与WebP压缩，合计335,766字节。逐个验证实际alpha最小0、最大255、透明与非透明像素均存在；未把棋盘格当透明。原PNG完整保存于design目录。[实际alpha与资源报告](assets/planet-validation.json)。

| 路径 | 字节 |
| --- | ---: |
| `app/assets/visual/planet-question.webp` | 68,892 |
| `app/assets/visual/planet-collection.webp` | 74,340 |
| `app/assets/visual/planet-cleaning.webp` | 60,904 |
| `app/assets/visual/planet-landscape.webp` | 68,706 |
| `app/assets/visual/planet-findings.webp` | 62,924 |

五个原链接仍分别进入question/collection/cleaning/landscape/findings，普通标签、说明、图标和访问语义保持原生。相同链接与相同 `.intro-optics` SVG完成原5.95秒开场交接；装饰图片留在这些同一节点内，不使用视频/GIF/逐帧序列。图片或增强脚本失败时仍有原生CSS/SVG玻璃与真实路由。

[真实浏览器开场与操作录屏](after/intro-demo.mp4) 由Chromium CDP直接记录611帧、约16.2秒、1,807,188字节。包括重播、完整交接、悬停、进入原研究页、返回、原证据位置滑块和跳过。无生成/插值视频帧；录屏不作为性能测量。临时原始CDP帧只作本地中间文件，MP4和清单已入库。

## 图表保护与真实检查

519个固定保护文件逐字节不变：原科学源码、数据、图稿、字体和第三方依赖。没有迁移科研绘制代码绕过保护。65个研究状态继续比较原文字、条件与SVG；184个非入口状态/设备还比较SVG完整形状、计算后的科学字体/颜色和实际可见图形像素。手机先原生滚动再截取图形可见区域，完整越界几何仍由SVG/样式对照覆盖。31种真实导出的CSV/SVG与冻结基线一致，SVG只归一化运行期局部ID。

[保护汇总](after/chart-preservation.json) · [逐文件哈希](after/preservation.json) · [原研究对照](after/master-alignment.json) · [图形/样式/像素对照](after/chart-render-preservation.json) · [实际下载](after/export-checks.json)

本地13套检查共1810条记录全部通过，不同维度会重复检查同一路由。这不是页面数量。详细检查如下：

| 检查 | 通过条目 |
| --- | ---: |
| [site-checks](after/site-checks.json) | 467/467 |
| [master-alignment](after/master-alignment.json) | 65/65 |
| [preservation](after/preservation.json) | 525/525 |
| [home-interactions](after/home-interactions.json) | 49/49 |
| [library-interactions](after/library-interactions.json) | 39/39 |
| [gateway-checks](after/gateway-checks.json) | 123/123 |
| [optical-checks](after/optical-checks.json) | 23/23 |
| [resilience](after/resilience.json) | 11/11 |
| [intro-checks](after/intro-checks.json) | 86/86 |
| [planet-checks](after/planet-checks.json) | 19/19 |
| [chart-render-preservation](after/chart-render-preservation.json) | 184/184 |
| [export-checks](after/export-checks.json) | 31/31 |
| [top-capture-checks](after/top-capture-checks.json) | 188/188 |

覆盖原方向/模型/条件、热图键盘单元格、位置滑块与置信区间、反馈修复播放、条件刷新/历史、真实触摸、抽屉焦点/Escape、原始记录与统计、图表导出、重播/跳过/窗口变化/减少动态效果/后台停止及故障降级；Axe检查未发现严重/关键级问题。测试与截图均由本轮真实Chromium执行。

## GitHub动效复用

继续实际使用本地Motion mini 14.9.0驱动五个原链接的轨道漂移、移动端局部高光与点击聚焦飞行，新的静态透明素材随同一节点运动。检索并核实[motiondivision/motion v14.9.0](https://github.com/motiondivision/motion/tree/7415b6cd14dfdb35d91dfc5b9758994444cc228b)，commit `7415b6cd14dfdb35d91dfc5b9758994444cc228b`，MIT许可；官方animateMini interruption示例与许可已归档。落地在 `app/src/gateway.js` 的animate/sync/navigate/cancelIdle，未添加新依赖。[来源、版本、许可与本地位置](assets/motion-source.json)。

## 性能

6组开场与8组Lighthouse在其他本轮浏览器检查、截图、录屏结束后独立顺序执行。Lighthouse使用provided throttling，同机冷加载；没有模拟弱网或CPU降速，首页明确intro=0。开场另含DPR3及CPU4倍减速模拟。这些是本机单次诊断，不能视为实机手机/GPU统计基准。

| 页面/视口 | 前性能分 | 后性能分 | 后CLS |
| --- | ---: | ---: | ---: |
| home/mobile | 100 | 100 | 0.000068 |
| home/desktop | 100 | 100 | 0.000101 |
| library/mobile | 100 | 100 | 0.000022 |
| library/desktop | 98 | 98 | 0.000432 |

[Lighthouse原始数据与方法](after/performance-summary.json) · [开场帧间隔/绘制成本](after/frame-performance.json)

| 开场条件 | 完成ms | 平均绘制FPS | p95 JS绘制ms | idle RAF / Canvas像素 |
| --- | ---: | ---: | ---: | ---: |
| 1440×900 | 5979 | 57.1 | 2.5 | 0 / 1 |
| 768×1024 | 5972 | 57.8 | 2.5 | 0 / 1 |
| 390×844 | 5964 | 29.6 | 1.7 | 0 / 1 |
| 320×740 | 5962 | 30.0 | 1.6 | 0 / 1 |
| 390×844 DPR3 | 5977 | 29.9 | 1.7 | 0 / 1 |
| 390×844 CPU4× | 5977 | 27.8 | 3.6 | 0 / 1 |

## 发布、线上与审计

生产实现提交：`b338faff02a0dff108db8946e0db7e0e5c00b4a4`，已正常快进main并推送，无reset/force push。[Pages工作流](https://github.com/Fwlyii/data-analysis-frontrefine/actions/runs/41217215015)成功。

[线上入口](https://fwlyii.github.io/data-analysis-frontrefine/?intro=0&v=fullsite-b338faff) · [观看完整开场](https://fwlyii.github.io/data-analysis-frontrefine/?intro=1&v=fullsite-b338faff) · [图表库](https://fwlyii.github.io/data-analysis-frontrefine/explore.html?mode=explore)

227个线上构建文件逐字节与本地dist一致，保留预期/实际SHA-256；包括全部HTML、CSS、脚本、数据、图稿、字体与新资源。真实线上93路由×桌面/手机及原研究/图表库交互、开场、减少动态效果、真实触摸和31种导出均通过。

[逐文件线上核对](after/public-assets.json) · [线上浏览器汇总](after/public-browser.json) · [线上全路由](after/public-routes/site-checks.json) · [线上导出](after/public-export-checks.json)

发布门禁 `scripts/system/check_visual_coverage.py` 已绑定本轮451个源文件/输入指纹与全套新证据。旧“三次生图/开场禁止任意img”规则扩展为14次以上真实来源、恰好5个静态透明装饰、原生标签/原链接、科学文件固定哈希和新素材降级/交接检查，其余保护保留。

检查工具最初遇到Plotly异步替换占位SVG、手机横向第二图裁切和原PNG参考被规范重拍覆盖等取证问题：均保留尝试日志并修正。Plotly等待最终renderer；手机按实际可见区域取样，完整DOM/样式仍严格比较；最初参考PNG以原SHA和字节数从本任务原图像记录恢复到独立归档输入路径，未改写原来源哈希。线上图表库首次因过快跨页取消Motion请求而有1项资源检查失败，原报告保留于iterations/public-attempt-1；只增加离开首页前的networkidle等待，再完整重跑39项全部通过，未放宽资源断言。最终没有以失败取证或旧PASS代替当前证据。

## 修改文件与保留项

实际生产与文档文件如下；完整截图/脚本/报告列表见[changed-files.json](changed-files.json)。没有新增呈现模块，没有改动科学绘制模块。

- `app/index.html`
- `app/explore.html`
- `app/gateway.css`
- `app/refinement.css`
- `app/src/gateway.js`
- `app/src/refinement.js`
- `app/visual-coverage.json`
- `scripts/system/check_visual_coverage.py`
- `README.md`
- `app/README.md`
- `docs/design-sources.md`
- `docs/visual-refinement-workflow.md`
- `app/assets/visual/planet-question.webp`
- `app/assets/visual/planet-collection.webp`
- `app/assets/visual/planet-cleaning.webp`
- `app/assets/visual/planet-landscape.webp`
- `app/assets/visual/planet-findings.webp`

原研究内页仍铺满视口，仅保留轻量research-home返回；未恢复侧栏和顶栏。所有未达到至少5分改进的布局均按账本保留，属于已完成的评审决策，不作为未完成伪装上线。科研图内字体/比例/几何/配色不动。

未完成项：无。
