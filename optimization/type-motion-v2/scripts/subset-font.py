"""Optional asset preparation: fonttools==4.60.1 and brotli==1.2.1.

Production/Pages build uses the checked-in WOFF2 and does not need these packages.
Usage: python subset-font.py /path/to/NotoSerifCJKsc-SemiBold.otf
"""
from pathlib import Path
import hashlib
import json
import re
import sys
from fontTools import subset
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parents[3]
source = Path(sys.argv[1])
script = (root / 'app/src/story.js').read_text()
initial = re.search(r'const headings=\{(.*?)\};', script).group(1)
headings = re.findall(r":'([^']*)'", initial)
headings += re.findall(r"headings\.\w+='([^']*)'", script)
headings += re.findall(r'<h2[^>]*>(.*?)</h2>', script)
text = ''.join(re.sub('<[^>]*>', '', heading) for heading in headings)
text += '模型行为研究' + ''.join(chr(n) for n in range(32, 127))
coverage = ''.join(sorted(set(text)))
out = root / 'app/assets/fonts/lens-editorial-semibold.woff2'
font = TTFont(source)
options = subset.Options()
options.flavor = 'woff2'
subsetter = subset.Subsetter(options=options)
subsetter.populate(text=coverage)
subsetter.subset(font)
names = {1:'LENS Editorial',2:'SemiBold',4:'LENS Editorial SemiBold',6:'LENSEditorial-SemiBold',16:'LENS Editorial',17:'SemiBold'}
for record in font['name'].names:
    if record.nameID in names:
        record.string = names[record.nameID].encode(record.getEncoding())
font.flavor = 'woff2'
font.save(out)
missing = sorted(set(map(ord,coverage))-set(font.getBestCmap()))
if missing:
    raise ValueError('Missing glyphs: '+str(missing))
audit = {'master':source.name,'masterSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'sourceURL':'https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/SimplifiedChinese/NotoSerifCJKsc-SemiBold.otf',
         'codepoints':len(coverage),'missing':missing,'bytes':out.stat().st_size,
         'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
artifact = root / 'optimization/type-motion-v2/assets'
(artifact/'display-coverage.txt').write_text(coverage+'\n')
(artifact/'font-subset.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit))
