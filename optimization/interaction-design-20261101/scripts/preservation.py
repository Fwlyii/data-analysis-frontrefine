from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1]
m=json.loads((J/'protected-files.json').read_text());results=[]
for name,expected in m['files'].items():results.append({'name':name+' byte preservation','passed':hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected})
for name in ['styles.css','story.css','refinement.css','content-layout.css','intro.css','gateway.css','palette.css','interaction.css']:results.append({'name':name+' source/build identical','passed':(ROOT/'app'/name).read_bytes()==(ROOT/'app/dist'/name).read_bytes()})
results.append({'name':'New interaction source/build identical','passed':(ROOT/'app/src/interaction.js').read_bytes()==(ROOT/'app/dist/runtime/interaction.js').read_bytes()})
results.append({'name':'No video or frame sequence shipped','passed':not list((ROOT/'app/dist').rglob('*.mp4'))})
(J/'after/preservation.json').write_text(json.dumps({'baseline':m['baseline'],'results':results},indent=2)+'\n');print({'checks':len(results),'passed':sum(x['passed']for x in results)});assert all(x['passed']for x in results)
