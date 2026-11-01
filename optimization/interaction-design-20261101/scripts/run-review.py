"""Reproduce the full local review; never commit, push or publish."""
from pathlib import Path
import concurrent.futures,os,subprocess,sys,hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;J=HERE.parent

def run(*args,env=None):subprocess.run(list(map(str,args)),cwd=ROOT,check=True,env=env)
frozen=ROOT/'.git/interaction-review/baseline-dist'
assert frozen.exists(),'Prepare a frozen build of 926c936 in .git/interaction-review/baseline-dist; see REPORT.md. Do not replace it with current app/dist.'
for p,h in json.loads((J/'frozen-build.json').read_text())['files'].items():assert hashlib.sha256((frozen/p).read_bytes()).hexdigest()==h,'Wrong frozen baseline: '+p
# Start current8838 and frozen8849 servers before running. They must serve those exact directories.
run(sys.executable,'scripts/system/build_web_app.py');run(sys.executable,'scripts/system/check_web_snapshot.py','--skip-build');run('node',HERE/'inventory.mjs');run(sys.executable,HERE/'preservation.py')
run('node',HERE/'coverage.mjs',env={**os.environ,'REVIEW_STAGE':'before','REVIEW_BASE':'http://127.0.0.1:8849/','REVIEW_SIZES':'pair'})
def sequence(names):
 for name in names:run('node',HERE/(name+'.mjs'))
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 tasks=[pool.submit(sequence,['coverage','home-interactions','library-interactions','gateway-checks','intro-checks','optical-checks','planet-checks','resilience','nav-access-checks','master-alignment','early-paint-checks','export-checks','desktop-recording-checks']),pool.submit(sequence,['interaction-checks','lifecycle-checks']),pool.submit(sequence,['layout-review','showcase']),pool.submit(sequence,['chart-render-preservation'])]
 for task in tasks:task.result()
# Isolated runs: do not benchmark while other browser suites or CDP recording are active.
sequence(['frame-performance','performance','record','contact-sheets','build-gallery','gallery-checks'])
run(sys.executable,HERE/'finalize.py');run(sys.executable,'scripts/system/check_visual_coverage.py')
