"""Normal, user-authorized fast-forward main publication; never resets or force-pushes."""
from pathlib import Path
import subprocess,json,re,sys
J=Path('optimization/fullsite-closed-loop-20261031')
def run(*args):
 r=subprocess.run(args,capture_output=True,text=True)
 if r.returncode:
  safe=re.sub(r'https://[^\s/@]+:[^\s/@]+@','https://[redacted]@',r.stderr)
  print(safe[-1500:]);raise SystemExit(r.returncode)
 return r.stdout.strip()
assert run('git','branch','--show-current')=='work/lens-fullsite-20261031'
run(sys.executable,'scripts/system/check_visual_coverage.py');run('git','diff','--check');run('git','fetch','origin','main')
# An incoming main commit requires integration/revalidation, never overwriting it.
assert subprocess.run(['git','merge-base','--is-ancestor','origin/main','HEAD'],capture_output=True).returncode==0,'Remote main advanced: integrate and revalidate before publication.'
paths=['README.md','app/README.md','app/index.html','app/explore.html','app/gateway.css','app/refinement.css','app/src/gateway.js','app/src/refinement.js','app/assets/visual','app/visual-coverage.json','scripts/system/check_visual_coverage.py','docs/design-sources.md','docs/visual-refinement-workflow.md',str(J)]
run('git','add','--',*paths);run('git','diff','--cached','--check','--','app','README.md','docs','scripts/system');run('git','commit','-m','Refine LENS visual system with generated alpha planets and full-site evidence')
sha=run('git','rev-parse','HEAD');run('git','switch','main');run('git','merge','--ff-only','work/lens-fullsite-20261031');run('git','push','origin','main')
(J/'release.json').write_text(json.dumps({'releaseCommit':sha,'previewUrl':'https://fwlyii.github.io/data-analysis-frontrefine/','publication':'Normal fast-forward main push after all local gates; Pages status pending.'},indent=2)+'\n')
print(json.dumps({'pushed':True,'releaseCommit':sha}))
