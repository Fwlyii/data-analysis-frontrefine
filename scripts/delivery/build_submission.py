"""Generate the course-PDF layout from one canonical full project.

The app directory carries the UI and pipeline modules, data carries anonymous
features, and report/presentation carry the submitted PDFs. No nested repository
or original model conversation is included. No API calls or code execution.
"""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,re,shutil
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
SKIP={'__pycache__','.git','.impeccable','node_modules','build','submission','dist','runtime','.DS_Store'}
PRIVATE={'response_text','reasoning_text','generated_code','question_text','gold_answer','gold_answers_json','extracted_answer','response_excerpt','complete_response','before_code','after_code'}
def include(p):
 r=p.relative_to(ROOT);a=r.parts
 if any(x in SKIP for x in a) or p.name.startswith('.env'):return False
 if a[0] in ['report','presentation']:return False
 if r.as_posix()=='scripts/delivery/build_submission.py':return False
 if a[:2]==('data','raw'):return False
 if a[:2]==('data','processed'):return len(a)==3 and p.name in {'all_records.csv.gz','data_dictionary.tsv','quality_report.json','missingness_report.csv','missingness_report.json'}
 if a[0]=='data' and 'record_lineage' in p.name:return False
 if a[0] not in {'app','scripts','experiments','requirements','configs','data','docs','reports'} and r.as_posix() not in {'project.json','DESIGN.md','PRODUCT.md'}:return False
 if any(t in p.name.lower() for t in ['example','原文','paired_cases','故事稿','review-sample','prompt_examples','task_examples','model_output_preview']):return False
 if a[0]=='experiments' and ('docs' in a or 'method_source' in a):return False
 if p.suffix=='.csv':
  with p.open(encoding='utf-8-sig') as f:header=next(csv.reader(f),[])
  if set(header)&PRIVATE:return False
 if p.suffix=='.json' and a[0] in {'reports','app'} and p.name!='story-evidence.json':
  try:obj=json.loads(p.read_text())
  except ValueError:return False
  def raw(x):
   if isinstance(x,dict):return any((k in PRIVATE and bool(v)) or raw(v) for k,v in x.items())
   if isinstance(x,list):return any(raw(v) for v in x)
   return False
  if raw(obj):return False
 return p.suffix not in {'.pyc','.key','.pem','.pkl'}
