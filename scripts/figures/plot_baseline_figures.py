"""Publication SVG masters, using editable Times New Roman text.

Reads local research evidence and saved paired contrasts. No API acquisition.
"""
from pathlib import Path
import argparse,csv,hashlib,io,json,os,re,xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT=ROOT/'reports/figures/publication';OUT.mkdir(parents=True,exist_ok=True)
DATA=json.loads((ROOT/'app/data/research-evidence.json').read_text())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--font-file',help='Installed Times New Roman TTF; also COURSE_FIGURE_FONT_FILE')
args=parser.parse_args()
custom_font=args.font_file or os.environ.get('COURSE_FIGURE_FONT_FILE')
if custom_font:
 font_file=Path(custom_font).expanduser().resolve()
 if not font_file.is_file():parser.error('The font file does not exist.')
 fm.fontManager.addfont(str(font_file))
 if fm.FontProperties(fname=str(font_file)).get_name()!='Times New Roman':parser.error('The selected font must be Times New Roman.')
try:fontpath=fm.findfont('Times New Roman',fallback_to_default=False)
except ValueError:parser.error('Times New Roman was not found. Install it or supply --font-file / COURSE_FIGURE_FONT_FILE. Snapshot app build does not require plotting.')
plt.rcParams.update({'font.family':'Times New Roman','font.size':12,'axes.titlesize':15,'axes.titleweight':'bold','axes.labelsize':12,'xtick.labelsize':11,'ytick.labelsize':11,'legend.fontsize':11,'svg.fonttype':'none','pdf.fonttype':42,'mathtext.fontset':'stix','axes.linewidth':.7,'axes.spines.top':False,'axes.spines.right':False,'axes.edgecolor':'#353842','axes.labelcolor':'#353842','text.color':'#252830','xtick.color':'#54545b','ytick.color':'#54545b','savefig.facecolor':'white'})
PURPLE='#955bc2';BLUE='#3978b6';TEAL='#2c8d83';ORANGE='#c87b47';GRAY='#7e8797';DARK='#252830'
MODEL_COLORS={'deepseek':'#3978b6','hy4':'#c87b47','qwen':'#8958b4','qwen3':'#2c8d83'}
NAMES={'qwen':'Qwen2.5 7B','qwen3':'Qwen3 8B','deepseek':'DeepSeek Flash','hy4':'Hunyuan HY4 preview'}
bundle={};axesmeta={}
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
def finish(fig,key,points=None,metas=None,png=False):
 b=io.StringIO();fig.savefig(b,format='svg',metadata={'Date':None,'Creator':'LENS · Matplotlib publication source'});svg=b.getvalue();start=svg.index('<svg');svg=svg[start:]
 if points:
  root=ET.fromstring(svg)
  for child in root.iter():
   if child.tag=='{'+NS+'}use':
    child.set('href',child.attrib.get('{http://www.w3.org/1999/xlink}href',''))
  for e in root.iter():
   gid=e.attrib.get('id')
   if gid in points:
    p=points[gid]
    if p.get('kind')=='paired-efficiency':
     e.set('data-efficiency-model',p['model_id']);e.set('data-efficiency-task',p['benchmark'])
     label=f"{NAMES[p['model_id']]}, {p['benchmark']}: output reduction {p['token_saving_pct']:.1f}%, score change {p['difference_pp']:+.1f} percentage points, 95% interval {p['ci_low_pp']:+.1f} to {p['ci_high_pp']:+.1f}. Open paired evidence."
    else:
     e.set('data-pub-prompt',p['prompt']);e.set('data-pub-model',p['model']);e.set('data-pub-task',p['task']);e.set('data-pub-dataset',p.get('dataset','reasoning'));e.set('data-pub-position',p.get('position',''))
     label=f"{p['prompt']}, {p['task']}, SR {p['sr']*100:.1f}%, {p['tokens']:.1f} tokens"
    e.set('tabindex','0');e.set('role','button');e.set('aria-label',label)
    title=ET.Element('{'+NS+'}title');title.text=e.attrib['aria-label'];e.insert(0,title)
  svg=ET.tostring(root,encoding='unicode')
 (OUT/f'{key}.svg').write_text(svg)
 if png:fig.savefig(OUT/f'{key}.png',dpi=180)
 bundle[key]=svg
 if metas:axesmeta[key]=metas
 plt.close(fig)
