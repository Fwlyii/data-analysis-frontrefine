from pathlib import Path
import subprocess,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
BASE='aa3116d69ce7c88a6fb03747da14e38655a0d17f'
paths=subprocess.check_output(['git','ls-tree','-rz','--name-only',BASE,'--','app/data','app/assets','reports/figures','data/processed','app/src']).decode().split('\0')
allowed={'app/src/intro.js','app/src/narrative.js','app/src/story.js'}
checked=[];failures=[]
for name in filter(None,paths):
    if name in allowed:continue
    original=subprocess.check_output(['git','show',BASE+':'+name]);current=(ROOT/name).read_bytes()
    checked.append(name)
    if original!=current:failures.append(name)
results=[{'name':'Original data, figures, fonts, vendors and scientific source bytes preserved','passed':not failures,'detail':{'checked':len(checked),'failures':failures,'explicitRouteAndIntroExceptions':sorted(allowed)}}]
for name in ['gateway.js','intro.js','narrative.js','story.js']:
    results.append({'name':'Source/runtime sync '+name,'passed':(ROOT/'app/src'/name).read_bytes()==(ROOT/'app/dist/runtime'/name).read_bytes()})
results.append({'name':'Gateway runtime adds no video or raster animation','passed':not list((ROOT/'app/dist').rglob('*.mp4')) and not list((ROOT/'app/dist').rglob('*.webm'))})
(ROOT/'optimization/knowledge-gateway/after/preservation.json').write_text(json.dumps({'baseline':BASE,'results':results},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'checks':len(results),'passed':sum(r['passed']for r in results),'failures':failures}))
assert all(r['passed']for r in results)
