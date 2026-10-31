"""Offline paired analysis of the two existing cleaned experimental datasets.

Reads local normalized data only. Outputs aggregates and figures, never dialogue text.
Run from the repository root: python scripts/analysis/analyze_baselines.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
OUT = ROOT / 'reports/baseline'
FIG = OUT / 'figures'
SEED = 20261023
BOOTSTRAPS = 5000
MODELS = ['deepseek', 'hy4', 'qwen', 'qwen3']
BENCHMARKS = ['gsm8k', 'math500', 'mmlu']
MODEL_LABELS = {'deepseek': 'DeepSeek Flash', 'hy4': 'HY4 preview',
                'qwen': 'Qwen2.5 7B', 'qwen3': 'Qwen3 8B',
                'Qwen/Qwen2.5-7B-Instruct': 'Qwen2.5 7B', 'Qwen/Qwen3-8B': 'Qwen3 8B'}
METRICS = ['paper_firstline', 'strict_final_em', 'final_contains', 'full_response_contains']
METRIC_LABELS = ['首行包含答案', '最终答案严格匹配', '最终答案包含', '全文包含答案']


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_table(name, rows):
    table = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    table.to_csv(OUT / f'{name}.csv', index=False, lineterminator='\n')
    return table


def bootstrap_difference(pairs, first, second):
    """Resample independent question clusters; retain all conditions in a cluster."""
    pairs = pairs.copy()
    pairs['difference'] = pairs[first] - pairs[second]
    g = pairs.groupby('question_id')['difference'].agg(['sum', 'count'])
    sums, counts = g['sum'].to_numpy(float), g['count'].to_numpy(float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g), size=(BOOTSTRAPS, len(g)))
    samples = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {'pairs': len(pairs), 'independent_questions': len(g),
            'first_rate': float(pairs[first].mean()),
            'second_rate': float(pairs[second].mean()),
            'difference_pp': float(pairs['difference'].mean() * 100),
            'ci_low_pp': float(lo * 100), 'ci_high_pp': float(hi * 100)}


def paired(frame, index, condition, first, second, metric):
    p = frame.pivot(index=index, columns=condition, values=metric)
    p = p[[first, second]].dropna().reset_index()
    return bootstrap_difference(p, first, second)


def load():
    zcols = ['model_id', 'benchmark', 'question_id', 'prompt_id', 'score_current',
             'grading_status', 'output_tokens', 'input_tokens', 'is_truncated', 'included_in_review']
    z = pd.read_csv(ROOT/'data/processed/reasoning/responses_clean.csv.gz', usecols=zcols)
    z['unresolved'] = ~z.grading_status.isin(['已判分', '已按保存的逐条复核结论判分'])
    fcols = ['model_id', 'question_id', 'scenario_id', 'task_type', 'prompt_id',
             'strategy_scope', 'document_count', 'position_label', *METRICS,
             'output_tokens', 'input_tokens', 'is_truncated', 'needs_review',
             'repaired_empty_marker', 'attempt_count']
    f = pd.read_csv(ROOT/'data/processed/document_qa/responses_clean.csv.gz', usecols=fcols)
    assert len(z) == 74400 and len(f) == 74800
    assert not z.duplicated(['model_id', 'benchmark', 'question_id', 'prompt_id']).any()
    assert not f.duplicated(['model_id', 'scenario_id']).any()
    assert z.groupby(['model_id', 'benchmark', 'prompt_id']).size().eq(200).all()
    return z, f


def analyze_reasoning(z):
    summary = z.groupby(['model_id', 'benchmark', 'prompt_id']).agg(
        responses=('score_current', 'size'), questions=('question_id', 'nunique'),
        current_score_rate=('score_current', 'mean'), mean_output_tokens=('output_tokens', 'mean'),
        median_output_tokens=('output_tokens', 'median'), truncation_rate=('is_truncated', 'mean'),
        unresolved_rate=('unresolved', 'mean'), review_rate=('included_in_review', 'mean')).reset_index()
    write_table('reasoning_prompt_summary', summary)
    contrasts = []
    chosen = [('DefaultCoT', 'NoCoT'), ('BeConcise', 'DefaultCoT'),
              ('WordLimit(25)', 'DefaultCoT'), ('WordLimit(50)', 'DefaultCoT'),
              ('WordLimit(100)', 'DefaultCoT'), ('StepLimit(2)', 'DefaultCoT'),
              ('TokenLimit(10)', 'DefaultCoT')]
    for (model, benchmark), group in z.groupby(['model_id', 'benchmark']):
        for first, second in chosen:
            stat = paired(group, ['question_id'], 'prompt_id', first, second, 'score_current')
            a = group[group.prompt_id == first].set_index('question_id').sort_index()
            b = group[group.prompt_id == second].set_index('question_id').sort_index()
            assert a.index.equals(b.index) and len(a) == 200
            # Extreme sensitivity only to unresolved grades, assuming resolved grades valid.
            a_low = a.score_current.where(~a.unresolved, 0).mean()
            a_high = a.score_current.where(~a.unresolved, 1).mean()
            b_low = b.score_current.where(~b.unresolved, 0).mean()
            b_high = b.score_current.where(~b.unresolved, 1).mean()
            contrasts.append({'model_id': model, 'benchmark': benchmark, 'first': first, 'second': second,
                **stat, 'first_mean_tokens': float(a.output_tokens.mean()),
                'second_mean_tokens': float(b.output_tokens.mean()),
                'token_saving_pct': float((1-a.output_tokens.mean()/b.output_tokens.mean())*100),
                'first_truncation_rate': float(a.is_truncated.mean()),
                'second_truncation_rate': float(b.is_truncated.mean()),
                'first_unresolved_rate': float(a.unresolved.mean()),
                'second_unresolved_rate': float(b.unresolved.mean()),
                'unresolved_sensitivity_low_pp': float((a_low-b_high)*100),
                'unresolved_sensitivity_high_pp': float((a_high-b_low)*100)})
    contrasts = write_table('reasoning_paired_contrasts', contrasts)
    status = z.groupby(['model_id', 'benchmark', 'grading_status']).size().reset_index(name='responses')
    write_table('reasoning_grading_status', status)
    budget = z[z.prompt_id.str.match(r'TokenLimit\(\d+\)')].copy()
    budget['requested_tokens'] = budget.prompt_id.str.extract(r'\((\d+)\)').astype(int)
    budget['exceeds_requested_tokens'] = budget.output_tokens > budget.requested_tokens
    write_table('reasoning_token_instruction_compliance', budget.groupby(['model_id','benchmark','prompt_id','requested_tokens']).agg(
        responses=('output_tokens','size'),mean_output_tokens=('output_tokens','mean'),
        median_output_tokens=('output_tokens','median'),exceeds_requested_rate=('exceeds_requested_tokens','mean')).reset_index())
    return summary, contrasts


def analyze_document_qa(f):
    main = f[f.task_type == 'document_qa'].copy()
    english = main[main.strategy_scope == 'main_comparison']
    source_manifest = json.loads((ROOT/'data/raw/document_qa/manifest.json').read_text())
    core_ids = source_manifest['primary_strategy_ids']
    scopes = [('NoCoT', main[main.prompt_id=='NoCoT']),
              ('core8', main[main.prompt_id.isin(core_ids)]), ('main19', english)]
    summary = main.groupby(['model_id', 'prompt_id', 'strategy_scope']).agg(
        responses=('paper_firstline', 'size'), **{m:(m,'mean') for m in METRICS},
        mean_output_tokens=('output_tokens', 'mean'), truncations=('is_truncated','sum'),
        truncation_rate=('is_truncated','mean'), review_rate=('needs_review','mean')).reset_index()
    write_table('document_qa_prompt_summary', summary)
    contrasts, positions = [], []
    for scope, subset in scopes:
        for (model, docs, pos), g in subset.groupby(['model_id','document_count','position_label']):
            positions.append({'scope':scope, 'model_id':model, 'document_count':int(docs),
                'position':pos,'responses':len(g), 'questions':g.question_id.nunique(),
                **{m:float(g[m].mean()) for m in METRICS}})
        for model, group in subset.groupby('model_id'):
            for metric in METRICS:
                for documents in ['pooled',10,20]:
                    g = group if documents=='pooled' else group[group.document_count==documents]
                    for first in ['front','back']:
                        stat=paired(g,['question_id','prompt_id','document_count'],'position_label',first,'middle',metric)
                        contrasts.append({'scope':scope,'model_id':model,'metric':metric,'kind':'position',
                            'documents':documents,'first':first,'second':'middle',**stat})
                stat=paired(group,['question_id','prompt_id','position_label'],'document_count',10,20,metric)
                contrasts.append({'scope':scope,'model_id':model,'metric':metric,'kind':'length',
                    'documents':'paired','first':'10docs','second':'20docs',**stat})
    for model, group in main.groupby('model_id'):
        for first, second in [('DefaultCoT','NoCoT'),('BeConcise','DefaultCoT'),('BeConcise','NoCoT'),('WordLimit(50)','DefaultCoT')]:
            for metric in METRICS:
                stat=paired(group,['question_id','document_count','position_label'],'prompt_id',first,second,metric)
                contrasts.append({'scope':'paired_prompts','model_id':model,'metric':metric,'kind':'prompt',
                    'documents':'paired','first':first,'second':second,**stat})
    for scope, subset in scopes:
        for metric in METRICS:
            a,b='Qwen/Qwen3-8B','Qwen/Qwen2.5-7B-Instruct'
            stat=paired(subset,['question_id','prompt_id','document_count','position_label'],'model_id',a,b,metric)
            contrasts.append({'scope':scope,'model_id':'Qwen3-Qwen2.5','metric':metric,'kind':'model',
                'documents':'paired','first':a,'second':b,**stat})
    controls = f[f.task_type=='closedbook_control']
    for model, group in main[main.prompt_id=='NoCoT'].groupby('model_id'):
        # Each of the six open-book conditions is paired with the same question's control.
        control = controls[controls.model_id==model].set_index('question_id')
        for metric in METRICS:
            pairs=group[['question_id',metric]].rename(columns={metric:'openbook'}).copy()
            pairs['closedbook']=pairs.question_id.map(control[metric])
            assert pairs.closedbook.notna().all()
            contrasts.append({'scope':'NoCoT','model_id':model,'metric':metric,'kind':'context',
                'documents':'pooled','first':'openbook','second':'closedbook',
                **bootstrap_difference(pairs,'openbook','closedbook')})
    contrasts=write_table('document_qa_paired_contrasts',contrasts)
    positions=write_table('document_qa_position_summary',positions)
    write_table('document_qa_control_summary',controls.groupby('model_id').agg(
        responses=('paper_firstline','size'),**{m:(m,'mean') for m in METRICS}).reset_index())
    diagnostics = []
    for model, group in main.groupby('model_id'):
        for scope, g in [('all31',group),('main19',group[group.strategy_scope=='main_comparison'])]:
            diagnostics.append({'model_id':model,'scope':scope,'responses':len(g),
                'truncated':int(g.is_truncated.sum()),'needs_review':int(g.needs_review.sum()),
                'firstline_positive_final_contains_negative':int(((g.paper_firstline==1)&(g.final_contains==0)).sum()),
                'firstline_negative_final_contains_positive':int(((g.paper_firstline==0)&(g.final_contains==1)).sum()),
                'full_positive_strict_negative':int(((g.full_response_contains==1)&(g.strict_final_em==0)).sum())})
    write_table('document_qa_scoring_diagnostics',diagnostics)
    write_table('document_qa_truncation_outcomes',main.groupby(['model_id','prompt_id','is_truncated']).agg(
        responses=('paper_firstline','size'),**{m:(m,'mean') for m in METRICS}).reset_index())
    return summary,contrasts,positions


def style():
    names={f.name for f in fm.fontManager.ttflist}
    font=next((s for s in ['PingFang SC','Noto Sans CJK SC','Arial Unicode MS','Heiti SC'] if s in names),'DejaVu Sans')
    plt.rcParams.update({'font.family':font,'font.size':11,'axes.unicode_minus':False,
        'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold',
        'axes.labelcolor':'#334155','text.color':'#172033','xtick.color':'#475569','ytick.color':'#475569',
        'figure.facecolor':'white','savefig.facecolor':'white','svg.fonttype':'none'})


def save(fig,name,caption):
    fig.text(.02,.015,caption,fontsize=9,color='#475569')
    fig.savefig(FIG/f'{name}.png',dpi=180,bbox_inches='tight')
    svg = FIG/f'{name}.svg'
    fig.savefig(svg,bbox_inches='tight')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    plt.close(fig)


def plots(zc,fs,fc,fp):
    style()
    fig,axes=plt.subplots(1,3,figsize=(13,4.8),sharey=True)
    for ax,b in zip(axes,BENCHMARKS):
        s=zc[(zc.benchmark==b)&(zc['first']=='DefaultCoT')&(zc['second']=='NoCoT')].set_index('model_id').loc[MODELS]
        y=np.arange(4)
        ax.axvline(0,color='#94a3b8',lw=1)
        ax.errorbar(s.difference_pp,y,xerr=[s.difference_pp-s.ci_low_pp,s.ci_high_pp-s.difference_pp],fmt='o',color='#2563eb',capsize=4)
        ax.set_yticks(y,[MODEL_LABELS[m] for m in MODELS]);ax.invert_yaxis()
        ax.set_title(b.upper());ax.set_xlabel('DefaultCoT − NoCoT 评分差（百分点）')
        ax.grid(axis='x',alpha=.16);ax.set_xlim(-23,86)
        for i,(_,r) in enumerate(s.iterrows()):
            ax.text(r.difference_pp+1.5,i-.17,f'{r.difference_pp:+.1f}',fontsize=10)
    fig.suptitle('逐步推理提示的收益随模型与任务改变',fontsize=16)
    fig.subplots_adjust(bottom=.21,top=.8,wspace=.2)
    save(fig,'01_reasoning_cot_effect','当前源评分快照；每个点 200 道同题配对；线为按题 bootstrap 95% 区间。模型间评分版本存在差异。')

    for prompt,name,title in [('BeConcise','02_reasoning_concise','简洁推理在 12 组条件下均减少返回 token'),('WordLimit(50)','03_reasoning_word50','同样的 50 词提示在不同模型上效果相反')]:
        s=zc[(zc['first']==prompt)&(zc['second']=='DefaultCoT')]
        fig,axes=plt.subplots(1,2,figsize=(11.4,5.2))
        for ax,col,label,cm in [(axes[0],'difference_pp','当前评分差（百分点）','RdBu'),(axes[1],'token_saving_pct','平均返回 token 减少（%）','Blues')]:
            matrix=s.pivot(index='model_id',columns='benchmark',values=col).loc[MODELS,BENCHMARKS]
            vmax=max(abs(matrix.min().min()),abs(matrix.max().max())) if col=='difference_pp' else 100
            im=ax.imshow(matrix,cmap=cm,vmin=-vmax if col=='difference_pp' else 0,vmax=vmax,aspect='auto')
            ax.set_xticks(range(3),[b.upper() for b in BENCHMARKS]);ax.set_yticks(range(4),[MODEL_LABELS[m] for m in MODELS])
            ax.set_title(label)
            for i in range(4):
                for j in range(3):
                    v=matrix.iloc[i,j]
                    ax.text(j,i,f'{v:+.1f}' if col=='difference_pp' else f'{v:.1f}',ha='center',va='center',color='white' if abs(v)>vmax*.6 else '#172033')
            fig.colorbar(im,ax=ax,shrink=.75)
        fig.suptitle(title,fontsize=16)
        fig.tight_layout(rect=[0,.10,1,.91])
        save(fig,name,f'{prompt} 相对 DefaultCoT；每格同样 200 道题。token 为接口返回量，不能等同真实内部推理量或金额。')

    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
    for ax,model in zip(axes,sorted(fp.model_id.unique())):
        for docs,color in [(10,'#2563eb'),(20,'#d97706')]:
            s=fp[(fp.scope=='main19')&(fp.model_id==model)&(fp.document_count==docs)].set_index('position').loc[['front','middle','back']]
            ax.plot(range(3),s.paper_firstline*100,'o-',color=color,label=f'{docs} 篇文档')
            for i,v in enumerate(s.paper_firstline*100):ax.annotate(f'{v:.1f}%',(i,v),xytext=(0,7 if docs==10 else -15),textcoords='offset points',ha='center',fontsize=10)
        ax.set_title(MODEL_LABELS[model]);ax.set_xticks(range(3),['前部','中部','尾部']);ax.set_ylim(45,77)
        ax.grid(axis='y',alpha=.15);ax.legend(frameon=False);ax.set_ylabel('首行答案命中率（%）')
    fig.suptitle('资料前置较稳定，完整 U 形未在两模型上重现',fontsize=16)
    fig.tight_layout(rect=[0,.11,1,.91])
    save(fig,'04_document_qa_position','19 种 main_comparison 提示的等权汇总；每个点 3,800 次响应，只有 200 道独立题；首行命中指标。')

    fig,axes=plt.subplots(1,2,figsize=(12,5),sharex=True)
    for ax,model in zip(axes,sorted(fs.model_id.unique())):
        s=fc[(fc.kind=='prompt')&(fc.model_id==model)&(fc['first']=='DefaultCoT')&(fc['second']=='NoCoT')].set_index('metric').loc[METRICS]
        y=np.arange(4);ax.axvline(0,color='#94a3b8',lw=1)
        ax.errorbar(s.difference_pp,y,xerr=[s.difference_pp-s.ci_low_pp,s.ci_high_pp-s.difference_pp],fmt='o',color='#7c3aed',capsize=4)
        ax.set_yticks(y,METRIC_LABELS);ax.set_title(MODEL_LABELS[model]);ax.set_xlabel('DefaultCoT − NoCoT（百分点）');ax.grid(axis='x',alpha=.15)
        ax.set_xlim(-15,21);ax.invert_yaxis()
        for i,v in enumerate(s.difference_pp):ax.text(v+1,i-.14,f'{v:+.1f}',fontsize=10)
    fig.suptitle('评分方式会改变提示词比较的方向',fontsize=16)
    fig.tight_layout(rect=[0,.11,1,.91])
    save(fig,'05_document_qa_metric_sensitivity','每模型 1,200 个同场景配对、200 道独立题；按题 bootstrap 95% 区间。全文包含只说明出现过答案字符串。')

    selected=['NoCoT','DefaultCoT','BeConcise','NoProperGrammar','BulletPoints','NoSpaces']
    s=fs[fs.model_id=='Qwen/Qwen3-8B'].set_index('prompt_id').loc[selected]
    fig,axes=plt.subplots(1,3,figsize=(13,5),sharey=True)
    for ax,col,title,color in zip(axes,['paper_firstline','final_contains','truncation_rate'],['首行答案命中率','最终答案包含率','输出截断率'],['#2563eb','#0891b2','#dc2626']):
        vals=s[col]*100;ax.barh(range(len(s)),vals,color=color,height=.58)
        ax.set_yticks(range(len(s)),selected);ax.set_xlim(0,100);ax.set_title(title);ax.set_xlabel('%');ax.grid(axis='x',alpha=.12)
        for i,v in enumerate(vals):ax.text(v+1,i,f'{v:.1f}',va='center',fontsize=10)
    axes[0].invert_yaxis()
    fig.suptitle('Qwen3 格式约束下出现高首行命中与高截断并存',fontsize=16)
    fig.tight_layout(rect=[0,.11,1,.91])
    save(fig,'06_document_qa_format_truncation','每条策略 1,200 次响应，200 道独立题；NoProperGrammar 截断 424 条。截断率是运行结果，不能直接解释为知识错误。')


def main():
    OUT.mkdir(parents=True,exist_ok=True);FIG.mkdir(exist_ok=True)
    z,f=load()
    zs,zc=analyze_reasoning(z)
    fs,fc,fp=analyze_document_qa(f)
    plots(zc,fs,fc,fp)
    manifest={'inputs':{str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'data/processed/reasoning/responses_clean.csv.gz',ROOT/'data/processed/document_qa/responses_clean.csv.gz']},
        'rows':{'reasoning':len(z),'document_qa_all':len(f),'document_qa_document_qa':int((f.task_type=='document_qa').sum())},
        'independent_questions':{'reasoning':int(z.question_id.nunique()),'document_qa':int(f.question_id.nunique())},
        'bootstrap':{'seed':SEED,'resamples':BOOTSTRAPS,'unit':'question_id','interval':'percentile 95%, pointwise, exploratory, no multiplicity adjustment'},
        'versions':{'pandas':pd.__version__,'numpy':np.__version__,'matplotlib':matplotlib.__version__},
        'api_calls_made':0,
        'scope':'reasoning current grades retained; document_qa metrics separate; core8 follows source manifest primary_strategy_ids; main19 means strategy_scope=main_comparison; no row-level text exported',
        'document_qa_metric_provenance':'Collection manifest originally calls extracted normalized exact match primary; cleaned table later labels paper_firstline primary. Report all metrics and acknowledge this change.',
        'reasoning_unresolved':int(z.unresolved.sum()),'reasoning_unresolved_with_positive_score':int((z.unresolved&(z.score_current==1)).sum())}
    (OUT/'analysis_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    print('Saved aggregate tables and six figures to reports/baseline/.')


if __name__=='__main__':
    main()
