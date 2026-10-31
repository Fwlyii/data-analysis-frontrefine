"""One real GitHub Pages workflow status read for a specific already-pushed SHA."""
from urllib.request import Request,urlopen
from pathlib import Path
import json,sys
J=Path('optimization/content-layout-20261101');release=json.loads((J/'release.json').read_text());sha=sys.argv[1]if len(sys.argv)>1 else release['releaseCommit']
u='https://api.github.com/repos/Fwlyii/data-analysis-frontrefine/actions/runs?head_sha='+sha+'&per_page=10'
with urlopen(Request(u,headers={'User-Agent':'LENS-visual-loop'}),timeout=40)as r:d=json.load(r)
runs=[r for r in d.get('workflow_runs',[])if r.get('path')=='.github/workflows/pages.yml']
if not runs:print(json.dumps({'sha':sha,'status':'not-found-yet'}));sys.exit(2)
r=max(runs,key=lambda r:r['id']);info={k:r.get(k)for k in ['id','status','conclusion','html_url','head_sha','run_number']};print(json.dumps(info))
if r['status']!='completed':sys.exit(2)
if r['conclusion']!='success':sys.exit(1)
if sha==release['releaseCommit']:
 release.update({'workflowUrl':r['html_url'],'workflowId':r['id'],'publication':'Normal fast-forward main push; matching Pages workflow succeeded.'});(J/'release.json').write_text(json.dumps(release,indent=2)+'\n');(J/'after/pages-deployment.json').write_text(json.dumps({'results':[{'name':'GitHub Pages workflow for production commit','passed':True,'detail':info}]},indent=2)+'\n')
