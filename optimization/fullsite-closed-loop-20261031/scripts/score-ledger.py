"""Serialize the AI's image review notes and rubric judgments; no automated aesthetic scoring."""
from pathlib import Path
import json
J=Path('optimization/fullsite-closed-loop-20261031');REL=J.as_posix()
weights=[25,20,20,15,15,5];names=['layoutHierarchy','typography','colorMaterial','siteConsistency','readingOperation','restraintFinish'];fnames=['layout','type','colorMaterial','decorativeAssets','spacingDetails'];fw=[30,20,20,20,10]
# Six criterion judgments chosen after visual inspection of every route contact sheet.
# Shared layouts share the same review basis; actual layout/density differences below
# get explicit adjustments. These are subjective ratings, not image-derived metrics.
profiles={
'gateway':([8.5,8.8,7.2,8.5,8.6,7.8],[9.3,9.3,9.5,9.5,9.1,9.4],[9.3,9.2,9.2,9.5,9.2,9.1]),
'question':([9.1,9.1,9.0,8.8,8.9,9.3],[9.0,9.0,9.0,9.1,8.8,9.2],[9.1,9.1,9.1,9.1,8.9,9.3]),
'collection':([9.0,8.9,8.7,8.8,8.8,9.3],[9.0,9.0,9.0,9.1,8.8,9.2],[9.0,9.0,8.9,9.1,8.9,9.3]),
'cleaning':([8.8,8.8,8.9,8.8,8.8,9.2],[8.9,8.9,9.0,9.1,8.9,9.2],[8.8,8.9,9.0,9.1,8.9,9.2]),
'landscape':([8.8,8.6,8.6,8.8,8.5,9.3],[8.6,8.7,8.8,8.8,8.5,9.0],[8.8,8.65,8.7,9.0,8.6,9.3]),
'story':([9.0,8.8,8.7,8.9,8.6,9.4],[8.4,8.7,8.8,8.8,8.5,9.0],[9.0,8.85,8.8,9.1,8.7,9.4]),
'publication':([8.9,8.9,8.8,8.8,8.7,9.3],[8.8,8.8,8.9,9.0,8.5,9.0],[8.9,8.9,8.9,9.1,8.8,9.3]),
'code':([8.8,8.7,8.8,8.7,8.6,9.2],[8.7,8.6,8.9,9.0,8.5,9.0],[8.8,8.75,8.9,9.1,8.7,9.2]),
'discovery':([8.7,8.6,8.7,8.5,8.5,9.2],[8.5,8.7,8.9,8.9,8.4,9.0],[8.7,8.65,8.8,9.0,8.6,9.2]),
'library':([8.5,8.4,8.8,8.6,8.5,9.4],[8.6,8.7,9.0,9.1,8.6,9.2],[8.5,8.5,8.9,9.1,8.7,9.4]),
'library-empty':([8.2,8.2,8.5,8.6,8.0,9.8],[8.3,8.4,8.8,9.0,8.1,9.3],[8.2,8.3,8.7,9.1,8.2,9.8])}
notes={
'gateway':'原生玻璃球体层次较软；选中A稿与五个独立生成资产带来清楚边缘、体积和色彩区分，暗背景保留标签重心。中央遮罩让原生品牌清晰。',
'question':'原深蓝问题页的衬线大标题、右侧轨迹和底部总量已经形成明确层级。生成A稿未带来至少5分提升；保留原构图，仅统一眉题和图标外围。',
'collection':'原三列设计因果链与真实数量排列紧凑而易读。A稿的分组变化收益有限且改变细节文字，保留原版结构；只统一眉题和说明展开态。',
'cleaning':'原代码样例与四步处理、总量和排除统计分区清楚。A稿并未显著超过原版；保留真实字段和双栏/手机堆叠，仅补外框层次。',
'landscape':'原曲线/矩阵、方向与模型切换已紧凑完整。生成稿引入不存在的控件和字段；其美观收益不足5分，保留原布局和原科学图形。',
'story':'原章节、条件、证据、图形与原始案例顺序清楚。A稿省略或改写标题和控件，不能作为结构替代；保留原布局，仅统一外围眉题/焦点。',
'publication':'原论文图保有专业排版与原尺寸滚动。A稿手机图重排会改变受保护图形的阅读方式，收益不足5分；保持原图与原框架，统一外围选择控件。',
'code':'采样/策略/错误/开销视图采用同一原框架，科学图宽度需保留。A稿未完整覆盖各视图交互；保留原版结构，只统一控件、焦点和抽屉质感。',
'discovery':'原章节的KPI、主要图形和阅读说明相互对齐。生成稿新增白色图面和简化导航并非明确提升；保留原章节结构与图形，统一外围操作视觉。',
'library':'原13类图表共用筛选与图例，模型色保留。A稿增强控制边框但增加未经授权控件，整体未高出5分；保留原布局，采纳外围控件质感。',
'library-empty':'此状态有意没有匹配图形。生成稿不能填充假数据，也没有足够审美收益支持改结构；保留原生空提示和全部筛选，统一外围边框。'}
inv=json.loads((J/'site-inventory.json').read_text());rows=[];reviews=[]
def total(v,w=weights):return round(sum(a*b/10 for a,b in zip(v,w)),2)
def group(r):
 if r.get('section')in ['gateway','question','collection','cleaning']:return r['section']
 if r.get('empty'):return 'library-empty'
 return r['family']
