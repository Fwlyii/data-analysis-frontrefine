"""Static deployment gate for the reviewed route graph and shared shell.

Does not replace a browser run. New views or changed presentation files require
new browser evidence and an updated app/visual-coverage.json before deployment.
"""
import hashlib
import json
from pathlib import Path
import re

APP=Path(__file__).resolve().parents[3]
ROOT=APP.parent

def digest(path):
    value=path.read_bytes()
    if path.suffix=='.html':
        value=re.sub(rb'\?v=[a-f0-9]+',b'?v=BUILD',value)
    if path.suffix=='.css':
        value=re.sub(rb'[ \t]+$',b'',value,flags=re.M)
    return hashlib.sha256(value).hexdigest()

def check():
    proof=json.loads((APP/'visual-coverage.json').read_text())
    routes=proof['routes'];keys={r['key'] for r in routes}
    source=(APP/'src/app.js').read_text()
    block=re.search(r'const library = \{(.*?)\n\};',source,re.S).group(1)
    charts=re.findall(r'(\w+): "[^"]+"',block)
    code=re.search(r'const VIEWS = \{(.*?)\};',(APP/'src/code-study.js').read_text()).group(1)
    views=re.findall(r'(\w+):',code)
    stories=re.search(r'const titles=\{(.*?)\};',(APP/'src/story.js').read_text()).group(1)
    stories=re.findall(r'(\w+):',stories)
    discoveries=re.search(r'const chapters = \[(.*?)\];',source).group(1)
    required={'chart-'+c for c in charts}|{'code-'+v for v in views}|{'story-'+s for s in stories}|{'discovery-'+str(i+1) for i in range(len(re.findall(r'"[^"]+"',discoveries)))}|{'efficiency','efficiency-prompts','position-matrix','position-profile','chart-flow-empty','story-language-gsm8k','story-language-mmlu'}
    assert required==keys,'Route graph changed: classify new views and rerun whole-site browser coverage'
    assert sorted(p.name for p in (APP/'dist').glob('*.html'))==proof['entryDocuments'],'Unclassified production entry document'
    for name in proof['entryDocuments']:
        markup=(APP/'dist'/name).read_text()
        assert 'site.css?v=' in markup and 'runtime/site-shell.js?v=' in markup and 'lens-primary-nav' in markup and 'lens-masthead' in markup,'Shared shell missing: '+name
        for href in re.findall(r'href="([^"?#]+\.html)(?:[?#][^"]*)?"',markup):
            assert '://' in href or href in proof['entryDocuments'],'Unclassified linked HTML: '+href
    audit=json.loads((ROOT/proof['screenshots']).read_text())
    for route in routes:
        for device in ['desktop','mobile']:
            row=next((r for r in audit['rows'] if r['key']==route['key'] and r['device']==device),None)
            assert row and not row['overflow'] and row['selectedViewMatches'],'Missing or failed actual-view screenshot: '+route['key']+' '+device
    checks=json.loads((ROOT/proof['browserChecks']).read_text())
    assert checks['results'] and all(r['passed'] for r in checks['results']),'Browser evidence has failures'
    for name in proof['additionalBrowserChecks']:
        report=json.loads((ROOT/name).read_text())
        assert report['results'] and all(r['passed'] for r in report['results']),'Additional browser evidence failed: '+name
    for filename,expected in proof['fingerprints'].items():
        assert digest(ROOT/filename)==expected,'Visual evidence predates source change: '+filename
    for filename,limit in [('assets/fonts/lens-editorial-site-semibold.woff2',90*1024),('site.css',8*1024),('src/site-shell.js',8*1024)]:
        assert (APP/filename).stat().st_size<=limit,'Shared presentation asset exceeds reviewed budget: '+filename
    performance=json.loads((ROOT/proof['performance']).read_text())['runs']
    assert len(performance)==8,'Missing paired entry-page performance diagnostics'
    for surface in ['home','library']:
        for device in ['mobile','desktop']:
            before=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='before')
            after=next(r for r in performance if r['surface']==surface and r['device']==device and r['stage']=='after')
            assert after['scores']['performance']>=before['scores']['performance']-5,'Investigate performance regression'
            assert after['metrics']['cumulative-layout-shift']<=.02,'Investigate layout instability'
    print('Whole-site coverage gate passed:',len(routes),'routes, 4 viewport widths, shared entry documents, current source fingerprints.')

if __name__=='__main__':check()
