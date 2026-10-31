from pathlib import Path
import os
ANCHOR=Path(__file__).resolve().parent
class ProjectLayout:
    def __init__(self):self.root=ANCHOR.parent
    def __fspath__(self):return str(self.root)
    def __str__(self):return str(self.root)
    def __getattr__(self,name):return getattr(self.root,name)
    def __truediv__(self,value):
        parts=Path(value).parts
        if parts[0]=='data' and len(parts)>1 and parts[1] in {'quality','inventory'}:
            return self.root.joinpath('data/processed/metadata',*parts[1:])
        mapping={'app':ANCHOR,'data':self.root/'data','report':self.root/'report','presentation':self.root/'presentation','scripts':ANCHOR/'pipeline/scripts','experiments':ANCHOR/'pipeline/experiments','configs':ANCHOR/'pipeline/configs','requirements':ANCHOR/'pipeline/requirements','reports':ANCHOR/'results','docs':ANCHOR/'docs','build':ANCHOR/'build'}
        if str(value)=='project.json':return ANCHOR/'project.json'
        return mapping.get(parts[0],self.root/parts[0]).joinpath(*parts[1:])
ROOT=ProjectLayout()
