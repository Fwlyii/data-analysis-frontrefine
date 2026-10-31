"""Independent finish gate for the detached visual task; never edits results."""
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[3]
JOB=Path(__file__).resolve().parents[1]
BASE='f751c3fe2db5a977f63d394ca185d09bc3ef8132'

def load(path):
    return json.loads(path.read_text())

def artifact(value):
    value=value['path'] if isinstance(value,dict) else value
    path=(ROOT/value).resolve()
    assert path.is_relative_to(ROOT),'Artifact outside workspace'
    assert path.is_file() and path.stat().st_size>0,'Missing artifact: '+str(path)
    return path

def check():
    config=load(ROOT/'.git/visual-loop/runtime-config.json')
    protection=JOB/'protected-files.json'
    assert hashlib.sha256(protection.read_bytes()).hexdigest()==config['protectionManifestSHA'],'Protection manifest was changed'
    protected=load(protection)
    assert protected['baseline']==BASE and len(protected['files'])==519
    for name,sha in protected['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'Protected content changed: '+name
    result=load(JOB/'completion.json')
    assert result['status']=='completed' and result['baseline']==BASE and result['incomplete']==[]
    assert result['previewUrl'].startswith('https://fwlyii.github.io/data-analysis-frontrefine/')
    release=result['releaseCommit']
    assert subprocess.check_output(['git','cat-file','-t',release],cwd=ROOT,text=True).strip()=='commit'
    subprocess.run(['git','merge-base','--is-ancestor',release,'HEAD'],cwd=ROOT,check=True,capture_output=True)
    inventory=load(JOB/'site-inventory.json');routes={r['key'] for r in inventory['routes']}
    assert len(routes)>=93,'Missing routes'
    ledger=load(JOB/'coverage-table.json')['rows']
    assert {(r['routeKey'],r['device'])for r in ledger}=={(r,d)for r in routes for d in ['desktop','mobile']}
    assert len(ledger)==len(routes)*2,'Duplicated coverage rows'
    for row in ledger:
        for field in ['beforeScreenshot','referenceImage','afterScreenshot']:
            assert artifact(row[field]).stat().st_size>1000
        assert all(isinstance(row[k],(int,float)) and 0<=row[k]<=100 for k in ['beforeScore','referenceScore','afterScore','fidelityScore'])
        assert len(row['reason'].strip())>=12
        assert row['decision'] in ['improved','kept_with_reason']
        if row['decision']=='improved':
            assert row['referenceScore']>=row['beforeScore']+5 and row['fidelityScore']>=90
            assert row['afterScore']>=row['referenceScore']-5
    overlays=load(JOB/'overlays.json')['states'];assert len(overlays)>=11
    for state in overlays:
        artifact(state['beforeScreenshot']);artifact(state['afterScreenshot'])
    provenance=load(JOB/'design/provenance.json');assert len(provenance['calls'])>=3
    for call in provenance['calls']:
        artifact(call['prompt']);artifact(call['output'])
        for value in call.get('inputs',[]):artifact(value)
    artifact(str((JOB/'design/visual-scores.json').relative_to(ROOT)))
    for name in ['functional-checks','chart-preservation','public-assets','public-browser']:
        report=load(JOB/'after'/f'{name}.json')
        assert report['results'] and all(row['passed'] is True for row in report['results']),name+' failed'
    published=load(JOB/'after/public-assets.json')
    dist=ROOT/'app/dist';local={p.relative_to(dist).as_posix():p for p in dist.rglob('*')if p.is_file()}
    assert {row['path']for row in published['results']}==set(local),'Incomplete live asset comparison'
    for row in published['results']:
        sha=hashlib.sha256(local[row['path']].read_bytes()).hexdigest()
        assert row['expectedSHA256']==row['actualSHA256']==sha,'Published artifact differs: '+row['path']
    assert (JOB/'after/intro-demo.mp4').stat().st_size>10000
    assert (JOB/'RESULT.md').stat().st_size>1000
    planets=result.get('planetAssets',[]);assert len(planets)==5,'Missing the five actual transparent planet assets'
    for value in planets:
        path=artifact(value)
        assert path.is_relative_to(ROOT/'app/assets')
        alpha=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vf','alphaextract','-frames:v','1','-f','rawvideo','-pix_fmt','gray','pipe:1'],stderr=subprocess.PIPE)
        assert alpha and min(alpha)==0 and max(alpha)==255,'Planet must have actual transparency: '+str(path)
    gate=subprocess.run([sys.executable,'scripts/system/check_visual_coverage.py'],cwd=ROOT,text=True,capture_output=True)
    assert gate.returncode==0,'Publication gate failed: '+gate.stdout[-1500:]+gate.stderr[-1500:]
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    assert not dirty,'Uncommitted final changes remain'
    return {'verified':True,'baseline':BASE,'releaseCommit':release,'routes':len(routes),'screenshots':len(ledger),'protectedFiles':len(protected['files']),'previewUrl':result['previewUrl']}

if __name__=='__main__':
    try:
        print(json.dumps(check(),ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'verified':False,'reason':str(exc)},ensure_ascii=False));sys.exit(1)
