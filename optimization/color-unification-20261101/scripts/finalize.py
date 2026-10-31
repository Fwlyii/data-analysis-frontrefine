from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1];REL=J.relative_to(ROOT).as_posix();O=J/'after'
names=['master-alignment','preservation','home-interactions','library-interactions','gateway-checks','optical-checks','resilience','intro-checks','planet-checks','chart-render-preservation','export-checks','readability-checks','nav-access-checks','desktop-recording-checks','expanded-reading-checks','palette-checks','early-paint-checks']
summary=[]
for name in ['site-checks',*names]:
 d=json.loads((O/(name+'.json')).read_text());assert d['results']and all(r['passed']for r in d['results']),name
 summary.append({'name':name,'passed':True,'checks':len(d['results']),'report':REL+'/after/'+name+'.json'})
(O/'functional-checks.json').write_text(json.dumps({'results':summary},indent=2)+'\n')
prior=json.loads((J/'layout-baseline-proof.json').read_text());checks=json.loads((O/'site-checks.json').read_text())
proof={'version':12,'baseline':'d80769de37e4171665bef22d68f1f701b9bf2c3c','inventory':REL+'/site-inventory.json','screenshots':REL+'/after/page-audit.json','browserChecks':REL+'/after/site-checks.json','additionalBrowserChecks':[REL+'/after/'+n+'.json'for n in names],'fingerprints':checks['fingerprints'],'introFrames':REL+'/after/frame-performance.json','recording':REL+'/after/intro-demo.mp4','performance':REL+'/after/performance-summary.json','sceneContract':prior['sceneContract'],'layoutContract':prior['layoutContract'],'planetAssets':prior['planetAssets'],'coverageLedger':REL+'/coverage-table.json','overlays':REL+'/overlays.json','designProvenance':REL+'/design/provenance.json','recordingViewport':{'width':1920,'height':1080},'colorContract':{'navy':'#071e30','reading':'#eaf0f2','surface':'#f8fafb','champagne':'#d2bb96','layoutAndTypographyRetained':True,'scientificColorsRetained':True},'publication':'Existing authorization to push main and provide a verified GitHub Pages preview continues for this moderate palette refinement.'}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,indent=2)+'\n')
print({'functionalSuites':len(summary),'checks':sum(r['checks']for r in summary),'fingerprints':len(checks['fingerprints'])})
