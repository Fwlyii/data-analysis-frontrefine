"""Prepare an isolated, pinned original Master build without touching main."""
from pathlib import Path
import subprocess,tarfile,io,hashlib,re,shutil,sys
ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'.git/master-rebuild-v6'
SOURCE=WORK/'upstream'
BASE=WORK/'baseline'
SHA='35f7318e45561da07c75eaf65374e4107004d5ec'
WORK.mkdir(parents=True,exist_ok=True)
if not (SOURCE/'.git').exists():
    subprocess.run(['git','clone','--depth','1','--single-branch','--branch','Master','https://github.com/Fwlyii/dataAnalysis-vision.git',str(SOURCE)],check=True)
current=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip()
if current!=SHA:
    subprocess.run(['git','-C',str(SOURCE),'fetch','origin',SHA],check=True)
    subprocess.run(['git','-C',str(SOURCE),'checkout','--detach',SHA],check=True)
BASE.mkdir(exist_ok=True)
archive=subprocess.check_output(['git','-C',str(SOURCE),'archive',SHA])
with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
    stream.extractall(BASE,filter='data')
for path in (BASE/'app/data').glob('*.gz'):
    pointer=path.read_bytes();match=re.search(rb'oid sha256:([a-f0-9]+)\nsize (\d+)',pointer)
    if match:
        payload=(ROOT/path.relative_to(BASE)).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==match[1].decode() and len(payload)==int(match[2]),'Dataset differs from pinned Master: '+str(path)
        path.write_bytes(payload)
subprocess.run([sys.executable,'scripts/system/build_web_app.py'],cwd=BASE,check=True)
print('Pinned Master baseline ready:',BASE/'app/dist')
print('Serve port8790 separately; do not rebuild it while a comparison is running.')
