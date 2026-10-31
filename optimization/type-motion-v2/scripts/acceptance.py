"""Validate the saved browser evidence and enforce this round's delivery budget."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parents[3]
out = root / 'optimization/type-motion-v2'
checks = []

def check(name, passed, detail=None):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))

for name in ['regression', 'motion-checks']:
    report = json.loads((out / 'after' / (name+'.json')).read_text())
    check(name+' browser checks', all(row['passed'] for row in report['results']), len(report['results']))
axe = json.loads((out/'after/accessibility.json').read_text())
check('No serious/critical accessibility issues', not any(v['impact'] in ['serious','critical'] for v in axe['violations']))
font = json.loads((out/'assets/font-subset.json').read_text())
check('Title glyph coverage', not font['missing'], font['codepoints'])
manifest = json.loads((root/'app/assets/visual/type-motion-manifest.json').read_text())
for asset in manifest['assets']:
    check('Asset SHA256: '+asset['file'], hashlib.sha256((root/'app'/asset['file']).read_bytes()).hexdigest()==asset['sha256'])
budgets = [('app/assets/fonts/lens-editorial-semibold.woff2',60*1024),
           ('app/assets/visual/lens-wordmark.webp',20*1024),
           ('app/assets/vendor/motion-mini-14.9.0.min.js',12*1024),
           ('app/src/story-motion.js',8*1024)]
total = 0
for name, limit in budgets:
    size=(root/name).stat().st_size
    total+=size
    check('Payload budget: '+name,size<=limit,dict(bytes=size,limit=limit))
check('Combined added asset budget',total<=90*1024,dict(bytes=total,limit=90*1024))
baseline=json.loads((out/'baseline.json').read_text())['commit']
paths=subprocess.check_output(['git','ls-tree','-r','--name-only',baseline,'app/data','app/assets/story','app/src','app/styles.css'],cwd=root,text=True).splitlines()
protected=[]
for name in paths:
    previous=subprocess.check_output(['git','show',baseline+':'+name],cwd=root)
    current=(root/name).read_bytes()
    if name=='app/src/story.js':current=current.replace(b'window.LensMotionUI?.onRender(s.chapter);',b'')
    protected.append(dict(file=name,passed=current==previous,baselineSha256=hashlib.sha256(previous).hexdigest()))
csv_same=(out/'after/export-baseline.csv').read_bytes()==(root/'optimization/homepage-pilot/after/export-baseline.csv').read_bytes()
(out/'after/content-fidelity.json').write_text(json.dumps(dict(base=baseline,files=protected,csvIdenticalToPreviousRelease=csv_same),indent=2)+'\n')
check('Protected data, SVG, sources and presentation-only hook',all(row['passed'] for row in protected),len(protected))
check('CSV unchanged',csv_same)
video=json.loads((out/'after/video-manifest.json').read_text())
check('Actual browser recording exists',(out/'after/motion-preview.mp4').stat().st_size>0 and video['frameCount']>20,video['frameCount'])
performance=json.loads((out/'after/performance-summary.json').read_text())['runs']
for device in ['mobile','desktop']:
    before=next(row for row in performance if row['stage']=='before' and row['device']==device)
    after=next(row for row in performance if row['stage']=='after' and row['device']==device)
    check(device+' performance diagnostic',after['scores']['performance']>=before['scores']['performance']-5,dict(before=before['scores'],after=after['scores']))
    check(device+' layout stability',after['metrics']['cumulative-layout-shift']<=.02,after['metrics']['cumulative-layout-shift'])
result=dict(checks=checks,passed=sum(row['passed'] for row in checks),total=len(checks))
(out/'after/acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not all(row['passed'] for row in checks):raise SystemExit(1)
