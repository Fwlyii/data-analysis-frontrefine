"""Generate native, editable Times New Roman SVGs for the saved code study."""
from pathlib import Path
import argparse, json, os, math
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import font_manager as fm

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
DATA=json.loads((ROOT/"app/data/code-evidence.json").read_text())
OUT=ROOT/"reports/figures/code_generation";OUT.mkdir(exist_ok=True,parents=True)
p=argparse.ArgumentParser(description=__doc__);p.add_argument("--font-file",default=os.environ.get("COURSE_FIGURE_FONT_FILE"));args=p.parse_args()
if args.font_file:fm.fontManager.addfont(args.font_file)
fm.findfont("Times New Roman",fallback_to_default=False)
plt.rcParams.update({"font.family":"Times New Roman","font.size":12,"axes.labelsize":12,"axes.titlesize":14,
 "axes.titleweight":"bold","svg.fonttype":"none","svg.hashsalt":"code-study-v1","pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False,
 "axes.edgecolor":"#8a8a93","xtick.color":"#54545b","ytick.color":"#54545b","text.color":"#252830","axes.labelcolor":"#353842"})
MODELS=DATA["models"];MIDS=[m["id"] for m in MODELS];NAMES={m["id"]:m["name"] for m in MODELS};COLORS={m["id"]:m["color"] for m in MODELS}
SHORT={"deepseek":"DeepSeek", "qwen":"Qwen2.5", "qwen3":"Qwen3"}
ERRORS={"assertion_failure":"Assertion failure","attribute_error":"Attribute error","type_error":"Type error","syntax_error":"Syntax error",
 "extraction_error":"Extraction error","dependency_error":"Dependency error","name_error":"Name error","timeout":"Timeout","runtime_error":"Runtime error",
 "file_error":"File error","index_error":"Index error","key_error":"Key error","value_error":"Value error","resource_error":"Resource error"}
PIDS=DATA["prompts"]
ORDER=[p for p in ["NoCoT","DefaultCoT","BeConcise","BulletPoints"] if p in PIDS]+[p for p in PIDS if p not in ["NoCoT","DefaultCoT","BeConcise","BulletPoints","NoSpaces","OnlyNumbers","NoProperGrammar"]]+["NoSpaces","OnlyNumbers","NoProperGrammar"]
def stat(mid,prompt="__all"):
 return next(r for r in DATA["stats"] if r["model"]==mid and r["prompt"]==prompt)
def nice(p):return p.replace("DefaultCoT","Default CoT").replace("BeConcise","Concise CoT").replace("NoCoT","Direct answer")
def axes(ax):
 ax.set_axisbelow(True);ax.grid(axis="y",color="#e8e7ed",linewidth=.65);ax.tick_params(length=3,color="#8a8a93")
def heatmap(ax, values, vmax):
 mesh=ax.pcolormesh(np.arange(4)-.5,np.arange(len(values)+1)-.5,values,cmap='Purples',vmin=0,vmax=vmax,shading='flat',rasterized=False,edgecolors='none')
 ax.set_xlim(-.5,2.5);ax.set_ylim(len(values)-.5,-.5)
 return mesh
bundle={}
def save(fig,key,links,preview=False):
 fig.text(.06,.035,'Source: code-generation@9dfc592; saved target-function-ast-v2 scores. 193 matched tasks; five independent samples per prompt.',size=10,color='#60606a')
 path=OUT/f'{key}.svg';fig.savefig(path,metadata={"Date":None})
 if preview:fig.savefig(OUT/f'{key}.png',dpi=150)
 plt.close(fig)
 ET.register_namespace('', 'http://www.w3.org/2000/svg');ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
 tree=ET.parse(path)
 for element in tree.iter():
  gid=element.get('id')
  if gid in links:
   meta=links[gid]
   for k,v in meta.items():element.set('data-code-'+k,str(v))
   element.set('role','button');element.set('tabindex','0')
   element.set('aria-label',meta['label']);element.set('style',(element.get('style','')+';cursor:pointer').strip(';'))
  href=element.get('{http://www.w3.org/1999/xlink}href')
  if href:element.set('href',href)
 tree.write(path,encoding='unicode',xml_declaration=False)
 bundle[key]=path.name

