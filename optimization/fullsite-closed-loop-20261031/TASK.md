# 独立后台 Codex 执行任务

你是用户明确授权在服务器tmux后台执行本轮全站视觉优化的独立Codex进程。请直接完成任务，用户将关闭个人电脑，不能依赖交互回复。先完整阅读同目录PLAN.md，再执行。你有内置image_gen、web、view_image、exec工具，预检已通过。使用当前默认模型与已登录认证，不改模型、不打印凭据、不调用需API Key的生图fallback，不再派生子代理。

用户原话：

> 把这个聊天放在tmux后台开始执行，我要关电脑，请你进行这样的一个闭环，认真思考规划完成以后再开始执行：1、从presentation的那个页面到图表库的那个页面，把每个页面的截图存下来进行我们的优化前端的那个生图然后代码执行的闭环流程。2、闭环里面注意评分，优化图更加好看就做到高规模还原，不能实现的图标和艺术字采用抠图直接放进去，封面动画五个星球效果不好，可以直接抠图。3、不要改变现在绘制好的图表等。4、可以从GitHub复用好的动态效果。5、检查不要漏掉哪个页面。

## 上下文与已准备内容

- 工作目录 `/home/codex/fwl-temporay/coursework/data-analysis-frontrefine`，Git origin为用户仓库 `Fwlyii/data-analysis-frontrefine`，最新已发布基线为f751c3fe2db5a977f63d394ca185d09bc3ef8132。
- 工作区最初干净。父任务只添加了本目录计划、任务、保护清单和运行脚本，并已切到工作分支work/lens-fullsite-20261031。请保护这些脚手架，不当成未知用户修改而停工。
- `protected-files.json` 固定519个保护文件：原科学模块、原数据、图稿、字体、第三方依赖。不可篡改或重写其baseline/哈希来掩盖变化。允许修改的现有JS仅app/src/gateway.js、app/src/intro.js、app/src/refinement.js；新增纯呈现模块需说明，不能迁移/篡改科学绘制逻辑来绕过保护。
- `.git/visual-loop/baseline-dist/` 是原样冻结的222个网页文件，8819端口由运行器提供；8818服务当前app/dist。不要停止其他8788/8790/8792/8793服务或tmux任务。
- 当前生产入口是app/index.html（知微之门+presentation）与app/explore.html（图表库/论文图/代码/发现）。现有93路由状态，至少186张桌面/手机截图；另补展开状态、长内容与开场关键阶段。
- 最新已完成版本与审查材料：optimization/gateway-polish/README.md、REPORT.md、scripts/。此前原Master重建材料在optimization/master-rebuild-v6/，开场原实现记录在optimization/cinematic-intro/。历史证据不可覆盖或拿来冒充本轮截图。
- 页面已移除研究内页的原侧栏和顶栏，只保留轻量research-home返回按钮。必须保留这个用户已要求的行为。
- 首页五个真实链接是#gate-question/collection/cleaning/landscape/findings，分别进入#question/#collection/#cleaning/#landscape/#findings。开场搬移同一组链接节点，同一个.intro-optics SVG最后交给主页；必须保持这个连续性。
- 用户新授权允许抠图/透明装饰星球及品牌艺术字，覆盖此前这些装饰只能纯代码的限制。仍禁止视频/GIF/逐帧序列及科学图表位图替换；原生标签和访问语义必须保留。
- 现有Motion mini在app/assets/vendor/，是首选动效引擎。真实浏览器检查依赖已安装在optimization/homepage-pilot/tools/node_modules/，Chromium为/snap/bin/chromium，ffmpeg可用。

## 执行顺序与记录

