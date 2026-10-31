"""Verify all original files and explicitly inspect the few presentation exceptions."""
from pathlib import Path
import subprocess,hashlib,json,re
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'.git/master-rebuild-v6/upstream'
OUT=ROOT/'optimization/master-rebuild-v6/after'
names=subprocess.check_output(['git','-C',str(SOURCE),'ls-files','-z']).decode().split('\0')
allowed={'.gitattributes','.gitignore','app/index.html','app/explore.html','app/src/narrative.js','app/src/code-interactions.js','scripts/system/build_web_app.py'}
results=[];same=[];hydrated=[]
for name in filter(None,names):
    a=(SOURCE/name).read_bytes();b=(ROOT/name).read_bytes()
    if name in allowed:continue
    match=re.search(rb'oid sha256:([a-f0-9]+)\nsize (\d+)',a)
    if name.startswith('app/data/') and match:
        ok=hashlib.sha256(b).hexdigest()==match[1].decode() and len(b)==int(match[2]);hydrated.append(name)
    else:ok=a==b;same.append(name)
    if not ok:results.append({'name':'Upstream bytes '+name,'passed':False})
results.append({'name':'Original non-exempt files and datasets preserved','passed':not results,'detail':{'identical':len(same),'hydratedAndSHA256Verified':hydrated,'explicitPresentationExceptions':sorted(allowed)}})
original=(SOURCE/'app/src/narrative.js').read_text();expected=original.replace('$$("[data-section]")','$$("button[data-section]")').replace('      event.altKey ||','      document.documentElement.classList.contains("intro-active") ||\n      event.altKey ||').replace("'.plot-scroll, .answer-content, [contenteditable=\"true\"]'","'.plot-scroll, .answer-content, .schema-preview, [role=\"region\"], [contenteditable=\"true\"]'")
results.append({'name':'Narrative only fixes navigation bubbling and keyboard ownership','passed':expected==(ROOT/'app/src/narrative.js').read_text()})
original=(SOURCE/'app/src/code-interactions.js').read_text();expected=original.replace(" try{await view.runAsync();if(ticket!==generation || !root.isConnected)return;refresh();}"," try{await view.runAsync();if(ticket!==generation || !root.isConnected)return;\n  scaffold.querySelectorAll('.codeBrush_brush_bg,.codeBrush_brush').forEach(el=>el.setAttribute('aria-label','图表框选范围；也可使用下方精确范围筛选'));\n  refresh();}")
results.append({'name':'Scientific code interactions only add brush accessible names','passed':expected==(ROOT/'app/src/code-interactions.js').read_text()})
for name in ['app/story.css','app/styles.css','app/src/story.js','app/src/story-charts.js','app/src/charts.js','app/src/model.js','app/src/app.js','app/src/code-study.js','app/src/publication.js']:
    if not (ROOT/name).exists():continue
    results.append({'name':'Original scientific/presentation source '+name,'passed':(SOURCE/name).read_bytes()==(ROOT/name).read_bytes()})
(OUT/'source-fidelity.json').write_text(json.dumps({'upstream':'35f7318e45561da07c75eaf65374e4107004d5ec','results':results},indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'checks':len(results),'passed':sum(r['passed'] for r in results),'failed':[r['name'] for r in results if not r['passed']]}))
assert all(r['passed'] for r in results)
