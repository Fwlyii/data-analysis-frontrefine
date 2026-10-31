"""Assemble the pilot report from saved browser and Lighthouse evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "optimization/homepage-pilot"


def load(path):
    return json.loads((OUT / path).read_text())


performance = load("after/performance-summary.json")
runs = {(run["stage"], run["device"]): run for run in performance["runs"]}
regression = load("after/regression.json")
extra = load("after/extra-checks.json")
accessibility = load("after/accessibility.json")
asset = ROOT / "app/assets/visual/optical-study.webp"
manifest = load("assets/manifest.json")
manifest.update(dimensions=[480, 240], bytes=asset.stat().st_size,
                sha256=hashlib.sha256(asset.read_bytes()).hexdigest(),
                delivery_optimization="FFmpeg WebP quality 72, 480 px width; alpha retained",
                preload="Desktop-only media-conditioned preload; no mobile request")
(OUT / "assets/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
shutil.copy2(asset, OUT / "assets/optical-study.webp")

table = []
for device, label in [("mobile", "移动端"), ("desktop", "桌面端")]:
    before, after = runs[("before", device)], runs[("after", device)]
    for stage, run in [("原版", before), ("优化后", after)]:
        m, s = run["metrics"], run["scores"]
        table.append(f"| {label}/{stage} | {s['performance']} | {s['accessibility']} | {s['best-practices']} | "
                     f"{m['first-contentful-paint']/1000:.2f}s | {m['largest-contentful-paint']/1000:.2f}s | "
                     f"{m['total-blocking-time']:.0f}ms | {m['cumulative-layout-shift']:.3f} |")
mobile_delta = runs[("after", "mobile")]["metrics"]["total-byte-weight"] - runs[("before", "mobile")]["metrics"]["total-byte-weight"]
desktop_delta = runs[("after", "desktop")]["metrics"]["total-byte-weight"] - runs[("before", "desktop")]["metrics"]["total-byte-weight"]
passed = sum(item["passed"] for item in regression["results"])
extra_passed = sum(item["passed"] for item in extra["checks"])
protected = load("after/protected-content.json")
audit = load("tools/dependency-audit.json")
tools = json.loads((OUT / "tools/package.json").read_text())["devDependencies"]

report = f"""# LENS 首页视觉优化 Pilot

本次完成默认首页的“真实截图 → 两份生图设计 → 独立素材 → 原生前端实现 → 浏览器反馈与验收”闭环。保留五章导航、左发现/右主图、证据表、方法区与图表库入口。工作分支为 `visual/homepage-pilot-20261031`，基线为 `069033c`；没有推送远程或修改线上部署。

## 1. 方法来源与工程适配

