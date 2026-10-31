"""Validate the moderate color refinement without discarding the accepted layout or scientific paint."""
from pathlib import Path
import hashlib,json,re

def check(root,proof):
    app=root/'app';job=root/'optimization/color-unification-20261101'
    read=lambda p:json.loads((root/p).read_text())
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def source_sha(p):
        b=p.read_bytes()
        if p.suffix=='.html':b=re.sub(rb'\?v=[a-f0-9]+',b'?v=BUILD',b)
        if p.suffix=='.css':b=re.sub(rb'[ \t]+$',b'',b,flags=re.M)
        return hashlib.sha256(b).hexdigest()
    assert proof['version']==12 and proof['baseline']=='d80769de37e4171665bef22d68f1f701b9bf2c3c'
    prior=job/'layout-baseline-proof.json'
    assert sha(prior)=='9d12303bd289de6826220c5c028e18c451da967bcf78eead8404da7e2b15c59b'
    accepted=json.loads(prior.read_text());assert accepted['version']==11
    inventory=read(proof['inventory']);routes=inventory['routes'];keys={r['key']for r in routes}
    old=read(accepted['inventory']);assert len(keys)==len(routes)==93 and keys=={r['key']for r in old['routes']}
    protected=job/'protected-files.json';assert sha(protected)=='ffb9fea1c5fc779193a7c5547be6b37b786f2837d6f078883fc3a274bbc19a81'
    manifest=json.loads(protected.read_text());assert manifest['baseline']==proof['baseline']and len(manifest['files'])==533
    for p,h in manifest['files'].items():assert sha(root/p)==h,'Existing data/drawing/layout changed: '+p
    for p,h in proof['fingerprints'].items():assert source_sha(root/p)==h,'Stale color evidence: '+p
    reports=[proof['browserChecks'],*proof['additionalBrowserChecks']]
    for p in reports:
        d=read(p);assert d['results']and all(r['passed']for r in d['results']),'Failed color review: '+p
        if 'fingerprints'in d:assert d['fingerprints']==proof['fingerprints'],'Mismatched source fingerprints: '+p
    checks=read(proof['browserChecks']);assert sorted(checks['matrix']['viewports'])==[1366,1440,1600,1920,2560]and set(checks['matrix']['routes'])==keys
    assert len([r for r in checks['results']if 'decoded/painted/layout'in r['name']])==465
    audit=read(proof['screenshots']);assert len(audit['rows'])==186
    assert {(r['key'],r['device'])for r in audit['rows']}=={(k,d)for k in keys for d in ['desktop','fullhd']}
    for row in audit['rows']:
        assert row['selectedViewMatches']and not row['overflow']and row['brandVisible']
        assert all(i['complete']and i['naturalWidth']>0 for i in row['images'])
        assert all((s['painted']>=(1 if s['decorative']else 3)or s.get('interactionLayer'))and not s['unresolved']and not s['invalid']for s in row['svgs'])
        assert (job/'after'/(row['key']+'-'+row['device']+'.png')).stat().st_size>1000
        assert (job/'before'/(row['key']+'-'+row['device']+'.png')).stat().st_size>1000
    palette=json.loads((job/'after/palette-checks.json').read_text())['results'];assert len(palette)==186
    for r in palette:assert r['passed']and r['detail']['unchangedLayout']and r['detail']['selectedViewMatches']
    early=json.loads((job/'after/early-paint-checks.json').read_text())['results'];assert len(early)==12 and all(r['passed']for r in early)
    reading=json.loads((job/'after/readability-checks.json').read_text());assert len(reading['rows'])==184 and all(r['liveView']['selectedViewMatches']for r in reading['rows'])
    science=json.loads((job/'after/chart-render-preservation.json').read_text())['results'];assert len(science)==184 and sum(r['actualGraphs']for r in science)==188
    for r in science:assert r['passed']and r['actualGraphs']==r['expectedGraphs']and all(g['sameMarkup']and g['sameStyles']and g['sameCanonicalPixels']for g in r['graphs'])
    exports=json.loads((job/'after/export-checks.json').read_text())['results'];assert len(exports)==31 and all(r['passed']for r in exports)
    ledger=read(proof['coverageLedger'])['rows'];assert len(ledger)==186
    for r in ledger:
        assert r['decision']==('entrance_preserved'if r['routeKey']=='deck-gateway'else'palette_unified')and r['unchangedLayout']
        for k in ['beforeScreenshot','referenceImage','afterScreenshot']:assert (root/r[k]).stat().st_size>1000
    overlays=read(proof['overlays'])['states'];assert len(overlays)==212
    for r in overlays:
        for k in ['beforeScreenshot','afterScreenshot']:assert (root/r[k]).stat().st_size>1000
    provenance=read(proof['designProvenance']);assert provenance['tool']=='image_gen.imagegen'and any(c['kind']=='palette-unification'for c in provenance['calls'])
    for call in provenance['calls']:
        for f in [call['prompt'],call['output'],*call['inputs']]:assert (root/f['path']).stat().st_size==f['bytes']and sha(root/f['path'])==f['sha256']
    assert proof['sceneContract']==accepted['sceneContract']and proof['layoutContract']==accepted['layoutContract']and proof['planetAssets']==accepted['planetAssets']
    assert proof['recordingViewport']=={'width':1920,'height':1080}and (root/proof['recording']).stat().st_size>10000
    frames=read(proof['introFrames'])['runs'];assert len(frames)==6
    assert all(r['run']['reason']=='complete'and not r['run']['error']and 5900<=r['run']['elapsed']<6500 and r['idleRAF']==0 and r['idlePixels']==1 for r in frames)
    perf=read(proof['performance'])['runs'];assert len(perf)==8
    for r in perf:assert r['metrics']['cumulative-layout-shift']<=.02
    for surface in ['home','library']:
        for device in ['desktop','fullhd']:
            before=next(r for r in perf if r['surface']==surface and r['device']==device and r['stage']=='before')
            after=next(r for r in perf if r['surface']==surface and r['device']==device and r['stage']=='after')
            assert after['scores']['performance']>=before['scores']['performance']-5,'Investigate palette performance regression'
    assert (app/'palette.css').stat().st_size<20*1024
    assert sorted(p.name for p in (app/'dist').glob('*.html'))==sorted(inventory['entryDocuments'])
    for name in ['index.html','explore.html']:
        html=(app/'dist'/name).read_text();assert re.search(r'palette.css\?v=[a-f0-9]{12}',html)and 'content-layout.css?v='in html
    home=(app/'dist/index.html').read_text();assert len(re.findall(r'data-gate-route=',home))==5 and 'class="chapter-rail"'not in home
    assert {p.name for p in (app/'dist/runtime').glob('*.js')}=={'summary.js','publication.js','features.js','code-features.js','code-data.js','app.js','story-data.js','story.js','story-charts.js','narrative-data.js','narrative.js','intro.js','refinement.js','gateway.js'},'Unclassified runtime script'
    assert 'runtime/intro.js?v='in home and 'runtime/gateway.js?v='in home
    assert 'runtime/intro.js'not in (app/'dist/explore.html').read_text()
    assert not list((app/'dist').rglob('*.mp4'))
    return {'routes':len(routes),'screenshots':len(audit['rows']),'viewports':checks['matrix']['viewports'],'protectedFiles':533,'fingerprintedSources':len(proof['fingerprints']),'paletteUnified':True,'scientificColorsRetained':True,'verified':True}