def style(ax):
 ax.set_axisbelow(True);ax.grid(axis='y',color='#e8e7ed',lw=.55);ax.tick_params(length=3,width=.65,pad=5);ax.spines['left'].set_color('#8a8a93');ax.spines['bottom'].set_color('#8a8a93')
# Observed strategy effects are the opening finding. No allocation model is plotted.
paired=[]
with (ROOT/'reports/baseline/reasoning_paired_contrasts.csv').open() as handle:
 for row in csv.DictReader(handle):
  if row['first']=='BeConcise' and row['second']=='DefaultCoT':
   paired.append({k:(v if k in ['model_id','benchmark','first','second'] else float(v)) for k,v in row.items()})
MODEL_ORDER=['deepseek','hy4','qwen','qwen3']
ordered=[next(r for r in paired if r['model_id']==mid and r['benchmark']==task) for mid in MODEL_ORDER for task in ['gsm8k','math500','mmlu']]
ys=np.array([i+i//3*.62 for i in range(12)])
for compact in [False,True]:
 fig=plt.figure(figsize=(10 if compact else 15.2,6.0))
 left=fig.add_axes([.31 if compact else .29,.19,.255,.67]);right=fig.add_axes([.68 if compact else .65,.19,.27 if compact else .29,.67]);points={}
 for ax in [left,right]:
  ax.set_ylim(ys[-1]+.65,-.65);ax.set_yticks([]);style(ax);ax.grid(False);ax.spines['left'].set_visible(False)
  for j in [2,5,8]:ax.axhline((ys[j]+ys[j+1])/2,color='#e5e3eb',lw=.6,zorder=0)
 left.set_xlim(0,52);left.set_xticks([0,10,20,30,40,50]);left.grid(axis='x',color='#e8e7ed',lw=.55)
 right.set_xlim(-8,21);right.set_xticks([-5,0,5,10,15,20]);right.axvline(0,color='#8a8a93',lw=.85,ls=(0,(3,3)),zorder=1)
 left.set_title('Output reduction (%)',loc='left',pad=14,size=13 if compact else 15);right.set_title('Score change (pp)' if compact else 'Score change (percentage points)',loc='left',pad=14,size=13 if compact else 15)
 left.set_xlabel('Less output',labelpad=10);right.set_xlabel('Concise − Default CoT' if compact else 'Concise CoT − Default CoT',labelpad=10)
 for i,(r,y) in enumerate(zip(ordered,ys)):
  point={**r,'kind':'paired-efficiency'}
  bar=left.barh(y,r['token_saving_pct'],height=.46,color=TEAL,alpha=.82,zorder=2)[0];gid=('compact-' if compact else '')+f'efficiency-output-{i}';bar.set_gid(gid);points[gid]=point
  left.text(r['token_saving_pct']+.9,y,f"{r['token_saving_pct']:.1f}%",va='center',size=10 if compact else 11,color=DARK)
  delta=r['difference_pp'];err=right.errorbar(delta,y,xerr=[[max(0,delta-r['ci_low_pp'])],[max(0,r['ci_high_pp']-delta)]],fmt='o',ms=6.2,color=TEAL,ecolor=TEAL,elinewidth=1.25,capsize=3,mec='white',mew=.6,zorder=3)
  gid=('compact-' if compact else '')+f'efficiency-score-{i}';err.lines[0].set_gid(gid);points[gid]=point
  right.text(20.6,y,f'{delta:+.1f}',ha='right',va='center',size=10 if compact else 11,color=DARK)
  left.text(-.045,y,'MMLU-Pro' if r['benchmark']=='mmlu' else r['benchmark'].upper(),transform=left.get_yaxis_transform(),ha='right',va='center',size=10 if compact else 11,color='#54545b')
 for j,mid in enumerate(MODEL_ORDER):
  y=float(ys[j*3+1]);left.text(-1.02 if compact else -.69,y,'HY4 preview' if compact and mid=='hy4' else NAMES[mid],transform=left.get_yaxis_transform(),ha='left',va='center',size=12 if compact else 13,weight='bold')
 fig.text(.05 if compact else .06,.965,'Concise reasoning across tasks',size=16 if compact else 17,weight='bold',va='top')
 fig.text(.95 if compact else .94,.955,'12 conditions / 200 paired questions' if compact else '4 models / 3 tasks / 200 paired questions per condition',ha='right',size=10 if compact else 11,color='#64646c')
 fig.text(.05 if compact else .06,.078,'Bars: mean output reduction. Points: paired score changes with 95% question-bootstrap intervals.' if compact else 'Bars: observed mean output reduction. Points: observed paired score differences; whiskers: 95% question-bootstrap intervals.',size=10,color='#60606a')
 fig.text(.05 if compact else .06,.033,'Source: reasoning saved responses. Exploratory, source-scored comparisons; crossing zero does not establish equivalence.' if compact else 'Source: reasoning saved responses. Pointwise exploratory intervals; source scoring retained. Crossing zero does not establish equivalence.',size=9.5 if compact else 10,color='#60606a')
 finish(fig,'efficiency-overview-compact' if compact else 'efficiency-overview',points,png=True)
for mid in NAMES:
 groups=[next(r for r in DATA['oracle'] if r['model']==mid and r['task']==task) for task in ['gsm8k','math500','mmlu']]
 fig,axs=plt.subplots(1,3,figsize=(15.2,5.3),sharey=True);fig.subplots_adjust(left=.06,right=.99,bottom=.28,top=.73,wspace=.23)
 fig.text(.06,.965,NAMES[mid],size=17,weight='bold',va='top');fig.text(.99,.955,'31 observed prompt strategies / 200 paired questions per task',size=11,ha='right',color='#64646c')
 handles=[Line2D([0],[0],marker='o',color='none',mfc=GRAY,mec='white',ms=6,label='Other prompts'),Line2D([0],[0],marker='D',color='none',mfc=DARK,mec='white',ms=7,label='Direct'),Line2D([0],[0],marker='o',color='none',mfc=BLUE,mec='white',ms=8,label='Default CoT'),Line2D([0],[0],marker='*',color='none',mfc=TEAL,mec='white',ms=11,label='Concise CoT')]
 fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.53,.91),ncol=4,frameon=False,columnspacing=2.3)
 points={}
 for ax,g in zip(axs,groups):
  default=g['baseline'];concise=next(p for p in g['prompts'] if p['prompt']=='BeConcise')
  ax.annotate('',xy=(concise['tokens'],concise['sr']*100),xytext=(default['tokens'],default['sr']*100),arrowprops={'arrowstyle':'->','color':TEAL,'lw':1.1,'alpha':.7,'shrinkA':6,'shrinkB':7},zorder=3)
  for i,prompt in enumerate(g['prompts']):
   color=GRAY;marker='o';size=35;z=4
   if prompt['prompt']=='NoCoT':color=DARK;marker='D';size=48;z=6
   if prompt['prompt']=='DefaultCoT':color=BLUE;size=85;z=7
   if prompt['prompt']=='BeConcise':color=TEAL;marker='*';size=165;z=8
   art=ax.scatter(prompt['tokens'],prompt['sr']*100,s=size,c=color,marker=marker,edgecolor='white',linewidth=.7,alpha=1 if z>4 else .78,zorder=z);gid=f"prompt-{g['task']}-{i}";art.set_gid(gid);points[gid]={**prompt,'model':mid,'task':g['task']}
  maxx=max(prompt['tokens'] for prompt in g['prompts'])*1.10
  ax.set_xlim(0,maxx);ax.set_ylim(-2,104);ax.xaxis.set_major_locator(MaxNLocator(nbins=4,integer=True));ax.set_yticks([0,25,50,75,100]);ax.set_title('MMLU-Pro' if g['task']=='mmlu' else g['task'].upper(),pad=13);style(ax)
  ax.set_xlabel('Mean output tokens',labelpad=10)
  ax.text(0,-.29,f"Default: {default['tokens']:.0f} tokens / {default['sr']*100:.1f}%",transform=ax.transAxes,size=10.5,color=BLUE)
  ax.text(0,-.39,f"Concise: {concise['tokens']:.0f} tokens / {concise['sr']*100:.1f}%",transform=ax.transAxes,size=10.5,color=TEAL)
 axs[0].set_ylabel('Observed source pass rate (%)',labelpad=10)
 fig.text(.06,.057,'Linear token axes; task-specific ranges. Arrows connect Default to Concise CoT. All 31 points are observed prompt conditions.',size=10,color='#60606a')
 fig.text(.06,.012,'Source: reasoning saved responses. Observed source scoring is retained; output length is not a preassigned generation budget.',size=10,color='#60606a')
 finish(fig,f'efficiency-{mid}',points,png=mid=='qwen3')
