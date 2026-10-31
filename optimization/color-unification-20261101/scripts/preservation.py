from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1]
manifest=json.loads((J/'protected-files.json').read_text());results=[]
for name,sha in manifest['files'].items():results.append({'name':name+' byte preservation','passed':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha})
for name in ['styles.css','story.css','refinement.css','content-layout.css','intro.css','gateway.css','palette.css']:results.append({'name':name+' source/build identical','passed':(ROOT/'app'/name).read_bytes()==(ROOT/'app/dist'/name).read_bytes()})
results.append({'name':'No video or frame sequence shipped in product','passed':not list((ROOT/'app/dist').rglob('*.mp4'))})
(J/'after/preservation.json').write_text(json.dumps({'baseline':manifest['baseline'],'results':results},indent=2)+'\n')
print({'protectedFiles':len(manifest['files']),'checks':len(results),'passed':sum(r['passed']for r in results)})
assert all(r['passed']for r in results)
