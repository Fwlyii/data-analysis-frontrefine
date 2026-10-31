from pathlib import Path
import json
J=Path('optimization/fullsite-closed-loop-20261031');out=J/'after';p=out/'public-browser.json';d=json.loads(p.read_text());core=[r for r in d['results'] if not r.get('externalReport')]
for name,rel in [('93 real online routes at desktop/mobile','public-routes/site-checks.json'),('Original home online interactions','public-ui/home-interactions.json'),('Original library online interactions','public-ui/library-interactions.json'),('All scientific online SVG/CSV exports','public-export-checks.json')]:
 q=json.loads((out/rel).read_text());assert q['results'] and all(r['passed'] for r in q['results']),rel
 core.append({'name':name,'passed':True,'checks':len(q['results']),'externalReport':(out/rel).as_posix()})
d['results']=core;p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print({'publicChecks':sum(r.get('checks',1)for r in core),'summaries':len(core)})