# Five estimates are calculated from five saved outcomes. No interpolated samples.
for prompt in ["__all"]+PIDS:
 pi="all" if prompt=="__all" else str(PIDS.index(prompt))
 for selection in ["all"]+MIDS:
  mids=MIDS if selection=="all" else [selection]
  fig,axs=plt.subplots(1,2,figsize=(15.2,5.5),gridspec_kw={"width_ratios":[1.1,1]});fig.subplots_adjust(left=.065,right=.985,bottom=.22,top=.76,wspace=.27)
  fig.text(.065,.96,'Independent sampling: expected coverage and observed gains',size=17,weight='bold',va='top')
  fig.text(.985,.945,'All 31 prompts' if prompt=="__all" else nice(prompt),size=12,ha='right')
  links={};x=np.arange(1,6)
  for j,mid in enumerate(mids):
   s=stat(mid,prompt);color=COLORS[mid];ax=axs[0]
   trend,=ax.plot(x,np.array(s['pass'])*100,color=color,linewidth=1.8,label=NAMES[mid],marker=['o','s','^'][MIDS.index(mid)],markersize=5)
   trend.set_gid('code-trend-'+mid)
   band=ax.fill_between(x,np.array(s['pass_low'])*100,np.array(s['pass_high'])*100,color=color,alpha=.10,linewidth=0)
   band.set_gid('code-band-'+mid)
   for k in range(5):
    a=ax.scatter([k+1],[s['pass'][k]*100],s=50,color=color,alpha=.001);gid=f'pass-{mid}-{k}';a.set_gid(gid)
    links[gid]={'action':'condition','model':mid,'prompt':prompt,'k':k+1,'label':f'{NAMES[mid]}, Pass@{k+1}, {s["pass"][k]*100:.2f}%'}
   offsets=(j-(len(mids)-1)/2)*(.7/len(mids));xx=np.arange(2,6)+offsets;bw=.7/len(mids)
   bars=axs[1].bar(xx,np.array(s['marginal'])*100,width=bw,color=color,alpha=.9)
   for k,b in enumerate(bars):
    gid=f'gain-{mid}-{k+2}';b.set_gid(gid);links[gid]={'action':'gains','model':mid,'prompt':prompt,'sample':k+2,'label':f'{NAMES[mid]}, sample {k+2}, +{s["marginal"][k]*100:.2f} pp'}
   last_gain=axs[1].text(xx[-1],s['marginal'][-1]*100+.12,f'{s["marginal"][-1]*100:.2f}',ha='center',size=10,color=color)
   last_gain.set_gid('code-lastgain-'+mid)
  axs[0].set(xlim=(.8,5.2),ylim=(0,min(105,math.ceil(max(stat(m,prompt)['pass_high'][-1] for m in mids)*10)*10+5)),xlabel='Independent samples available (k)',ylabel='Estimated Pass@k (%)')
  axs[0].set_xticks(x);axs[0].set_title('Unbiased Pass@k estimate',loc='left',pad=14)
  axs[1].set(xlim=(1.5,5.5),xlabel='Observed sample index',ylabel='Additional conditions solved (pp)');axs[1].set_xticks([2,3,4,5]);axs[1].set_title('Marginal gain in the observed order',loc='left',pad=14)
  for ax in axs:axes(ax)
  fig.legend(*axs[0].get_legend_handles_labels(),loc='upper left',bbox_to_anchor=(.06,.91),ncol=3,frameon=False,fontsize=12)
  fig.text(.065,.105,'Left: estimator from all five saved outcomes; shading: task-cluster bootstrap 95% intervals. Right: order-specific first-success gains.',size=10,color='#60606a')
  save(fig,f'code-sampling-{selection}-{pi}',links,preview=selection=='all' and prompt=='__all')

