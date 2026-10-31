"""Show this job's state without reading credentials or unrelated sessions."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[3]
JOB=Path(__file__).resolve().parents[1]
p=ROOT/'.git/visual-loop/runtime-status.json'
if p.exists():print(json.dumps(json.loads(p.read_text()),ensure_ascii=False,indent=2))
else:print('后台进程尚未写入状态。')
print('\n最近执行日志：')
p=ROOT/'.git/visual-loop/progress.log'
if p.exists():print('\n'.join(p.read_text().splitlines()[-15:]))
print('\n任务进度：')
p=JOB/'STATUS.md'
if p.exists():print(p.read_text())
print('\n连接后台：tmux attach -t lens-visual-loop')
print('仅脱离查看：按 Ctrl+B，松开，再按 D。')
