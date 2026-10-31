"""Reproduce the local gateway review; never pushes or deploys."""
from pathlib import Path
import subprocess,sys,shutil,argparse
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--functional-only',action='store_true');args=p.parse_args()
def run(*argv):
    print('+',' '.join(map(str,argv)),flush=True);subprocess.run(list(map(str,argv)),cwd=ROOT,check=True)
shutil.rmtree(ROOT/'app/runtime',ignore_errors=True)
run(sys.executable,'scripts/system/build_web_app.py')
run(sys.executable,'scripts/system/check_web_snapshot.py','--skip-build')
run('node',HERE/'inventory.mjs');run(sys.executable,HERE/'preservation.py')
# Current build on8788 and independent aa3116d app/dist on8792 must already be served.
for name in ['master-alignment','coverage','gateway-checks','resilience','home-interactions','library-interactions','intro-checks']:
    run('node',HERE/(name+'.mjs'))
if args.functional_only:
    print('Functional checks complete; performance and capture review still required before publishing.');sys.exit(0)
for name in ['frame-performance','performance','record']:run('node',HERE/(name+'.mjs'))
run('node',HERE/'capture-intro.mjs','after/intro-desktop','1440');run('node',HERE/'capture-intro.mjs','after/intro-mobile','390')
run(sys.executable,HERE/'finalize.py');run(sys.executable,'scripts/system/check_visual_coverage.py')
