"""Verify the complete frozen raw-file inventory without fetching or modifying it."""
from pathlib import Path
import argparse,hashlib,json
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-only',action='store_true');p.parse_args()
 index=json.loads((ROOT/'data/inventory/raw_files.json').read_text());bad=[]
 for r in index['files']:
  f=ROOT/r['path']
  if not f.is_file() or digest(f)!=r['sha256']:bad.append(r['path'])
 if bad:raise SystemExit('Raw snapshot missing/changed: '+', '.join(bad))
 print(f"Unchanged raw artifacts: {len(index['files'])}; API calls: 0.")
if __name__=='__main__':main()
