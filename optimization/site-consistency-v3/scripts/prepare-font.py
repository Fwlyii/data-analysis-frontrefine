"""Asset preparation only: fonttools==4.60.1, brotli==1.2.1.

Usage: python prepare-font.py /path/to/NotoSerifCJKsc-SemiBold.otf
Page/CI builds use the checked-in asset and Python's standard library only.
"""
import hashlib
import json
from pathlib import Path
import sys
from fontTools import subset
from fontTools.ttLib import TTFont

root=Path(__file__).resolve().parents[3]
source=Path(sys.argv[1])
expected='d627b53dbcde61e07de1498d2623a8b287f78585ffbc90cc0618d0caaa2ed6b0'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected, 'Review changed font master before preparing assets'
coverage=(root/'optimization/type-motion-v2/assets/display-coverage.txt').read_text().strip('\n')
audit=json.loads((root/'optimization/site-consistency-v3/before/page-audit.json').read_text())
coverage+=''.join(row.get('title') or '' for row in audit['rows'])
coverage=''.join(sorted(char for char in set(coverage) if ord(char)>=32))
font=TTFont(source,recalcTimestamp=False)
options=subset.Options();options.flavor='woff2'
subsetter=subset.Subsetter(options=options);subsetter.populate(text=coverage);subsetter.subset(font)
names={1:'LENS Editorial',2:'SemiBold',4:'LENS Editorial SemiBold',6:'LENSEditorial-SemiBold',16:'LENS Editorial',17:'SemiBold'}
for record in font['name'].names:
    if record.nameID in names:record.string=names[record.nameID].encode(record.getEncoding())
font.flavor='woff2'
path=root/'app/assets/fonts/lens-editorial-site-semibold.woff2';font.save(path)
missing=sorted(set(map(ord,coverage))-set(font.getBestCmap()))
assert not missing
asset={'file':'assets/fonts/'+path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
manifest={'assets':[asset],'font':{'family':'LENS Editorial','source':'https://github.com/notofonts/noto-cjk/tree/main/Serif','license':'SIL OFL 1.1','masterSha256':expected,'codepoints':len(coverage),'missing':missing,'coverage':'optimization/site-consistency-v3/font-coverage.txt','scope':'all audited route main titles plus prior dynamic story titles and ASCII'}}
(root/'app/assets/visual/site-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(root/'optimization/site-consistency-v3/font-coverage.txt').write_text(coverage+'\n')
(root/'optimization/site-consistency-v3/font-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
