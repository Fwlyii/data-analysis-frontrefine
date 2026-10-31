"""Publish a local evidence manifest only after real browser and performance checks pass."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'optimization/cinematic-intro'
spec=importlib.util.spec_from_file_location('coverage_gate',ROOT/'app/pipeline/scripts/system/check_visual_coverage.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
inventory=json.loads((OUT/'site-inventory.json').read_text())
checks=json.loads((OUT/'after/site-checks.json').read_text())
assert checks['results'] and all(row['passed'] for row in checks['results'])
assert set(checks['matrix']['routes'])=={row['key'] for row in inventory['routes']}
for name,sha in checks['fingerprints'].items():assert gate.digest(ROOT/name)==sha,'Source changed since browser review: '+name
extra=['optimization/cinematic-intro/after/home-regression/regression.json','optimization/cinematic-intro/after/home-regression/motion-checks.json','optimization/cinematic-intro/after/intro-checks.json','optimization/cinematic-intro/after/deep-link-check.json']
for name in extra:
    report=json.loads((ROOT/name).read_text());assert report['results'] and all(row['passed'] for row in report['results']),name
proof={'version':4,'entryDocuments':['explore.html','index.html'],'routes':inventory['routes'],'viewports':checks['matrix']['viewports'],'screenshots':'optimization/cinematic-intro/after/page-audit.json','browserChecks':'optimization/cinematic-intro/after/site-checks.json','additionalBrowserChecks':extra,'performance':'optimization/cinematic-intro/after/performance-summary.json','introReview':{'frames':'optimization/cinematic-intro/after/frame-performance.json','recording':'optimization/cinematic-intro/after/intro-demo-desktop.mp4','duration':5950,'runtimeMedia':False},'fingerprints':checks['fingerprints']}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
gate.check()
paths=subprocess.check_output(['git','ls-tree','-r','--name-only','f353a18','app/data','app/assets/story','app/assets/logos','app/src','app/runtime/app.js','app/runtime/publication.js','app/runtime/code-data.js','app/runtime/story-data.js'],cwd=ROOT,text=True).splitlines()
protected=[]
for name in paths:
    if name in ['app/src/site-shell.js','app/src/story-motion.js']:continue
    prior=subprocess.check_output(['git','show','f353a18:'+name],cwd=ROOT)
    protected.append({'file':name,'passed':prior==(ROOT/name).read_bytes(),'baselineSha256':hashlib.sha256(prior).hexdigest()})
assert all(row['passed'] for row in protected)
(OUT/'after/content-fidelity.json').write_text(json.dumps({'base':'f353a18','files':protected,'presentationExceptions':['site-shell.js and story-motion.js only add an intro-active/pending guard; new intro module never imports experiment data']},indent=2)+'\n')
print('Protected research/data/renderer files unchanged:',len(protected))
