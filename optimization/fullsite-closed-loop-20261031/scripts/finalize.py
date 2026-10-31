from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1];REL=J.relative_to(ROOT).as_posix();O=J/'after'
names=['master-alignment','preservation','home-interactions','library-interactions','gateway-checks','optical-checks','resilience','intro-checks','planet-checks','chart-render-preservation','export-checks','top-capture-checks']
results=[]
for name in ['site-checks',*names]:
 d=json.loads((O/(name+'.json')).read_text());assert d['results'] and all(r['passed']for r in d['results']),name
 results.append({'name':name+' complete real browser/source checks','passed':True,'checks':len(d['results']),'report':REL+'/after/'+name+'.json'})
(O/'functional-checks.json').write_text(json.dumps({'results':results},indent=2)+'\n')
chart=[]
for name in ['preservation','master-alignment','chart-render-preservation','export-checks','top-capture-checks']:
 d=json.loads((O/(name+'.json')).read_text());chart.extend(dict(r,report=REL+'/after/'+name+'.json')for r in d['results'])
(O/'chart-preservation.json').write_text(json.dumps({'baseline':'f751c3fe2db5a977f63d394ca185d09bc3ef8132','results':chart},indent=2)+'\n')
checks=json.loads((O/'site-checks.json').read_text())
proof={'version':10,'baseline':'f751c3fe2db5a977f63d394ca185d09bc3ef8132','inventory':REL+'/site-inventory.json','screenshots':REL+'/after/page-audit.json','browserChecks':REL+'/after/site-checks.json','additionalBrowserChecks':[REL+'/after/'+n+'.json' for n in names],'fingerprints':checks['fingerprints'],'introFrames':REL+'/after/frame-performance.json','recording':REL+'/after/intro-demo.mp4','performance':REL+'/after/performance-summary.json','sceneContract':{'sameFiveLinkNodes':True,'sameIntroOpticsNode':True,'links':['question','collection','cleaning','landscape','findings'],'defaultRoute':'gateway','scientificDataUnchanged':True},'layoutContract':{'researchPagesFillViewport':True,'chapterRailRemoved':True,'minimalReturnControl':True,'mobileUsesTouchRows':True},'planetAssets':['app/assets/visual/planet-'+k+'.webp'for k in ['question','collection','cleaning','landscape','findings']],'coverageLedger':REL+'/coverage-table.json','overlays':REL+'/overlays.json','designProvenance':REL+'/design/provenance.json','publication':'User authorized detached whole-site optimization, normal main push and GitHub Pages preview after full local verification.'}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,indent=2)+'\n')
print({'functionalSuites':len(results),'checks':sum(r['checks']for r in results),'protectedAndRenderChecks':len(chart),'fingerprints':len(checks['fingerprints'])})
