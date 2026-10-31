"""Reusable, opt-in benchmark collector. Only --execute performs model requests.

The historical reasoning bundle did not include its acquisition entry point.
This collector reconstructs a documented prompt protocol from saved questions
and prompt strategies; it is not represented as the missing historical program.
Document QA reuses the exact saved prompt_text, document ordering and questions.
"""
from pathlib import Path
import argparse,concurrent.futures,csv,datetime as dt,gzip,hashlib,json,os,random,threading,time,urllib.error,urllib.request
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
def open_text(p):return gzip.open(p,'rt',encoding='utf-8') if p.suffix=='.gz' else p.open(encoding='utf-8-sig')
def jobs(dataset,models,prompt_ids,task_limit,seed):
 if dataset=='reasoning':
  with open_text(ROOT/'data/processed/reasoning/questions_clean.csv') as f:questions=list(csv.DictReader(f))
  with open_text(ROOT/'data/processed/reasoning/prompts_clean.csv') as f:prompts=list(csv.DictReader(f))
  if task_limit:questions=questions[:task_limit]
  for q in questions:
   for p in prompts:
    pid=p['prompt_id']
    if prompt_ids and pid not in prompt_ids:continue
    options=json.loads(q.get('options_json') or '[]');question=q['question_text']
    if options:question+='\n'+'\n'.join(f'{chr(65+i)}. {v}' for i,v in enumerate(options))
    text=question+'\n\n'+p['prompt_text']+'\n\nEnd with: Answer: <final answer>'
    for m in models:yield {'question_id':q['question_id'],'question':question,'answers':[q.get('gold_answer')],'benchmark':q['benchmark'],'prompt_id':pid,'protocol':'reconstructed-reasoning-v1','model':m,'prompt_text':text}
 else:
  seen=set()
  with open_text(ROOT/'data/raw/document_qa/scenarios.jsonl.gz') as f:
   for line in f:
    r=json.loads(line)
    if prompt_ids and r['prompt_id'] not in prompt_ids:continue
    if task_limit and r['question_id'] not in seen and len(seen)>=task_limit:continue
    seen.add(r['question_id'])
    for m in models:yield {**r,'model':m,'protocol':'saved-document-scenario-v1'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('dataset',choices=['reasoning','document_qa']);p.add_argument('--model',action='append',required=True);p.add_argument('--prompt',action='append');p.add_argument('--task-limit',type=int,default=1);p.add_argument('--all-tasks',action='store_true');p.add_argument('--concurrency',type=int,default=16);p.add_argument('--temperature',type=float,default=0);p.add_argument('--max-tokens',type=int,default=800);p.add_argument('--api-key-env',default='SILICONFLOW_API_KEY');p.add_argument('--endpoint',default='https://api.siliconflow.cn/v1/chat/completions');p.add_argument('--seed',type=int,default=20261028);p.add_argument('--execute',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
 if a.concurrency<1 or a.max_tokens<1 or a.task_limit<1:p.error('Positive concurrency, task limit and max tokens are required.')
 batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=(a.output or ROOT/f'data/raw/{a.dataset}/collections/{batch}').resolve()
 frozen=ROOT/f'data/raw/{a.dataset}'
 if out==frozen or not out.is_relative_to(frozen/'collections'):p.error('Output must be a new dataset collections/<run> directory.')
 all_jobs=list(jobs(a.dataset,a.model,a.prompt,None if a.all_tasks else a.task_limit,a.seed));random.Random(a.seed).shuffle(all_jobs)
 print(json.dumps({'dataset':a.dataset,'planned_requests':len(all_jobs),'execute':a.execute,'output':str(out.relative_to(ROOT))},ensure_ascii=False))
 if not a.execute:return
 key=os.environ.get(a.api_key_env)
 if not key:raise SystemExit('Set '+a.api_key_env+' in the environment.')
 out.mkdir(parents=True,exist_ok=False);lock=threading.Lock()
 (out/'config.json').write_text(json.dumps({k:v for k,v in vars(a).items() if k!='output'},ensure_ascii=False,indent=2,default=str)+'\n')
 def collect(job):
  payload={'model':job['model'],'messages':[{'role':'user','content':job['prompt_text']}],'temperature':a.temperature,'max_tokens':a.max_tokens,'stream':False}
  if 'Qwen3' in job['model']:payload['enable_thinking']=False
  start=time.monotonic();result=None;error=None;status=None
  try:
   req=urllib.request.Request(a.endpoint,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=180) as response:status=response.status;result=json.load(response)
  except urllib.error.HTTPError as e:status=e.code;error='HTTP '+str(e.code)
  except Exception as e:error=type(e).__name__
  row={**job,'record_id':hashlib.sha256((job['model']+'|'+job['question_id']+'|'+job.get('scenario_id',job['prompt_id'])).encode()).hexdigest(),'timestamp':dt.datetime.now(dt.timezone.utc).isoformat(),'request':payload,'response':result,'http_status':status,'error':error,'latency_seconds':time.monotonic()-start}
  with lock:
   with (out/'responses.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.concurrency) as pool:
  for i,_ in enumerate(pool.map(collect,all_jobs),1):
   if i%20==0:print(f'completed={i}/{len(all_jobs)}',flush=True)
if __name__=='__main__':main()
