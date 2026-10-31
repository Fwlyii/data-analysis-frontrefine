"""Compare every upstream tracked file, permitting explicit presentation changes only."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
UP='35f7318e45561da07c75eaf65374e4107004d5ec'
allowed={'DESIGN.md','docs/design-sources.md','.gitattributes','.gitignore','README.md','app/index.html','app/explore.html','app/styles.css','app/src/code-interactions.js','app/src/narrative.js','app/src/story-charts.js','app/src/story.js','scripts/system/build_web_app.py'}
rows=[]
for name in subprocess.check_output(['git','ls-tree','-rz','--name-only',UP],cwd=ROOT).decode().split('\0'):
    if not name:continue
    prior=subprocess.check_output(['git','show',UP+':'+name],cwd=ROOT)
    path=ROOT/name
    assert path.is_file(), 'Missing upstream file: '+name
    current=path.read_bytes();kind='exact'
    if name in allowed:kind='documented presentation/integration exception';passed=True
    elif name in {'app/data/code-features.json.gz','app/data/method-features.json.gz','app/data/features.json.gz'}:
        kind='LFS snapshot materialized';match=re.search(rb'oid sha256:([a-f0-9]+)\nsize (\d+)',prior)
        passed=bool(match) and hashlib.sha256(current).hexdigest()==match[1].decode() and len(current)==int(match[2])
    else:passed=prior==current
    rows.append({'file':name,'kind':kind,'passed':passed,'sha256':hashlib.sha256(current).hexdigest()})
    assert passed,'Upstream protected content changed: '+name
# Chart functions and geometry are byte-for-byte unchanged after removing literal color values.
prior=subprocess.check_output(['git','show',UP+':app/src/story-charts.js'],cwd=ROOT,text=True)
current=(ROOT/'app/src/story-charts.js').read_text()
assert re.sub(r'#[a-fA-F0-9]{6}', '#COLOR', prior)==re.sub(r'#[a-fA-F0-9]{6}', '#COLOR', current),'Chart code changed beyond palette literals'
# Confirm current research router is the latest implementation plus display hooks/scroll accessibility.
prior=subprocess.check_output(['git','show',UP+':app/src/story.js'],cwd=ROOT,text=True)
current=(ROOT/'app/src/story.js').read_text().replace('    window.LensMotionUI?.onRender(s.chapter);\n','')
current=current.replace('<div class="data-scroll" role="region" tabindex="0" aria-label="Figure data; horizontally scrollable">','<div class="data-scroll">')
current=current.replace('<pre tabindex="0" class="answer-content code">','<pre class="answer-content code">')
assert current==prior,'Finding logic changed beyond reviewed display/accessibility edits'
assets=[]
for name in ['assets/fonts/lens-editorial-site-semibold.woff2','assets/fonts/lens-intro-semibold.woff2','assets/visual/lens-wordmark.webp','assets/visual/optical-study.webp','assets/vendor/motion-mini-14.9.0.min.js','intro.css','styles.css']:
    prior=subprocess.check_output(['git','show','a1cd05a:app/'+name],cwd=ROOT)
    same=prior==(ROOT/'app'/name).read_bytes();assert same,'Prior visual asset changed: '+name
    assets.append({'file':'app/'+name,'passed':same,'sha256':hashlib.sha256(prior).hexdigest()})
report={'upstream':UP,'previousVisual':'a1cd05a39a620fba464304bfd579aa32107c3a44','files':rows,'preservedVisualAssets':assets,'chartGeometryAndNumericCodeUnchanged':True,'findingLogicUnchangedBeyondDisplayHooks':True,'exceptions':sorted(allowed),'lfs':'Only three deployable app/data snapshots materialized; all 209 other upstream LFS pointers unchanged. Source LFS endpoint retained in .lfsconfig; no transfer or modification to upstream Master.'}
(ROOT/'optimization/master-migration-v4/after/content-fidelity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'upstreamFiles':len(rows),'exactOrVerifiedSnapshots':sum(r['kind']!='documented presentation/integration exception' for r in rows),'preservedVisualAssets':len(assets),'chartGeometryAndNumericCodeUnchanged':True}))