# Conditional position curves, with paired end-minus-middle contrasts.
for scope in ['DefaultCoT','NoCoT','BeConcise','main19','core8']:
 for metric in range(4):
  rs=[next(r for r in DATA['positions'] if r['scope']==scope and r['metric']==metric and r['model']==mid) for mid in ['qwen','qwen3']]
  interaction=next(r for r in DATA['interactions'] if r['scope']==scope and r['metric']==metric)
  fig=plt.figure(figsize=(15.2,5.1));gs=fig.add_gridspec(1,3,width_ratios=[1,1,1.05],left=.065,right=.985,bottom=.20,top=.68,wspace=.36);axs=[fig.add_subplot(gs[0,i]) for i in range(3)]
  label={'DefaultCoT':'Default CoT','NoCoT':'Direct answer','BeConcise':'Concise CoT','main19':'19 regular strategies','core8':'8 core strategies'}[scope]
  metricname=['First-line answer hit','Strict final match','Final answer contains','Full-response contains'][metric]
  fig.text(.065,.965,'Position effects by context length',size=17,weight='bold',va='top');fig.text(.985,.955,f'{label} / {metricname}',size=11,ha='right',color='#64646c')
  fig.text(.065,.865,'200 matched questions. Points: measured document indices; error bars: question-cluster bootstrap 95% intervals.',size=11,color='#64646c')
  handles=[Line2D([0],[0],color=MODEL_COLORS['qwen'],lw=2,marker='o',ms=6,label=NAMES['qwen']),Line2D([0],[0],color=MODEL_COLORS['qwen3'],lw=2,ls=(0,(4,2)),marker='s',ms=5,label=NAMES['qwen3'])]
  fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.06,.825),ncol=2,frameon=False,columnspacing=2.2)
  lo=min(np.min(r['low']) for r in rs)*100;hi=max(np.max(r['high']) for r in rs)*100;lower=max(0,np.floor((lo-4)/10)*10);upper=min(100,np.ceil((hi+5)/10)*10)
  for di,(ax,docs,xx) in enumerate(zip(axs[:2],[10,20],[[1,5,10],[1,10,20]])):
   for r,col,marker,ls in zip(rs,[MODEL_COLORS['qwen'],MODEL_COLORS['qwen3']],['o','s'],['-',(0,(4,2))]):
    y=np.array(r['rates'][di])*100;l=np.array(r['low'][di])*100;h=np.array(r['high'][di])*100
    ax.errorbar(xx,y,yerr=[y-l,h-y],fmt='none',ecolor=col,elinewidth=.85,capsize=3,alpha=.55);ax.plot(xx,y,color=col,lw=2,ls=ls,marker=marker,markersize=6,mec='white',mew=1,zorder=4)
   ax.set(xlim=(.35,docs+.65),ylim=(lower,upper));ax.set_xticks([1,5,10] if docs==10 else [1,5,10,15,20]);ax.set_title(f'{docs} documents',pad=13);ax.set_yticks(np.arange(lower,upper+1,10));style(ax);ax.set_xlabel('Relevant document index',labelpad=11)
  axs[0].set_ylabel(f'{metricname} (%)',labelpad=10)
  ax=axs[2];contr=[rs[0]['contrasts']['back_mid'],rs[1]['contrasts']['back_mid'],interaction];labels=['Qwen2.5','Qwen3','Difference'];colors=[MODEL_COLORS['qwen'],MODEL_COLORS['qwen3'],GRAY]
  for i,(r,col) in enumerate(zip(contr,colors)):
   x=r['delta']*100;l=r['lo']*100;h=r['hi']*100
   ax.plot([l,h],[2-i,2-i],color=col,lw=1.8);ax.plot([l,l],[2-i-.045,2-i+.045],color=col,lw=1);ax.plot([h,h],[2-i-.045,2-i+.045],color=col,lw=1);ax.scatter([x],[2-i],s=50,color=col,edgecolors='white',lw=.8,zorder=4);ax.annotate(f'{x:+.2f}',(x,2-i),xytext=(0,10),textcoords='offset points',ha='center',size=11,color=col)
  ax.axvline(0,color='#9b98a3',lw=.8,ls=(0,(3,3)));ax.set_yticks([2,1,0],labels);ax.set_ylim(-.5,2.7);ax.set_title('End − middle (pooled)',pad=13);ax.set_xlabel('Paired difference (pp)',labelpad=11);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=8);ax.grid(axis='x',color='#eceaf0',lw=.5);ax.set_axisbelow(True)
  fig.text(.065,.057,'Only three observations per curve: positions 5 and 15 are unmeasured in the 20-document panel. Contrasts pool both context lengths equally.',size=9.5,color='#60606a')
  fig.text(.065,.012,'Source: project document_qa response snapshot; NQ-Open multi-document QA. Definition of each score is retained separately.',size=9.5,color='#60606a')
  finish(fig,f'position-{scope}-{metric}',png=(scope=='DefaultCoT' and metric==0))
