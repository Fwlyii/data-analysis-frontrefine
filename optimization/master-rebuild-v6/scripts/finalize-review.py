from pathlib import Path
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[3]
REL='optimization/master-rebuild-v6'
OUT=ROOT/REL/'after'
checks=json.loads((OUT/'site-checks.json').read_text())
reports=['master-alignment','source-fidelity','home-interactions','library-interactions','intro-checks','typography-checks']
for name in ['site-checks',*reports]:
    report=json.loads((OUT/(name+'.json')).read_text())
    assert report['results'] and all(r['passed'] for r in report['results']),'Resolve failed checks before finalizing: '+name
proof={'version':7,'baseline':'35f7318e45561da07c75eaf65374e4107004d5ec','restorationCheckpoint':'73a1e8c','inventory':REL+'/site-inventory.json','screenshots':REL+'/after/page-audit.json','browserChecks':REL+'/after/site-checks.json','additionalBrowserChecks':[REL+'/after/'+n+'.json' for n in reports],'fingerprints':checks['fingerprints'],'introFrames':REL+'/after/frame-performance.json','recording':REL+'/after/intro-demo-desktop.mp4','performance':REL+'/after/performance-summary.json','designInputs':['before/home-desktop.png','before/design-desktop.png','before/library-desktop.png'],'designOutputs':['design/candidates-a-b.png','design/screenshot-feedback.png'],'implementationBrief':REL+'/codex-implementation-brief.md'}
(ROOT/'app/visual-coverage.json').write_text(json.dumps(proof,indent=2)+'\n')
print('Bound v6 browser evidence to',len(checks['fingerprints']),'current source files.')
