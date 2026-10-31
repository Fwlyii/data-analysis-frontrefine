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
    assert len(keys)==len(routes)==93 and 'deck-gateway' in keys,'Regenerate route inventory and classify new routes'
    assert sorted(p.name for p in (APP/'dist').glob('*.html'))==sorted(inventory['entryDocuments'])
    # Re-derive inventory from actual source, so a new view cannot silently escape review.
    source=(APP/'src/app.js').read_text();charts=re.findall(r'(\w+): "[^"]+"',re.search(r'const library = \{(.*?)\n\};',source,re.S)[1])
    views=re.findall(r'(\w+):',re.search(r'const VIEWS = \{(.*?)\};',(APP/'src/code-study.js').read_text(),re.S)[1])
    data=json.loads((APP/'data/narrative-evidence.json').read_text())
    expected={'deck-'+s for s in ['question','collection','cleaning']}|{f'landscape-{d}-{m}-{v}' for d,c in data['directions'].items() for m in c['models'] for v in ['curve','heatmap']}|{'story-concise-baseline','story-concise-cross','story-position','story-repair-qwen','story-repair-qwen3'}|{'story-language-'+t for t in ['math500','gsm8k','mmlu']}|{f'story-limits-{m}-{t}-{f}' for m in ['deepseek','hy4','qwen','qwen3'] for t in ['math500','gsm8k','mmlu'] for f in ['WordLimit','CharLimit','TokenLimit']}|{'chart-'+c for c in charts}|{'code-'+v for v in views}|{'discovery-'+str(i+1) for i in range(len(re.findall(r'"[^"]+"',re.search(r'const chapters = \[(.*?)\];',source)[1])))}|{'efficiency','efficiency-prompts','position-matrix','position-profile','chart-flow-empty'}
    expected.add('deck-gateway')
    assert keys==expected,'Source route graph changed'
    audit=json.loads((ROOT/proof['screenshots']).read_text());rows=audit['rows']
    assert len(rows)==len(routes)*2
    for r in routes:
        for device in ['desktop','mobile']:
            row=next(x for x in rows if x['key']==r['key'] and x['device']==device)
            assert row['selectedViewMatches'] and not row['overflow'] and row['brandVisible'],r['key']
            assert (ROOT/proof['screenshots']).parent.joinpath(r['key']+'-'+device+'.png').stat().st_size>1000
            assert all(i['complete'] and i['naturalWidth']>0 and i['width']>0 and i['height']>0 for i in row['images'])
            assert all((s['painted']>=(1 if s.get('decorative') else 3) or s.get('interactionLayer')) and s['opacity']>(.1 if s.get('decorative') else .95) and not s['unresolved'] and not s['invalid'] for s in row['svgs'])
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
    assert 'runtime/gateway.js?v=' in home and 'gateway.css?v=' in home and 'id="gateway"' in home
    assert len(re.findall(r'data-gate-route=',home))==5 and 'runtime/gateway.js' not in library
    contract=proof['sceneContract'];assert contract['sameFiveLinkNodes'] and contract['sameIntroOpticsNode'] and set(contract['links'])=={'question','collection','cleaning','landscape','findings'}
    assert proof['version']>=9 and all(proof['layoutContract'].values()),'Missing full-screen research and responsive optical review'
    assert 'class="chapter-rail"' not in home and 'class="research-home"' in home
    assert 'assets/visual/gateway-atmosphere.webp' in home
    provenance=json.loads((ROOT/proof['designProvenance']).read_text())
    assert provenance['tool']=='image_gen.imagegen' and len(provenance['calls'])>=14
    assert len([c for c in provenance['calls'] if c.get('kind')=='transparent-planet'])==5
    assert any(c.get('kind')=='implementation-feedback' for c in provenance['calls'])
    for call in provenance['calls']:
        for item in [call['prompt'],call['output'],*call['inputs'],*([call['runtime']] if 'runtime' in call else [])]:
            artifact=ROOT/item['path']
            assert artifact.stat().st_size==item['bytes'] and hashlib.sha256(artifact.read_bytes()).hexdigest()==item['sha256'],'Changed design evidence: '+str(artifact)
    assert (APP/'assets/visual/gateway-atmosphere.webp').stat().st_size<50*1024
    optical=json.loads((ROOT/proof['browserChecks']).parent.joinpath('optical-checks.json').read_text())
    assert len(optical['results'])==23 and all(r['passed'] for r in optical['results'])
    scene=json.loads((ROOT/proof['browserChecks']).parent.joinpath('gateway-checks.json').read_text());assert {row['width']for row in scene['layouts']}=={320,390,768,1366,1440}
    assert len([r for r in scene['results'] if 'original page has no navbar and uses full viewport' in r['name']])==25
    assert (APP/'src/gateway.js').stat().st_size<20*1024 and (APP/'gateway.css').stat().st_size<24*1024
    assert 'runtime/intro.js' not in library
    assert {p.name for p in (APP/'dist/runtime').glob('*.js')}=={'summary.js','publication.js','features.js','code-features.js','code-data.js','app.js','story-data.js','story.js','story-charts.js','narrative-data.js','narrative.js','intro.js','refinement.js','gateway.js'},'Stale or unclassified generated runtime script; clean runtime and rebuild'
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
    # This round explicitly authorizes five STATIC alpha decorations, while
    # keeping native links/text, the same optical SVG, and all scientific bytes.
    job=ROOT/'optimization/fullsite-closed-loop-20261031'
    assert proof['version']>=10 and proof['baseline']=='f751c3fe2db5a977f63d394ca185d09bc3ef8132'
    protected=job/'protected-files.json'
    assert hashlib.sha256(protected.read_bytes()).hexdigest()=='29181b4d163b48c098ea5269eed624684abbc1bbf222ad66cefd2345870d914c'
    protection=json.loads(protected.read_text());assert len(protection['files'])==519
    for name,sha in protection['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'Protected bytes changed: '+name
    planets=['app/assets/visual/planet-'+k+'.webp' for k in contract['links']]
    assert set(proof['planetAssets'])==set(planets)
    assert len(re.findall(r'class="orb-planet"',home))==5
    for path in planets:
        assert home.count('src="'+path.removeprefix('app/')+'"')==1
    asset_report=json.loads((job/'assets/planet-validation.json').read_text())
    assert len(asset_report['results'])==5 and all(r['passed'] and r['alpha']['min']==0 and r['alpha']['max']==255 for r in asset_report['results'])
    for row in asset_report['results']:
        asset=ROOT/row['runtime']['path'];assert hashlib.sha256(asset.read_bytes()).hexdigest()==row['runtime']['sha256']
    ledger=json.loads((ROOT/proof['coverageLedger']).read_text())['rows']
    assert len(ledger)==len(keys)*2 and {(r['routeKey'],r['device']) for r in ledger}=={(k,d)for k in keys for d in ['desktop','mobile']}
    for row in ledger:
        assert row['reason'].strip() and row['decision'] in ['improved','kept_with_reason']
        for key in ['beforeScreenshot','referenceImage','afterScreenshot']:assert (ROOT/row[key]).stat().st_size>1000
        for key in ['beforeScore','referenceScore','afterScore','fidelityScore']:assert 0<=row[key]<=100
        if row['decision']=='improved':assert row['referenceScore']>=row['beforeScore']+5 and row['fidelityScore']>=90 and row['afterScore']>=row['referenceScore']-5
    overlays=json.loads((ROOT/proof['overlays']).read_text())['states'];assert len(overlays)>=26
    for state in overlays:
        for key in ['beforeScreenshot','afterScreenshot']:assert (ROOT/state[key]).stat().st_size>1000
    assert json.loads((job/'design/visual-scores.json').read_text())['assessmentType']=='AI subjective visual judgment'
    for report in ['functional-checks','chart-preservation','planet-checks']:
        report=json.loads((job/'after'/f'{report}.json').read_text());assert report['results'] and all(r['passed'] for r in report['results'])
    return {'routes':len(routes),'screenshots':len(rows),'viewports':checks['matrix']['viewports'],'fingerprintedSources':len(proof['fingerprints']),'verified':True}
if __name__=='__main__':print(json.dumps(check()))
