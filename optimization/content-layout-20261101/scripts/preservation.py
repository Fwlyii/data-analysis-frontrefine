from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];JOB=Path(__file__).resolve().parents[1]
manifest=json.loads((JOB/'protected-files.json').read_text());results=[]
for name,sha in manifest['files'].items():
 actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest();results.append({'name':'Protected bytes: '+name,'passed':actual==sha,'expectedSHA256':sha,'actualSHA256':actual})
for name in ['gateway.js','intro.js','refinement.js','narrative.js','story.js']:
 results.append({'name':'Source/runtime sync '+name,'passed':(ROOT/'app/src'/name).read_bytes()==(ROOT/'app/dist/runtime'/name).read_bytes()})
results.append({'name':'No video/GIF/image sequence in production','passed':not any(list((ROOT/'app/dist').rglob('*.'+ext)) for ext in ['mp4','webm','gif'])})
(JOB/'after/preservation.json').write_text(json.dumps({'baseline':manifest['baseline'],'results':results},indent=2)+'\n');print({'files':len(manifest['files']),'passed':sum(r['passed']for r in results),'checks':len(results)});assert all(r['passed']for r in results)
