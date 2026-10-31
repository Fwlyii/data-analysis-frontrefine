from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1];REL=J.relative_to(ROOT).as_posix()
routes=json.loads((J/'site-inventory.json').read_text())['routes'];audit=json.loads((J/'after/palette-checks.json').read_text());assert len(audit['results'])==186 and all(r['passed']for r in audit['results'])
rows=[];cards=[]
for route in routes:
 for device in ['desktop','fullhd']:
  r=next(x['detail']for x in audit['results']if x['detail']['routeKey']==route['key']and x['detail']['device']==device)
  reason='保留开场与五个星球入口。'if route.get('section')=='gateway'else'采用深海蓝品牌框架、雾蓝灰阅读背景、冷白卡片与少量香槟金；原布局/字号及科研图形配色保持。'
  row={'routeKey':route['key'],'device':device,'url':route['url'],'decision':'entrance_preserved'if route.get('section')=='gateway'else'palette_unified','reason':reason,'unchangedLayout':r['unchangedLayout'],'beforeScreenshot':f'{REL}/before/{route["key"]}-{device}.png','referenceImage':REL+'/design/palette-reference.png','afterScreenshot':f'{REL}/after/{route["key"]}-{device}.png'}
  for k in ['beforeScreenshot','referenceImage','afterScreenshot']:assert (ROOT/row[k]).stat().st_size>1000
  rows.append(row)
  images=''.join('<figure><figcaption>'+label+'</figcaption><a href="../../'+row[k]+'"><img loading="lazy" src="../../'+row[k]+'" alt="'+html.escape(label+' '+route['key'])+'"></a></figure>'for label,k in [('调整前','beforeScreenshot'),('配色参考','referenceImage'),('实际实现','afterScreenshot')])
  cards.append('<article data-device="'+device+'"><h2>'+html.escape(route['key']+' · '+device)+'</h2><p>'+reason+'</p><section>'+images+'</section></article>')
(J/'coverage-table.json').write_text(json.dumps({'scope':'Moderate desktop palette unification; existing layout and scientific colors are retained.','rows':rows},ensure_ascii=False,indent=2)+'\n')
(J/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>LENS color continuity review</title><style>body{background:#eaf0f2;color:#153447;font:16px/1.6 Arial;margin:32px}section{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}figure{margin:0}img{width:100%}article{margin:40px 0}button{padding:10px 20px;margin-right:10px;font:inherit}video{max-width:100%;width:1000px}</style><h1>LENS · 全站配色统一</h1><p>现有布局和科学颜色保持；参考中的新增导航及改画图形不采用。</p><p><a href="REPORT.md">配色说明与测试</a></p><button onclick="filter(\'fullhd\')">1920×1080</button><button onclick="filter(\'desktop\')">1440×900</button>'+''.join(cards)+'<h2>真实操作录屏</h2><video controls preload="metadata" src="after/intro-demo.mp4"></video><script>function filter(d){document.querySelectorAll("article").forEach(a=>a.hidden=a.dataset.device!==d)}filter("fullhd")</script>')
print({'rows':len(rows),'paletteChanged':sum(r['decision']=='palette_unified'for r in rows)})
