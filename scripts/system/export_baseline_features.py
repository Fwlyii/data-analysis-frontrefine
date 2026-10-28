"""Build anonymous browser features and aggregate cubes from local cleaned data.

No conversation text, source response IDs, credentials or machine paths are exported.
Python standard library only; no network operations.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
OUT = ROOT / 'app/data'
CORE = ['NoCoT','DefaultCoT','BeConcise','BulletPoints','WordLimit(25)',
        'WordLimit(100)','TokenLimit(100)','StepLimit(2)']
MODELS = [
    {'id':'deepseek','name':'DeepSeek Flash','vendor':'DeepSeek','logo':'deepseek.svg','color':'#3978b6','parameters_b':None},
    {'id':'hy4','name':'HY4 preview','vendor':'腾讯混元','logo':'hunyuan.svg','color':'#c87b47','parameters_b':None},
    {'id':'qwen','name':'Qwen2.5 7B','vendor':'通义千问','logo':'qwen.svg','color':'#8958b4','parameters_b':7.61},
    {'id':'qwen3','name':'Qwen3 8B','vendor':'通义千问','logo':'qwen.svg','color':'#2c8d83','parameters_b':8.2},
]
MODEL_MAP={'Qwen/Qwen2.5-7B-Instruct':'qwen','Qwen/Qwen3-8B':'qwen3'}
FIELDS=['id','question','dataset','model','task','prompt','documents','position',
        'scores','tokens','truncated','unresolved','review','finish','latency','attempts']


def number(value,integer=False):
    if value in ['',None]:return None
    return int(float(value)) if integer else float(value)


def flag(v):
    return str(v).lower()=='true'


def filehash(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def json_write(p,data):
    p.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cubes={};features=[];questions=defaultdict(dict);retry_ids={};sources={}
    totals={};statuses=defaultdict(lambda:defaultdict(int))
    for dataset,folder in [('reasoning','reasoning'),('document_qa','document_qa')]:
        path=ROOT/'data/processed'/folder/'responses_clean.csv.gz'
        sources[str(path.relative_to(ROOT))]=filehash(path)
        count=0
        with gzip.open(path,'rt',encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                count+=1
                model=MODEL_MAP.get(r['model_id'],r['model_id'])
                task=r['benchmark'] if dataset=='reasoning' else r['task_type']
                docs=0 if dataset=='reasoning' else int(r['document_count'])
                pos='none' if dataset=='reasoning' else r['position_label']
                prompt=r['prompt_id']
                token=number(r['output_tokens'],True)
                truncated=flag(r['is_truncated'])
                unresolved=(r['grading_status'] not in ['已判分','已按保存的逐条复核结论判分']) if dataset=='reasoning' else not bool(r['extracted_answer'].strip())
                review=flag(r['included_in_review'] if dataset=='reasoning' else r['needs_review'])
                scores=[int(r['score_current']),None,None,None] if dataset=='reasoning' else [int(float(r[m])) for m in ['paper_firstline','strict_final_em','final_contains','full_response_contains']]
                q=r['question_id']
                if q not in questions[dataset]:questions[dataset][q]=f"{'Z' if dataset=='reasoning' else 'C'}{len(questions[dataset])+1:03d}"
                qid=questions[dataset][q]
                rid=f"{'Z' if dataset=='reasoning' else 'F'}{count:06d}"
                attempts=1 if dataset=='reasoning' else int(r['attempt_count'])
                if dataset=='document_qa' and attempts>1:retry_ids[r['record_id']]=rid
                features.append([rid,qid,dataset,model,task,prompt,docs,pos,scores,token,
                                 int(truncated),int(unresolved),int(review),r['finish_reason'],
                                 number(r['latency_seconds']),attempts])
                key=(dataset,model,task,prompt,docs,pos)
                if key not in cubes:
                    cubes[key]={'dataset':dataset,'model':model,'task':task,'prompt':prompt,
                        'documents':docs,'position':pos,'scope':r.get('strategy_scope',''),
                        'n':0,'questions':set(),'scores':[0,0,0,0],'tokens':0,'token_n':0,
                        'truncated':0,'unresolved':0,'review':0,'disagreement':[0,0,0,0]}
                c=cubes[key];c['n']+=1;c['questions'].add(qid)
                for i,s in enumerate(scores):
                    if s is not None:c['scores'][i]+=s
                if token is not None:c['tokens']+=token;c['token_n']+=1
                c['truncated']+=truncated;c['unresolved']+=unresolved;c['review']+=review
                if dataset=='document_qa':c['disagreement'][scores[0]*2+scores[2]]+=1
                if dataset=='reasoning':statuses[model][r['grading_status']]+=1
        totals[dataset]={'responses':count,'questions':len(questions[dataset])}
    for c in cubes.values():c['questions']=len(c['questions'])
    assert totals['reasoning']=={'responses':74400,'questions':600}
    assert totals['document_qa']=={'responses':74800,'questions':200}
    assert len(features)==149200 and len(cubes)==746
    attempts=defaultdict(list)
    with gzip.open(ROOT/'data/processed/document_qa/attempts_clean.csv.gz','rt',encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            rid=retry_ids.get(r['record_id'])
            if rid:
                attempts[rid].append({'attempt':int(r['attempt_number']),'started_at':r['started_at'],
                    'ended_at':r['ended_at'],'latency_seconds':number(r['latency_seconds']),
                    'http_status':number(r['http_status'],True),'retry_after':number(r['retry_after'])})
    for seq in attempts.values():seq.sort(key=lambda x:x['attempt'])
    prompts=[]
    with (ROOT/'data/processed/reasoning/prompts_clean.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):prompts.append({'id':r['prompt_id'],'instruction':r['prompt_text']})
    comparisons={}
    for kind in ['reasoning','document_qa']:
        with (ROOT/f'reports/baseline/{kind}_paired_contrasts.csv').open(newline='') as f:
            rows=[]
            for r in csv.DictReader(f):
                for k,v in list(r.items()):
                    if k in ['pairs','independent_questions']:r[k]=int(v)
                    elif k not in ['model_id','benchmark','first','second','scope','metric','kind','documents']:
                        r[k]=number(v)
                r['model_id']=MODEL_MAP.get(r['model_id'],r['model_id'])
                rows.append(r)
            comparisons[kind]=rows
    payload={'schema_version':'dashboard-v1','snapshot':'2026-10-23','models':MODELS,'prompts':prompts,
        'core_prompts':CORE,'totals':totals,'cells':list(cubes.values()),'comparisons':comparisons,
        'grading_statuses':dict(statuses),'attempts':dict(attempts),
        'provenance':{'inputs':sources,'api_calls_made':0,'feature_fields':FIELDS,
            'parameter_sources':[
                {'model':'qwen','parameters_b':7.61,'url':'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct'},
                {'model':'qwen3','parameters_b':8.2,'url':'https://huggingface.co/Qwen/Qwen3-8B'}],
            'size_caveat':'Only two distinct models have verified public parameter counts. No scale law or causal size claim can be inferred.',
            'scoring_caveat':'reasoning source grades are not harmonized across model groups. document_qa collection manifest originally names strict final EM primary, later cleaned data names first-line containment primary.',
            'privacy':'Only anonymous numeric/categorical response features are exported. No question, answer, reasoning, prompt instance, original response ID or code is included.'}}
    json_write(OUT/'summary.json',payload)
    feature_payload=json.dumps({'fields':FIELDS,'rows':features},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    (OUT/'features.json.gz').write_bytes(gzip.compress(feature_payload,mtime=0))
    print(f"Exported {len(cubes)} aggregate cells, {len(features)} anonymous feature records, {len(attempts)} retry runs.")
    print(f"Summary {(OUT/'summary.json').stat().st_size:,} bytes; compressed features {(OUT/'features.json.gz').stat().st_size:,} bytes.")


if __name__=='__main__':main()
