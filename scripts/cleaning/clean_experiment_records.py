"""Normalize saved code-generation, evidence-position and code-repair records.

Reads frozen files only. Does not request models, execute code, or change scores.
CSV nulls are empty cells; JSON cells are canonical JSON; booleans are true/false.
"""
from pathlib import Path
import csv,gzip,hashlib,importlib.util,json,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())

def cell(v):
 if v is None:return ''
 if isinstance(v,bool):return str(v).lower()
 if isinstance(v,(dict,list)):return json.dumps(v,ensure_ascii=False,separators=(',',':'),allow_nan=False)
 return v

def write(path,records):
 path.parent.mkdir(parents=True,exist_ok=True)
 it=iter(records);first=next(it,None)
 if first is None:raise ValueError('Empty dataset: '+str(path))
 fields=list(first);n=0;seen=set()
 with gzip.open(path,'wt',encoding='utf-8',newline='') if path.suffix=='.gz' else path.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
  for r in __import__('itertools').chain([first],it):
   if list(r)!=fields:raise ValueError('Inconsistent schema')
   rid=r.get('record_id')
   if rid is not None:
    if rid in seen:raise ValueError('Duplicate record identity')
    seen.add(rid)
   w.writerow({k:cell(v) for k,v in r.items()});n+=1
 return {'path':str(path.relative_to(ROOT)),'records':n,'columns':fields,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def jsonlines(p):
 with gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8') as f:
  for line in f:
   if line.strip():yield json.loads(line)

def number(v):
 if v in ['',None]:return None
 return float(v) if '.' in str(v) else int(v)

def code_generations():
 base=ROOT/'data/raw/code_generation'
 with gzip.open(base/'source_scores/scores.csv.gz','rt') as f:
  scores={(r['analysis_model'],r['task_id'],r['analysis_prompt_id'],int(r['analysis_turn_id'])):r for r in csv.DictReader(f)}
 for p in sorted(base.glob('raw_*.jsonl.gz')):
  for r in jsonlines(p):
   key=(r.get('profile',r['model']),r['task_id'],r['compression_prompt_id'],int(r['turn_id']))
   if key not in scores:key=(p.name.removeprefix('raw_').removesuffix('.jsonl.gz'),*key[1:])
   score=scores.pop(key);excluded=score['analysis_error_category']=='environment_error'
   yield {'record_id':'|'.join(map(str,key)),'experiment_id':'code_generation','model_id':score['analysis_model'],'task_id':r['task_id'],'prompt_id':r['compression_prompt_id'],'sample_id':int(r['turn_id']),'sampling_mode':'independent','prompt_text':r['prompt'],'response_text':r['complete_response'],'generated_code':r.get('generated_code'),'passed':None if excluded else score['analysis_passed'].lower()=='true','environment_excluded':excluded,'error_type':score['analysis_error_category'],'input_tokens':number(r.get('input_tokens')),'output_tokens':number(r.get('output_tokens')),'total_tokens':number(r.get('total_tokens')),'latency_seconds':number(r.get('latency_seconds')),'finish_reason':r.get('finish_reason'),'scorer':score['normalization'],'function_name':r['function_name'],'source_file':str(p.relative_to(ROOT))}
 if scores:raise ValueError('Scores without a raw response')

def evidence_positions():
 base=ROOT/'data/raw/document_positions/no_cot_20_documents'
 src=ROOT/'experiments/document_qa/src';sys.path.insert(0,str(src))
 spec=importlib.util.spec_from_file_location('position_scores',src/'analyze_document_positions.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for r in jsonlines(base/'raw_responses.jsonl'):
  metrics=module.summarize_record(r,{r['question_id']:r['question_id']});resp=r['response'];message=resp['choices'][0]['message'];usage=resp.get('usage') or {}
  yield {'record_id':r['model']+'|'+r['scenario_id'],'experiment_id':'document_positions','model_id':r['model'],'question_id':r['question_id'],'scenario_id':r['scenario_id'],'prompt_id':r['prompt_id'],'document_count':r['document_count'],'gold_position':r['gold_position'],'question_text':r['question'],'gold_answers_json':r['answers'],'response_text':message.get('content'),'timestamp':r['timestamp'],'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),'total_tokens':usage.get('total_tokens'),'latency_seconds':r['latency_s'],'finish_reason':resp['choices'][0].get('finish_reason'),'final_contains':bool(metrics['final_contains']),'strict_final_em':bool(metrics['strict_final_em']),'paper_firstline':bool(metrics['paper_firstline']),'full_response_contains':bool(metrics['full_response_contains']),'is_truncated':bool(metrics['truncated'])}

def repair_records():
 base=ROOT/'data/raw/code_repair/code-repair-20261026-humaneval-mini'
 scores={r['record_id']:r for r in jsonlines(base/'evaluations.jsonl')}
 for r in jsonlines(base/'responses.jsonl'):
  score=scores.pop(r['record_id']);usage=r.get('usage') or {}
  yield {'record_id':r['record_id'],'experiment_id':'code_repair','model_id':r['model'],'task_id':r['task_id'],'arm':r['arm'],'revision_round':r['round'],'parent_record_id':r.get('parent_id'),'shared_seed_id':r.get('shared_seed_id'),'feedback_source_id':r.get('feedback_source_id'),'feedback_text':r.get('feedback'),'response_text':r['content'],'generated_code':r['code'],'timestamp':r['timestamp'],'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),'total_tokens':usage.get('total_tokens'),'latency_seconds':r['seconds'],'finish_reason':r['finish_reason'],'diagnostic_passed':bool(score['public']['passed']),'heldout_passed':bool(score['hidden']['passed']),'full_pass':bool(score['full_pass']),'diagnostic_error_json':score['public'].get('first_failure'),'evaluation_seconds':score['evaluation_seconds'],'sandboxed':bool(score['sandboxed'])}
 if scores:raise ValueError('Evaluations without a response')

def main():
 entries=[]
 for name,fn,expected in [('code_generation',code_generations,90210),('document_positions',evidence_positions,3600),('code_repair',repair_records,5576)]:
  entry=write(ROOT/f'data/processed/{name}/responses.csv.gz',fn())
  if entry['records']!=expected:raise ValueError(f'{name}: expected {expected} rows')
  entries.append(entry);print(name,entry['records'],flush=True)
 # A complete source benchmark is retained as raw; cleaned question/prompt tables are thin and unambiguous.
 base=ROOT/'data/raw/code_generation'
 with (base/'tasks.csv').open(encoding='utf-8-sig') as f:questions=list(csv.DictReader(f))
 write(ROOT/'data/processed/code_generation/questions.csv',questions)
 prompts=json.loads((base/'prompts.json').read_text())
 write(ROOT/'data/processed/code_generation/prompts.csv',[{'prompt_id':k,'original_instruction':v['original'],'code_instruction':v['code']} for k,v in prompts.items()])
 out=ROOT/'data/inventory/normalized_records.json';out.write_text(json.dumps({'api_calls':0,'generated_code_executed':False,'score_policy':'Retain source grades; environment exclusions are null, not failures. Position scores use the saved official rule.','tables':entries},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
