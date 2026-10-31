"""Offline analysis of fitted token thresholds, held-out prompts and paired position effects.

No acquisition, API calls or source-score changes. Requires NumPy from current-analysis.txt.
"""
from pathlib import Path
import gzip,json,numpy as np,collections,sys
root=Path(__file__).resolve().parents[1]; app=root/'app/data'
p=json.loads(gzip.decompress((app/'features.json.gz').read_bytes())); fields=p['fields']; rows=[dict(zip(fields,a)) for a in p['rows']]
summary=json.loads((app/'summary.json').read_text()); groups=collections.defaultdict(list)
for r in rows:
 if r['dataset']=='reasoning':groups[r['model'],r['task']].append(r)
result={'oracle':[],'positions':[],'method':{'bootstrap':5000,'seed':20261024,'notes':'Thresholds fitted within question over prompts. LOO holds out prompts, not new questions. Oracle is an in-sample reference; not an achievable guarantee.'}}
rng=np.random.default_rng(20261024)
position_arrays={}
for (model,task),rs in sorted(groups.items()):
 prompts=sorted(set(r['prompt'] for r in rs)); qs=sorted(set(r['question'] for r in rs)); rec={(r['prompt'],r['question']):r for r in rs}
 scores=np.array([[rec[p,q]['scores'][0] for q in qs] for p in prompts]); tokens=np.array([[rec[p,q]['tokens'] for q in qs] for p in prompts]); n=len(qs)
 def fit(g,t):
  thresholds=[]; fits=[]
  for y,x in zip(g.T,t.T):
   can=np.r_[np.unique(x),np.inf]; acc=((x[None,:]>=can[:,None])==y[None,:]).mean(axis=1); j=np.argmax(acc);thresholds.append(can[j] if y.any() else np.inf);fits.append(acc[j])
  return np.array(thresholds),np.array(fits)
 thresholds,fits=fit(scores,tokens); finite=np.sort(thresholds[np.isfinite(thresholds)]); cost=np.r_[0,np.cumsum(finite)/n];sr=np.arange(len(finite)+1)/n
 cv=[]; maj=[]
 for i in range(len(prompts)):
  keep=np.arange(len(prompts))!=i; t,_=fit(scores[keep],tokens[keep]);cv.append((tokens[i]>=t)==scores[i]);maj.append((scores[keep].mean(axis=0)>=.5)==scores[i])
 cv=np.array(cv);maj=np.array(maj);cvdiff=cv.mean(axis=0)-maj.mean(axis=0);boot=cvdiff[rng.integers(0,n,(5000,n))].mean(axis=1)
 observed=[]
 for i,prompt in enumerate(prompts):
  observed.append({'prompt':prompt,'tokens':float(tokens[i].mean()),'sr':float(scores[i].mean()),'truncated':sum(rec[prompt,q]['truncated'] for q in qs)/n,'predicted_sr_loo':float((~cv[i].astype(bool)^scores[i].astype(bool)).mean())})
 baseline=next(r for r in observed if r['prompt']=='DefaultCoT'); target=round(baseline['sr']*n);oracle_at=float(cost[min(target,len(cost)-1)])
 violations=sum(bool((x[y==1].min()<x[y==0].max())) if y.any() and not y.all() else False for x,y in zip(tokens.T,scores.T))
 both=sum(not y.all() and y.any() for y in scores.T)
 row={'model':model,'task':task,'n':n,'prompts':observed,'oracle':{'tokens':cost.tolist(),'sr':sr.tolist()},'thresholds':[None if np.isinf(t) else float(t) for t in thresholds],'fit':float(fits.mean()),'finite':len(finite),'trivial':int(np.sum(np.all(scores==scores[0],axis=0))),'loo_accuracy':float(cv.mean()),'majority_accuracy':float(maj.mean()),'loo_advantage_ci':np.quantile(boot,[.025,.975]).tolist(),'inverse_questions':violations,'mixed_questions':int(both),'baseline':baseline,'reference_cost_at_baseline_sr':oracle_at,'reference_ratio':baseline['tokens']/oracle_at if oracle_at else None,'tail20_cost_share':float((cost[-1]-cost[int(.8*len(finite))])/cost[-1]) if cost[-1] else 0}
 result['oracle'].append(row)
 print(model,task,'fit',round(row['fit'],3),'LOO',round(row['loo_accuracy'],3),'major',round(row['majority_accuracy'],3),'inverse',violations,'ref',round(row['reference_ratio'],1),'tailshare',round(row['tail20_cost_share'],3))
