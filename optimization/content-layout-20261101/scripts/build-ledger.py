"""Record measured changes and design decisions; do not invent aesthetic scores."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[3];J=Path(__file__).resolve().parents[1];REL=J.relative_to(ROOT).as_posix()
inventory=json.loads((J/'site-inventory.json').read_text())
reading=json.loads((J/'after/readability-checks.json').read_text())
assert all(r['passed']for r in reading['results'])
lookup={(r['routeKey'],r['device']):r for r in reading['rows']}
notes={
 'question':'原巨幅标题和小号三维度提示失衡。现在将原三维度做成清晰的宽屏信息模块，说明字号增大，统计信息移至主叙事区域，并补充解释性文案。',
 'collection':'从窄侧栏加细小台账，重排为三项研究原则、三步实验流程、三类任务样本和特殊研究分区，给实际内容清晰的层次和可读字号。',
 'cleaning':'从小字号代码与细步骤，重排为代码样例、独立处理时间线、质量总量和贯穿底部的两项数据规则；代码自然换行，说明随主页面滚动。',
 'landscape':'将极小内联条件重排为清晰的任务/模型/视图控制区，放大说明与模型名称，图形保持原始科学几何，解释区用独立底部条承载。',
 'story':'用可读章节条、主要结论与证据说明双区、明确条件和导出操作区重建层级，展开案例、方法与数据表字号同步增加。',
 'publication':'建立标题/背景/导出、研究条件、原始科学图形、可读结论说明的独立阅读区，增加正文、说明与操作尺寸。',
 'code':'四种代码研究视图使用明确的选择条和模型条件分区，放大背景、播放与导出操作，保留原始绘图与全部条件语义。',
 'discovery':'将细小统计行变成有层次的实际KPI分区，放大上下文、图形外围标题和解释，保留所有发现章节与真实图形。',
 'library':'将极小的一排筛选重排为分组筛选区，放大页面标题、条件标签、选择器、图例和说明；原13类图形的绘制逻辑和科学配色保持。'
}
references={g:('implementation-feedback.png' if g=='question' else 'implementation-feedback.png'if g in ['collection','cleaning','library'] else 'publication-discovery-layouts.png'if g in ['publication','discovery'] else 'analytics-layouts.png')for g in notes}
rows=[]
for route in inventory['routes']:
 for device in ['desktop','fullhd']:
  key=(route['key'],device);reading_row=lookup.get(key)
  if route.get('section')=='gateway':
   decision='entrance_preserved';reason='本轮针对内容页与电脑录制，保留已经完成的五个透明星球入口和开场交接。';reference='optimization/fullsite-closed-loop-20261031/design/direction-a.png';ratio=1;group='gateway'
  else:
   assert reading_row and reading_row['passed'],key
   group=reading_row['group'];decision='redesigned';reason=notes[group]
   reference=REL+'/design/'+references[group]
   ratios=[]
   for sample in reading_row['after']['samples']:
    before=next((b for b in reading_row['before']['samples']if b['selector']==sample['selector']),None)
    if before:ratios.append(sample['size']/before['size'])
   ratio=max(ratios);assert ratio>=1.15
  row={'routeKey':route['key'],'device':device,'url':route['url'],'group':group,'decision':decision,'reason':reason,'beforeScreenshot':f'{REL}/before/{route["key"]}-{device}.png','referenceImage':reference,'afterScreenshot':f'{REL}/after/{route["key"]}-{device}.png','measuredTypeImprovement':ratio,'measurements':reading_row['after']['samples'] if reading_row else []}
  for k in ['beforeScreenshot','referenceImage','afterScreenshot']:assert (ROOT/row[k]).stat().st_size>1000,row[k]
  rows.append(row)
(J/'coverage-table.json').write_text(json.dumps({'scope':'Desktop recording:1440×900 and1920×1080; all states also rendered at1366/1600/2560 widths.','rows':rows},ensure_ascii=False,indent=2)+'\n')
(J/'design/visual-review.json').write_text(json.dumps({'assessmentType':'Human-readable AI design review with actual measured typography; no automatic aesthetic veto','reasonForChangingMethod':'The prior high group-level baseline scores masked tiny text and wasted space. This round requires actual layout changes and live measured type improvements for every content state. Subjective appearance is described with reasons, not prefilled numeric scores.','referenceAdoption':'Native layout hierarchy, text sizes, panel architecture and material adopted. Invented navigation, data, graph colors and changed scientific marks in generated drafts rejected.','groups':[{'group':g,'review':n,'reference':references[g]}for g,n in notes.items()],'knownDifference':'Chart internals are retained from actual scientific rendering. Generated image redraws of charts are never adopted; native line materials and existing SVG icons approximate decorative textures.'},ensure_ascii=False,indent=2)+'\n')
cards=[]
for row in rows:
 imgs=''.join('<div><b>'+label+'</b><a href="../../'+row[field]+'"><img loading="lazy" src="../../'+row[field]+'"></a></div>'for label,field in [('Before','beforeScreenshot'),('Reference','referenceImage'),('After','afterScreenshot')])
 cards.append('<article data-device="'+row['device']+'"><h2>'+html.escape(row['routeKey']+' · '+row['device'])+'</h2><p>'+html.escape(row['reason'])+'</p><section>'+imgs+'</section></article>')
(J/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>LENS desktop layout review</title><style>body{background:#f5f2eb;color:#202522;font:16px/1.6 Arial;margin:32px}article{margin-bottom:48px}section{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}img{width:100%;display:block}h2{font-size:22px}button{font-size:16px;padding:10px 20px;margin-right:10px}</style><h1>LENS · 电脑录制版布局对照</h1><p>每页都关联本轮截图、设计参考与实测改动。设计图中的科学图形不作为实现依据。</p><nav><button onclick="filter(\'fullhd\')">1920×1080</button><button onclick="filter(\'desktop\')">1440×900</button></nav>'+''.join(cards)+'<script>function filter(d){document.querySelectorAll("article").forEach(a=>a.hidden=a.dataset.device!==d)}filter("fullhd")</script>')
print({'rows':len(rows),'contentStatesRedesigned':sum(r['decision']=='redesigned'for r in rows),'entranceStatesPreserved':sum(r['decision']=='entrance_preserved'for r in rows)})
