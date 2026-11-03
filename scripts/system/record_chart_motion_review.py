"""Record reviewed motion patches only after fresh browser/scientific evidence.

Original 1100-file manifest, 184 scientific fixtures and 31 golden exports are
never rewritten. The separate review stores reversible patches against main.
"""
from pathlib import Path
import argparse,difflib,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[2]
BASE='7de85e836e8bc0f7c28c79188b71f1818c0aa234'
PATHS=['app/index.html','app/explore.html','app/src/app.js','app/src/charts.js','app/src/code-interactions.js','app/src/interaction.js','app/src/story.js','scripts/system/build_web_app.py']
ADDED=['app/src/chart-motion.js','app/chart-motion.css']
def normal(path,text):
 if path.endswith('.html'):text=re.sub(r'\?v=[a-f0-9]+','?v=BUILD',text)
 if path.endswith('.css'):text=re.sub(r'[ \t]+$','',text,flags=re.M)
 return text
def digest(path,text):return hashlib.sha256(normal(path,text).encode()).hexdigest()
def validate_science(report,fingerprints):
 assert report['baseline']==BASE and report['fingerprints']==fingerprints
 assert not report['errors']
 rows=report['results'];assert len(rows)==184 and sum(r['actualGraphs']for r in rows)==188
 routes=json.loads((ROOT/'tests/fixtures/routes.json').read_text())['routes']
 assert {(r['key'],r['width'])for r in rows}=={(r['key'],w)for r in routes if r.get('section')!='gateway'for w in(1440,1920)}
 assert all(r['passed']and r['actualGraphs']==r['expectedGraphs']and all(g['sameMarkup']and g['sameStyles']and g['sameCanonicalPixels']and g['sameBounds']for g in r['graphs'])for r in rows)
 assert len(report['normalResults'])==13 and all(r['passed']and all(g['sameMarkup']and g['sameStyles']and g['sameCanonicalPixels']for g in r['graphs'])for r in report['normalResults'])
 assert {r['name']for r in report['normalResults']}=={r['key']+' normal final geometry/style/pixels'for r in routes if r.get('chart')and not r.get('empty')}
 assert len(report['exports'])==31 and all(r['passed']for r in report['exports'])
 assert {r['name']for r in report['exports']}=={r['name']for r in json.loads((ROOT/'tests/fixtures/export-comparison.json').read_text())['results']}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--science-report',type=Path,required=True);p.add_argument('--browser-report',type=Path,required=True);p.add_argument('--motion-report',type=Path,required=True);a=p.parse_args()
 cmd="import{fingerprints}from'./tests/browser/source-fingerprints.mjs';console.log(JSON.stringify(await fingerprints()));"
 fingerprints=json.loads(subprocess.check_output(['node','--input-type=module','-e',cmd],cwd=ROOT))
 science=json.loads(a.science_report.read_text());validate_science(science,fingerprints)
 for file,minimum in[(a.browser_report,460),(a.motion_report,210)]:
  report=json.loads(file.read_text());assert report['fingerprints']==fingerprints and report['routeCount']==93
  assert len(report['results'])>=minimum and all(r['passed']for r in report['results'])and not report['errors']and not report['failed']
  routes=json.loads((ROOT/'tests/fixtures/routes.json').read_text())['routes']
  suffix=' reduced-motion remains finite and original layout fits'if file==a.motion_report else' live correct scene and visible content'
  assert all(any(r['name']==route['key']+suffix and r['passed']for r in report['results'])for route in routes)
 fixture=ROOT/'tests/fixtures';baseline=json.loads((fixture/'accepted-release.json').read_text());protected=json.loads((fixture/'research-protection.json').read_text())['files']
 review={'baselineCommit':BASE,'policy':'Reviewed chart-local timing/emphasis, lifecycle, original-control playback and exact original-cohort click integration. No data, geometry, axis, normal style or scientific calculation changes. Reversible patches reconstruct the accepted original sources exactly.','changes':{},'added':{}}
 for path in PATHS:
  old=normal(path,subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT).decode());new=normal(path,(ROOT/path).read_text());assert digest(path,old)==baseline['fingerprints'][path]
  before=old.splitlines(keepends=True);after=new.splitlines(keepends=True);edits=[]
  for group in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_grouped_opcodes(2):edits.append({'old':''.join(before[group[0][1]:group[-1][2]]),'new':''.join(after[group[0][3]:group[-1][4]])})
  restored=new
  for edit in reversed(edits):
   assert restored.count(edit['new'])==1,path;restored=restored.replace(edit['new'],edit['old'],1)
  assert restored==old,path
  review['changes'][path]={'before':digest(path,old),'after':digest(path,new),'originalProtectedSHA256':protected.get(path),'edits':edits}
 for path in ADDED:review['added'][path]=digest(path,(ROOT/path).read_text())
 (fixture/'chart-motion-ui-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
 # Keep actual comparison evidence, not stale historical PASS values.
 (fixture/'chart-motion-scientific-review.json').write_text(json.dumps(science,ensure_ascii=False,indent=2)+'\n')
 (fixture/'chart-motion-release.json').write_text(json.dumps({'variant':'chart-motion','baselineCommit':BASE,'baselineFingerprints':baseline['fingerprints'],'fingerprints':fingerprints,'review':'chart-motion-ui-review.json','scientificReview':'chart-motion-scientific-review.json'},indent=2)+'\n')
 print(json.dumps({'reviewedPatches':len(PATHS),'newSources':len(ADDED),'sources':len(fingerprints),'freshScientificStates':184,'freshNormalEndpoints':13,'freshExports':31,'originalFixturesRewritten':False}))
if __name__=='__main__':main()
