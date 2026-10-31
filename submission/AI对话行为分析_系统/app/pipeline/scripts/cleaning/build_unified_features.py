"""Build a typed, anonymous numeric index for all five experiment directions.

Physical saved responses only: shared repair seeds appear once, and the pilot
subset is not added again. Different success metrics remain explicitly named.
No model calls, code execution, score harmonization or missing-value imputation.
"""
from pathlib import Path
from collections import Counter,defaultdict
import csv,gzip,hashlib,json,datetime as dt
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
FIELDS={
 'record_id':('string','Anonymous unique identity within this released project','never missing'),
 'experiment_id':('category','Experiment direction; identifies the unit and protocol','never missing'),
 'model_id':('category','Canonical model family identifier','never missing'),
 'benchmark':('category','Benchmark/task family; not a score scale','never missing'),
 'question_key':('string','Experiment-scoped SHA-256 pseudonym of the source question ID','never missing'),
 'prompt_id':('category/null','Named prompt strategy','not applicable to repair baseline'),
 'timestamp':('UTC datetime/null','Recorded response timestamp normalized to UTC','not recorded in historical reasoning/code-generation sources'),
 'input_tokens':('integer/null','Provider input token count','provider/source did not record it'),
 'output_tokens':('integer/null','Provider output token count','provider/source did not record it'),
 'latency_seconds':('float/null','Recorded request elapsed seconds','source did not record it'),
 'finish_reason':('category/null','Provider completion stop reason','provider/source did not return it'),
 'is_truncated':('boolean/null','True only when the recorded finish reason indicates length','unknown when source finish reason absent'),
 'metric_name':('category','Native primary scoring rule; different tasks are not pooled','never missing'),
 'metric_value':('float/null','Native 0/1 observation under the named score','environment exclusion or unresolved source result; never filled with zero'),
 'environment_excluded':('boolean','Common code benchmark environment exclusion','false for experiments without this exclusion'),
 'document_count':('integer/null','Number of supplied reference documents','not applicable outside document QA'),
 'evidence_position':('integer/null','One-based relevant-document position','not applicable outside document QA'),
 'independent_sample':('integer/null','Index of an independent generation; not a repair turn','not applicable outside code-generation repetitions'),
 'revision_round':('integer/null','Number of code revisions after the shared seed; seed is 0','not applicable outside code repair'),
 'feedback_type':('category/null','seed/resample/self_review/pass_fail/counterexample','not applicable outside code repair'),
 'parent_record_key':('string/null','Pseudonym of the preceding physical repair response','no previous response or not applicable'),
}
MODEL_MAP={'deepseek':'deepseek','deepseek-flash':'deepseek','hy4':'hy4','qwen':'qwen','qwen3':'qwen3','Qwen/Qwen2.5-7B-Instruct':'qwen','Qwen/Qwen3-8B':'qwen3','qwen2.5-7b-instruct-cloud':'qwen','qwen3-8b-cloud':'qwen3'}
TABLES=[('reasoning','responses_clean.csv.gz','score_current','source_score'),('document_qa','responses_clean.csv.gz','final_contains','final_answer_contains'),('code_generation','responses.csv.gz','passed','test_pass'),('document_positions','responses.csv.gz','final_contains','final_answer_contains'),('code_repair','responses.csv.gz','full_pass','base_and_heldout_pass')]
def boolean(x):
 if x in [None,'']:return None
 if str(x).lower() in ['1','1.0','true']:return True
 if str(x).lower() in ['0','0.0','false']:return False
 raise ValueError('Invalid boolean')
def numeric(x):
 if x in [None,'']:return None
 v=float(x)
 if not __import__('math').isfinite(v):raise ValueError('Non-finite number')
 return int(v) if v.is_integer() else v
def pseudo(direction,value):return hashlib.sha256((direction+'|'+value).encode()).hexdigest()[:24]
def utc(x):
 if not x:return None
 date=dt.datetime.fromisoformat(x.replace('Z','+00:00'))
 if date.tzinfo is None:raise ValueError('Ambiguous source timestamp')
 return date.astimezone(dt.timezone.utc).isoformat()
def cell(v):return '' if v is None else str(v).lower() if isinstance(v,bool) else v

