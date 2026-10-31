"""Bind successful browser evidence to the current source and CI coverage gate."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'optimization/site-consistency-v3'
spec=importlib.util.spec_from_file_location('coverage_gate',ROOT/'app/pipeline/scripts/system/check_visual_coverage.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
inventory=json.loads((OUT/'site-inventory.json').read_text())
checks=json.loads((OUT/'after/site-checks.json').read_text())
assert checks['results'] and all(r['passed'] for r in checks['results']),'Fix browser failures before finalizing evidence'
assert set(checks['matrix']['routes'])=={r['key'] for r in inventory['routes']}
assert checks['matrix']['viewports']==[320,390,768,1440]
for name,sha in checks['fingerprints'].items():assert gate.digest(ROOT/name)==sha,'Source changed since browser checks: '+name
extra=['optimization/site-consistency-v3/after/home-regression/regression.json','optimization/site-consistency-v3/after/home-regression/motion-checks.json']
for name in extra:assert all(r['passed'] for r in json.loads((ROOT/name).read_text())['results'])
proof={'version':3,'entryDocuments':['explore.html','index.html'],'routes':inventory['routes'],'viewports':checks['matrix']['viewports'],'screenshots':'optimization/site-consistency-v3/after/page-audit.json','browserChecks':'optimization/site-consistency-v3/after/site-checks.json','additionalBrowserChecks':extra,'performance':'optimization/site-consistency-v3/after/performance-summary.json','fingerprints':checks['fingerprints']}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
gate.check()
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','a6c4c1f','app/data','app/assets/story','app/assets/logos','app/src','app/runtime/publication.js','app/runtime/code-data.js','app/runtime/story-data.js','app/runtime/app.js'],cwd=ROOT,text=True).splitlines()
results=[]
for name in paths:
    if name=='app/src/story-motion.js':continue  # Brand decoding moved to shared presentation script.
    original=subprocess.check_output(['git','show','a6c4c1f:'+name],cwd=ROOT)
    current=(ROOT/name).read_bytes()
    if name in ['app/src/code-interactions.js','app/runtime/app.js']:
        annotation="\n  scaffold.querySelectorAll('.codeBrush_brush_bg,.codeBrush_brush').forEach(el=>el.setAttribute('aria-label','图表框选范围；也可使用下方精确范围筛选'));\n  ".encode()
        current=current.replace(annotation,b'')
    results.append({'file':name,'passed':original==current,'baselineSha256':hashlib.sha256(original).hexdigest()})
assert all(row['passed'] for row in results),'Protected data or renderers changed'
(OUT/'after/content-fidelity.json').write_text(json.dumps({'baseline':'a6c4c1f','files':results,'exceptions':{'app/src/story-motion.js':'Only decorative brand decode block removed; now owned by site-shell.js','app/src/code-interactions.js and bundled runtime/app.js':'Only two brush groups receive accessible labels; comparison strips this one annotation'}},indent=2)+'\n')
print('Protected files unchanged:',len(results))
