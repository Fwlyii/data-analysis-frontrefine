"""Verify the deployed Pages artifact against this exact local build."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.parse import quote
import hashlib,json,time,sys,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
DIST=ROOT/'app/dist'
BASE='https://fwlyii.github.io/data-analysis-frontrefine/'
stamp=str(time.time_ns())
def inspect(path):
    relative=path.relative_to(DIST).as_posix();local=path.read_bytes()
    try:
        req=Request(BASE+quote(relative,safe='/')+'?releaseReview='+stamp,headers={'Cache-Control':'no-cache'})
        with urlopen(req,timeout=45) as response:remote=response.read();status=response.status
        passed=local==remote
        return {'path':relative,'passed':passed,'status':status,'bytes':len(remote),'expectedSHA256':hashlib.sha256(local).hexdigest(),'actualSHA256':hashlib.sha256(remote).hexdigest()}
    except Exception as e:return {'path':relative,'passed':False,'error':str(e)}
files=sorted(p for p in DIST.rglob('*') if p.is_file())
with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(inspect,files))
report={'releaseCommit':subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'base':BASE,'method':'Every published file compared byte-for-byte with local app/dist; cache-busting query and no-cache header. No HTML normalization.','results':results}
out=ROOT/'optimization/content-layout-20261101/after/public-assets.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'files':len(results),'passed':sum(r['passed']for r in results),'failed':[r for r in results if not r['passed']]}))
if any(not r['passed']for r in results):sys.exit(1)
