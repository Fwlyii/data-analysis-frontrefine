"""Publish only freshly verified, complete interaction scenes with scientific evidence intact."""
from pathlib import Path
import hashlib
import json
import re


def check(root, proof):
    job = root / 'optimization/interaction-design-20261101'
    app = root / 'app'

    def read(path):
        return json.loads((root / path).read_text())

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def source_sha(path):
        content = path.read_bytes()
        if path.suffix == '.html':
            content = re.sub(rb'\?v=[a-f0-9]+', b'?v=BUILD', content)
        if path.suffix == '.css':
            content = re.sub(rb'[ \t]+$', b'', content, flags=re.M)
        return hashlib.sha256(content).hexdigest()

    assert proof['version'] == 13
    assert proof['baseline'] == '926c936a3571153eb855571b9ab7768e65c1c1f0'
    assert sha(job / 'accepted-palette-proof.json') == '4c67994420e32290c94dcfe9d3b15741cdb8eb6d51dd4e9ff213ed185136e314'
    accepted = json.loads((job / 'accepted-palette-proof.json').read_text())
    assert accepted['version'] == 12
    manifest_path = job / 'protected-files.json'
    assert sha(manifest_path) == '364b630f923c2c60b96369ee0f014d8ba25ad67c68f63bb8ac4b6aaf4ac92d03'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['baseline'] == proof['baseline'] and len(manifest['files']) == 1100
    for path, expected in manifest['files'].items():
        assert sha(root / path) == expected, 'Protected research or existing UI changed: ' + path
    assert sha(job / 'frozen-build.json') == 'e186960df6542b574ec223013a981a85ea40002967cc461494919c2f5dae025b'
    assert len(json.loads((job / 'frozen-build.json').read_text())['files']) == 229

    inventory = read(proof['inventory'])
    routes = inventory['routes']
    keys = {r['key'] for r in routes}
    prior = read(accepted['inventory'])
    assert len(keys) == len(routes) == 93 and keys == {r['key'] for r in prior['routes']}
    source = (app / 'src/app.js').read_text()
    chart_enum = re.search(r'const library = \{(.*?)\n\};', source, re.S)[1]
    charts = re.findall(r'(\w+): "[^"]+"', chart_enum)
    code_enum = re.search(r'const VIEWS = \{(.*?)\};', (app / 'src/code-study.js').read_text(), re.S)[1]
    code_views = re.findall(r'(\w+):', code_enum)
    assert {'chart-' + c for c in charts} == {r['key'] for r in routes if r.get('chart') and not r.get('empty')}
    assert {'code-' + c for c in code_views} == {r['key'] for r in routes if r['family'] == 'code'}
    narrative = json.loads((app / 'data/narrative-evidence.json').read_text())
    assert {f'landscape-{d}-{m}-{v}' for d, c in narrative['directions'].items() for m in c['models'] for v in ['curve', 'heatmap']} == {r['key'] for r in routes if r['family'] == 'landscape'}

    for path, expected in proof['fingerprints'].items():
        assert source_sha(root / path) == expected, 'Stale interaction evidence: ' + path
    for path in [proof['browserChecks'], *proof['additionalBrowserChecks']]:
        report = read(path)
        assert report['results'] and all(r['passed'] for r in report['results']), 'Failed interaction review: ' + path
        if 'fingerprints' in report:
            assert report['fingerprints'] == proof['fingerprints'], 'Different source reviewed: ' + path

    checks = read(proof['browserChecks'])
    assert set(checks['matrix']['routes']) == keys
    assert sorted(checks['matrix']['viewports']) == [1366, 1440, 1600, 1920, 2560]
    assert len([r for r in checks['results'] if 'decoded/painted/layout' in r['name']]) == 465
    audit = read(proof['screenshots'])
    assert {(r['key'], r['device']) for r in audit['rows']} == {(key, device) for key in keys for device in ['desktop', 'fullhd']}
    assert len(audit['rows']) == 186
    for row in audit['rows']:
        assert row['selectedViewMatches'] and not row['overflow'] and row['brandVisible']
        for stage in ['before', 'after']:
            assert (job / stage / (row['key'] + '-' + row['device'] + '.png')).stat().st_size > 1000
        assert all(i['complete'] and i['naturalWidth'] > 0 for i in row['images'])
        assert all((s['painted'] >= (1 if s['decorative'] else 3) or s.get('interactionLayer')) and not s['unresolved'] and not s['invalid'] for s in row['svgs'])

    interaction = read(proof['interactions'])
    for key in keys:
        for width in [1440, 1920]:
            phrase = 'usage guide opens' if key == 'deck-gateway' else 'custom card/step module' if key in ['deck-question', 'deck-collection', 'deck-cleaning'] else 'one view-specific interaction scene'
            result = next((r for r in interaction['results'] if r['name'] == f'{key} {width} {phrase}'), None)
            assert result and result['passed'], 'Unreviewed interaction: ' + key
            if phrase == 'one view-specific interaction scene':
                route = next(r for r in routes if r['key'] == key)
                expected = route.get('finding') if route['family'] == 'story' else 'landscape' if route['family'] == 'landscape' else 'chart-flow' if key == 'chart-flow-empty' else key
                assert result['detail']['state']['key'] == expected, 'Wrong interaction scene: ' + key
    assert len(interaction['results']) > 900

    science = read(proof['scientificPreservation'])['results']
    assert len(science) == 184 and sum(r['actualGraphs'] for r in science) == 188
    for r in science:
        assert r['passed'] and r['actualGraphs'] == r['expectedGraphs']
        assert all(g['sameMarkup'] and g['sameStyles'] and g['sameCanonicalPixels'] for g in r['graphs'])
    exports = read(proof['exports'])['results']
    assert len(exports) == 31 and all(r['passed'] for r in exports)
    layout = read(proof['layoutReview'])
    assert len(layout['results']) >= 186 and all(r['passed'] for r in layout['results'])
    ledger = read(proof['coverageLedger'])['rows']
    assert len(ledger) == 93 and {r['routeKey'] for r in ledger} == keys
    for row in ledger:
        assert row['decision'] == 'implemented_and_browser_reviewed' and row['interaction'] and row['transition']
    assert (root / proof['recording']).stat().st_size > 10000
    recording = read(proof['recordingManifest'])
    assert recording['viewport'] == {'width': 1920, 'height': 1080} and recording['frameCount'] > 100 and len(recording['actions']) >= 30
    frames = read(proof['introFrames'])['runs']
    assert len(frames) == 6
    assert all(r['run']['reason'] == 'complete' and not r['run']['error'] and 5900 <= r['run']['elapsed'] < 6500 and r['idleRAF'] == 0 and r['idlePixels'] == 1 for r in frames)
    perf = read(proof['performance'])['runs']
    assert len(perf) == 8 and all(r['metrics']['cumulative-layout-shift'] <= .02 for r in perf)
    for surface in ['home', 'library']:
        for device in ['desktop', 'fullhd']:
            before = next(r for r in perf if r['surface'] == surface and r['device'] == device and r['stage'] == 'before')
            after = next(r for r in perf if r['surface'] == surface and r['device'] == device and r['stage'] == 'after')
            assert after['scores']['performance'] >= before['scores']['performance'] - 5, 'Investigate interaction performance regression'

    assert sorted(p.name for p in (app / 'dist').glob('*.html')) == sorted(inventory['entryDocuments'])
    expected_runtime = {'summary.js', 'publication.js', 'features.js', 'code-features.js', 'code-data.js', 'app.js', 'story-data.js', 'story.js', 'story-charts.js', 'narrative-data.js', 'narrative.js', 'intro.js', 'refinement.js', 'gateway.js', 'interaction.js'}
    assert {p.name for p in (app / 'dist/runtime').glob('*.js')} == expected_runtime
    for name in inventory['entryDocuments']:
        html = (app / 'dist' / name).read_text()
        assert re.search(r'interaction.css\?v=[a-f0-9]{12}', html)
        assert re.search(r'runtime/interaction.js\?v=[a-f0-9]{12}', html)
        assert 'motion-mini-14.9.0.min.js' in html and 'palette.css?v=' in html
    assert (app / 'src/interaction.js').read_bytes() == (app / 'dist/runtime/interaction.js').read_bytes()
    assert (app / 'interaction.css').read_bytes() == (app / 'dist/interaction.css').read_bytes()
    assert (app / 'interaction.css').stat().st_size < 20 * 1024
    assert (app / 'src/interaction.js').stat().st_size < 40 * 1024
    assert not list((app / 'dist').rglob('*.mp4'))
    return {'routes': len(routes), 'screenshots': len(audit['rows']), 'protectedFiles': len(manifest['files']), 'charts': len(charts), 'codeViews': len(code_views), 'freshInteractionChecks': len(interaction['results']), 'scientificColorsAndGeometryRetained': True, 'verified': True}
