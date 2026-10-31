"""Create current case-report and defense PDFs from saved, editable SVG evidence.
No model requests; no generated-code execution. Historical baseline files remain.
"""
from pathlib import Path
from html import escape
import csv,json,os,hashlib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from matplotlib import font_manager as fm
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'project.json').is_file())
INK=colors.HexColor('#243c52');TEAL=colors.HexColor('#167b7b');GREY=colors.HexColor('#526779');LINE=colors.HexColor('#d9e2e9')
CJK=os.getenv('COURSE_CJK_FONT_FILE','/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
if not Path(CJK).is_file():raise SystemExit('Set COURSE_CJK_FONT_FILE to a licensed Chinese TrueType font.')
pdfmetrics.registerFont(TTFont('CJK',CJK))
for name,weight in [('Times New Roman','normal'),('TNR-Bold','bold')]:pdfmetrics.registerFont(TTFont(name,fm.findfont(fm.FontProperties(family='Times New Roman',weight=weight),fallback_to_default=False)))
pdfmetrics.registerFontFamily('Times New Roman',normal='Times New Roman',bold='TNR-Bold',italic='Times New Roman',boldItalic='TNR-Bold')
P=ParagraphStyle('body',fontName='CJK',fontSize=10.5,leading=18,textColor=INK,spaceAfter=9,wordWrap='CJK')
H=ParagraphStyle('heading',parent=P,fontSize=20,leading=29,spaceAfter=18)
S=ParagraphStyle('small',parent=P,fontSize=8.5,leading=14,textColor=GREY)
T=ParagraphStyle('table',parent=P,fontSize=9,leading=15,spaceAfter=0)
SL=ParagraphStyle('slide',fontName='CJK',fontSize=18,leading=29,textColor=INK,wordWrap='CJK')
DATA=json.loads((ROOT/'app/data/story-evidence.json').read_text())
QUALITY=json.loads((ROOT/'data/quality/quality_report.json').read_text())
def para(t,style=P):return Paragraph(escape(t),style)
def draw(name,width=480):
 d=svg2rlg(str(ROOT/'app/assets/story'/(name+'.svg')))
 scale=width/d.width;d.scale(scale,scale);d.width*=scale;d.height*=scale;return d

def table(rows,widths):
 data=[[para(str(x),T) for x in row] for row in rows];t=Table(data,colWidths=widths,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf3f6')),('TEXTCOLOR',(0,0),(-1,-1),INK),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,LINE)]));return t

TOPICS=[
 {'name':'分步回答的高分，可以用简洁表达保留下来','kind':'低维发现 1','figure':'concise-baseline','source':'reports/baseline/reasoning_paired_contrasts.csv；reports/story/concise-cross-task-points.csv','body':'先比较只给答案的 NoCoT 与分步作答的 DefaultCoT，再在分步要求后追加 but be concise。固定 Qwen2.5/GSM8K 的 200 道同题，得分为 22.0%、91.5%、92.0%，平均输出为 6.5、236.7、185.8 Token。分步对照的配对得分差为 +69.5 pp，[63.0, 76.0]。','interpret':'17 个模型×任务分组的简洁回答全部缩短，15 组得分点估计持平或提高，输出下降 11.4%–57.5%。默认表述中存在可压缩的复述和铺陈；两种得分相近不能单独证明统计等效。文档与代码任务按各自评分解释。','speech':'我们先研究最常用的分步提示。在同一批两百道基础数学题上，Qwen二点五只给答案时得分百分之二十二，改为分步解题后达到百分之九十一点五。接下来，只在原提示后加一句，保持简洁。输出从二百三十七个Token降到一百八十六，得分仍是百分之九十二。这个现象在三个任务方向反复出现：十七组全部更短，十五组得分点估计没有下降。简洁要求压缩了表达，却保留了有效的解题过程。'},
 {'name':'中文作答模板在 MATH500 上帮助多数模型省 Token、提分','kind':'低维发现 2','figure':'language-math500','source':'reports/story/chinese-template-comparison.csv','body':'相同英文题，比较 DefaultCoT 与实际指令为 Respond in Chinese 的中文模板。MATH500 上，DeepSeek 76.0%→75.0%，HY4 68.5%→74.0%，Qwen2.5 68.0%→70.5%，Qwen3 58.0%→69.5%。四模型全部缩短输出，三模型提分。','interpret':'Qwen3 提高 11.5 pp，输出减少 19.5%；Qwen2.5 截断率从 22.0% 降至 2.5%。得分改善的题中，原回答被截断的比例为 HY4 20/21、Qwen2.5 13/19、Qwen3 18/30。紧凑表达与完成情况改善共同解释这一现象。提分主张定位于 MATH500；GSM8K 四模型下降 0.5–4.5 pp。这是模板对照，不等同于只改变内部思考语言。','speech':'第二个发现来自语言模板。题目仍然使用英文，我们只比较默认分步模板与中文作答模板。在MATH五百上，四个模型都更省Token，三个模型的得分提高。Qwen三从百分之五十八提高到六十九点五。Qwen二点五的截断率，从百分之二十二降到二点五。查看同题结果后，我们发现，许多得分改善的题，原先都没有在输出上限内完成。更紧凑的表达，有助于把答案真正交付出来。这个提分发现主要发生在较难的数学题上。'},
 {'name':'极端限长会引发输出反弹，格式处理挤占解题预算','kind':'异常 / 特殊现象','figure':'limit-deepseek-math500-WordLimit','source':'reports/prompt_variants/reasoning-all-prompt-profiles.csv','body':'把词数上限从 10 压到 1，12 个模型×benchmark 分组中有 9 组平均输出增加。字母数 100→10 也有 9/12 组输出增加。DeepSeek/MATH500 的字母限制从 100→10 时，平均 Token 102.0→520.6，得分 83.5%→38.0%。','interpret':'同题因数案例中，100 字母条件用 25 Token 结束；10 字母条件已经算出答案，仍反复处理如何满足字母格式，最终在 801 Token 截断。温和简洁和极端限长产生了不同结果。主图每档均为实测，横轴是离散提示档位，未生成额外采样点；词数、字母数和接口 Token 也不是同一单位。','speech':'简洁有效，不代表越短越好。我们把提示中的词数上限，从十个词压到一个词。十二组比较里，有九组的实际输出反而增加。图上七档都是真实采样，没有插值补点。一个因数题案例尤其直观：模型早已算出答案，却开始反复讨论怎样凑成规定的字母数，最后被截断。极端格式约束引入了额外任务，把本可用于完成答案的预算消耗掉了。'},
 {'name':'证据位置会改变问答表现，也会改变模型差距','kind':'多维发现 1：模型 × 位置 → 命中','figure':'position','source':'reports/document_positions/position-summary.csv；paired-model-position-contrasts.csv','body':'固定 NoCoT、20 篇相同资料、200 道相同问题，仅移动相关文档。两模型、文档位置共 3,600 条回答。第1/10/20位：Qwen2.5 为 54.5%/52.5%/56.5%；Qwen3 为 71.0%/61.5%/59.0%。','interpret':'模型增益从首位 16.5 pp 缩至尾位 2.5 pp，首尾增益差 14.0 pp，配对区间 [5.5, 23.0]。Qwen2.5 呈浅 U 形轮廓，Qwen3 更突出首位优势；不强行给两条曲线套同一种形状。阴影为各位置命中率的95%区间。Qwen2.5 有 78/200 道题在文档位置间至少改变一次命中状态。文档问答提示实验与新文档位置批次分别保存。','speech':'接下来把注意力转向资料组织。我们固定问题、二十篇参考资料和提示词，只移动唯一相关的文档，测量了九个证据位置。位置的作用还与模型有关：相关证据放在第一篇时，Qwen三领先十六点五个百分点；放到最后，只领先二点五个百分点。升级模型带来的收益，依赖证据出现在哪里。Qwen二点五呈现较浅的U形，Qwen三主要表现为前置优势。我们用两条实测曲线共同说明模型与位置的关系。'},
 {'name':'具体执行反例比笼统检查更能推动多轮代码修复','kind':'多维发现 2：反馈 × 修改轮次 → 通过率','figure':'repair-qwen3-4','source':'reports/code_repair/full/curves.csv；contrasts.csv','body':'HumanEval+ Mini 164 题、两个 Qwen，每个模型×题目共享同一个初稿。四组分别是独立重采样、自行检查、仅通过/失败、具体失败输入与预期/实际结果。初稿后最多四轮；后三组保留历史，保留集测试结果不进入反馈。','interpret':'Qwen3 初稿 126/164；第四轮具体反例组 141/164，自检 129/164，差 +7.32 pp，[3.05, 12.20]。Qwen2.5 的对应差值 +1.83 pp。Qwen3 初始诊断测试失败的 30 题中，最终自检修复3题、仅状态4题、具体反例15题。图示当前版本完整测试通过率，不是把历轮成功累计在一起；5,576 条物理响应不重复累计共享初稿。','speech':'代码方向，我们采用了多轮代码修复。两组模型在同一道题上共享初稿，再分别接受四种处理：独立重采样，自行检查，只告知是否通过，或者提供具体失败输入、预期结果和实际结果。Qwen三到第四轮时，具体反例通过一百四十一题，自行检查通过一百二十九题。初始诊断测试失败的三十题中，自行检查修好三题，具体反例修好十五题。这个实验研究的是反馈如何帮助模型定位错误，与前面五次独立采样有明确区别。'},
]
def page_footer(c,doc):
 c.setStrokeColor(LINE);c.line(55,42,A4[0]-55,42);c.setFont('CJK',8);c.setFillColor(GREY);c.drawString(55,28,'LENS · 模型行为研究 / 2026-10-28');c.drawRightString(A4[0]-55,28,str(doc.page))
def report():
 out=ROOT/'report';out.mkdir(exist_ok=True);story=[];md=['# LENS · 模型行为研究','', '## 从提示表达、资料位置到代码反馈','']
 def section(title,body,fig=None,source=None):
  if story:story.append(PageBreak())
  story.extend([para(title,H),para(body)])
  md.extend(['## '+title,'',body,''])
  if fig:story.extend([Spacer(1,8),draw(fig,480),Spacer(1,8)])
  if source:story.append(para('数据来源：'+source,S))
 section('模型行为研究：输出、资料与反馈','本项目通过推理/选择题、文档问答和 Python 代码实验，研究输出组织与任务结果的关系。以当前五条主发现形成“分步解题—简洁表达—语言模板—极端约束—证据位置—具体反馈”的故事。完整项目保存原始数据与代码；课程提交目录按匿名特征版本单独生成。')
 story.append(table([['实验方向','物理回答','主要条件'],['推理提示','74,400','600题 / 四模型 / 31提示'],['文档问答','74,800','200题 / 文档数、位置与提示'],['代码生成','90,210','194题 / 三模型 / 31提示 / 五次独立采样'],['文档位置','3,600','复用200题 / 两模型 / 文档位置'],['代码修复','5,576','164题 / 两模型 / 共享初稿与四种处理']], [105,75,300]))
 story.append(Spacer(1,16));story.append(para('总计248,586条物理响应。不同任务的成功指标、重复条件和题目单位分别解释，不计算跨任务总准确率。'))
 section('数据管道与匿名化','冻结源文件 → 唯一键与类型解析 → 源评分/执行结果连接 → 统一数值特征 → 同题配对分析 → 科学图稿与交互视图。原始输入405个不可变制品的SHA-256与整理前一致。源码、原始数据、清洗数据、统计和图稿分别存放，过程不覆盖原始文件。')
 for text in ['CSV空单元格表示null，布尔true/false，时间统一UTC；未记录的耗时或Token不补0。','代码生成465条环境排除保留但不进入性能分母；89,745条回答可评，来自193道共同题。','修复初稿只记一次，pilot是全量批次的子集；共享初稿对应的逻辑组视图不增加API调用计数。','匿名提交版只携带数值特征、代码、统计和图稿；完整原题、回答、代码与源ID映射留在完整项目。']:
  story.append(para(text))
 story.append(table([['材料','位置'],['原始校验','data/inventory/raw_files.json'],['统一匿名表','data/processed/all_records.csv.gz'],['字段与缺失','data/data_dictionary.md；data/quality/missingness.csv'],['按阶段复算','scripts/pipeline.py；scripts/reproduce_anonymous.py']],[100,380]))
 for i,t in enumerate(TOPICS,1):
  section(f"发现{i}：{t['name']}",t['kind']+'。'+t['body'],t['figure'],t['source']);story.append(para(t['interpret']))
 section('代码生成补充：独立采样与提示适配','CodePromptEval原始221题，经过参考实现检查和题意审查保留194题。每题×31提示×三模型独立生成五次。DeepSeek、Qwen2.5、Qwen3 的 Pass@1 分别为30.22%、22.59%、22.09%，Pass@5为34.97%、27.34%、28.01%。增加独立采样有覆盖收益，第4、5次的边际收益已较低。')
 story.append(table([['模型','Pass@1','Pass@3','Pass@5'],['DeepSeek','30.22%','33.73%','34.97%'],['Qwen2.5','22.59%','26.04%','27.34%'],['Qwen3','22.09%','26.36%','28.01%']],[150,110,110,110]))
 story.append(Spacer(1,14));story.append(para('提示策略不仅影响代码逻辑，也影响完整可执行代码的交付。Qwen3的NoCoT提取失败较多；极端数字/语法格式会破坏函数交付。完整重新评分需要源CodePromptEval的项目依赖环境，本项目日常离线复算直接读取已保存的target-function-ast-v2结果。'))
 story.append(para('数据来源：data/raw/code_generation/source_scores/；reports/code_generation/。',S))
 section('可视交互系统与课程对应','系统首页以五条发现、主图与结果解释组织。简洁作答提供同题与跨任务切换；语言和长度对照可选模型/题库；资料位置可选择九个位置与区间；代码修复可逐轮播放。完整图表库保留行为时间线、状态与错误类型、恢复路径、散点与热力、分组箱线和平行坐标等图。')
 story.append(table([['课程要求','实现'],['两条低维','固定Qwen2.5/GSM8K的策略—得分；固定Qwen3/MATH500的模板—得分'],['两条多维','模型×证据位置→命中率；反馈×修改轮次→通过率'],['异常或局限','极端限长的输出反弹与截断；原评分、模板混合变化等边界'],['至少三个交互视图与联动','五章条件切换，完整图表库及筛选/记录联动'],['可运行交付','标准库启动、全部本地依赖、匿名特征复算、可编辑SVG']], [150,330]))
 section('解释范围、复算与反思','数据支持的是当前模型、任务、提示和评测环境下的实测关系。我们不把接口输出当成已测得的内部思考过程，不把提示中的词数/Token数当成接口硬上限，也不把来源不同的分数合并解释。位置采集跨日期，模型ID相同不保证服务权重相同；代码测试通过也不保证所有输入都正确。')
 for text in ['完整项目：python scripts/pipeline.py all --plan 查看阶段；snapshot只构建系统，不访问模型。','匿名复算：python scripts/reproduce_anonymous.py 从248,586行数值特征重算全部条件汇总；加--figures重绘主图。','图表全部有坐标、单位、真实实测点和来源；英文图字为Times New Roman。没有以插值假造更多证据位置。','AI辅助范围为代码整理、清洗统计、可视化及表达；源响应和已保存评分不由本轮重写，未伪造人工语义复核。','参考材料：课程题目二PDF；Compressed-CoT提示策略；Lost in the Middle 文档位置协议；CodePromptEval源提交9dfc592；HumanEval+ Mini v0.1.10。来源与SHA-256随各实验元信息保存。']:
  story.append(para(text))
 SimpleDocTemplate(str(out/'case_report.pdf'),pagesize=A4,rightMargin=55,leftMargin=55,topMargin=52,bottomMargin=58,title='LENS 模型行为研究',author='Coursework Research Team').build(story,onFirstPage=page_footer,onLaterPages=page_footer)
 (out/'case_report.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

def text(c,t,x,y,w,size=18,color=INK):
 style=ParagraphStyle('s',parent=SL,fontSize=size,leading=size*1.55,textColor=color);p=Paragraph(escape(t),style);_,h=p.wrap(w,500);p.drawOn(c,x,y-h);return h

def slides():
 out=ROOT/'presentation';out.mkdir(exist_ok=True);path=out/'defense_slides.pdf';c=canvas.Canvas(str(path),pagesize=(960,540));c.setTitle('LENS 模型行为研究 · 课程答辩')
 records=[]
 def base(title,n):
  c.setFillColor(colors.white);c.rect(0,0,960,540,fill=1,stroke=0);text(c,title,44,500,872,29);c.setStrokeColor(LINE);c.line(44,47,916,47);c.setFont('Times New Roman',11);c.setFillColor(GREY);c.drawString(44,28,'LENS / MODEL BEHAVIOR RESEARCH');c.drawRightString(916,28,f'{n}/12')
 def finish(title,speech):
  records.append({'page':len(records)+1,'title':title,'speech':speech});c.showPage()
 base('模型行为研究：输出、资料与反馈',1);text(c,'输出、资料与反馈，怎样组织更有效？',60,390,800,32);text(c,'推理 / 文档问答 / Python代码',60,230,800,22,TEAL);text(c,'从完整数据管道出发，形成五条可解释、可追溯的发现。',60,175,800,18);finish('研究问题','本项目研究，怎样组织模型的输出、资料和反馈，让任务更有效地完成。我们从推理、文档问答和Python代码三个场景出发，把采集、清洗、分析和可视化整理到同一个项目中。接下来介绍五条有同题数据支持的发现。')
 base('数据规模与比较方式',2)
 ys=[395,338,281,224,167]
 for (a,b,desc),y in zip([('推理提示','74,400','600题，四模型，31提示'),('文档问答','74,800','200题，多种资料与提示条件'),('代码生成','90,210','194题，三模型，五次独立采样'),('文档位置实验','3,600','200题，两模型，9个证据位置'),('多轮代码修复','5,576','164题，两模型，共享初稿与反馈')],ys):
  text(c,a,56,y,180,20);text(c,b,240,y,130,22,TEAL);text(c,desc,400,y,500,18)
 text(c,'共248,586条物理响应；重复条件不等于独立题目。',56,92,850,16,GREY);finish('实验规模','这些数据共有二十四万八千五百八十六条物理响应。推理方向包含六百道题，文档问答有两百道问题。代码生成是五次独立采样；代码修复才真正使用了上一轮程序和测试反馈。所有源文件保持原字节，清洗时保留缺失值与失败，不把环境问题算成模型错误。')
 def topic_slide(t,n):
  base(t['name'],n);d=draw(t['figure'],660);scale=min(1,335/d.height);d.scale(scale,scale);d.width*=scale;d.height*=scale;renderPDF.draw(d,c,32,102+(335-d.height)/2)
  brief={'低维发现 1':'Qwen2.5 / GSM8K\n分步后再要求简洁，平均输出少21.5%，得分91.5%→92.0%。','低维发现 2':'MATH500\n四模型全部更短，三模型提分。Qwen3提高11.5 pp。','异常 / 特殊现象':'WordLimit 10→1\n12组中9组实际输出增加。提示限制不是接口硬上限。','多维发现 1：模型 × 位置 → 命中':'证据在首位→末位\n两模型差距16.5 pp→2.5 pp。九点全部实测。','多维发现 2：反馈 × 修改轮次 → 通过率':'Qwen3 第四轮\n具体反例141/164；自行检查129/164。'}[t['kind']]
  text(c,brief,730,392,180,19,TEAL);text(c,t['kind'],730,205,180,14,GREY);text(c,'来源：'+t['source'].split('；')[0],45,78,870,9,GREY);finish(t['name'],t['speech'])
 topic_slide(TOPICS[0],3)
 base('简洁表达在三个任务方向反复出现',4);d=draw('concise-cross',630);sc=min(1,368/d.height);d.scale(sc,sc);d.width*=sc;d.height*=sc;renderPDF.draw(d,c,45,72)
 text(c,'17/17 组缩短输出',690,368,225,24,TEAL);text(c,'15/17 组得分点估计持平或提高。推理、文档与代码按各自原评分对照。',690,285,225,19);text(c,'不把三种评分合成一个准确率。',690,140,225,15,GREY);finish('跨任务简洁现象','更重要的是，这并非单个模型单道题的故事。我们把推理、问答和代码的简洁提示对照放在一起。左边是输出缩短比例，右边是同一组题的得分变化。十七组的输出全部减少，两个略微下降的结果也原样保留。我们发现的是多个任务方向共有的表达压缩空间，各任务仍然使用自己的评价规则。')
 topic_slide(TOPICS[1],5);topic_slide(TOPICS[2],6);topic_slide(TOPICS[3],7)
 base('模型优势取决于证据出现在哪里',8)
 x=[80,340,600];labels=['第1篇','第10篇','第20篇'];gaps=['16.5 pp','9.0 pp','2.5 pp']
 for xx,lab,gap in zip(x,labels,gaps):text(c,lab,xx,350,220,22);text(c,gap,xx,280,230,34,TEAL)
 text(c,'首尾模型增益差14.0 pp，配对95%区间 [5.5, 23.0]。',80,170,800,23);text(c,'同题配对，比较“模型×证据位置”的联合关系。',80,110,800,17,GREY);finish('模型与位置交互','将两条曲线作差，关系会更清楚。Qwen三相对Qwen二点五的优势，在首位最大，在末位显著缩小。首尾的模型增益差为十四个百分点，配对区间不跨零。位置不是一个只影响所有模型相同幅度的因素，它改变了模型升级能带来的实际收益。')
 topic_slide(TOPICS[4],9)
 base('区分独立采样与收到反馈后的修复',10)
 text(c,'五次独立生成',55,390,360,26,TEAL);text(c,'模型看不到上一次回答，也不知道测试结果。DeepSeek Pass@1 30.22% → Pass@5 34.97%。',55,320,380,21)
 text(c,'共享初稿 + 四轮反馈',505,390,390,26,TEAL);text(c,'后续回答携带历史程序与实际反馈。比较当前版本通过率，观察错误是否被修复。',505,320,390,21)
 text(c,'Prompt可同时影响逻辑正确性与完整可执行代码的交付。',55,132,850,20);finish('代码任务的比较边界','原代码生成实验还有九万多条保存回答，它们是独立采样，不能称为多轮修复。增加采样的覆盖收益主要集中在前几次。真正的修复实验，必须给模型上一轮程序和诊断信息，再观察后续版本。我们把两个实验的数据、脚本和指标分开保留，也把环境排除与模型失败分开。')
 base('一个仓库，完整的数据到图表流程',11)
 steps=[('冻结原始','405个源制品原字节保留'),('规范清洗','唯一键、类型、缺失与来源'),('配对分析','保留任务评分与重复结构'),('图稿与系统','SVG、五章与完整图表库')]
 for i,(h,b) in enumerate(steps):
  xx=48+i*226;c.setFillColor(colors.HexColor('#edf3f6'));c.roundRect(xx,260,204,130,8,fill=1,stroke=0);text(c,h,xx+15,369,174,23,TEAL);text(c,b,xx+15,319,174,15)
 text(c,'标准库启动网页；匿名特征可以复算全部条件汇总。',52,180,850,22);text(c,'完整原始项目与课程匿名提交目录分别生成，后者按PDF目录树交付。',52,118,850,17,GREY);finish('可复现管道','最后，我们把所有材料整理成了一个完整仓库。冻结原始文件、清洗数据、分析、绘图和网页都有独立入口。统一匿名索引保留了全部物理响应，缺失值不补零。系统可以切换任务、模型和位置，也可以逐轮查看代码修复。另有一个按课程目录树生成的匿名提交版本，带数据字典、当前报告和答辩材料。')
 base('五条发现，形成一条完整故事',12)
 for i,line in enumerate(['保留分步解题，压缩冗余表达。','中文模板帮助多数模型完成较难数学题。','过度限长可能反弹，更多约束不总是更省。','模型升级的收益，取决于证据的位置。','具体执行反例，让代码修复更有方向。']):text(c,line,64,410-i*52,830,22)
 text(c,'全部结论均有保存统计与真实实测点；模板、评分和环境范围在报告中说明。',64,95,830,15,GREY);finish('结论','总的来说，我们形成了五条主发现。分步解题可以保留，冗余表达可以压缩。中文模板帮助多数模型完成较难数学题。过度限长可能产生反弹。模型升级的收益依赖证据位置。具体执行反例则让代码修复更有方向。这五条发现覆盖两条低维规律、两条多维关系和一条异常现象，也都能在系统图表与保存统计中找到依据。')
 c.save();(out/'current_slide_content.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');(out/'defense_slides.md').write_text('\n\n'.join('# '+r['title']+'\n\n'+r['speech'] for r in records)+'\n')

def main():
 report();slides()
 paths=['report/case_report.pdf','presentation/defense_slides.pdf'];manifest={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths};(ROOT/'report/current_documents.json').write_text(json.dumps({'date':'2026-10-28','scope':'Five current findings; anonymous data and saved evidence.','physical_responses':248586,'api_calls':0,'files':manifest},ensure_ascii=False,indent=2)+'\n');print('Current report and 12-page defense PDF generated.')
if __name__=='__main__':main()
