"""Recompute model/prompt/position/repair summaries from anonymous numeric rows.

Works in both the full repository and the coursework submission. Standard Python
is enough for aggregate CSV; --figures additionally uses local plotting packages.
"""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,csv,gzip,json,subprocess,sys
ROOT = __import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--figures',action='store_true');a=p.parse_args();groups=defaultdict(lambda:[0,0,0.,0,0.]);counts=Counter()
 with gzip.open(ROOT/'data/processed/all_records.csv.gz','rt',encoding='utf-8') as f:
  for r in csv.DictReader(f):
   counts[r['experiment_id']]+=1
   key=tuple(r[k] for k in ['experiment_id','model_id','benchmark','prompt_id','metric_name','document_count','evidence_position','revision_round','feedback_type'])
   g=groups[key];g[0]+=1
   if r['metric_value']!='':g[1]+=1;g[2]+=float(r['metric_value'])
   if r['output_tokens']!='':g[3]+=1;g[4]+=float(r['output_tokens'])
 out=ROOT/'reports/reproduced';out.mkdir(parents=True,exist_ok=True)
 fields=['experiment_id','model_id','benchmark','prompt_id','metric_name','document_count','evidence_position','revision_round','feedback_type','responses','scored_responses','native_score_rate','mean_output_tokens']
 with (out/'condition_summary.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for key,g in sorted(groups.items()):w.writerow(dict(zip(fields,[*key,g[0],g[1],g[2]/g[1] if g[1] else None,g[4]/g[3] if g[3] else None])))
 (out/'summary.json').write_text(json.dumps({'physical_responses':sum(counts.values()),'experiments':dict(counts),'groups':len(groups),'api_calls':0,'score_policy':'Task-native scores remain separate; repair seed is one physical row, not four independent samples.'},ensure_ascii=False,indent=2)+'\n')
 if a.figures:
  subprocess.run([sys.executable,str(ROOT/'scripts/figures/plot_story_figures.py')],cwd=ROOT,check=True)
  subprocess.run([sys.executable,str(ROOT/'scripts/system/build_web_app.py')],cwd=ROOT,check=True)
 print(json.dumps({'physical_responses':sum(counts.values()),'condition_groups':len(groups),'api_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
