"""Reproduce this round's read-only browser QA against8818 and frozen8819; does not push."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
for name in ['coverage','master-alignment','gateway-checks','optical-checks','resilience','home-interactions','library-interactions','intro-checks','planet-checks','chart-render-preservation','export-checks']:
 subprocess.run(['node',str(HERE/(name+'.mjs'))],cwd=ROOT,check=True)
subprocess.run(['node',str(HERE/'overlays.mjs'),'after'],cwd=ROOT,check=True)
for name in ['merge-overlays.py','score-ledger.py','build-gallery.py']:
 subprocess.run([sys.executable,str(HERE/name)],cwd=ROOT,check=True)
# Keep diagnostics sequential and run with no other browser tasks.
for name in ['record','frame-performance','performance']:
 subprocess.run(['node',str(HERE/(name+'.mjs'))],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(HERE/'finalize.py')],cwd=ROOT,check=True)
subprocess.run([sys.executable,'scripts/system/check_visual_coverage.py'],cwd=ROOT,check=True)
