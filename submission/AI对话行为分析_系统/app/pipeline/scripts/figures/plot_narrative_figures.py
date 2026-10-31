"""Build the research-design narrative from frozen evidence. No API requests."""
from pathlib import Path
import csv
import gzip
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator
import numpy as np

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
APP = ROOT / 'app'
OUT = APP / 'assets/narrative'
OUT.mkdir(parents=True, exist_ok=True)
font_manager.findfont('Times New Roman', fallback_to_default=False)
INK, TEAL, MUTED, GRID, PURPLE = '#243c52', '#167b7b', '#526779', '#e7edf1', '#756193'
plt.rcParams.update({'font.family':'Times New Roman','font.size':13,'svg.fonttype':'none',
    'svg.hashsalt':'lens-narrative','axes.spines.top':False,'axes.spines.right':False,
    'axes.spines.left':False,'axes.edgecolor':'#bbc7d0','axes.labelcolor':INK,
    'text.color':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.linewidth':.7})

source = ROOT / 'reports/prompt_variants/reasoning-all-prompt-profiles.csv'
with source.open(encoding='utf-8-sig') as f:
    profiles = list(csv.DictReader(f))
for r in profiles:
    for key in ['score_pct','mean_tokens','questions']:
        r[key] = float(r[key])
prompt_source=ROOT/'data/processed/reasoning/prompts_clean.csv'
if prompt_source.is_file():
    with prompt_source.open(encoding='utf-8-sig') as f:
        prompts=list(csv.DictReader(f))
else:
    prompts=json.loads((APP/'data/narrative-evidence.json').read_text())['prompts']
with gzip.open(ROOT/'data/processed/all_records.csv.gz', 'rt') as f:
    record = next(csv.DictReader(f))
sample_keys = ['record_id','model_id','benchmark','prompt_id','output_tokens','finish_reason','is_truncated','metric_name','metric_value','timestamp']
sample = {key:record[key] if record[key] else None for key in sample_keys}
for key in ['output_tokens','metric_value']:
    sample[key] = int(sample[key]) if sample[key] is not None else None
sample['is_truncated'] = sample['is_truncated'] == 'true'
quality = json.loads((ROOT/'data/quality/quality_report.json').read_text())
names = {'deepseek':'DeepSeek','hy4':'HY4','qwen':'Qwen2.5 7B','qwen3':'Qwen3 8B'}
benchmarks = ['gsm8k','math500','mmlu']
prompt_order = ['NoCoT','DefaultCoT','BeConcise','ChineseCoT','BulletPoints']
prompt_order += [p['prompt_id'] for p in prompts if p['prompt_id'] not in prompt_order]
fits = []

def export(fig, name):
    fig.savefig(OUT/(name+'.svg'), facecolor='white', metadata={'Date':None,'Creator':'Matplotlib / frozen prompt profiles'})
    plt.close(fig)

summary=json.loads((APP/'data/summary.json').read_text())
document_profiles=[]
position_names={'begin':'Position 1','start':'Position 1','front':'Position 1','middle':'Position 10','end':'Position 20','last':'Position 20','back':'Position 20'}
for r in summary['cells']:
    if r['dataset']=='document_qa' and r['task']=='document_qa' and r['documents']==20:
        label=position_names.get(r['position'])
        if label is None:
            raise ValueError('Unknown document position: '+r['position'])
        document_profiles.append({'model':r['model'],'task':label,'prompt':r['prompt'],
            'questions':r['questions'],'score_pct':100*r['scores'][2]/r['n'],
            'mean_tokens':r['tokens']/r['token_n']})
code_source=ROOT/'reports/code_generation/conditions.csv'
with code_source.open(encoding='utf-8-sig') as f:
    code_profiles=[{'model':r['model'],'task':'CodePromptEval','prompt':r['prompt'],
        'questions':int(r['questions']),'score_pct':100*float(r['pass_1']),
        'mean_tokens':float(r['mean_output_tokens'])} for r in csv.DictReader(f) if r['prompt']!='__all']
directions={
    'reasoning':{'profiles':profiles,'groups':benchmarks,'models':list(names),'ylabel':'Score (%)'},
    'document_qa':{'profiles':document_profiles,'groups':['Position 1','Position 10','Position 20'],'models':['qwen','qwen3'],'ylabel':'Answer hit rate (%)'},
    'code_generation':{'profiles':code_profiles,'groups':['CodePromptEval'],'models':['deepseek','qwen','qwen3'],'ylabel':'Pass@1 (%)'}}
for direction,config in directions.items():
    profiles_in_scope=config['profiles'];groups=config['groups']
    prefix='' if direction=='reasoning' else direction+'-'
    for model in config['models']:
        for mobile in [False, True]:
            count=len(groups)
            fig,axes=plt.subplots(count,1,figsize=(6.3,9.2 if count==3 else 4.8)) if mobile else plt.subplots(1,count,figsize=(11.2,4.3) if count==3 else (9,4.4))
            axes=np.atleast_1d(axes)
            if mobile:
                fig.subplots_adjust(left=.16,right=.94,bottom=.10,top=.94,hspace=.62)
            else:
                fig.subplots_adjust(left=.075,right=.97,bottom=.28,top=.85,wspace=.25)
            for i, (ax, benchmark) in enumerate(zip(axes,groups)):
                rs = [r for r in profiles_in_scope if r['model']==model and r['task']==benchmark]
                x = np.array([r['mean_tokens'] for r in rs]); y = np.array([r['score_pct'] for r in rs])
                slope, intercept = np.polyfit(np.log(x),y,1)
                prediction = intercept + slope*np.log(x)
                r2 = 1-np.sum((y-prediction)**2)/np.sum((y-y.mean())**2)
                if not mobile:
                    fits.append({'direction':direction,'model':model,'benchmark':benchmark,'slope':float(slope),'r2':float(r2),'points':len(rs)})
                ax.scatter(x,y,s=34,c='#aab9c2',alpha=.85,edgecolors='white',linewidths=.7,zorder=3)
                curve_x = np.linspace(max(1,float(x.min())),float(x.max()),200)
                ax.plot(curve_x,np.clip(intercept+slope*np.log(curve_x),0,100),c=PURPLE,lw=1.7,zorder=2)
                for prompt,color,marker in [('DefaultCoT',INK,'o'),('BeConcise',TEAL,'D')]:
                    row = next(r for r in rs if r['prompt']==prompt)
                    ax.scatter(row['mean_tokens'],row['score_pct'],s=62,c=color,marker=marker,edgecolors='white',linewidths=.8,zorder=5,label=prompt if i==0 else None)
                ax.set(title=benchmark.upper(),xlim=(0,max(x)*1.12),ylim=(0,105),yticks=[0,50,100])
                if direction=='code_generation':
                    ax.set_ylim(0,min(100,max(y)+10));ax.yaxis.set_major_locator(MaxNLocator(4))
                ax.xaxis.set_major_locator(MaxNLocator(4))
                ax.tick_params(length=0,pad=7,labelsize=16)
                ax.set_axisbelow(True);ax.grid(axis='y',color=GRID,lw=.7)
                ax.set_xlabel('Mean output tokens',fontsize=16,labelpad=8)
                if i==0 or mobile:ax.set_ylabel(config['ylabel'],fontsize=16)
            fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.005),fontsize=16)
            export(fig,prefix+'overview-'+model+('-mobile' if mobile else ''))

            matrix=np.array([[next(r['score_pct'] for r in profiles_in_scope if r['model']==model and r['task']==b and r['prompt']==p) for b in groups] for p in prompt_order])
            fig,ax=plt.subplots(figsize=(6.3,9.0) if mobile else (9.5,8.6))
            fig.subplots_adjust(left=.38 if mobile else .30,right=.91,bottom=.10,top=.94)
            cmap=LinearSegmentedColormap.from_list('research-score',['#f4f7f9','#b8d7d5',TEAL])
            image=ax.imshow(matrix,cmap=cmap,vmin=0,vmax=100,aspect='auto')
            ax.set_xticks(range(len(groups)),labels=[b.upper() for b in groups],fontsize=14)
            ax.set_yticks(range(len(prompt_order)),labels=prompt_order,fontsize=16 if mobile else 14)
            ax.tick_params(length=0,pad=8)
            for row in range(matrix.shape[0]):
                for col in range(matrix.shape[1]):
                    score=matrix[row,col]
                    ax.text(col,row,f'{score:.1f}',ha='center',va='center',fontsize=15 if mobile else 12,color='white' if score>=72 else INK)
            for spine in ax.spines.values():spine.set_visible(False)
            cb=fig.colorbar(image,ax=ax,orientation='horizontal',fraction=.025,pad=.06,aspect=30)
            cb.set_ticks([0,50,100]);cb.set_label(config['ylabel'],fontsize=12);cb.outline.set_visible(False);cb.ax.tick_params(length=0,labelsize=11)
            export(fig,prefix+'heatmap-'+model+('-mobile' if mobile else ''))

data={'counts':quality['counts'],'total':quality['total_physical_responses'],
    'environment_excluded':quality['code_generation_environment_exclusions'],
    'sample':sample,'prompts':prompts,'profiles':profiles,'fits':fits,
    'profiles_by_direction':{key:config['profiles'] for key,config in directions.items()},
    'directions':{key:{k:v for k,v in value.items() if k!='profiles'} for key,value in directions.items()},
    'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,APP/'data/summary.json',code_source]},
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'primary_metrics':{'reasoning':'source_score','document_qa':'final_contains','code_generation':'passed','document_positions':'final_contains','code_repair':'full_pass'}}
(APP/'data/narrative-evidence.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
print(f'Narrative: {len(profiles)} prompt conditions; {sum(r["slope"]>0 for r in fits if r["direction"]=="reasoning")}/{sum(r["direction"]=="reasoning" for r in fits)} positive reasoning slopes; {len(list(OUT.glob("*.svg")))} SVGs.')