document_qa=[r for r in rows if r['dataset']=='document_qa' and r['task']=='document_qa']; main={c['prompt'] for c in summary['cells'] if c['dataset']=='document_qa' and c['scope']=='main_comparison'};core={'NoCoT','DefaultCoT','BeConcise','BulletPoints','WordLimit(25)','WordLimit(100)','TokenLimit(100)','StepLimit(2)'}
scopes={'NoCoT':{'NoCoT'},'DefaultCoT':{'DefaultCoT'},'BeConcise':{'BeConcise'},'main19':main,'core8':core}
for scope,prompts in scopes.items():
 select=[r for r in document_qa if r['prompt'] in prompts]
 for metric in range(4):
  for model in ['qwen','qwen3']:
   rs=[r for r in select if r['model']==model]; qs=sorted({r['question'] for r in rs});idx={q:i for i,q in enumerate(qs)};arr=np.zeros((len(qs),2,3));cnt=np.zeros_like(arr)
   for r in rs:
    at=(idx[r['question']],[10,20].index(r['documents']),['front','middle','back'].index(r['position']));arr[at]+=r['scores'][metric];cnt[at]+=1
   arr/=cnt; position_arrays[scope,metric,model]=arr; bidx=rng.integers(0,len(qs),(5000,len(qs))); boot=arr[bidx].mean(axis=1)
   entry={'scope':scope,'metric':metric,'model':model,'n':len(rs),'questions':len(qs),'rates':arr.mean(axis=0).tolist(),'low':np.quantile(boot,.025,axis=0).tolist(),'high':np.quantile(boot,.975,axis=0).tolist(),'pooled_rates':arr.mean(axis=(0,1)).tolist(),'pooled_low':np.quantile(boot.mean(axis=1),.025,axis=0).tolist(),'pooled_high':np.quantile(boot.mean(axis=1),.975,axis=0).tolist(),'contrasts':{}}
   for label,vals in [('front_mid',arr[:,:,0].mean(axis=1)-arr[:,:,1].mean(axis=1)),('back_mid',arr[:,:,2].mean(axis=1)-arr[:,:,1].mean(axis=1)),('edge_mid',(arr[:,:,0].mean(axis=1)+arr[:,:,2].mean(axis=1))/2-arr[:,:,1].mean(axis=1))]:
    ci=np.quantile(vals[bidx].mean(axis=1),[.025,.975]);entry['contrasts'][label]={'delta':float(vals.mean()),'lo':float(ci[0]),'hi':float(ci[1])}
   result['positions'].append(entry)
   if scope=='DefaultCoT' and metric==0: print('document_qa',model,entry['pooled_rates'],entry['contrasts'])
result['interactions']=[]
for scope in scopes:
 for metric in range(4):
  a=position_arrays[scope,metric,'qwen'];b=position_arrays[scope,metric,'qwen3']
  d=(a[:,:,2]-a[:,:,1]-b[:,:,2]+b[:,:,1]).mean(axis=1); ci=np.quantile(d[rng.integers(0,len(d),(5000,len(d)))].mean(axis=1),[.025,.975])
  result['interactions'].append({'scope':scope,'metric':metric,'delta':float(d.mean()),'lo':float(ci[0]),'hi':float(ci[1]),'n_questions':len(d)})
result['position_interaction']=next(r for r in result['interactions'] if r['scope']=='DefaultCoT' and r['metric']==0)
result['position_matrix']=[]
for mid in ['qwen','qwen3']:
 for prompt in [p['id'] for p in summary['prompts']]:
  sel=[r for r in document_qa if r['model']==mid and r['prompt']==prompt]
  result['position_matrix'].append({'model':mid,'prompt':prompt,'positions':[
   {'position':pos,'n':len(a),'scores':np.mean([r['scores'] for r in a],axis=0).tolist(),'tokens':float(np.mean([r['tokens'] for r in a]))}
   for pos in ['front','middle','back'] for a in [[r for r in sel if r['position']==pos]]
  ]})
import hashlib
result['source_sha256']=hashlib.sha256((app/'features.json.gz').read_bytes()).hexdigest()
(app/'research-evidence.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
