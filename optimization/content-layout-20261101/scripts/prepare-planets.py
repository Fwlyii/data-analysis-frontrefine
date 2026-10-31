from pathlib import Path
import subprocess,json,hashlib
job=Path('optimization/content-layout-20261101');results=[]
def info(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
for key in ['question','collection','cleaning','landscape','findings']:
 src=job/'design'/f'planet-{key}.png';out=Path('app/assets/visual')/f'planet-{key}.webp'
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(src),'-vf','scale=512:512:flags=lanczos','-frames:v','1','-c:v','libwebp','-quality','88','-compression_level','6',str(out)],check=True)
 a=subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-vf','alphaextract','-frames:v','1','-f','rawvideo','-pix_fmt','gray','pipe:1'])
 results.append({'name':key+' transparent static decorative asset','passed':min(a)==0 and max(a)==255,'source':info(src),'runtime':info(out),'alpha':{'min':min(a),'max':max(a),'clearPixels':a.count(0),'opaquePixels':a.count(255),'pixels':len(a)},'conversion':'FFmpeg Lanczos resize to512px and WebP quality88; preserves generated alpha; no recoloring, painted mask or replacement imagery'})
(job/'assets/planet-validation.json').write_text(json.dumps({'results':results},indent=2)+'\n');assert all(r['passed'] for r in results)
prov=json.loads((job/'design/provenance.json').read_text())
for r in results:
 call=next(c for c in prov['calls'] if c['output']['path']==r['source']['path']);call['runtime']=r['runtime']
(job/'design/provenance.json').write_text(json.dumps(prov,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'assets':5,'totalBytes':sum(r['runtime']['bytes'] for r in results),'passed':all(r['passed'] for r in results)}))