1. 阅读PLAN.md、现有全站流程与真实路由，确认保护清单与冻结服务；更新STATUS.md为当前阶段。
2. 在本目录建立before/design/assets/after/scripts等目录，复制并适配上一轮检查工具到本目录（8788改8818，旧基线端口改8819，基线SHA改f751c3f）。不要重跑旧目录脚本覆盖历史。生成本轮inventory与全部before截图，包含展开/滚动/开场状态。在生产改动前写出基线完成标记。
3. 基于本轮实际截图进行评分、生成两套全站方向与各视觉组的设计稿。必须真实调用image_gen，先view_image读取本地参考。覆盖每种布局与每个路由，逐页账本可按设计组共享稿。若模型工具返回图像须保存实际生成文件并记录来源；不得用HTML截图或旧稿伪装新生成稿。
4. 优先让五个星球达到选中稿的质感：以选中稿为参考，生成/抠取独立透明素材，验证真实alpha并压缩成合适资源。用户明确允许抠图，但仍优先按imagegen技能使用内置工具完成透明背景。普通界面文字保持原生；只有品牌等装饰可选艺术字，保留可访问文本。
5. 在真实源码进行布局/视觉改造，主展示、图表库、手机、开场一起统一。从GitHub检索、核实许可并实际复用合适动效，优先现有Motion而非大依赖。记录仓库、commit/version、许可与落地位置。
6. 按PLAN的100分量表评价原版、生成稿、实现；候选胜出才采用。高还原目标90，至多两轮真实实现截图反馈，逐页修复，不能仅用“测试通过”替代审美评估。评分明确是AI视觉判断且写理由。
7. 完成每个路由/设备的coverage-table.json、展开状态清单、所有前/参考/后截图与总览画廊，查漏补缺。对图表保护、原功能、键盘、手机、减少动画、离页停止、降级、导出、性能执行真实检查。
8. 更新app/visual-coverage.json及scripts/system/check_visual_coverage.py指向本轮新证据。旧门禁对“三次生图”和“开场不允许任何img”的限制可按本轮真实素材扩展，必须新增替代语义检查，不能简单移除保护。真实源码指纹变动后不能复用旧PASS。
9. 本地全部通过后正常提交，确认main仍可安全快进（不得reset/force push覆盖新内容），推送main并等待Pages成功，再线上逐文件与浏览器验证。用户此前明确要求推送每版预览，此次要求整个闭环无人值守执行，按既有预览授权完成。未通过验收时不要推送半成品。
10. 写RESULT.md和completion.json。报告包括线上预览、详细文件列表、每页评分与采用/保留原因、设计还原度、图表不变证据、GitHub动效来源、全部测试与真实截图录屏；未完成项如实列出。

## 完成契约（运行器会独立检查）

本目录必须提供：

- site-inventory.json，routes键仍来自真实源码，含全部基础状态。
- coverage-table.json，顶层rows数组，至少每路由×desktop/mobile一行，行字段：routeKey、device、beforeScreenshot、referenceImage、afterScreenshot（均为仓库根目录相对路径）、beforeScore、referenceScore、afterScore、fidelityScore（0–100）、decision、reason；可增加详细分项与布局组。decision为improved或kept_with_reason。improved需referenceScore>=beforeScore+5、fidelityScore>=90且afterScore>=referenceScore-5。保留原版必须写真实评审理由与对应稿。
- overlays.json，states数组，列出全部实际展开/滚动状态及截图路径beforeScreenshot/afterScreenshot。
- design/provenance.json，calls数组，真实生图工具调用，每项prompt、output、inputs（可使用{path,sha256,bytes}或路径），最终所有产物实际存在。必须有独立透明星球资产的真实生成/编辑记录及实现截图反馈记录。
- design/visual-scores.json，逐图/逐页的评分理由、量表分项与还原评审；清楚标注主观性，不要虚构客观评分工具。
- after/functional-checks.json，results数组，每项name/passed，覆盖所有已有功能并全部通过；可汇总指向真实各专项报告，但不能杜撰结果。
- after/chart-preservation.json，包含原图/数据/源码与实际渲染对照的results且全部passed。
- after/public-assets.json 与 after/public-browser.json，真实线上结果，results全部passed，线上资产比对必须逐字节；所有科学CSV/SVG导出仍正确。
- after/intro-demo.mp4，真实浏览器录屏，体积>10000字节；无此录屏不能声称动画验收完成。
- RESULT.md，完整中文结果；STATUS.md写最终状态。
- completion.json，status为completed，baseline为f751c3fe2db5a977f63d394ca185d09bc3ef8132，incomplete数组为空，releaseCommit为真实已部署的生产提交SHA，previewUrl为真实Pages链接，planetAssets为恰好五个实际用于首页/开场的透明资产的仓库根目录相对路径。请在保护校验与全套发布门禁成功、线上复核完毕之后再写completed，并将最终状态和完成清单一同提交，保持工作区干净。

## 持续执行规则

每个阶段与至少每若干工具调用更新STATUS.md；不要只写设计方案或说下一步会做。遇到工具/网络错误有限重试并记录；持续无法调用模型时保存现场，明确等待原因，不冒充生成过图片。达到上下文边界时依靠计划、账本和STATUS恢复，不从头重复截图。先完成当前阶段再进入下一个，最终性能测试要独立顺序运行。所有新素材在项目内保存，不能仅留在生成缓存目录。

不得读取/打印auth.json、私钥、token、完整环境或.git/config凭据；不得更改全局配置、删除无关文件、覆盖既有用户修改、未经理由改科研图表和数据。不要修改本目录scripts/run_background.py与verify_completion.py来伪造运行完成。
