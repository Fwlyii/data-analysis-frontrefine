"""Archive the full branch content and independent course submission.

Full source ZIP contains original datasets, not LFS pointer files. Git metadata,
private environments, caches, build outputs and submission duplicates are omitted.
"""
from pathlib import Path
import argparse,hashlib,json,zipfile
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
SKIP={'.git','.venv','venv','node_modules','__pycache__','build','runtime','dist','submission','.impeccable','.DS_Store'}
COMPRESSED={'.gz','.zip','.mp4','.m4a','.png','.jpg','.jpeg','.pdf','.pptx'}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pack(base,dest,prefix,filter_full=False):
 files=[p for p in sorted(base.rglob('*')) if p.is_file()]
 with zipfile.ZipFile(dest,'w',allowZip64=True) as z:
  count=0
  for p in files:
   rel=p.relative_to(base)
   if filter_full and (any(x in SKIP for x in rel.parts) or (p.name.startswith('.env') and p.name!='.env.example') or p.suffix in {'.pyc','.key','.pem'}):continue
   if not filter_full and '__pycache__' in rel.parts:continue
   z.write(p,str(Path(prefix)/rel),compress_type=zipfile.ZIP_STORED if p.suffix in COMPRESSED else zipfile.ZIP_DEFLATED,compresslevel=3);count+=1
 checksum=digest(dest);dest.with_suffix(dest.suffix+'.sha256').write_text(checksum+'  '+dest.name+'\n')
 return {'archive':dest.name,'files':count,'bytes':dest.stat().st_size,'sha256':checksum}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT.parent);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 full=pack(ROOT,a.output/'model-behavior-project.zip','model-behavior-project',True)
 sub=ROOT/'submission/AI对话行为分析_系统'
 if not sub.is_dir():raise SystemExit('Run build_submission.py first.')
 submission=pack(sub,a.output/'coursework-system-submission.zip','AI对话行为分析_系统')
 report={'full_project':full,'course_submission':submission,'api_calls':0,'git_push_performed':False};(a.output/'project-delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
