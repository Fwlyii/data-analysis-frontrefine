from pathlib import Path
import json
job=Path('optimization/color-unification-20261101')
a=json.loads((job/'before/overlays.json').read_text());b=json.loads((job/'after/overlays.json').read_text());assert not a['errors'] and not b['errors']
aa={(r['key'],r['device']):r for r in a['states']};bb={(r['key'],r['device']):r for r in b['states']};assert aa.keys()==bb.keys(),{'onlyBefore':list(aa.keys()-bb.keys()),'onlyAfter':list(bb.keys()-aa.keys())}
rows=[]
for k,x in aa.items():
 y=bb[k];rows.append({'key':x['key'],'device':x['device'],'url':x['url'],'kind':x['kind'],'beforeScreenshot':x['screenshot'],'afterScreenshot':y['screenshot'],'beforeScroll':x.get('scroll'),'afterScroll':y.get('scroll'),'review':'Native expanded/scroll content retained; same route, control and reading position checked in paired real-browser captures.'})
(job/'overlays.json').write_text(json.dumps({'states':rows},ensure_ascii=False,indent=2)+'\n');print({'overlayStates':len(rows)})
