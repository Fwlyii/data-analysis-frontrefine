"""Fail Pages publication when visual evidence is missing, failed or stale."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
APP=ROOT/'app'
def digest(path):
    value=path.read_bytes()
    if path.suffix=='.html':value=re.sub(rb'\?v=[a-f0-9]+',b'?v=BUILD',value)
    if path.suffix=='.css':value=re.sub(rb'[ \t]+$',b'',value,flags=re.M)
    return hashlib.sha256(value).hexdigest()
def check():
    proof=json.loads((APP/'visual-coverage.json').read_text())
    inventory=json.loads((ROOT/proof['inventory']).read_text());routes=inventory['routes'];keys={r['key'] for r in routes}
    assert len(keys)==len(routes)==92,'Regenerate route inventory and classify new routes'
    assert sorted(p.name for p in (APP/'dist').glob('*.html'))==sorted(inventory['entryDocuments'])
    # Re-derive inventory from actual source, so a new view cannot silently escape review.
    source=(APP/'src/app.js').read_text();charts=re.findall(r'(\w+): "[^"]+"',re.search(r'const library = \{(.*?)\n\};',source,re.S)[1])
    views=re.findall(r'(\w+):',re.search(r'const VIEWS = \{(.*?)\};',(APP/'src/code-study.js').read_text(),re.S)[1])
    data=json.loads((APP/'data/narrative-evidence.json').read_text())
    expected={'deck-'+s for s in ['question','collection','cleaning']}|{f'landscape-{d}-{m}-{v}' for d,c in data['directions'].items() for m in c['models'] for v in ['curve','heatmap']}|{'story-concise-baseline','story-concise-cross','story-position','story-repair-qwen','story-repair-qwen3'}|{'story-language-'+t for t in ['math500','gsm8k','mmlu']}|{f'story-limits-{m}-{t}-{f}' for m in ['deepseek','hy4','qwen','qwen3'] for t in ['math500','gsm8k','mmlu'] for f in ['WordLimit','CharLimit','TokenLimit']}|{'chart-'+c for c in charts}|{'code-'+v for v in views}|{'discovery-'+str(i+1) for i in range(len(re.findall(r'"[^"]+"',re.search(r'const chapters = \[(.*?)\];',source)[1])))}|{'efficiency','efficiency-prompts','position-matrix','position-profile','chart-flow-empty'}
    assert keys==expected,'Source route graph changed'
    audit=json.loads((ROOT/proof['screenshots']).read_text());rows=audit['rows']
    assert len(rows)==len(routes)*2
    for r in routes:
        for device in ['desktop','mobile']:
            row=next(x for x in rows if x['key']==r['key'] and x['device']==device)
            assert row['selectedViewMatches'] and not row['overflow'] and row['brandVisible'],r['key']
            assert (ROOT/proof['screenshots']).parent.joinpath(r['key']+'-'+device+'.png').stat().st_size>1000
            assert all(i['complete'] and i['naturalWidth']>0 and i['width']>0 and i['height']>0 for i in row['images'])
            assert all((s['painted']>=3 or s.get('interactionLayer')) and s['opacity']>.95 and not s['unresolved'] and not s['invalid'] for s in row['svgs'])
            assert all(i['passed'] for i in row['embeddedImages'])
    checks=json.loads((ROOT/proof['browserChecks']).read_text())
    assert set(checks['matrix']['routes'])==keys and sorted(checks['matrix']['viewports'])==[320,390,768,1366,1440]
    assert len([r for r in checks['results'] if 'decoded/painted/layout' in r['name']])==len(routes)*5
    for name in [proof['browserChecks'],*proof['additionalBrowserChecks']]:
        report=json.loads((ROOT/name).read_text());assert report['results'] and all(r['passed'] for r in report['results']),'Failed browser/fidelity check: '+name
        if 'fingerprints' in report:assert report['fingerprints']==proof['fingerprints'],'Evidence source mismatch: '+name
    assert checks['fingerprints']==proof['fingerprints']
    for name,sha in proof['fingerprints'].items():assert digest(ROOT/name)==sha,'Stale browser evidence: '+name
    home=(APP/'dist/index.html').read_text();library=(APP/'dist/explore.html').read_text()
    for markup in [home,library]:
        assert 'refinement.css?v=' in markup and 'runtime/refinement.js?v=' in markup
        assert not any(old in markup for old in ['site.css','deck.css','lens-masthead','site-shell.js','story-motion.js'])
    assert 'runtime/intro.js?v=' in home and 'intro.css?v=' in home and 'id="intro-replay"' in home
    assert 'runtime/intro.js' not in library
    frames=json.loads((ROOT/proof['introFrames']).read_text())['runs'];assert len(frames)==6
    assert all(r['run']['reason']=='complete' and not r['run']['error'] and 5900<=r['run']['elapsed']<6500 and r['idleRAF']==0 and r['idlePixels']==1 and r['run']['canvasPixels']<=2010000 for r in frames)
    assert (ROOT/proof['recording']).stat().st_size>10000
    assert not list((APP/'dist').rglob('*.mp4'))
    assert (APP/'refinement.css').stat().st_size<12*1024 and (APP/'src/intro.js').stat().st_size<32*1024
    for f in (APP/'data').glob('*.gz'):assert f.read_bytes()[:2]==b'\x1f\x8b','Unhydrated dataset: '+str(f)
    performance=json.loads((ROOT/proof['performance']).read_text())['runs'];assert len(performance)==8
    for r in performance:
        assert r['metrics']['cumulative-layout-shift']<=.02,'Layout shift needs investigation'
    for surface in ['home','library']:
        for device in ['mobile','desktop']:
            before=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='before')
            after=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='after')
            assert after['scores']['performance']>=before['scores']['performance']-5,'Investigate paired performance regression'
    return {'routes':len(routes),'screenshots':len(rows),'viewports':checks['matrix']['viewports'],'fingerprintedSources':len(proof['fingerprints']),'verified':True}
if __name__=='__main__':print(json.dumps(check()))
