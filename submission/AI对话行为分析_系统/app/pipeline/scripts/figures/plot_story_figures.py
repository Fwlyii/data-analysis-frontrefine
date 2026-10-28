"""Generate the exhibition from saved aggregate tables and actual examples only.
No network calls and no execution of generated model code. Regeneration uses Matplotlib.
Ordinary app build uses the committed SVG/JSON snapshot without plot dependencies.
"""
from pathlib import Path
import csv, json, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
APP=ROOT/'app'; OUT=APP/'assets/story'; OUT.mkdir(parents=True,exist_ok=True)
PREVIEW=ROOT/'build/figure_previews'; PREVIEW.mkdir(parents=True,exist_ok=True)
font_manager.findfont('Times New Roman',fallback_to_default=False)
INK='#243C52'; TEAL='#167B7B'; GOLD='#AC772E'; RED='#AF5961'; MUTED='#5D6D7C'; GRID='#E7EDF1'
plt.rcParams.update({'font.family':'Times New Roman','font.size':13,'axes.labelsize':13,'xtick.labelsize':12,'ytick.labelsize':13,'legend.fontsize':12,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.edgecolor':'#BBC7D0','axes.labelcolor':INK,'text.color':INK,'xtick.color':MUTED,'ytick.color':INK,'axes.linewidth':.7,'savefig.facecolor':'white'})
SOURCES={}
def rows(path):
    p=ROOT/path; SOURCES[str(path)]=hashlib.sha256(p.read_bytes()).hexdigest()
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def save(fig,name):
    fig.savefig(OUT/(name+'.svg'),metadata={'Date':None,'Creator':'Matplotlib / LENS saved evidence'})
    if name in ['concise-baseline','concise-cross','language-math500','limit-deepseek-math500-WordLimit','position','repair-qwen3-4']:
        fig.savefig(PREVIEW/(name+'.png'),dpi=145)
    if name=='position':
        p=OUT/(name+'.svg'); markup=p.read_text(); marker=markup.index('>',markup.index('<svg'))+1
        markup=markup[:marker]+'<style>[id^=position-focus-],[id^=interval-]{display:none}</style>'+markup[marker:];p.write_text(markup)
    plt.close(fig)
def grid(ax,axis='x'):
    ax.set_axisbelow(True);ax.grid(axis=axis,color=GRID,lw=.7);ax.tick_params(length=0,pad=8)
NAMES={'deepseek':'DeepSeek','hy4':'HY4','qwen':'Qwen2.5','qwen3':'Qwen3'}
TASKS={'gsm8k':'GSM8K','math500':'MATH500','mmlu':'MMLU','document_qa':'Document QA','code':'Code'}
profiles=rows('reports/prompt_variants/reasoning-all-prompt-profiles.csv')
concise=rows('reports/story/concise-cross-task-points.csv')
chinese=rows('reports/story/chinese-template-comparison.csv')
positions=rows('reports/document_positions/position-summary.csv')
curves=rows('reports/code_repair/full/curves.csv')
examples=json.loads((ROOT/'reports/story/saved-examples.json').read_text())
repairs=json.loads((ROOT/'reports/code_repair/full/examples.json').read_text())
for table in [profiles,concise,chinese,positions,curves]:
    for r in table:
        for key,value in list(r.items()):
            try:r[key]=float(value)
            except (ValueError,TypeError):pass
# Three actual discrete strategies; score and output have independent axes.
base=[next(r for r in profiles if r['model']=='qwen' and r['task']=='gsm8k' and r['prompt']==p) for p in ['NoCoT','DefaultCoT','BeConcise']]
fig,axs=plt.subplots(1,2,figsize=(9.3,4.5),gridspec_kw={'width_ratios':[1,1]})
fig.subplots_adjust(left=.19,right=.94,bottom=.16,top=.86,wspace=.28)
for ax,key,title,lim in zip(axs,['score_pct','mean_tokens'],['Score (%)','Mean output tokens'],[108,280]):
    for y,r,c in zip(range(3),base,[MUTED,INK,TEAL]):
        ax.barh(y,r[key],height=.37,color=c,zorder=3)
        ax.text(r[key]+lim*.025,y,f'{r[key]:.1f}',va='center',fontsize=14,color=c,weight='bold')
    ax.set(yticks=range(3),yticklabels=['NoCoT','DefaultCoT','BeConcise'],xlim=(0,lim),ylim=(2.65,-.65),xlabel=title)
    ax.set_xticks([0,50,100] if key=='score_pct' else [0,100,200]);grid(ax)
axs[1].set_yticklabels([])
save(fig,'concise-baseline')
# All 17 replications: keep the two negative estimates visible.
fig,axs=plt.subplots(1,2,figsize=(9.3,6.6),gridspec_kw={'width_ratios':[1,1]})
fig.subplots_adjust(left=.25,right=.94,bottom=.11,top=.94,wspace=.38)
for i,r in enumerate(concise):
    label=f"{NAMES.get(r['model'],r['model'])} / {TASKS.get(r['task'],r['task'])}"
    axs[0].barh(i,r['saving'],height=.47,color=TEAL)
    axs[0].text(r['saving']+1,i,f"{r['saving']:.1f}%",va='center',fontsize=11)
    axs[1].plot([0,r['delta']],[i,i],c=TEAL if r['delta']>=0 else RED,lw=2)
    axs[1].scatter(r['delta'],i,c=TEAL if r['delta']>=0 else RED,s=30,zorder=3)
    axs[1].text(r['delta']+(.32 if r['delta']>=0 else -.32),i,f"{r['delta']:+.1f}",va='center',ha='left' if r['delta']>=0 else 'right',fontsize=11)
for ax in axs:ax.set(ylim=(len(concise)-.4,-.7),yticks=range(len(concise)));grid(ax)
axs[0].set(yticklabels=[f"{NAMES.get(r['model'],r['model'])} / {TASKS.get(r['task'],r['task'])}" for r in concise],xlim=(0,70),xlabel='Output token reduction (%)')
axs[1].set(yticklabels=[],xlim=(-4,16),xlabel='Score difference (pp)');axs[1].axvline(0,color=MUTED,lw=.8)
save(fig,'concise-cross')
# Language templates, one benchmark per figure.
for task in TASKS:
    a=[r for r in chinese if r['task']==task]
    if not a:continue
    fig,axs=plt.subplots(1,2,figsize=(9.3,4.5),gridspec_kw={'width_ratios':[1.3,1]})
    fig.subplots_adjust(left=.15,right=.94,bottom=.17,top=.85,wspace=.33)
    for i,r in enumerate(a):
        x0,x1=r['default_score_pct'],r['chinese_score_pct']
        axs[0].plot([x0,x1],[i,i],color='#A9BCC6',lw=2.5)
        axs[0].scatter(x0,i,s=65,color=INK,zorder=3,label='DefaultCoT' if i==0 else None)
        axs[0].scatter(x1,i,s=65,color=TEAL,marker='D',zorder=3,label='Chinese template' if i==0 else None)
        axs[0].text(x0,i-.19,f'{x0:.1f}',ha='center',fontsize=12,color=INK)
        axs[0].text(x1,i+.29,f'{x1:.1f}',ha='center',fontsize=12,color=TEAL)
        axs[1].barh(i,r['token_saving_pct'],height=.34,color=TEAL)
        axs[1].text(r['token_saving_pct']+1,i,f"{r['token_saving_pct']:.1f}%",va='center')
    allscores=[r[k] for r in a for k in ['default_score_pct','chinese_score_pct']]
    axs[0].set(xlim=(max(0,min(allscores)-8),min(101,max(allscores)+9)),xlabel='Score (%)',yticks=range(4),yticklabels=[NAMES[r['model']] for r in a],ylim=(3.65,-.65));grid(axs[0])
    axs[1].set(xlim=(0,60),xlabel='Output token reduction (%)',yticks=range(4),yticklabels=[],ylim=(3.65,-.65));grid(axs[1])
    fig.legend(*axs[0].get_legend_handles_labels(),loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.55,1))
    save(fig,'language-'+task)
# Ordinal constraint categories; no synthetic interpolated points.
limits={}
for model in NAMES:
    for task in ['gsm8k','math500','mmlu']:
        for family in ['WordLimit','CharLimit','TokenLimit']:
            a=sorted([r for r in profiles if r['model']==model and r['task']==task and r['prompt'].startswith(family+'(')],key=lambda r:int(r['prompt'].split('(')[1].rstrip(')')))
            if not a:continue
            key=f'{model}-{task}-{family}'; limits[key]=a
            fig,axs=plt.subplots(2,1,figsize=(9.3,4.8),sharex=True,gridspec_kw={'height_ratios':[1.6,1]})
            fig.subplots_adjust(left=.13,right=.94,bottom=.16,top=.94,hspace=.28)
            x=range(len(a)); ys=[r['mean_tokens'] for r in a]
            axs[0].bar(x,ys,color=[RED if i==0 else INK for i in x],width=.46,zorder=3)
            for i,v in enumerate(ys):axs[0].text(i,v+max(ys)*.045,f'{v:.0f}',ha='center',fontsize=13)
            axs[0].set(ylabel='Mean output tokens',ylim=(0,max(ys)*1.28));grid(axs[0],'y')
            axs[1].plot(x,[r['score_pct'] for r in a],'-o',c=TEAL,lw=1.8,ms=5)
            axs[1].set(ylabel='Score (%)',ylim=(0,105),yticks=[0,50,100],xticks=list(x),xticklabels=[r['prompt'].split('(')[1].rstrip(')') for r in a],xlabel={'WordLimit':'Requested word limit','CharLimit':'Requested letter limit','TokenLimit':'Requested token limit'}[family]);grid(axs[1],'y')
            save(fig,'limit-'+key)
# Nine measured evidence positions, two models. Optional intervals are native SVG groups.
a=[r for r in positions if r['metric']=='final_contains']
fig,ax=plt.subplots(figsize=(9.3,4.7));fig.subplots_adjust(left=.12,right=.95,bottom=.17,top=.87)
for model,c,label in [('Qwen/Qwen3-8B',INK,'Qwen3 8B'),('Qwen/Qwen2.5-7B-Instruct',TEAL,'Qwen2.5 7B')]:
    rs=sorted([r for r in a if r['model']==model],key=lambda r:r['position'])
    if not rs:raise ValueError(model)
    x=[r['position'] for r in rs]; y=[r['rate']*100 for r in rs]
    band=ax.fill_between(x,[r['ci_low']*100 for r in rs],[r['ci_high']*100 for r in rs],color=c,alpha=.09);band.set_gid('interval-'+label.split()[0])
    ax.plot(x,y,'-o',color=c,label=label,lw=2,ms=6)
for p in [1,3,5,8,10,13,15,18,20]:
    line=ax.axvline(p,c=GOLD,alpha=.55,lw=1,ls=':');line.set_gid('position-focus-'+str(p))
ax.set(xlim=(.5,20.6),ylim=(40,82),xticks=[1,3,5,8,10,13,15,18,20],yticks=[40,50,60,70,80],xlabel='Evidence document position (out of 20)',ylabel='Final-answer hit rate (%)');grid(ax,'y')
ax.legend(loc='upper right',frameon=False,ncol=2,bbox_to_anchor=(1,1.2));save(fig,'position')
# Multi-turn versions. Current-version pass rate; independent samples are not called repair.
repair={}
arm_names={'counterexample':'Specific counterexample','pass_fail':'Pass / fail only','self_review':'Self-review','resample':'Independent resampling'}
arm_colors={'counterexample':TEAL,'pass_fail':GOLD,'self_review':INK,'resample':MUTED}
for model,key in [('Qwen3-8B','qwen3'),('Qwen2.5-7B','qwen')]:
    repair[key]=[r for r in curves if r['model']==model]
    for stage in range(5):
        fig,ax=plt.subplots(figsize=(9.3,4.7));fig.subplots_adjust(left=.12,right=.8,bottom=.17,top=.79)
        for arm in arm_names:
            rs=sorted([r for r in repair[key] if r['arm']==arm and r['round']<=stage],key=lambda r:r['round'])
            ax.plot([r['round'] for r in rs],[r['rate']*100 for r in rs],marker='o',lw=2,ms=5,color=arm_colors[arm],ls='--' if arm=='resample' else '-',label=arm_names[arm])
            last=rs[-1];ax.annotate(f"{last['success']:.0f}/164",(last['round'],last['rate']*100),xytext=(9,0),textcoords='offset points',va='center',fontsize=11,color=arm_colors[arm]) if stage==4 and arm in ['counterexample','self_review'] else None
        ax.set(xlim=(-.12,4.48),ylim=(72,90),xticks=range(5),xticklabels=['Initial','Revision 1','Revision 2','Revision 3','Revision 4'],yticks=[75,80,85,90],ylabel='Full-test pass rate (%)');grid(ax,'y')
        ax.legend(loc='upper left',bbox_to_anchor=(.01,1.28),ncol=2,frameon=False,columnspacing=1.4,handlelength=1.8)
        save(fig,f'repair-{key}-{stage}')
# Compact browser evidence; no raw archive or secrets.
data={'baseline':base,'concise':concise,'chinese':chinese,'limits':limits,'positions':a,'repair':repair,'examples':{'reasoning':examples['reasoning'],'positions':examples['positions'],'repair':[r for r in repairs if r['task_id']=='HumanEval/102' and r['model']=='Qwen3-8B']},'prompts':examples['prompt_specs'],'sources':SOURCES}
(APP/'data/story-evidence.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')))
(OUT/'provenance.json').write_text(json.dumps({'generator':'scripts/figures/plot_story_figures.py','font':'Times New Roman','sources':SOURCES,'figures':[p.name for p in OUT.glob('*.svg')]},ensure_ascii=False,indent=2))
print(f'Exhibition: {len(list(OUT.glob("*.svg")))} SVG figures + compact evidence.')
