"""Package the runnable research website and editable figure sources; stdlib only."""
import argparse
import ast
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LAUNCHER = '''"""启动知微展示系统：python3 启动系统.py [--port 8770]。"""
import argparse
import functools
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

p = argparse.ArgumentParser(description="启动知微研究展示系统")
p.add_argument("--port", type=int, default=8770)
p.add_argument("--no-open", action="store_true")
args = p.parse_args()
handler = functools.partial(SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parent / "网站"))
try:
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
except OSError:
    p.exit(1, "端口无法使用，请用 --port 指定其他端口。\\n")
url = f"http://127.0.0.1:{args.port}"
print("知微研究展示系统：" + url, flush=True)
print("Ctrl+C 停止。全部图表读取本地保存结果。", flush=True)
if not args.no_open:
    threading.Timer(.4, lambda: webbrowser.open(url)).start()
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
'''

REBUILD = '''"""从随包冻结统计重新绘制SVG并更新网站；Python标准库即可。"""
import csv
import importlib.util
import io
import json
import shutil
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent
source = root / "科研源图"
spec = importlib.util.spec_from_file_location("research_atlas", source / "scripts/figures/build_research_atlas.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.build()
shutil.copytree(source / "app/assets/research", root / "网站/assets/research", dirs_exist_ok=True)
catalog_path = source / "app/data/research-charts.json"
shutil.copy2(catalog_path, root / "网站/data/research-charts.json")
catalog = json.loads(catalog_path.read_text())
with zipfile.ZipFile(root / "网站/assets/research-svg.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(catalog_path, "图表目录与数值.json")
    for chart in catalog["charts"]:
        archive.write(source / "app" / chart["file"], chart["id"] + ".svg")
        rows = chart["data"]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        archive.writestr(chart["id"] + ".csv", "\\ufeff" + buffer.getvalue())
print("37张图稿及数值图包已更新，刷新网站即可。")
'''

GUIDE = '''知微展示系统 · 研究内容重构版

一、直接运行
解压后在此目录运行：python3 启动系统.py
浏览器地址：http://127.0.0.1:8770
如端口占用：python3 启动系统.py --port 8780
使用Python标准库，不需要npm或模型API。请通过HTTP打开，避免双击网站/index.html。

二、现在包含什么
五章：研究问题 → 采集设计 → 数据处理 → 核心发现 → 总结与反思。
总体四项：Token与质量的log关系、模型规模、简洁表达、限长反弹。
专项三项：数学中英文模板、文档证据位置、代码执行反馈。
37张中文可编辑SVG，逐图SVG/CSV与整包下载；保留13类通用交互图和4个代码生成视图。
清洗演示：红色同义异名字段 → 映射规则 → 已保存统一CSV及JSON读取预览。
专项9,176条匿名记录来自248,586条物理响应中的对应子集，不额外累计。

三、交给页面美化同学
网站/ 就是可运行的静态前端，src/中保留ES模块源码，可直接编辑后刷新。
网站/index.html、research.css、src/research.js：主框架、路由和图册。
网站/src/research-content.js、research-content.css：中文章节、四维31策略和清洗演示。
网站/src/research-explorer.js、research-explorer.css：13类交互图、4代码视图。
网站/src/research-special-records.js：位置和修复匿名记录。
网站/assets/research/：全部可编辑SVG；网站/data/research-charts.json：目录与实际数值。
网站/runtime/：已生成的冻结数据脚本，页面通过本地HTTP按需读取。
内容与图表交接.md：模块接口及后续美化边界。

可以继续美化导航、页面切换、布局与动画。请保留图形坐标、单位、条件、来源和评分口径；
筛选、记录与导出必须对应同一集合；未知规模保持缺失；独立生成不称为反馈修复轮次。
本版图表已设计配色、直接标注、点线形状与重点数字，可继续使用SVG原图。

四、重新绘制科研图
科研源图/ 保存生成器和它实际读取的冻结统计，编辑其scripts/figures/build_research_atlas.py后运行：
python3 重建科研图册.py
该命令更新网站SVG、目录与图包。它不修改原始研究数据，不重新调用模型。
完整数据分析及采集代码保留在原Git仓库，本包用于展示、页面美化与图形重绘。
'''


def package(output):
    dist = ROOT / 'app/dist'
    if not (dist / 'index.html').is_file():
        raise SystemExit('请先运行 python3 scripts/system/build_web_app.py')
    output.mkdir(parents=True, exist_ok=True)
    destination = output / '知微展示系统'
    if destination.exists():
        raise SystemExit('目标目录已存在；请保留已有修改并换一个输出目录。')
    destination.mkdir()
    shutil.copytree(dist, destination / '网站')
    (destination / '启动系统.py').write_text(LAUNCHER, encoding='utf-8')
    (destination / '重建科研图册.py').write_text(REBUILD, encoding='utf-8')
    (destination / '使用与交接.txt').write_text(GUIDE, encoding='utf-8')
    shutil.copy2(ROOT / 'docs/reconstruction-handoff.md', destination / '内容与图表交接.md')
    source_path = Path('scripts/figures/build_research_atlas.py')
    inputs = {source_path}
    for node in ast.walk(ast.parse((ROOT / source_path).read_text())):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {'jread', 'read_csv'}:
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                inputs.add(Path(node.args[0].value))
    for relative in sorted(inputs):
        target = destination / '科研源图' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    catalog = json.loads((ROOT / 'app/data/research-charts.json').read_text())
    (destination / '科研源图/app/data/research-charts.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    shutil.copy2(ROOT / 'app/assets/research-svg.zip', output / '知微科研SVG图包.zip')
    shutil.copy2(destination / '使用与交接.txt', output / '重构版_使用与交接.txt')
    report = ROOT / 'artifacts/qa/reconstruction/report.json'
    if report.is_file():
        shutil.copy2(report, destination / '浏览器检查结果.json')
    archive_path = output / '知微展示系统_重构版.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(output))
    print(json.dumps({'website': str(destination), 'archive': str(archive_path), 'figures': len(catalog['charts']), 'figure_source_files': len(inputs)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    package(parser.parse_args().output.resolve())
