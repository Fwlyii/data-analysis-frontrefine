"""Entry for the supplied 31-prompt Python collector; dry-run unless --execute."""
from pathlib import Path
import runpy,sys,datetime as dt
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
if '--execute' in sys.argv:sys.argv.remove('--execute')
elif '--dry-run' not in sys.argv:sys.argv.append('--dry-run')
if not any(x in sys.argv for x in ['--turns','--samples','--repeats']):sys.argv.extend(['--turns','5'])
if '--prompt-set' not in sys.argv:sys.argv.extend(['--prompt-set','cot-compression31'])
if '--output' not in sys.argv:sys.argv.extend(['--output',str(ROOT/'data/raw/code_generation/collections'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')/'responses.jsonl')])
runpy.run_path(str(ROOT/'experiments/code_generation/src/run_experiment.py'),run_name='__main__')
