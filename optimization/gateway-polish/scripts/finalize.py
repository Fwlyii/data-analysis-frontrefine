from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
REL='optimization/gateway-polish'
OUT=ROOT/REL/'after'
checks=json.loads((OUT/'site-checks.json').read_text())
names=['master-alignment','preservation','home-interactions','library-interactions','gateway-checks','optical-checks','resilience','intro-checks']
for name in ['site-checks',*names]:
    d=json.loads((OUT/(name+'.json')).read_text())
    assert d['results'] and all(r['passed'] for r in d['results']),'Resolve failed report: '+name
proof={'version':9,'baseline':'f44a54f93760a8c9a51c1762ace002834c3d670b','inventory':REL+'/site-inventory.json','screenshots':REL+'/after/page-audit.json','browserChecks':REL+'/after/site-checks.json','additionalBrowserChecks':[REL+'/after/'+n+'.json'for n in names],'fingerprints':checks['fingerprints'],'introFrames':REL+'/after/frame-performance.json','recording':REL+'/after/gateway-demo-desktop.mp4','performance':REL+'/after/performance-summary.json','sceneContract':{'sameFiveLinkNodes':True,'sameIntroOpticsNode':True,'links':['question','collection','cleaning','landscape','findings'],'defaultRoute':'gateway','scientificDataUnchanged':True},'layoutContract':{'researchPagesFillViewport':True,'chapterRailRemoved':True,'minimalReturnControl':True,'mobileUsesTouchRows':True},'designProvenance':REL+'/design/provenance.json','publication':'User explicitly authorized pushing this gateway version to main and publishing a Pages preview after local verification.'}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Bound gateway review to',len(checks['fingerprints']),'source/input files.')
