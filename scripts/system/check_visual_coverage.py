"""Check current whole-site browser evidence before uploading the Pages artifact.

This gate verifies real saved evidence and source hashes; it does not run a browser.
"""
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
    proof=json.loads((APP/'visual-coverage.json').read_text());routes=proof['routes'];keys={r['key'] for r in routes}
    source=(APP/'src/app.js').read_text();block=re.search(r'const library = \{(.*?)\n\};',source,re.S).group(1)
    charts=re.findall(r'(\w+): "[^"]+"',block)
    views=re.findall(r'(\w+):',re.search(r'const VIEWS = \{(.*?)\};',(APP/'src/code-study.js').read_text(),re.S).group(1))
    sections=re.findall(r'(\w+):',re.search(r'const sectionNames = \{(.*?)\};',(APP/'src/narrative.js').read_text(),re.S).group(1))
    assert set(sections)=={'question','collection','cleaning','landscape','findings'},'New deck section requires coverage classification'
    titles=re.findall(r'(\w+):',re.search(r'const titles = \{(.*?)\};',(APP/'src/story.js').read_text(),re.S).group(1))
    assert set(titles)=={'concise','language','limits','position','repair'},'New finding requires explicit coverage'
    data=json.loads((APP/'data/narrative-evidence.json').read_text())
    required={'deck-'+s for s in ['question','collection','cleaning']}|{f'landscape-{direction}-{model}-{view}' for direction,config in data['directions'].items() for model in config['models'] for view in ['curve','heatmap']}|{'story-concise-baseline','story-concise-cross','story-position','story-repair-qwen','story-repair-qwen3'}|{'story-language-'+task for task in ['math500','gsm8k','mmlu']}|{f'story-limits-{model}-{task}-{family}' for model in ['deepseek','hy4','qwen','qwen3'] for task in ['math500','gsm8k','mmlu'] for family in ['WordLimit','CharLimit','TokenLimit']}|{'chart-'+c for c in charts}|{'code-'+v for v in views}|{'discovery-'+str(i+1) for i in range(len(re.findall(r'"[^"]+"',re.search(r'const chapters = \[(.*?)\];',source).group(1))))}|{'efficiency','efficiency-prompts','position-matrix','position-profile','chart-flow-empty'}
    assert required==keys and len(keys)==len(routes),'Route graph changed; regenerate inventory and browser coverage'
    assert sorted(p.name for p in (APP/'dist').glob('*.html'))==sorted(proof['entryDocuments']),'Unclassified production entry document'
    for name in proof['entryDocuments']:
        markup=(APP/'dist'/name).read_text()
        assert 'site.css?v=' in markup and 'runtime/site-shell.js?v=' in markup and 'lens-masthead' in markup,'Shared shell missing: '+name
        for href in re.findall(r'href="([^"?#]+\.html)(?:[?#][^"]*)?"',markup):assert '://' in href or href in proof['entryDocuments'],'Unclassified linked HTML: '+href
    audit=json.loads((ROOT/proof['screenshots']).read_text())
    for route in routes:
        for device in ['desktop','mobile']:
            row=next((r for r in audit['rows'] if r['key']==route['key'] and r['device']==device),None)
            assert row and not row['overflow'] and row['selectedViewMatches'],'Missing/failed screenshot: '+route['key']+' '+device
            assert (ROOT/proof['screenshots']).parent.joinpath(route['key']+'-'+device+'.png').is_file(),'Screenshot bytes missing'
    checks=json.loads((ROOT/proof['browserChecks']).read_text());assert checks['results'] and all(r['passed'] for r in checks['results']),'Browser matrix failed'
    assert set(checks['matrix']['routes'])==keys and sorted(checks['matrix']['viewports'])==[320,390,768,1440],'Incomplete viewport matrix'
    for name in proof['additionalBrowserChecks']:
        report=json.loads((ROOT/name).read_text());assert report['results'] and all(r['passed'] for r in report['results']),'Interaction/intro checks failed: '+name
    assert proof['fingerprints']==checks['fingerprints'],'Evidence fingerprints disagree'
    for filename,expected in proof['fingerprints'].items():assert digest(ROOT/filename)==expected,'Browser review predates current source: '+filename
    for name,limit in [('assets/fonts/lens-editorial-site-semibold.woff2',90*1024),('site.css',8*1024),('deck.css',16*1024),('src/site-shell.js',8*1024),('src/story-motion.js',8*1024),('src/intro.js',32*1024),('intro.css',8*1024),('assets/fonts/lens-intro-semibold.woff2',8*1024)]:assert (APP/name).stat().st_size<=limit,'Presentation asset budget exceeded: '+name
    performance=json.loads((ROOT/proof['performance']).read_text())['runs'];assert len(performance)==8,'Missing paired entry-page performance runs'
    for surface in ['home','library']:
        for device in ['mobile','desktop']:
            before=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='before');after=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='after')
            assert after['scores']['performance']>=before['scores']['performance']-5,'Investigate performance regression'
            assert after['metrics']['cumulative-layout-shift']<=.02,'Investigate layout instability'
    markup=(APP/'dist/index.html').read_text();assert 'runtime/intro.js?v=' in markup and 'intro.css?v=' in markup and 'id="intro-replay"' in markup,'Homepage intro missing'
    assert 'runtime/intro.js' not in (APP/'dist/explore.html').read_text(),'Library must not load the intro'
    intro=proof['introReview'];frame_runs=json.loads((ROOT/intro['frames']).read_text())['runs'];assert len(frame_runs)==6,'Missing intro frame/DPR/CPU diagnostics'
    for run in frame_runs:
        assert run['run']['reason']=='complete' and not run['run']['error'],'Intro failed to complete'
        assert 5900<=run['run']['elapsed']<6500 and run['idleRAF']==0 and run['idlePixels']==1,'Intro duration or cleanup failed'
        assert run['run']['canvasPixels']<=2010000,'Canvas pixel budget exceeded'
    assert (ROOT/intro['recording']).is_file(),'Real browser review recording missing'
    assert not list((APP/'dist').rglob('*.mp4')) and not list((APP/'dist').rglob('*.webm')),'Review recording must not become runtime media'
    fidelity=json.loads((ROOT/proof['contentFidelity']).read_text());assert all(row['passed'] for row in fidelity['files']),'Upstream content fidelity failed'
    assert fidelity['chartGeometryAndNumericCodeUnchanged'] and fidelity['findingLogicUnchangedBeyondDisplayHooks'],'Unreviewed research logic changes'
    print('Whole-site coverage gate passed:',len(routes),'actual states × 4 viewport widths; shared shell, latest Master fidelity, finite intro, current source fingerprints.')
if __name__=='__main__':check()
