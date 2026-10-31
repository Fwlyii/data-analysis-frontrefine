"""Document-QA acquisition entry using exact saved scenarios. Opt-in API only."""
from pathlib import Path
import runpy,sys
sys.argv.insert(1,'document_qa')
runpy.run_path(str(Path(__file__).with_name('collect_chat_benchmarks.py')),run_name='__main__')
