"""Reproduce the v6 review. Start current app/dist on 8788, baseline on 8790 first."""
from pathlib import Path
import subprocess,sys,argparse,shutil
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--skip-build',action='store_true')
p.add_argument('--functional-only',action='store_true',help='Do not overwrite performance/capture evidence')
args=p.parse_args()
def run(*argv):
    print('+',' '.join(map(str,argv)),flush=True)
    subprocess.run(list(map(str,argv)),cwd=ROOT,check=True)
if not args.skip_build:
    # runtime is ignored, generated output; removed modules must not survive a rebuild.
    shutil.rmtree(ROOT/'app/runtime',ignore_errors=True)
    run(sys.executable,'scripts/system/build_web_app.py')
run(sys.executable,'scripts/system/check_web_snapshot.py','--skip-build')
run('node',HERE/'inventory.mjs')
run(sys.executable,HERE/'fidelity.py')
# Sequential by design: browser tasks never race against a build or each other.
for script in ['master-alignment','coverage','home-interactions','library-interactions','intro-checks','typography-checks']:
    run('node',HERE/(script+'.mjs'))
if args.functional_only:
    print('Functional review finished; full performance/capture review is still required before publication.')
    sys.exit(0)
if not args.functional_only:
    for script in ['frame-performance','performance','record-intro']:
        run('node',HERE/(script+'.mjs'))
    run('node',HERE/'capture-intro.mjs','after/intro-desktop','1440')
    run('node',HERE/'capture-intro.mjs','after/intro-mobile','390')
run(sys.executable,HERE/'finalize-review.py')
run(sys.executable,'scripts/system/check_visual_coverage.py')
