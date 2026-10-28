"""Run the coursework application on loopback; Python standard library only."""
import argparse
import functools
import importlib.util
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']


def main():
    p=argparse.ArgumentParser(description='启动模型行为分析课程系统')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--no-open',action='store_true')
    args=p.parse_args()
    spec=importlib.util.spec_from_file_location('build_app',ROOT/'scripts/system/build_web_app.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    dist=module.build()
    handler=functools.partial(SimpleHTTPRequestHandler,directory=str(dist))
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),handler)
    except OSError:
        p.exit(1,f'端口 {args.port} 无法使用，请通过 --port 指定其他端口。\n')
    url=f'http://127.0.0.1:{args.port}'
    print(f'Local: {url}',flush=True)
    print('仅提供 app/dist 内的研究图表、精选案例与静态文件。Ctrl+C 停止。',flush=True)
    if not args.no_open:threading.Timer(.6,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
