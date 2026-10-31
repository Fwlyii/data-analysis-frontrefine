"""Reasoning/MCQA acquisition entry. Preview by default; --execute calls API."""
from pathlib import Path
import runpy,sys
sys.argv.insert(1,'reasoning')
runpy.run_path(str(Path(__file__).with_name('collect_chat_benchmarks.py')),run_name='__main__')