LAYOUT='''from pathlib import Path
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
        mapping={'app':ANCHOR,'data':self.root/'data','report':self.root/'report','presentation':self.root/'presentation','scripts':ANCHOR/'pipeline/scripts','experiments':ANCHOR/'pipeline/experiments','configs':ANCHOR/'pipeline/configs','requirements':ANCHOR/'pipeline/requirements','reports':ANCHOR/'results','docs':ANCHOR/'docs'}
        if str(value)=='project.json':return ANCHOR/'project.json'
        return mapping.get(parts[0],self.root/parts[0]).joinpath(*parts[1:])
ROOT=ProjectLayout()
'''
ROOT_EXPR="__import__('runpy').run_path(str(next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file()) / 'project_layout.py'))['ROOT']"
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'submission/AI对话行为分析_系统');a=p.parse_args();out=a.output.resolve()
 if json.loads((ROOT/'project.json').read_text()).get('profile')=='anonymous-coursework-submission':raise SystemExit('Build this generated profile from the full project, not from itself.')
 if out==ROOT or ROOT.is_relative_to(out):p.error('Unsafe output directory')
 files=[f for f in ROOT.rglob('*') if f.is_file() and include(f)]
 if out.exists():
  marker=out/'app/project.json';old_marker=out/'app/project/project.json';m=marker if marker.exists() else old_marker
  if not m.is_file() or json.loads(m.read_text()).get('profile')!='anonymous-coursework-submission':raise SystemExit('Refusing to replace an unrecognized directory.')
  shutil.rmtree(out)
 out.mkdir(parents=True);app=out/'app';app.mkdir()
 for source in files:
  rel=source.relative_to(ROOT);a=rel.parts
  if a[0] in ['scripts','experiments','configs','requirements']:dest=app/'pipeline'/rel
  elif a[0]=='docs':dest=app/'docs'/Path(*a[1:])
  elif a[0]=='reports':dest=app/'results'/Path(*a[1:])
  elif a[0] in ['DESIGN.md','PRODUCT.md']:dest=app/'docs'/source.name
  elif a[0]=='project.json':dest=app/'project.json'
  elif a[0]=='data' and len(a)>1 and a[1] in {'quality','inventory'}:dest=out/'data/processed/metadata'/Path(*a[1:])
  else:dest=out/rel
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
  if source.suffix=='.py':
   text=dest.read_text()
   text=re.sub(r"next\(p for p in Path\(__file__\)\.resolve\(\)\.parents if \(p / 'project.json'\)\.is_file\(\)\)",lambda m:ROOT_EXPR,text)
   text=re.sub(r'(?m)^ROOT\s*=\s*Path\(__file__\)\.resolve\(\)\.parents\[1\]',lambda m:'ROOT = '+ROOT_EXPR,text)
   dest.write_text(text)
 (app/'project_layout.py').write_text(LAYOUT)
 meta=json.loads((app/'project.json').read_text());meta.update({'profile':'anonymous-coursework-submission','raw_payloads_included':False});(app/'project.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
 evidence=app/'data/story-evidence.json';d=json.loads(evidence.read_text());d['examples']={};d['anonymous_submission']=True;evidence.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n')
 js=app/'src/story.js';text=js.read_text();start=text.index('function example(){');end=text.index('function currentRows(){',start)
 text=text[:start]+'function example(){return `<p class="question">本章条件的匿名数值对照</p>${table()}`;}\n'+text[end:]
 text=text.replace('看一组真实回答','查看结果对照').replace('同一道题，回答改变了什么','同一组题，结果改变了什么').replace('保留原始回答与实际评分','保留匿名特征与实际评分');js.write_text(text)
 data=out/'data';(data/'raw').mkdir(parents=True,exist_ok=True);(data/'processed/metadata').mkdir(parents=True,exist_ok=True)
 (data/'raw/README.md').write_text('# 原始数据说明\n\n按课程匿名化要求，本提交目录只包含特征、统计、图稿和代码。完整原始响应在完整项目data/raw，原始文件SHA-256见source_checksums.json；取得完整原始数据后可按清单核对。\n')
 shutil.copy2(ROOT/'data/inventory/raw_files.json',data/'raw/source_checksums.json')
 for name in ['quality_report.json','missingness.csv']:shutil.copy2(ROOT/'data/quality'/name,data/'processed/metadata'/name)
 dictionary=(ROOT/'data/data_dictionary.md').read_text().split('## 分实验清洗表')[0]
 dictionary+='\n## 质量与来源\n\n逐实验缺失率见processed/metadata/missingness.csv，质量与评分规则见processed/metadata/quality_report.json。原始文件校验见raw/source_checksums.json。提交数据不含全文或源ID映射。\n'
 (data/'data_dictionary.md').write_text(dictionary)
 typed=ROOT/'scripts/cleaning/build_unified_features.py';spec=importlib.util.spec_from_file_location('submission_dictionary',typed);types=importlib.util.module_from_spec(spec);spec.loader.exec_module(types)
 with (data/'processed/data_dictionary.tsv').open('w',encoding='utf-8',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['table','field','type','meaning','missing_policy','source_or_rule'],delimiter='\t');writer.writeheader()
  for field,(dtype,meaning,policy) in types.FIELDS.items():writer.writerow({'table':'all_records','field':field,'type':dtype,'meaning':meaning,'missing_policy':policy,'source_or_rule':'scripts/cleaning/build_unified_features.py'})
 for folder in ['report','presentation']:(out/folder).mkdir()
 shutil.copy2(ROOT/'report/case_report.pdf',out/'report/案例报告.pdf');shutil.copy2(ROOT/'presentation/defense_slides.pdf',out/'presentation/答辩PPT.pdf')
 for source,name in [('research_demo_340s.mp4','汇报演示_1080P.mp4'),('research_demo.srt','汇报字幕.srt')]:
  if (ROOT/'presentation'/source).is_file():shutil.copy2(ROOT/'presentation'/source,out/'presentation'/name)
 (out/'README.md').write_text('''# AI对话行为分析 · 可视交互系统

研究输出表达、资料位置与执行反馈对模型表现的影响。五条发现覆盖两条低维、两条多维和一条异常。

```text
README.md
app/                       可运行系统
  launch.py                标准库启动入口
  src/                     前端代码
  pipeline/                采集、清洗、分析、绘图与生成脚本
  results/                 聚合统计与科学图稿
  docs/                    方法、来源与依赖说明
data/
  raw/                     来源与校验清单
  processed/               248,586条匿名物理响应及质量元数据
  data_dictionary.md       字段、单位与缺失原因
report/
  案例报告.pdf
presentation/
  答辩PPT.pdf
  汇报演示_1080P.mp4
```

## 运行系统

`python3 app/launch.py --port 8766`。无API调用、无密钥、无npm，使用本地数据与SVG。预构建运行时也支持直接打开app/index.html。

## 复算

`python3 app/pipeline/scripts/reproduce_anonymous.py`，从匿名数值表重算五类实验的条件汇总。加`--figures`重绘主图，需安装app/pipeline/requirements/analysis.txt和Times New Roman。文档重绘另需documents.txt。

系统支持条件切换、九个证据位置选择、版本播放、完整图表库与匿名记录联动。CSV/SVG可下载。不同任务评分按metric_name分别解释；修复共享初稿只计一次。

原始全文和源ID映射不进入本匿名目录，完整项目保留这些材料。外层文件夹可按学校要求填写真实学号姓名。
''')
 # Standard-library snapshot build of the routed, anonymous layout.
 source=app/'pipeline/scripts/system/build_web_app.py';spec=importlib.util.spec_from_file_location('course_submission_web',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.build()
 inventory=[]
 for f in sorted(out.rglob('*')):
  if f.is_file():inventory.append({'path':str(f.relative_to(out)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 (app/'docs/submission_inventory.json').write_text(json.dumps({'profile':'anonymous-coursework','files':inventory},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'submission':str(out),'files':len(inventory)+1,'top_level':sorted(p.name for p in out.iterdir())},ensure_ascii=False))
if __name__=='__main__':main()
