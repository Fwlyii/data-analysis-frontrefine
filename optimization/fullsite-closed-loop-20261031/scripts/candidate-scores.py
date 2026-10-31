from pathlib import Path
import json
J=Path('optimization/fullsite-closed-loop-20261031');weights=[25,20,20,15,15,5];keys=['layoutHierarchy','typography','colorMaterial','siteConsistency','readingOperation','restraintFinish']
rows=[
('direction-a.png','A gateway desktop',[9.3,9.3,9.5,9.5,9.1,9.4],'selected','准确延续原入口位置，玻璃材质与不同色调更完整；普通文字需以原生实现。'),
('gateway-mobile-selected.png','A gateway mobile',[9.4,9.3,9.5,9.5,9.4,9.4],'selected','完整触摸行与独立材质协调；实际实现保持原154px中心和74px行高，避免占用阅读空间。'),
('direction-a-research.png','A question/collection/cleaning',[8.9,8.95,9,9.1,8.8,9.2],'retained-layouts','外围眉题、分割和材质合适，但生成文字有误，整体收益未超过各原页5分；只参考外围。'),
('direction-b-research.png','B question/collection/cleaning',[8.5,8.5,8.5,7.9,8.3,8.6],'rejected','冷白青色与已有深蓝/铜色/衬线品牌脱节，且手机增加不存在的菜单。'),
('direction-a-analysis.png','A landscape/findings',[8.5,8.7,8.8,8.8,8.5,9.0],'retained-layouts','控制外框可参考，但省略总标题、发明控件、改写图表内容；完整原版更符合科研阅读。'),
('direction-b-analysis.png','B landscape/findings',[8.3,8.5,8.5,7.9,8.4,8.5],'rejected','更重的按钮和冷白底改变原研究语气，部分手机图缩小，不能证明更好的操作阅读。'),
('direction-a-library.png','A publication/code/discovery/explorer/empty',[8.6,8.7,9,9.1,8.6,9.2],'retained-layouts','同一控制边框与焦点语言有效，但稿件含额外菜单和筛选，原图与导航结构保留更妥当。'),
('direction-b-library.png','B publication/code/discovery/explorer/empty',[8.5,8.5,8.6,8.0,8.3,8.8],'rejected','青白色图面和标题变化不足以抵偿全站不一致，生成图简化/改写科研元素，未采用。')]
result=[]
for file,label,v,decision,reason in rows:result.append({'image':(J/'design'/file).as_posix(),'label':label,'rubric':dict(zip(keys,v)),'score':round(sum(x*y/10 for x,y in zip(v,weights)),2),'decision':decision,'reason':reason})
assets=[]
for key,score,reason in [('question',92,'蓝色上沿高光、较暗中部与下沿流体层次清楚。'),('collection',92,'翡翠与金色细节在小尺寸仍区分明确。'),('cleaning',91,'紫色边缘细腻，压缩后小尺寸内部略密。'),('landscape',91,'冰蓝波纹与研究问题蓝色同族但流体走向有差别。'),('findings',92,'琥珀色形成视觉重心，未覆盖原生线图标。')]:assets.append({'image':(J/'design'/f'planet-{key}.png').as_posix(),'visualQualityScore':score,'reason':reason,'objectiveValidation':'assets/planet-validation.json contains actual alpha/hash/size checks; this aesthetic value remains subjective.'})
(J/'design/candidate-scores.json').write_text(json.dumps({'assessmentType':'AI subjective visual judgment','weights':dict(zip(keys,weights)),'candidates':result,'assets':assets},ensure_ascii=False,indent=2)+'\n')
p=J/'design/visual-scores.json';d=json.loads(p.read_text());d['candidateReviews']='optimization/fullsite-closed-loop-20261031/design/candidate-scores.json';p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