| 参考 | 实际借鉴 | 未声称复现的部分 |
|---|---|---|
| [Editable Visual Design](https://arxiv.org/abs/2609.04034) | 先看生图参考；独立生成素材；代码分层实现；截图检查 | 固定画布、作者完整 Replay 编辑器与论文实验 |
| [UI Remix](https://arxiv.org/abs/2601.18759v2) | 限定原结构，局部改造组件，防止设计漂移 | MMRAG 检索系统、UI 数据库与用户研究 |
| [UI2Code-N](https://proceedings.mlr.press/v306/yang26v.html) | 用实际渲染反馈修订；相对比较候选方案 | 9B 模型训练、RVPO/GRPO 与 benchmark 成绩 |

响应式约束、浏览器测试、资源预算和这三篇方法的组合是本次工程设计，不能称为论文已验证的完整流程。[方法笔记](research/method-notes.md)、[来源与全文校验](research/sources.json)。作者开源库仅核对方法范围和 Apache-2.0 许可，没有执行其代码或安装作者技能。

## 2. 视觉方案与真实截图

- 原始：[桌面](before/desktop.png)、[桌面全页](before/desktop-full.png)、[手机](before/mobile.png)、[手机全页](before/mobile-full.png)。
- 两份真实生图：[A 冷色研究期刊](designs/variant-a.png)、[B 暖色档案展陈](designs/variant-b.png)。
- 选定 A：与原品牌更一致，结论层次清楚，装饰可独立实现；B 的暖纸/山水元素与研究主题联系较弱。[七维选择记录](designs/selection.md)。
- 最终真实网页：[桌面](after/desktop.png)、[桌面全页](after/desktop-full.png)、[手机](after/mobile.png)、[手机全页](after/mobile-full.png)。
- 额外状态：[资料位置](after/position-desktop-full.png)、[手机限长选择器](after/limits-mobile-full.png)、[手机修复](after/repair-mobile-full.png)。
- [浏览成果对照页](index.html)。

生成工具为内置 `image_gen`，共 3 次成功调用：两份参考、一份独立透明素材。工具没有返回具体模型版本，不推断型号。当前助手以 VLM 视觉能力比较实际输出并审阅真实截图；未另行调用独立审美打分服务，也没有用户实验。原始输出、完整提示词和哈希保存在 [生成记录](designs/generation-manifest.json)，生成过程不保证像素级确定性。

## 3. 修改与素材

| 文件/区域 | 变化 |
|---|---|
| `app/story.css` | 复用并细化蓝青色变量；明确正文 CJK 字体回退；结论浅底与侧线；图纸细边与轻阴影；分段控件和选择器；证据表和方法展开区 |
| 同一响应式样式 | 手机同时展示五章入口；将现有宽图滑动提示放到图上方；装饰只在 850px 以上显示；为初始加载文本预留空间，降低布局位移 |
| `app/index.html` | 同步主题色、桌面限定的素材预加载，以及构建生成的样式版本标识 |
| `app/assets/visual/optical-study.webp` | 单独生图得到的透镜纹理；透明、480×240、{asset.stat().st_size/1024:.1f} KiB；没有裁切整页设计图 |
| `app/dist/` | 同步构建产物及同一素材，便于本地预览 |

数据图、正文、按钮、表单和动态数值全部保留原生；没有使用整页图片替换界面。{len(protected['unchanged_files'])} 个受保护的 `app/src`、`app/data`、原图稿及图表库样式文件与基线逐字节相同，[校验记录](after/protected-content.json)。生产页面没有新增 JavaScript 依赖。

开发检查工具单独位于 `tools/`：{', '.join(f'{name}@{version}' for name, version in tools.items())}。使用系统 FFmpeg 压缩素材。Noto Sans/Serif CJK 字体只安装到本机截图环境，已核对 OFL 许可，不进入网页下载包。

## 4. 反馈与验收

主要视觉实现 2 轮，另做 1 轮验收修复，没有反复重生整页：

1. 第一轮实现 A 的颜色、层次、控件和独立装饰；查看真实桌面与手机截图。
2. 第二轮修正手机导航和滑动提示的发现性。
3. 第三轮把结论强调文字从 4.46 的对比度修正到合格范围；压缩素材并限制桌面加载，完成性能复查。

[第一轮反馈](iterations/round-1-review.md)、[第二轮与验收修复](iterations/round-2-review.md)。

- 功能回归：**{passed}/{len(regression['results'])}**，覆盖四档宽度×五主题、条件切换、真实 SVG、CSV/SVG 下载、数据/方法展开、位置与 CI、刷新恢复、修复播放、模型切换、全屏按钮和图表库往返。[详细结果](after/regression.json)。
- 额外检查：**{extra_passed}/{len(extra['checks'])}**，包含五个导航入口在各尺寸内可见、冷启动手机不请求装饰、实际字体和透明通道。[详细结果](after/extra-checks.json)。
- axe：**{len(accessibility['violations'])} 个已确认违规项**；浏览器未捕获新增未处理异常或失败资源。[结果](after/accessibility.json)。
- 响应式：320、390、768、1440px 页面均无横向溢出；宽 SVG 的横向滚动限于图表容器，不改变图稿数据。

## 5. 性能对照

Lighthouse 在同一浏览器和本机服务器上顺序执行，使用真实 DevTools 网络/CPU 节流；原版由基线提交直接提取到独立静态预览目录。以下均为单次诊断，不是多机统计实验。

| 设备/版本 | 性能 | 可访问性 | 最佳实践 | FCP | LCP | TBT | CLS |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

冷加载资源增量：移动端约 **{mobile_delta/1024:.1f} KiB**，桌面约 **{desktop_delta/1024:.1f} KiB**。手机没有装饰图请求，也没有新增运行脚本。对初始加载区预留空间后，本轮 CLS 为 0。

不把分数变化解释为必然提速：桌面 LCP 候选由标题变为带装饰的容器，移动端依然需要加载原有约 0.72 MiB 的展示脚本/数据，慢网下仍有明显等待。早期 simulated-throttling 报告的 LCP 依赖图推断存在波动，已原样保存在 `iterations/performance-simulation/`；最终改用相同条件下的实际 DevTools 节流比较，未删除低分报告。[汇总及原始报告路径](after/performance-summary.json)。

## 6. 限制与判断

- 生图提供了可观察的方向与独立光学素材，强化了原有研究界面的识别度与层次；提升幅度属于本次 VLM 定性判断，未证明优于所有纯代码设计。
- 代码还原了主要色调、结论强调、图纸层次和装饰；主动保留原始 SVG，不照搬生成图中的文字误差、图表材质或固定画布。
- 普通几何、排版、控件与数据图继续用代码；复杂且非信息性的光学材质适合独立生图。
- 图表库只做加载/往返冒烟检查，未在此 Pilot 中改造；没有穷尽全部浏览器、所有图表组合或真实移动设备。系统字体跨平台可能有差异。
- 工具链 npm 审计报告 {audit['metadata']['vulnerabilities']['moderate']} 项中危、0 项高危/严重项，仅在本地开发检查依赖中；未打包进 `app/dist`。[工具依赖审计](tools/dependency-audit.json)。
- 这套流程适合继续用于受约束的局部优化。推广到高密度图表库前，应另做 Pilot，先验证筛选、图例和记录面板的可读性；不建议把装饰机械铺满全站。

## 7. 预览、复查和回退

- 优化预览：`http://127.0.0.1:8780/`；基线预览：`http://127.0.0.1:8781/`，均为当前工作环境中的临时服务。
- 成果对照：`http://127.0.0.1:8782/`（若该端口预览已启动）。
- 重建：`PYTHONDONTWRITEBYTECODE=1 python3 app/pipeline/scripts/system/build_web_app.py`。
- 开发检查工具恢复：`npm ci --prefix optimization/homepage-pilot/tools --ignore-scripts`；本机需有 Chromium 和 CJK 字体，脚本记录了当前环境路径。
- 复查：`node optimization/homepage-pilot/scripts/browser.mjs capture after`、`node optimization/homepage-pilot/scripts/browser.mjs regression after`、`node optimization/homepage-pilot/scripts/extra-checks.mjs`。
- 性能：确保 8780 优化预览和 8781 基线预览均启动，再运行 `node optimization/homepage-pilot/scripts/performance.mjs`。
- 工作区干净时切回 `main` 可恢复基线页面；本次修改保存在独立本地分支/提交中。线上 GitHub Pages 保持原版。
"""
(OUT / "REPORT.md").write_text(report)
print("Report assembled from saved evidence:", OUT / "REPORT.md")
