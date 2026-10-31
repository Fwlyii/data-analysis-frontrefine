"""Check built resources and frozen data bindings without model requests."""
from pathlib import Path
import argparse
import functools
import importlib.util
import json
import re
import shutil
import subprocess
import threading
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
from urllib.request import ProxyHandler, build_opener

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        value = attributes.get('src') or attributes.get('href')
        if value and not value.startswith(('#', 'data:', 'http:', 'https:', 'mailto:')):
            self.paths.add(unquote(urlsplit(value).path))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-build', action='store_true')
    args = parser.parse_args()
    if not args.skip_build:
        spec = importlib.util.spec_from_file_location('web_snapshot', ROOT/'scripts/system/build_web_app.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.build()
    app = ROOT/'app'
    dist = app/'dist'
    data = json.loads((app/'data/narrative-evidence.json').read_text())
    expected = {'reasoning': 372, 'document_qa': 186, 'code_generation': 93}
    assert {key: len(rows) for key, rows in data['profiles_by_direction'].items()} == expected
    for direction, config in data['directions'].items():
        for model in config['models']:
            for task in config['groups']:
                rows = [r for r in data['profiles_by_direction'][direction] if r['model'] == model and r['task'] == task]
                assert len(rows) == 31 and len({r['prompt'] for r in rows}) == 31
    for name in ['story.js', 'narrative.js', 'story-charts.js']:
        assert (app/'src'/name).read_bytes() == (dist/'runtime'/name).read_bytes(), name
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(dist)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opener = build_opener(ProxyHandler({}))
    paths = set()
    for name in ['index.html', 'explore.html']:
        html = Resources()
        html.feed((dist/name).read_text())
        paths.update(html.paths)
        paths.add(name)
    for name in ['story.css', 'styles.css']:
        paths.update(unquote(value.strip('"\' ')) for value in re.findall(r'url\(([^)]+)\)', (dist/name).read_text()) if not value.startswith('data:'))
    try:
        for path in sorted(paths):
            with opener.open(f'http://127.0.0.1:{server.server_port}/{path}', timeout=10) as response:
                assert response.status == 200 and response.read(), path
    finally:
        server.shutdown()
        server.server_close()
    if shutil.which('node'):
        for path in [*sorted((app/'src').glob('*.js')), *sorted((dist/'runtime').glob('*.js'))]:
            subprocess.run(['node', '--check', str(path)], check=True, capture_output=True)
        check = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context={window:{}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
for(const direction of Object.keys(data.directions)){
  const model='qwen',group=data.directions[direction].groups[0];
  const output=context.window.LENS_CHARTS.landscape(data,{direction,model,view:'heatmap'});
  const row=data.profiles_by_direction[direction].find(r=>r.model===model&&r.task===group&&r.prompt==='BeConcise');
  assert(output.includes(`BeConcise · ${group} · ${row.score_pct.toFixed(1)}%`));
  assert.equal((output.match(/data-profile-prompt=/g)||[]).length,31*data.directions[direction].groups.length);
  assert(!output.includes('NaN'));
  const trend=context.window.LENS_CHARTS.landscape(data,{direction,model,view:'curve'});
  assert(trend.includes('Mean output tokens')&&!trend.includes('NaN'));
}
'''
        subprocess.run(['node', '-e', check, str(app/'src/story-charts.js'), str(app/'data/narrative-evidence.json')], check=True)
    print(json.dumps({'local_resources': len(paths), 'prompt_conditions': expected,
        'source_runtime_sync': True, 'chart_bindings': 'passed', 'api_calls': 0}))


if __name__ == '__main__':
    main()