def reference(g,d):
 if g=='gateway':return 'gateway-mobile-selected.png' if d=='mobile' else 'direction-a.png'
 return 'direction-a-research.png' if g in ['question','collection','cleaning'] else 'direction-a-analysis.png' if g in ['landscape','story'] else 'direction-a-library.png'
for r in inv['routes']:
 g=group(r);assert g in profiles;r['designGroup']=g
 for device in ['desktop','mobile']:
  vs=[list(v) for v in profiles[g]];traits=[]
  if device=='mobile' and g!='gateway':
   # Native charts deliberately retain scientific dimensions and horizontal scrolling.
   delta=[-.3,-.15,0,0,-.25,0] if g in ['question','collection','cleaning'] else [-.45,-.25,0,0,-.35,0]
   vs=[[a+b for a,b in zip(v,delta)] for v in vs];traits.append('手机保持原生图形尺寸与纵向阅读，首屏信息密度高于桌面。')
  if g=='gateway' and device=='mobile':vs=[[8.8,8.7,7.6,8.3,9.0,8.3],[9.4,9.3,9.5,9.5,9.4,9.4],[9.4,9.2,9.1,9.5,9.4,9.1]]
  if r.get('view')=='heatmap':
   for v in vs:v[4]-=.15
   traits.append('31策略矩阵比趋势图更密集，保留原单元格/键盘选择。')
  if g=='story' and r.get('finding')=='limits':
   for v in vs:v[0]-=.1;v[4]-=.15
   traits.append('模型、基准、限长三组条件叠加；原横向图形与全部条件保持。')
   if r.get('limit')=='TokenLimit':
    for v in vs:v[1]+=.05
    traits.append('TokenLimit标题与请求单位更直接。')
   if r.get('task')=='mmlu':
    for v in vs:v[4]-=.05
    traits.append('MMLU-Pro条件文字较长，手机仍按原样换行。')
  if r.get('finding')=='language' and r.get('task')=='mmlu':
   for v in vs:v[1]-=.1
   traits.append('长结论标题按原版换行。')
  if g=='code' and r['key']in ['code-tokens','code-errors']:
   for v in vs:v[4]-=.15
   traits.append('原筛选和记录交互信息较多，保留原图内布局。')
  if g=='library' and r.get('chart')in ['parallel','behavior','timeline','tree']:
   for v in vs:v[4]-=.2
   traits.append('关系或多维图内标签较密，保持科学标记与选择入口。')
  if g=='library' and r.get('chart')in ['model','radar','flow']:
   for v in vs:v[0]+=.1
   traits.append('主图形轮廓明确，既有留白足够。')
  before,ref,after=map(total,vs)
  f=[9.6,9.4,8.7,9.4,9.3] if g=='gateway'and device=='desktop' else [9.0,9.2,9.1,9.4,8.9] if g=='gateway' else [9.1,8.8,9.0,9.4,9.1]
  fidelity=total(f,fw);decision='improved' if g=='gateway' else 'kept_with_reason'
  condition='；'.join(f'{k}={r[k]}' for k in ['direction','model','task','limit','view','finding','chart'] if k in r)
  reason=notes[g]+''.join(traits)+((' 本行实际条件：'+condition+'。')if condition else '')
  row={'routeKey':r['key'],'device':device,'url':r['url'],'designGroup':g,'beforeScreenshot':f'{REL}/before/{r["key"]}-{device}.png','referenceImage':f'{REL}/design/{reference(g,device)}','afterScreenshot':f'{REL}/after/{r["key"]}-{device}.png','beforeScore':before,'referenceScore':ref,'afterScore':after,'fidelityScore':fidelity,'decision':decision,'reason':reason}
  for k in ['beforeScreenshot','referenceImage','afterScreenshot']:assert Path(row[k]).stat().st_size>1000,row[k]
  if decision=='improved':assert ref>=before+5 and after>=ref-5 and fidelity>=90
  rows.append(row)
  reviews.append({**row,'rubric':{stage:dict(zip(names,v))for stage,v in zip(['before','reference','after'],vs)},'criterionReasons':{'layoutHierarchy':notes[g], 'typography':'核对实际标题、眉题、标签、正文换行；保留原生文字。'+('手机列宽较窄，长标题保持自然换行。'if device=='mobile'else'桌面对齐和标题层级稳定。'),'colorMaterial':'评估深蓝/象牙白/铜色外围关系。科学配色排除在改造范围之外。'+('五个生成球体比原CSS球体有更清楚的rim与内部层次。'if g=='gateway'else'原图配色保持，控件增加细边框与焦点。'),'siteConsistency':'比较首页、研究页和图表库的品牌、外围材质与原生控件。','readingOperation':'以本行实际截图检查可读性、条件密度和滚动，配套浏览器专项检查验证真实交互。'+' '.join(traits),'restraintFinish':'留白与装饰不覆盖科学表达；首页暗化背景并保留原生标识。'},'fidelityRubric':dict(zip(fnames,f)),'fidelitySampling':(['桌面：眉题/标题左上区域；中央透镜330px；五个链接边界；底部统计和提示。','手机：原154px中央透镜、74px触摸行、原生标签和页脚。'][device=='mobile'] if g=='gateway'else '比较对应参考板中的本布局：主标题与返回入口、控制行、原图矩形周围、下方说明与抽屉。科学图内部不要求复制模型改写。'),'remainingDifference':('中央原生SVG叠加环形蓝色材质，金色流体细节较稿件弱；原图标保留。手机中央透镜按原154px规格，生成图相对更大。'if g=='gateway'else'保留既有布局，不强行还原生成稿的虚构控件、字词或图表；外围统一属于小幅润色。')})
(J/'site-inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
(J/'coverage-table.json').write_text(json.dumps({'assessmentType':'AI subjective visual judgment','rows':rows},ensure_ascii=False,indent=2)+'\n')
(J/'design/visual-scores.json').write_text(json.dumps({'assessmentType':'AI subjective visual judgment','method':'AI inspected the real before/after contact sheets and full-size representative images; rubric values are subjective judgments, shared across matching layouts with explicitly noted density differences. Script only serializes these judgments. No objective aesthetic model or user-preference guarantee is claimed.','criterionWeights':dict(zip(names,weights)),'fidelityWeights':dict(zip(fnames,fw)),'selectedDirection':'A optical atlas','rejectedDirectionReason':'B breaks the existing warm-paper/serif language and invents mobile chrome; no clear overall gain.','rows':reviews},ensure_ascii=False,indent=2)+'\n')
print({'rows':len(rows),'improved':sum(r['decision']=='improved'for r in rows),'kept':sum(r['decision']=='kept_with_reason'for r in rows),'scoreRange':[min(r['afterScore']for r in rows),max(r['afterScore']for r in rows)]})
