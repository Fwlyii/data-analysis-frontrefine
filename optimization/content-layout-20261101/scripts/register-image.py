from pathlib import Path
import hashlib,json,sys,datetime
job=Path('optimization/content-layout-20261101')
p=job/'design/provenance.json'
d=json.loads(p.read_text()) if p.exists() else {'tool':'image_gen.imagegen','calls':[]}
def item(n):
 f=Path(n);b=f.read_bytes();return {'path':str(f),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
prompt,output,origin,kind,*inputs=sys.argv[1:]
d['calls'].append({'id':len(d['calls'])+1,'kind':kind,'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prompt':item(prompt),'output':item(output),'inputs':[item(n) for n in inputs],'generatedSource':origin})
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print({'registered':output,'calls':len(d['calls'])})
