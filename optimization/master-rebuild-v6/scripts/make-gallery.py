from pathlib import Path
import json,shutil,html,subprocess
ROOT=Path(__file__).resolve().parents[1]
routes=json.loads((ROOT/'site-inventory.json').read_text())['routes']
for name,key in [('home','deck-question'),('design','deck-collection'),('pipeline','deck-cleaning'),('landscape','landscape-reasoning-qwen-curve'),('findings','story-concise-baseline'),('library','chart-distribution')]:
    for device in ['desktop','mobile']:
        shutil.copy2(ROOT/'after'/f'{key}-{device}.png',ROOT/'after'/f'{name}-{device}.png')
selected=['deck-question','deck-collection','deck-cleaning','landscape-reasoning-qwen-curve','story-concise-baseline','story-limits-qwen3-math500-TokenLimit','chart-model','chart-distribution','code-tokens','discovery-5','efficiency','position-matrix']
for device,w,h,cols in [('desktop',360,225,3),('mobile',156,338,6)]:
    frames=ROOT.parents[1]/'.git/master-rebuild-v6'/('contact-'+device);frames.mkdir(exist_ok=True)
    for i,key in enumerate(selected):
        target=frames/f'{i:02d}.png'
        if target.exists():target.unlink()
        target.symlink_to((ROOT/'after'/f'{key}-{device}.png').resolve())
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','1','-i',str(frames/'%02d.png'),'-vf',f'scale={w}:{h},tile={cols}x{(len(selected)+cols-1)//cols}','-frames:v','1',str(ROOT/'after'/f'review-sheet-{device}.jpg')],check=True)
parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>LENS v6 browser review</title><style>body{margin:32px;background:#f5f2eb;color:#202522;font:14px/1.6 system-ui}article{margin:36px 0;border-top:1px solid #aaa;padding-top:20px}img{max-width:100%;height:auto}section{display:grid;grid-template-columns:3fr 1fr;gap:24px}a{color:#a34f36}</style><h1>LENS v6 — actual browser captures</h1><p>92 states; desktop 1440×900 and mobile390×844. Images are browser captures, not generated designs.</p>']
for r in routes:
    key=html.escape(r['key']);parts.append(f'<article id="{key}"><h2>{key}</h2><code>{html.escape(r["url"])}</code><section>')
    for device in ['desktop','mobile']:
        file=key+'-'+device+'.png';parts.append(f'<a href="after/{file}"><img loading="lazy" src="after/{file}" alt="{key} {device}"></a>')
    parts.append('</section></article>')
parts.append('</html>');(ROOT/'review-gallery.html').write_text('\n'.join(parts))
print('Wrote paired 92-state gallery and two contact sheets.')