# A univariate companion: distribution of finite fitted thresholds.
fig,axs=plt.subplots(1,3,figsize=(15.2,4.4),sharey=True);fig.subplots_adjust(left=.06,right=.99,bottom=.19,top=.78,wspace=.24)
fig.text(.06,.96,'Qwen2.5 7B',size=17,weight='bold',va='top');fig.text(.99,.95,'Distribution of fitted per-question token thresholds',size=12,ha='right')
for ax,g in zip(axs,[r for r in DATA['oracle'] if r['model']=='qwen']):
 vals=np.sort([t for t in g['thresholds'] if t is not None]);ax.step(vals,np.arange(1,len(vals)+1)/len(vals)*100,where='post',color=PURPLE,lw=2);ax.set_xlim(0,max(vals)*1.05);ax.set_ylim(0,102);style(ax);ax.set_title('MMLU-Pro' if g['task']=='mmlu' else g['task'].upper(),pad=13);ax.set_xlabel('Fitted threshold (tokens)');ax.text(.96,.1,f"Finite: {g['finite']}/200",transform=ax.transAxes,ha='right',size=11,color='#64646c')
axs[0].set_ylabel('Finite-threshold questions (%)');fig.text(.06,.057,'Empirical CDF. Infinite thresholds are excluded from the CDF and counted separately.',size=9.5,color='#60606a');fig.text(.06,.012,'Source: project reasoning response archive; same-question thresholds fitted across 31 prompt observations.',size=9.5,color='#60606a');finish(fig,'threshold-cdf')
for metric in range(4):
 prompts=list(dict.fromkeys(r['prompt'] for r in DATA['position_matrix']))
 fig,axs=plt.subplots(2,1,figsize=(15.2,5.7));fig.subplots_adjust(left=.075,right=.925,bottom=.26,top=.79,hspace=.58)
 fig.text(.075,.965,'Position sensitivity across prompt strategies',size=17,weight='bold',va='top')
 fig.text(.075,.875,'Each cell: 400 responses from 200 matched questions; 10- and 20-document settings pooled equally.',size=11,color='#64646c')
 points={}
 for ax,mid in zip(axs,['qwen','qwen3']):
  rs=[next(r for r in DATA['position_matrix'] if r['model']==mid and r['prompt']==p) for p in prompts]
  vals=np.array([[r['positions'][j]['scores'][metric]*100 for r in rs] for j in range(3)])
  im=ax.pcolormesh(np.arange(len(prompts)+1),np.arange(4),vals,cmap='Purples',vmin=0,vmax=100,edgecolors='white',linewidth=.8,rasterized=False)
  for j in range(3):
   for i,r in enumerate(rs):
    v=vals[j,i];art=ax.text(i+.5,j+.5,f'{v:.0f}',ha='center',va='center',size=10.5,color='white' if v>=70 else '#252830')
    gid=f"matrix-{mid}-{j}-{i}";art.set_gid(gid);a=r['positions'][j]
    points[gid]={'model':mid,'task':'document_qa','dataset':'document_qa','position':a['position'],'prompt':r['prompt'],'tokens':a['tokens'],'sr':v/100}
  ax.set_xlim(0,len(prompts));ax.set_ylim(3,0);ax.set_yticks([.5,1.5,2.5],['Beginning','Middle','End']);ax.set_xticks(np.arange(len(prompts))+.5)
  labels=[p.replace('DefaultCoT','Default CoT').replace('BeConcise','Concise').replace('WordLimit','Words').replace('TokenLimit','Tokens').replace('StepLimit','Steps') for p in prompts]
  ax.set_xticklabels(labels,rotation=55,ha='right',size=11);ax.set_title(NAMES[mid],loc='left',pad=11,size=14);ax.tick_params(length=0,pad=6)
  for spine in ax.spines.values():spine.set_visible(False)
  if mid=='qwen':ax.set_xticklabels([])
 cax=fig.add_axes([.945,.30,.012,.47]);cb=fig.colorbar(im,cax=cax,ticks=[0,25,50,75,100]);cb.outline.set_visible(False);cb.ax.tick_params(length=2,labelsize=10);cb.set_label(['First-line hit (%)','Strict final match (%)','Final contains (%)','Full-response contains (%)'][metric],size=11,labelpad=9)
 fig.text(.075,.057,'Observed rates. Prompt conditions include formatting and budget stress tests.',size=9.5,color='#60606a')
 fig.text(.075,.012,'Source: project document_qa response snapshot; NQ-Open multi-document QA. Each metric is a separate string-based scoring definition.',size=9.5,color='#60606a')
 finish(fig,f'position-matrix-{metric}',points,png=metric==0)
(OUT/'figure-metadata.json').write_text(json.dumps({'figures':list(bundle),'axes':axesmeta,'font':'Times New Roman','font_file_used':Path(fontpath).name,'input_features_sha256':DATA['source_sha256'],'paired_contrasts_sha256':hashlib.sha256((ROOT/'reports/baseline/reasoning_paired_contrasts.csv').read_bytes()).hexdigest()},ensure_ascii=False,separators=(',',':')))
print(f'{len(bundle)} editable SVG masters generated; Times New Roman: {fontpath}')
