"""Opt-in nine-position collection in a NEW batch; defaults to printing a plan."""
from pathlib import Path
import argparse,datetime as dt,json,runpy,sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--batch',default=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));p.add_argument('--model',action='append');a=p.parse_args()
 c=json.loads((ROOT/'configs/document_positions.json').read_text());c['batch_id']='document-positions-'+a.batch;c['raw_output']='data/raw/document_positions/collections/'+a.batch
 if a.model:c['models']=a.model
 print(json.dumps({'new_batch':c['batch_id'],'api_enabled':a.execute,'responses':c['questions']*len(c['models'])*len(c['positions_1_based'])},ensure_ascii=False))
 if not a.execute:return
 f=ROOT/'build/collection_configs'/('document_positions_'+a.batch+'.json');f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 entry=str(ROOT/'experiments/document_qa/src/collect_document_positions.py')
 for mode in ['prepare','collect']:
  sys.argv=[entry,mode,'--config',str(f)];runpy.run_path(entry,run_name='__main__')
if __name__=='__main__':main()