def main():
 out=ROOT/'data/processed';meta=ROOT/'data/quality';meta.mkdir(parents=True,exist_ok=True);counts=Counter();missing=Counter();seen=set();lineage=[];tables=[]
 index=out/'all_records.csv.gz'
 with gzip.open(index,'wt',encoding='utf-8',newline='') as dest:
  writer=csv.DictWriter(dest,fieldnames=list(FIELDS),lineterminator='\n');writer.writeheader()
  for direction,name,metric,metric_name in TABLES:
   p=out/direction/name;n=0;columns=None;unique=set()
   with gzip.open(p,'rt',encoding='utf-8',newline='') as f:
    for r in csv.DictReader(f):
     columns=list(r);n+=1;rid=r['record_id']
     if rid in unique:raise ValueError('Duplicate source identity in '+direction)
     unique.add(rid);rkey=pseudo(direction,rid)
     if rkey in seen:raise ValueError('Pseudonym collision')
     seen.add(rkey);excluded=boolean(r.get('environment_excluded')) or False;value=None if excluded else numeric(int(boolean(r[metric]))) if metric!='score_current' else numeric(r[metric])
     finish=r.get('finish_reason') or None
     qid=r.get('question_id') or r.get('task_id')
     row={'record_id':rkey,'experiment_id':direction,'model_id':MODEL_MAP[r['model_id']],'benchmark':r.get('benchmark') or ('HumanEvalPlus-Mini' if direction=='code_repair' else 'CodePromptEval' if direction=='code_generation' else 'NaturalQuestions-Open'),'question_key':pseudo(direction,qid),'prompt_id':r.get('prompt_id') or None,'timestamp':utc(r.get('timestamp')),'input_tokens':numeric(r.get('input_tokens')),'output_tokens':numeric(r.get('output_tokens')),'latency_seconds':numeric(r.get('latency_seconds')),'finish_reason':finish,'is_truncated':boolean(r.get('is_truncated')) if 'is_truncated' in r else (finish=='length' if finish else None),'metric_name':metric_name,'metric_value':value,'environment_excluded':excluded,'document_count':numeric(r.get('document_count')),'evidence_position':numeric(r.get('gold_position')),'independent_sample':numeric(r.get('sample_id')) if direction=='code_generation' else None,'revision_round':numeric(r.get('revision_round')) if direction=='code_repair' else None,'feedback_type':r.get('arm') if direction=='code_repair' else None,'parent_record_key':pseudo(direction,r['parent_record_id']) if r.get('parent_record_id') else None}
     if value is not None and value not in [0,1]:raise ValueError('Unexpected primary score')
     for k,v in row.items():missing[direction,k]+=v is None
     counts[direction]+=1;writer.writerow({k:cell(v) for k,v in row.items()});lineage.append({'record_id':rkey,'experiment_id':direction,'source_record_id':rid,'table':str(p.relative_to(ROOT))})
   tables.append({'experiment_id':direction,'path':str(p.relative_to(ROOT)),'records':n,'columns':columns,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 with gzip.open(out/'record_lineage.csv.gz','wt',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(lineage[0]),lineterminator='\n');w.writeheader();w.writerows(lineage)
 with (meta/'missingness.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['experiment_id','field','records','missing_count','missing_rate','missing_policy']);w.writeheader()
  for d,n in counts.items():
   for k,(_,_,policy) in FIELDS.items():w.writerow({'experiment_id':d,'field':k,'records':n,'missing_count':missing[d,k],'missing_rate':missing[d,k]/n,'missing_policy':policy})
 report={'schema':'unified-physical-responses-v1','api_calls':0,'generated_code_executed':False,'total_physical_responses':sum(counts.values()),'counts':dict(counts),'shared_seed_policy':'Each physical seed appears once; 6560 logical arm views and the pilot subset are not added to response counts.','metric_policy':'Keep task-native metric_name. Never calculate an all-task pooled accuracy from metric_value.','null_policy':'Empty CSV cell = null; no zero filling; booleans true/false; times UTC.','code_generation_environment_exclusions':465,'tables':tables,'unified_sha256':hashlib.sha256(index.read_bytes()).hexdigest()}
 if report['total_physical_responses']!=248586:raise ValueError('Unexpected total response count')
 (meta/'quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (ROOT/'data/inventory/processed_tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2)+'\n')
 lines=['# 数据字典','', '## 统一匿名特征表','', '`processed/all_records.csv.gz` 共 248,586 条物理响应。CSV 空单元格表示 null；布尔为 true/false；时间为 UTC。不同任务的评分规则由 metric_name 区分，不计算跨任务总准确率。','', '| 字段 | 类型 | 含义 | 缺失原因 / 规则 |','|---|---|---|---|']
 for k,(typ,meaning,policy) in FIELDS.items():lines.append(f'| {k} | {typ} | {meaning} | {policy} |')
 lines+=['','## 分实验清洗表','', '原题、完整回答、原始 ID 和代码只在完整项目的各实验表中保留。匿名提交版仅包含统一数值特征及原有匿名视图快照。','']
 for t in tables:
  lines += [f"### {t['experiment_id']} — {t['records']:,} 条",'',f"`{t['path']}`",'', '| 字段 | 来源 / 说明 |','|---|---|']
  for k in t['columns']:
   meaning=FIELDS.get(k,(None,None,None))[1] or {'response_text':'Saved model response; preserved text, not re-generated.','generated_code':'Code extracted in the source experiment; no execution during cleaning.','passed':'Saved test result; null for environment exclusion.','full_pass':'Both diagnostic/base and held-out mini tests passed.','score_current':'Original source grading snapshot; not a harmonized semantic judge.','record_id':'Original stable response key within the experiment.','source_file':'Canonical raw-file path.','prompt_text':'Recorded task-adapted prompt text.','gold_answers_json':'Reference aliases serialized as JSON.','diagnostic_error_json':'Saved first diagnostic failure; null on no failure.','feedback_text':'Actual external feedback passed to that revision.','parent_record_id':'Previous physical response, not an independently sampled answer.','reasoning_text':'Provider field, nullable; absence does not prove absence of reasoning.'}.get(k,'Retained source field; original definition in processed/data_dictionary.tsv or the corresponding experiment source schema.')
   lines.append(f'| {k} | {meaning} |')
 lines+=['','## 原始字段与评分说明','', '历史问答字段的逐字段来源、缺失数量和处理依据见 `processed/data_dictionary.tsv`。新增实验的原始字段见 `raw/code_generation/data_dictionary.tsv` 与 `experiments/code_repair/README.md`。全量缺失统计见 `quality/missingness.csv`，逐表 SHA-256 见 `inventory/processed_tables.json`。']
 (ROOT/'data/data_dictionary.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'physical_responses':sum(counts.values()),'counts':dict(counts),'api_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
