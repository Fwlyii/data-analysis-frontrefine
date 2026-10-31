"""Opt-in fresh paired repair collection. A plan is printed unless --execute.

Executing prepares trusted benchmark references in a macOS sandbox and then
collects model responses with actual test feedback. Frozen source runs are never
resumed or overwritten by this entry.
"""
from pathlib import Path
import argparse,datetime as dt,json,os,subprocess,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--batch',default=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));a=p.parse_args()
 c=json.loads((ROOT/'configs/code_repair.json').read_text());c['batch_id']='code-repair-'+a.batch;c['raw_output']='data/raw/code_repair/collections/'+a.batch
 print(json.dumps({'new_batch':c['batch_id'],'api_enabled':a.execute,'max_requests':(c['pilot_size'] if a.pilot else c['expected_tasks'])*len(c['models'])*17},ensure_ascii=False))
 if not a.execute:return
 path=ROOT/'build/collection_configs'/('code_repair_'+a.batch+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n');env=os.environ.copy();env['COURSE_REPAIR_CONFIG']=str(path)
 for script in ['prepare.py','collect.py']:
  args=[sys.executable,str(ROOT/'experiments/code_repair/src'/script)]
  if script=='collect.py' and a.pilot:args.append('--pilot')
  subprocess.run(args,cwd=ROOT,env=env,check=True)
if __name__=='__main__':main()
