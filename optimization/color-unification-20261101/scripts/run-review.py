"""Reproduce palette evidence against current8838/frozen d80769d8839. Never pushes."""
from pathlib import Path
import subprocess,sys,os,concurrent.futures
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def run(*args,env=None):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,env=env)
run(sys.executable,'scripts/system/build_web_app.py');run(sys.executable,'scripts/system/check_web_snapshot.py','--skip-build')
run('node',HERE/'inventory.mjs');run(sys.executable,HERE/'preservation.py')
run('node',HERE/'coverage.mjs',env={**os.environ,'REVIEW_STAGE':'before','REVIEW_BASE':'http://127.0.0.1:8839/','REVIEW_SIZES':'pair'})
def sequence(names):
 for n in names:run('node',HERE/(n+'.mjs'))
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 jobs=[pool.submit(sequence,['coverage','desktop-recording-checks']),pool.submit(sequence,['readability-checks','palette-checks','expanded-reading-checks','early-paint-checks']),pool.submit(sequence,['home-interactions','library-interactions','gateway-checks','intro-checks','optical-checks','planet-checks','resilience','nav-access-checks','master-alignment','export-checks']),pool.submit(sequence,['chart-render-preservation'])]
 for j in jobs:j.result()
for stage in ['before','after']:run('node',HERE/'overlays.mjs',stage)
run(sys.executable,HERE/'merge-overlays.py');run(sys.executable,HERE/'build-ledger.py')
for name in ['frame-performance','performance','record']:run('node',HERE/(name+'.mjs'))
run(sys.executable,HERE/'finalize.py');run(sys.executable,'scripts/system/check_visual_coverage.py')