for scope in ['core','all']:
 ps=DATA['core'] if scope=='core' else ORDER
 for metric in [1,3,5,0]:
  fig,axs=plt.subplots(1,2,figsize=(15.2,6.0 if scope=='core' else 10.5),gridspec_kw={'width_ratios':[1.15,1]});fig.subplots_adjust(left=.17,right=.94,bottom=.15 if scope=='core' else .09,top=.79 if scope=='core' else .88,wspace=.38)
  fig.text(.06,.96,'Prompt effects depend on the model',size=17,weight='bold',va='top')
  fig.text(.06,.90 if scope=='core' else .92,'Prompt constraints apply to optional reasoning before the code; Python code requirements remain common.',size=11,color='#64646c')
  links={};vals=np.array([[(stat(m,p)['pass'][metric-1] if metric else stat(m,p)['pass'][4]-stat(m,p)['pass'][0])*100 for m in MIDS] for p in ps])
  ax=axs[0];im=heatmap(ax,vals,100 if metric else 20);ax.set_xticks(range(3),[SHORT[m] for m in MIDS]);ax.xaxis.tick_top();ax.set_yticks(range(len(ps)),[nice(p) for p in ps]);ax.tick_params(length=0,pad=9)
  for j,prompt in enumerate(ps):
   for i,mid in enumerate(MIDS):
    v=vals[j,i];t=ax.text(i,j,f'{v:.1f}',ha='center',va='center',size=11,color='white' if v>(55 if metric else 11) else '#252830');gid=f'prompt-{mid}-{j}';t.set_gid(gid);links[gid]={'action':'condition','model':mid,'prompt':prompt,'k':metric or 5,'label':f'{NAMES[mid]}, {prompt}, {v:.1f}%'}
    hit=Rectangle((i-.5,j-.5),1,1,facecolor=(0,0,0,.001),edgecolor='none',zorder=4);ax.add_patch(hit);hit.set_gid(gid+'-hit');links[gid+'-hit']=links.pop(gid)
  for sp in ax.spines.values():sp.set_visible(False)
  cb=fig.colorbar(im,ax=ax,orientation='horizontal',fraction=.035,pad=.07);cb.outline.set_visible(False);cb.solids.set_rasterized(False);cb.solids.set_edgecolor('face');cb.set_label(f'Pass@{metric} (%)' if metric else 'Pass@5 - Pass@1 (pp)',size=11)
  ax=axs[1]
  for i,mid in enumerate(MIDS):
   r=next(r for r in DATA['contrasts'] if r['model']==mid and r['prompt']=='DefaultCoT');k=(metric or 1)-1
   v=r['difference'][k]*100;lo=r['low'][k]*100;hi=r['high'][k]*100
   ax.errorbar([v],[2-i],xerr=[[v-lo],[hi-v]],color=COLORS[mid],fmt='o',capsize=4,markersize=7,linewidth=1.6)
   ax.text(v,2-i+.18,f'{v:+.2f} pp',ha='center',size=12,color=COLORS[mid]);t=ax.scatter([v],[2-i],alpha=.001,s=150);gid='contrast-'+mid;t.set_gid(gid);links[gid]={'action':'contrast','model':mid,'k':k+1,'label':f'{NAMES[mid]}, Default CoT - Direct answer, {v:+.2f} pp'}
  ax.axvline(0,color='#a49aac',linestyle='--',linewidth=.8);ax.set_ylim(-.6,2.7);ax.set_yticks(range(3),[SHORT[m] for m in MIDS[::-1]]);ax.set_xlabel('Paired Pass difference (pp)');ax.set_title(f'Default CoT - Direct answer / Pass@{metric or 1}',loc='left',pad=23);axes(ax);ax.grid(axis='y',visible=False)
  save(fig,f'code-prompts-{metric}-{scope}',links,preview=scope=='core' and metric==1)

