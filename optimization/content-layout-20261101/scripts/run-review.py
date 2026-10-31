"""Reproduce the desktop content review against current8828/frozen8829. Never pushes."""
from pathlib import Path
import subprocess,sys,os
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def run(*args,env=None):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,env=env)
run(sys.executable,'scripts/system/build_web_app.py');run(sys.executable,'scripts/system/check_web_snapshot.py','--skip-build')
run('node',HERE/'inventory.mjs');run(sys.executable,HERE/'preservation.py')
run('node',HERE/'coverage.mjs',env={**os.environ,'REVIEW_STAGE':'before','REVIEW_BASE':'http://127.0.0.1:8829/','REVIEW_SIZES':'pair'})
for name in ['coverage','readability-checks','desktop-recording-checks','expanded-reading-checks','master-alignment','home-interactions','library-interactions','gateway-checks','intro-checks','optical-checks','planet-checks','resilience','nav-access-checks','chart-render-preservation','export-checks']:
 run('node',HERE/(name+'.mjs'))
for stage in ['before','after']:run('node',HERE/'overlays.mjs',stage)
run(sys.executable,HERE/'merge-overlays.py');run(sys.executable,HERE/'build-ledger.py')
for name in ['frame-performance','performance','record']:run('node',HERE/(name+'.mjs'))
run(sys.executable,HERE/'finalize.py');run(sys.executable,'scripts/system/check_visual_coverage.py')
