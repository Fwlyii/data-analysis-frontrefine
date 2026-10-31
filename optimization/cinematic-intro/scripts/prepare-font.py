"""Optional font preparation: fontTools 4.60.1 + brotli 1.2.1; not needed by production builds."""
from pathlib import Path
import hashlib,json,sys
from fontTools import subset
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[3]
master=Path(sys.argv[1])
assert hashlib.sha256(master.read_bytes()).hexdigest()=='d627b53dbcde61e07de1498d2623a8b287f78585ffbc90cc0618d0caaa2ed6b0'
text='知微'  # Other copy uses the same native sans-serif stack as the live system.
font=TTFont(master,recalcTimestamp=False);options=subset.Options();options.flavor='woff2'
worker=subset.Subsetter(options=options);worker.populate(text=text);worker.subset(font)
names={1:'LENS Intro',2:'SemiBold',4:'LENS Intro SemiBold',6:'LENSIntro-SemiBold',16:'LENS Intro',17:'SemiBold'}
for record in font['name'].names:
 if record.nameID in names:record.string=names[record.nameID].encode(record.getEncoding())
font.flavor='woff2';out=ROOT/'app/assets/fonts/lens-intro-semibold.woff2';font.save(out)
asset={'file':'assets/fonts/'+out.name,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
metadata={'assets':[asset],'source':'https://github.com/notofonts/noto-cjk/tree/main/Serif','license':'SIL OFL 1.1, app/assets/fonts/Noto-CJK-OFL.txt','scope':'native Chinese brand 知微; other copy reuses the system UI font; no rendered scene assets','codepoints':len(set(text))}
(ROOT/'app/assets/visual/intro-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
(ROOT/'optimization/cinematic-intro/font-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata))