for scope in ['core','all']:
 ps=DATA['core'] if scope=='core' else ORDER
 for category in DATA['error_categories']:
  cats=sorted(DATA['error_categories'],key=lambda e:-sum(stat(m)['errors'].get(e,0) for m in MIDS))
  fig,axs=plt.subplots(1,2,figsize=(15.2,7.0 if scope=='core' else 10.5));fig.subplots_adjust(left=.17,right=.94,bottom=.16 if scope=='core' else .09,top=.75 if scope=='core' else .82,wspace=.53)
  fig.text(.06,.96,'Where generated answers fail',size=17,weight='bold',va='top');fig.text(.06,.90 if scope=='core' else .92,'Denominator: all evaluable responses in each condition. Environment-excluded records are not model errors.',size=11,color='#64646c')
  links={}
  for ax,labels,kind in zip(axs,[cats,ps],['overall','prompt']):
   vals=np.array([[stat(m,p if kind=='prompt' else '__all')['errors'].get(category if kind=='prompt' else p,0)/stat(m,p if kind=='prompt' else '__all')['n']*100 for m in MIDS] for p in labels])
   im=heatmap(ax,vals,100);ax.set_xticks(range(3),[SHORT[m] for m in MIDS]);ax.xaxis.tick_top();ax.set_yticks(range(len(labels)),[nice(p) if kind=='prompt' else ERRORS.get(p,p) for p in labels]);ax.tick_params(length=0,pad=9)
   for j,prompt in enumerate(labels):
    for i,mid in enumerate(MIDS):
     v=vals[j,i];t=ax.text(i,j,f'{v:.1f}',ha='center',va='center',size=11,color='white' if v>55 else '#252830');gid=f'error-{kind}-{mid}-{j}';t.set_gid(gid);links[gid]={'action':'errors','model':mid,'prompt':prompt if kind=='prompt' else '__all','error':category if kind=='prompt' else prompt,'label':f'{NAMES[mid]}, {prompt}, {v:.1f}%'}
     hit=Rectangle((i-.5,j-.5),1,1,facecolor=(0,0,0,.001),edgecolor='none',zorder=4);ax.add_patch(hit);hit.set_gid(gid+'-hit');links[gid+'-hit']=links.pop(gid)
   for sp in ax.spines.values():sp.set_visible(False)
  axs[0].set_title('All prompt conditions',loc='left',pad=38);axs[1].set_title(ERRORS.get(category,category),loc='left',pad=38)
  cb=fig.colorbar(im,ax=list(axs),orientation='horizontal',fraction=.025,pad=.08,shrink=.6);cb.outline.set_visible(False);cb.solids.set_rasterized(False);cb.solids.set_edgecolor('face');cb.set_label('Error / evaluable responses (%)',size=11)
  save(fig,f'code-errors-{category}-{scope}',links,preview=scope=='core' and category=='extraction_error')

for k in [1,3,5]:
 fig,ax=plt.subplots(figsize=(15.2,5.8));fig.subplots_adjust(left=.075,right=.985,bottom=.2,top=.79)
 fig.text(.075,.96,'Output length and code-test performance',size=17,weight='bold',va='top');links={}
 for mid in MIDS:
  ss=[stat(mid,p) for p in PIDS]
  ax.scatter([s['mean_output_tokens'] for s in ss],[s['pass'][k-1]*100 for s in ss],s=44,color=COLORS[mid],alpha=.7,label=NAMES[mid],marker=['o','s','^'][MIDS.index(mid)])
  for j,s in enumerate(ss):
   a=ax.scatter([s['mean_output_tokens']],[s['pass'][k-1]*100],s=75,alpha=.001);gid=f'tokens-{mid}-{j}';a.set_gid(gid);links[gid]={'action':'condition','model':mid,'prompt':s['prompt'],'k':k,'label':f'{NAMES[mid]}, {s["prompt"]}, {s["mean_output_tokens"]:.1f} output tokens, Pass@{k} {s["pass"][k-1]*100:.1f}%'}
   if mid=='qwen3' and s['prompt'] in ['NoCoT','DefaultCoT','BeConcise']:ax.annotate(nice(s['prompt']),[s['mean_output_tokens'],s['pass'][k-1]*100],xytext=(5,5),textcoords='offset points',size=10,color=COLORS[mid])
 ax.set(xlabel='Mean returned output tokens / response',ylabel=f'Pass@{k} (%)',ylim=(0,math.ceil(max(s['pass'][k-1] for s in DATA['stats'] if s['prompt']!='__all')*10)*10+5));axes(ax);ax.legend(frameon=False,ncol=3,loc='upper left',bbox_to_anchor=(0,1.18));fig.text(.075,.10,'Each point: one model x prompt condition, 193 tasks x five saved samples. Association only; output tokens are not latency or price.',size=10,color='#60606a')
 save(fig,f'code-tokens-{k}',links,preview=k==1)
metadata={'font':'Times New Roman','source_evidence_sha256':__import__('hashlib').sha256((ROOT/'app/data/code-evidence.json').read_bytes()).hexdigest(),'figures':bundle}
(OUT/'figure-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
print(f'Generated {len(bundle)} editable code-study SVGs in Times New Roman.')
