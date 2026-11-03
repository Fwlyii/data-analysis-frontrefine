"""Verify the current scientific/source contract and optionally a fresh browser run.

No recording, screenshot archive or historical optimization directory is required.
Pages additionally passes --browser-report after running the current 93-route smoke.
"""
from pathlib import Path
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_sha(p):
 b=p.read_bytes()
 if p.suffix=='.html':b=re.sub(rb'\?v=[a-f0-9]+',b'?v=BUILD',b)
 if p.suffix=='.css':b=re.sub(rb'[ \t]+$',b'',b,flags=re.M)
 return hashlib.sha256(b).hexdigest()
def check(browser_report=None):
 proof=json.loads((ROOT/'app/visual-coverage.json').read_text());assert proof['version'] in (14,16)
 fixtures=ROOT/'tests/fixtures';baseline=json.loads((fixtures/'accepted-release.json').read_text());accepted=baseline;changes={}
 if proof['version']==16:
  from record_chart_motion_review import PATHS,ADDED,BASE,validate_science
  review=json.loads((fixtures/'chart-motion-ui-review.json').read_text());assert review['baselineCommit']==BASE
  assert set(review['changes'])==set(PATHS)and set(review['added'])==set(ADDED)
  for path,item in review['changes'].items():
   current=(ROOT/path).read_text()
   if path.endswith('.html'):current=re.sub(r'\?v=[a-f0-9]+','?v=BUILD',current)
   assert item['before']==baseline['fingerprints'][path]and source_sha(ROOT/path)==item['after'],'Unreviewed source change: '+path
   for edit in reversed(item['edits']):
    assert current.count(edit['new'])==1,'Reviewed patch is not unique: '+path
    current=current.replace(edit['new'],edit['old'],1)
   assert hashlib.sha256(current.encode()).hexdigest()==item['before'],'Original logic cannot be reconstructed: '+path
  for path,h in review['added'].items():assert source_sha(ROOT/path)==h
  accepted=json.loads((fixtures/'chart-motion-release.json').read_text());assert accepted['baselineFingerprints']==baseline['fingerprints']
  validate_science(json.loads((fixtures/'chart-motion-scientific-review.json').read_text()),accepted['fingerprints'])
  changes=review['changes']
 protected=fixtures/'research-protection.json';assert sha(protected)=='364b630f923c2c60b96369ee0f014d8ba25ad67c68f63bb8ac4b6aaf4ac92d03'
 manifest=json.loads(protected.read_text());assert len(manifest['files'])==1100
 for path,h in manifest['files'].items():
  if path in changes:assert changes[path]['originalProtectedSHA256']==h and source_sha(ROOT/path)==changes[path]['after'],'Unreviewed protected source: '+path
  else:assert sha(ROOT/path)==h,'Protected scientific/source file changed: '+path
 for path,h in accepted['fingerprints'].items():assert source_sha(ROOT/path)==h,'Source changed: run the browser review and explicitly review/update the accepted baseline: '+path
 inventory=json.loads((fixtures/'routes.json').read_text());routes=inventory['routes'];keys={r['key']for r in routes};assert len(keys)==len(routes)==93
 source=(ROOT/'app/src/app.js').read_text();charts=re.findall(r'(\w+): "[^"]+"',re.search(r'const library = \{(.*?)\n\};',source,re.S)[1])
 code=re.findall(r'(\w+):',re.search(r'const VIEWS = \{(.*?)\};',(ROOT/'app/src/code-study.js').read_text(),re.S)[1])
 assert {'chart-'+c for c in charts}=={r['key']for r in routes if r.get('chart')and not r.get('empty')}
 assert {'code-'+c for c in code}=={r['key']for r in routes if r['family']=='code'}
 narrative=json.loads((ROOT/'app/data/narrative-evidence.json').read_text())
 assert {f'landscape-{d}-{m}-{v}'for d,c in narrative['directions'].items()for m in c['models']for v in ['curve','heatmap']}=={r['key']for r in routes if r['family']=='landscape'}
 science=json.loads((fixtures/'scientific-comparison.json').read_text());assert science['fingerprints']==baseline['fingerprints']
 assert len(science['results'])==184 and sum(r['actualGraphs']for r in science['results'])==188
 for r in science['results']:
  assert r['passed']and r['actualGraphs']==r['expectedGraphs']
  assert all(g['sameMarkup']and g['sameStyles']and g['sameCanonicalPixels']for g in r['graphs'])
 exports=json.loads((fixtures/'export-comparison.json').read_text())['results'];assert len(exports)==31
 for r in exports:
  assert r['passed'];path=fixtures/'exports'/Path(r['afterFile']).name
  assert sha(path)==r['afterSHA256'],'Scientific export fixture changed: '+str(path)
 assert sorted(p.name for p in (ROOT/'app/dist').glob('*.html'))==sorted(inventory['entryDocuments'])
 assert {p.name for p in (ROOT/'app/dist/runtime').glob('*.js')}=={'summary.js','publication.js','features.js','code-features.js','code-data.js','app.js','story-data.js','story.js','story-charts.js','narrative-data.js','narrative.js','intro.js','refinement.js','gateway.js','interaction.js'} | ({'chart-motion.js'} if proof['version']==16 else set())
 for name in inventory['entryDocuments']:
  html=(ROOT/'app/dist'/name).read_text();assert re.search(r'interaction.css\?v=[a-f0-9]{12}',html)and re.search(r'runtime/interaction.js\?v=[a-f0-9]{12}',html)
 for name in ['interaction.js','story-charts.js','intro.js','gateway.js']+(['chart-motion.js']if proof['version']==16 else []):assert (ROOT/'app/src'/name).read_bytes()==(ROOT/'app/dist/runtime'/name).read_bytes()
 if proof['version']==16:
  assert (ROOT/'app/chart-motion.css').read_bytes()==(ROOT/'app/dist/chart-motion.css').read_bytes()
  for name in inventory['entryDocuments']:
   html=(ROOT/'app/dist'/name).read_text();assert re.search(r'chart-motion.css\?v=[a-f0-9]{12}',html)and re.search(r'runtime/chart-motion.js\?v=[a-f0-9]{12}',html)
 assert not any(p.suffix.lower()in{'.mp4','.mov','.webm','.m4a'}for p in (ROOT/'app/dist').rglob('*'))
 result={'routes':len(routes),'charts':len(charts),'codeViews':len(code),'protectedFiles':len(manifest['files']),'scientificComparisons':184,'exportFixtures':31,'reviewedMotionSources':list(changes),'freshMotionScientificStates':184 if changes else 0,'staticVerified':True,'recordingsRequired':False}
 if browser_report:
  report=json.loads(Path(browser_report).read_text());assert report['fingerprints']==accepted['fingerprints'],'Browser checked different production sources'
  assert report['routeCount']==93 and len(report['results'])>=450 and all(r['passed']for r in report['results'])
  for key in keys:assert any(r['name']==key+' live correct scene and visible content'and r['passed']for r in report['results']),key
  assert not report['errors']and not report['failed'];result.update(freshBrowserChecks=len(report['results']),browserVerified=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--browser-report',type=Path);a=p.parse_args();print(json.dumps(check(a.browser_report)))
