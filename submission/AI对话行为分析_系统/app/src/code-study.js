import { esc, fmt, pct, signed, csvString, promptName } from "./model.js";
import * as interact from "./code-interactions.js";
import * as libraries from "./libraries.js";

const D = window.COURSE_CODE;
const VIEWS = {sampling:"采样收益",prompts:"提示差异",errors:"错误类型",tokens:"输出开销"};
const ERROR_LABELS = {assertion_failure:"测试断言失败",attribute_error:"属性或接口错误",type_error:"类型错误",syntax_error:"语法错误",extraction_error:"代码提取失败",dependency_error:"依赖错误",name_error:"名称未定义",timeout:"执行超时",runtime_error:"其他运行错误",file_error:"文件错误",index_error:"索引错误",key_error:"键错误",value_error:"值错误",resource_error:"资源限制",environment_error:"环境排除",success:"测试通过"};
let previousSignature;
let featurePromise, featureRows=[], activeRecords=[], recordPage=0, environment, currentState;
const name=(m)=>D?.models.find(r=>r.id===m)?.name || m;
const label=(p)=>p==="__all"?"全部 31 种提示":promptName(p);
const stat=(m,p="__all")=>D.stats.find(r=>r.model===m && r.prompt===p);
const button=(action,text)=>`<button class="text-action" data-code-action="${action}">${text}</button>`;
const form=(id,title,options,value)=>`<label for="${id}">${title}<select class="form-select form-select-sm" id="${id}">${options.map(([v,t])=>`<option value="${v}" ${String(value)===String(v)?"selected":""}>${esc(t)}</option>`).join("")}</select></label>`;
const icon=()=>'<img src="assets/ui/download.svg" width="17" height="17" alt="">';

function parseBrush(value){if(!value)return null;const b=value.split(",").map(Number);return b.length===4 && b.every(Number.isFinite) && b[0]>=0 && b[0]<b[1] && b[2]>=0 && b[2]<b[3] && b[3]<=100?b:null;}
export function disposeCodeStudy(){interact.dispose();}
export function codeRoute(params) {
 return {view:Object.hasOwn(VIEWS,params.get("codeView"))?params.get("codeView"):"sampling",
  model:["all","deepseek","qwen","qwen3"].includes(params.get("codeModel"))?params.get("codeModel"):"all",
  prompt:D?.prompts.includes(params.get("codePrompt"))?params.get("codePrompt"):"__all",
  k:["0","1","3","5"].includes(params.get("codeK"))?+params.get("codeK"):1,
  scope:params.get("codeScope")==="all"?"all":"core",
  error:D?.error_categories.includes(params.get("codeError"))?params.get("codeError"):"extraction_error",
  step:[1,2,3,4,5].includes(+params.get("codeStep"))?+params.get("codeStep"):5,
  brush:parseBrush(params.get("codeBrush"))};
}
export function codeQuery(s) {
 const p=new URLSearchParams();p.set("codeView",s.view);
 if(s.view==="sampling"){p.set("codeModel",s.model);p.set("codePrompt",s.prompt);if(s.step!==5)p.set("codeStep",s.step);}
 if(["prompts","tokens"].includes(s.view))p.set("codeK",s.k);
 if(["prompts","errors"].includes(s.view))p.set("codeScope",s.scope);
 if(s.view==="errors")p.set("codeError",s.error);
 if(s.view==="tokens" && s.brush)p.set("codeBrush",s.brush.join(","));
 return p;
}
function figureKey(s) {
 if(s.view==="sampling")return `code-sampling-${s.model}-${s.prompt==="__all"?"all":D.prompts.indexOf(s.prompt)}`;
 if(s.view==="prompts")return `code-prompts-${s.k}-${s.scope}`;
 if(s.view==="errors")return `code-errors-${s.error}-${s.scope}`;
 return `code-tokens-${s.k || 1}`;
}
function caption(s) {
 if(s.view==="sampling"){
  if((s.step || 5)<5)return `<h2>逐次查看独立采样的覆盖变化。</h2><p>当前显示至第 ${s.step} 次；每个点都是由五次已保存结果计算的 Pass@k 估计，右侧为固定次序中的新增成功。采样之间没有测试反馈。</p>`;
  const ms=s.model==="all"?D.models.map(m=>m.id):[s.model];
  const gains=ms.map(m=>stat(m,s.prompt).marginal[3]*100);
  return `<h2>${s.prompt==="__all"?"第 5 次独立生成，新增收益已明显收窄。":"当前提示下的独立采样收益。"}</h2><p>当前范围的第 5 次新增为 ${fmt(Math.min(...gains),2)}${gains.length>1?`–${fmt(Math.max(...gains),2)}`:""} 个百分点。左图估计任取 k 个答案至少一个通过的概率；右图按本次实际生成次序统计新增。</p>`;
 }
 if(s.view==="prompts"){
  const k=s.k || 1;const values=D.models.map(m=>{const r=D.contrasts.find(r=>r.model===m.id && r.prompt==='DefaultCoT');return `${m.name} ${signed(r.difference[k-1]*100,2)} pp`;});
  return `<h2>同一提示，对不同模型的作用方向也会改变。</h2><p>右图 DefaultCoT 相对 NoCoT 的 Pass@${k}：${values.join('，')}。区间按题配对；Qwen3 的差异还包含代码提取是否成功。</p>`;
 }
 if(s.view==="errors" && s.error!=="extraction_error"){
  const candidates=D.stats.filter(r=>r.prompt!=="__all" && (s.scope==="all" || D.core.includes(r.prompt))).map(r=>({...r,rate:(r.errors[s.error] || 0)/r.n})).sort((a,b)=>b.rate-a.rate);const r=candidates[0];
  return `<h2>${esc(ERROR_LABELS[s.error])}在不同提示条件下的分布。</h2><p>当前展示范围中，最高为 ${esc(name(r.model))} / ${esc(r.prompt)}：${pct(r.rate,1)}。每个提示×模型条件的分母均为 965 条可评回答。</p>`;
 }
 if(s.view==="errors")return `<h2>格式压力会影响能否得到可提取的 Python 函数。</h2><p>环境排除后，Qwen2.5 / NoProperGrammar 的提取失败为 ${pct(stat('qwen','NoProperGrammar').errors.extraction_error/stat('qwen','NoProperGrammar').n,1)}；Qwen3 / OnlyNumbers 为 ${pct(stat('qwen3','OnlyNumbers').errors.extraction_error/stat('qwen3','OnlyNumbers').n,1)}。分母为各条件的 965 条可评回答。</p>`;
 if(s.view==='tokens' && s.brush){
  const b=s.brush,rs=D.stats.filter(r=>r.prompt!=='__all' && r.mean_output_tokens>=b[0] && r.mean_output_tokens<=b[1] && r.pass[s.k-1]*100>=b[2] && r.pass[s.k-1]*100<=b[3]);
  const n=rs.reduce((a,r)=>a+r.n,0);if(!n)return '<h2>这个范围内没有实测条件。</h2><p>扩大范围或清除框选，可返回全部 93 个模型与提示条件。</p>';
  const rates=D.error_categories.map(error=>({error,count:rs.reduce((a,r)=>a+(r.errors[error] || 0),0)})).sort((a,b)=>b.count-a.count),top=rates[0];
  return `<h2>${top.error==='extraction_error' && top.count/n>.5?'所选范围的失败，主要集中在代码提取环节。':'结合输出开销，进一步区分失败发生的环节。'}</h2><p>${rs.length} 个条件中，${esc(ERROR_LABELS[top.error])}为 ${fmt(top.count)} / ${fmt(n)}（${pct(top.count/n,2)}）。这些条件由交互选择，属于探索性描述；点击右图可追溯对应评分。</p>`;
 }
 return '<h2>更多输出，没有对应统一的通过率提升。</h2><p>每个点保留模型与提示条件；开销采用返回 token，评分来自 193 道共同题。点选后可同时查看提取错误、截断和测试结果。</p>';
}
function tools(s){
 if(s.view==="sampling")return `<div class="model-tabs" role="group" aria-label="代码实验模型"><button data-code-model="all" aria-pressed="${s.model==="all"}">全部模型</button>${D.models.map(m=>`<button data-code-model="${m.id}" aria-pressed="${s.model===m.id}"><img src="assets/logos/${m.id==='deepseek'?'deepseek.svg':'qwen.svg'}" width="18" height="18" alt="">${esc(m.name)}</button>`).join("")}</div>${form("code-study-prompt","提示",[["__all","全部 31 种提示"],...D.prompts.map(p=>[p,label(p)])],s.prompt)}`;
 if(s.view==="prompts")return form("code-study-k","指标",[[1,"Pass@1"],[3,"Pass@3"],[5,"Pass@5"],[0,"Pass@5 − Pass@1"]],s.k)+form("code-study-scope","范围",[["core","8 种对照提示"],["all","全部 31 种提示"]],s.scope);
 if(s.view==="errors")return form("code-study-error","右图错误",D.error_categories.map(k=>[k,ERROR_LABELS[k] || k]),s.error)+form("code-study-scope","范围",[["core","8 种对照提示"],["all","全部 31 种提示"]],s.scope);
 return form("code-study-k","通过指标",[[1,"Pass@1"],[3,"Pass@3"],[5,"Pass@5"]],s.k)+interact.tokenTools(s.brush);
}
function method() {
 interact.pause();
 const rows=D.models.map(m=>{const s=stat(m.id);return `<tr><td>${esc(m.name)}</td>${[1,3,5].map(k=>`<td class="numeric">${pct(s.pass[k-1],2)}</td>`).join("")}</tr>`;}).join("");
 environment.openInspector("代码生成实验",`<p class="subline">CodePromptEval · code-generation@9dfc592</p><p>194 道保留题 × 31 种提示 × 5 次独立生成 × 3 个模型，共 90,210 条。共同排除 1 道环境预检不稳定的题，465 条记录保留但不进入性能分母；有效范围为 193 题、89,745 条。</p><h3>独立采样与 Pass@k</h3><p>每次生成都没有前次回答或测试反馈。Pass@k 使用全部 5 次已保存结果，估计任取 k 次至少一次通过的概率：1 − C(5−c,k)/C(5,k)。观测累计按本次次序计算，和 Pass@k 估计分别保留。k=2、4 由同一批结果计算。</p><table><thead><tr><th>模型</th><th>Pass@1</th><th>Pass@3</th><th>Pass@5</th></tr></thead><tbody>${rows}</tbody></table><h3>评分与区间</h3><p>保留 target-function-ast-v2 的单元测试结果；193 道题为重抽样簇，5,000 次、种子 91。置信区间未作多重比较校正。单元测试通过表示通过当前测试。此次接入没有调用模型，也没有重新执行生成代码。</p><h3>错误率分母</h3><p>图中的错误率以可评回答为分母。源交付部分错误表采用含环境排除的全部记录：Qwen2.5 / NoProperGrammar 为 94.5%，Qwen3 / OnlyNumbers 为 78.7%；换成可评口径分别为 95.0% 和 79.1%。环境记录未被计为模型错误。</p><h3>Prompt 适配</h3><p>长度与格式限制作用于代码前的可选说明，完整 Python 代码要求保持一致。31 种提示的探索性排名取决于模型和当前题集。</p><div class="record-actions">${button("export-summary","导出当前统计 CSV")}${button("excluded","查看 465 条环境排除")}</div>`);
 wireActions(document.getElementById("inspector-body"));
}
async function loadFeatures() {
 if(!featurePromise)featurePromise=new Promise((resolve,reject)=>{
  if(window.COURSE_CODE_FEATURES)return resolve(window.COURSE_CODE_FEATURES);
  const script=document.createElement("script");script.src="runtime/code-features.js?v="+encodeURIComponent(D.feature_version);
  script.onload=()=>window.COURSE_CODE_FEATURES?resolve(window.COURSE_CODE_FEATURES):reject(new Error("评分记录未能打开"));
  script.onerror=()=>reject(new Error("评分文件未找到，请重新启动系统"));document.head.append(script);
 }).then(p=>featureRows=p.rows.map(r=>Object.fromEntries(p.fields.map((k,i)=>[k,r[i]]))));
 return featurePromise;
}
function matches(r,q){return (!q.conditionKeys || q.conditionKeys.has(r.model+"|"+r.prompt)) && (!q.model || q.model==="all" || r.model===q.model) && (!q.prompt || q.prompt==="__all" || r.prompt===q.prompt) && (!q.question || r.question===q.question) && (!q.prompts || q.prompts.includes(r.prompt)) && (!q.error || r.error===q.error) && (q.excluded?r.environment_excluded:!r.environment_excluded);}
async function records(q,title) {
 interact.pause();
 if(q.conditions)q={...q,conditionKeys:new Set(q.conditions.map(r=>r.model+"|"+r.prompt))};
 environment.openInspector(title,'<p class="subline">正在打开已保存评分…</p>');
 try {
  let rs=(await loadFeatures()).filter(r=>matches(r,q));
  if(q.sample){
   const first=new Map();
   for(const r of await loadFeatures())if(r.passed && !r.environment_excluded){const key=r.model+'|'+r.question+'|'+r.prompt;first.set(key,Math.min(first.get(key) || 6,r.sample));}
   rs=rs.filter(r=>r.passed && r.sample===+q.sample && first.get(r.model+'|'+r.question+'|'+r.prompt)===+q.sample);
  }
  activeRecords=rs;recordPage=0;drawRecords(title,q);
 } catch(e){environment.openInspector("评分记录未能打开",`<p>${esc(e.message)}</p>`);}
}
function drawRecords(title,q){
 const pages=Math.max(1,Math.ceil(activeRecords.length/20));recordPage=Math.min(recordPage,pages-1);
 const text=q.excluded?'这些记录由共同环境规则排除，测试结果保留为空，不计为模型失败。':q.sample?'这里只列出该次独立采样首次通过的条件记录；采样之间没有测试反馈。':'同一题目、模型和提示下的 5 次是独立生成；采样序号不表示修复轮次。';
 environment.openInspector(title,`<p class="subline">${fmt(activeRecords.length)} 条已保存评分 · ${new Set(activeRecords.map(r=>r.question)).size} 道题</p><p>${text}</p><div class="table-wrap"><table><thead><tr><th>匿名记录</th><th>题号</th><th>采样</th><th>结果</th><th class="numeric">输出 token</th></tr></thead><tbody>${activeRecords.slice(recordPage*20,(recordPage+1)*20).map(r=>`<tr><td><button class="text-action" data-code-record="${r.id}" aria-label="查看评分 ${r.id}">${r.id}</button></td><td>${r.question}</td><td>${r.sample}</td><td>${esc(r.environment_excluded?'环境排除':r.passed?'通过':ERROR_LABELS[r.error] || r.error)}</td><td class="numeric">${fmt(r.output_tokens)}</td></tr>`).join("")}</tbody></table></div><div class="record-actions"><button class="plain-button" id="code-export-records">导出筛选</button><button class="plain-button" id="code-previous" ${recordPage===0?'disabled':''}>上一页</button><span>${recordPage+1} / ${pages}</span><button class="plain-button" id="code-next" ${recordPage+1>=pages?'disabled':''}>下一页</button></div>`);
 const body=document.getElementById("inspector-body");
 body.querySelector("#code-export-records").onclick=()=>environment.download("code-selection.csv",csvString([Object.keys(activeRecords[0] || featureRows[0] || {}).map(k=>k),...activeRecords.map(r=>Object.values(r))]),"text/csv;charset=utf-8");
 body.querySelector("#code-previous").onclick=()=>{recordPage--;drawRecords(title,q);};body.querySelector("#code-next").onclick=()=>{recordPage++;drawRecords(title,q);};
 body.querySelectorAll("[data-code-record]").forEach(el=>{el.onclick=()=>recordDetail(el.dataset.codeRecord);el.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();recordDetail(el.dataset.codeRecord);}};});
}
function recordDetail(id){
 const r=featureRows.find(r=>r.id===id);if(!r)return;
 const siblings=featureRows.filter(v=>v.question===r.question && v.model===r.model && v.prompt===r.prompt).sort((a,b)=>a.sample-b.sample);
 environment.openInspector(id,`<p class="subline">${esc(name(r.model))} / ${esc(label(r.prompt))} / ${r.question}</p><div class="facts">${[["独立采样序号",r.sample],["源结果",r.environment_excluded?'环境排除':r.passed?'测试通过':ERROR_LABELS[r.error] || r.error],["输出 token",fmt(r.output_tokens)],["输入 token",fmt(r.input_tokens)],["生成延迟",`${fmt(r.latency_seconds,2)} 秒`],["结束原因",r.finish || '未记录'],["评分器","target-function-ast-v2"]].map(([k,v])=>`<div class="fact"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join("")}</div><h3>相同条件的 5 次独立结果</h3><table><thead><tr><th>采样</th><th>结果</th><th>返回 token</th></tr></thead><tbody>${siblings.map(a=>`<tr><td>${a.sample}</td><td>${esc(a.environment_excluded?'环境排除':a.passed?'通过':ERROR_LABELS[a.error] || a.error)}</td><td>${fmt(a.output_tokens)}</td></tr>`).join("")}</tbody></table><p>模型没有看到其他采样的回答或测试反馈。此处仅展示保存的评分与匿名特征。</p><div class="record-actions">${button('record-condition','查看同条件全部评分')}</div>`);
 document.getElementById("inspector-body").querySelector('[data-code-action="record-condition"]').onclick=()=>records({model:r.model,prompt:r.prompt,excluded:r.environment_excluded},`${name(r.model)} / ${label(r.prompt)}`);
}
function condition(meta){
 interact.pause();
 const s=stat(meta.model,meta.prompt || "__all");const k=+meta.k || currentState.k || 1;
 const contrast=D.contrasts.find(r=>r.model===meta.model && r.prompt===(meta.prompt || '__all'));
 const rows=[1,2,3,4,5].map(i=>`<tr><td>${i}</td><td class="numeric">${pct(s.pass[i-1],2)}</td><td class="numeric">${pct(s.pass_low[i-1],2)}–${pct(s.pass_high[i-1],2)}</td><td class="numeric">${pct(s.cumulative[i-1],2)}</td></tr>`).join("");
 environment.openInspector(`${name(meta.model)} / ${label(s.prompt)}`,`<p class="subline">${fmt(s.n)} 条可评回答 / 193 道题 / ${fmt(s.units)} 个题目×提示条件</p><div class="metric-pair"><div><strong>${pct(s.pass[k-1],2)}</strong><span>Pass@${k}</span></div><div><strong>${fmt(s.mean_output_tokens,1)}</strong><span>平均返回 token</span></div></div><table><thead><tr><th>k</th><th>Pass@k</th><th>按题 95% 区间</th><th>观测累计</th></tr></thead><tbody>${rows}</tbody></table>${contrast && s.prompt!=='NoCoT'?`<p>当前提示相对 NoCoT 的 Pass@${k} 差为 ${signed(contrast.difference[k-1]*100,2)} pp，95% 区间 ${signed(contrast.low[k-1]*100,2)} 至 ${signed(contrast.high[k-1]*100,2)} pp。</p>`:""}<p>提取失败 ${fmt(s.errors.extraction_error || 0)} 条；输出截断 ${fmt(s.truncated)} 条。Pass@k 估计使用全部 5 次保存结果，观测累计采用本次固定次序。</p><div class="record-actions">${button('condition-records','查看评分记录')}${button('condition-extraction','仅看提取失败')}</div>`);
 const body=document.getElementById("inspector-body");body.querySelector('[data-code-action="condition-records"]').onclick=()=>records({model:s.model,prompt:s.prompt},`${name(s.model)} / ${label(s.prompt)}`);body.querySelector('[data-code-action="condition-extraction"]').onclick=()=>records({model:s.model,prompt:s.prompt,error:'extraction_error'},`${name(s.model)} / 提取失败`);
}
function contrast(meta){
 const k=+meta.k || 1;
 environment.openInspector(`DefaultCoT − NoCoT / Pass@${k}`,`<p>相同的 193 道共同题目；模型内配对。提示适配只改变代码前说明要求。</p><table><thead><tr><th>模型</th><th>差值 / pp</th><th>95% 区间 / pp</th></tr></thead><tbody>${D.models.map(m=>{const r=D.contrasts.find(r=>r.model===m.id && r.prompt==='DefaultCoT');return `<tr><td>${m.name}</td><td>${signed(r.difference[k-1]*100,2)}</td><td>${signed(r.low[k-1]*100,2)} 至 ${signed(r.high[k-1]*100,2)}</td></tr>`;}).join("")}</tbody></table><p>Qwen3 / NoCoT 的代码提取失败率为 ${pct(stat('qwen3','NoCoT').errors.extraction_error/stat('qwen3','NoCoT').n,1)}，因此这项差异同时包含是否输出可提取函数的影响。</p>${button('contrast-records','查看所选模型 NoCoT 评分')}`);
 document.getElementById("inspector-body").querySelector('[data-code-action="contrast-records"]').onclick=()=>records({model:meta.model,prompt:'NoCoT'},`${name(meta.model)} / NoCoT`);
}
function wireActions(root){
 root.querySelectorAll('[data-code-action]').forEach(el=>{
  const action=()=>{
   const m=el.dataset;
   if(m.codeAction==='method')method();
   else if(m.codeAction==='excluded')records({excluded:true},'共同环境排除');
   else if(m.codeAction==='records'){
    const s=currentState;const q=s.view==='sampling'?{model:s.model,prompt:s.prompt}:s.view==='tokens'?{conditions:interact.selectedConditions()}:{prompts:s.scope==='core'?D.core:D.prompts,...(s.view==='errors'?{error:s.error}:{})};
    records(q,s.view==='errors'?'所选错误类型的评分记录':'当前范围的评分记录');
   }
   else if(m.codeAction==='condition')condition({model:m.codeModel,prompt:m.codePrompt,k:m.codeK});
   else if(m.codeAction==='contrast')contrast({model:m.codeModel,k:m.codeK});
   else if(m.codeAction==='gains')records({model:m.codeModel,prompt:m.codePrompt,sample:+m.codeSample},`${name(m.codeModel)} / 第 ${m.codeSample} 次首次通过`);
   else if(m.codeAction==='errors')records({model:m.codeModel,prompt:m.codePrompt,error:m.codeError},`${name(m.codeModel)} / ${ERROR_LABELS[m.codeError] || m.codeError}`);
   else if(m.codeAction==='svg')environment.download(figureKey(currentState)+'.svg',interact.svgSnapshot() || D.figures[figureKey(currentState)],'image/svg+xml;charset=utf-8');
   else if(m.codeAction==='export-summary'){
    const chosen=interact.selectedConditions();
    const rs=D.stats.filter(r=>(currentState.view!=='tokens' || chosen.some(c=>c.model===r.model && c.prompt===r.prompt)) && (currentState.view!=='sampling' || ((currentState.model==='all' || r.model===currentState.model) && r.prompt===currentState.prompt)));
    environment.download('code-study-summary.csv',csvString([['model','prompt','eligible_responses','question_clusters','pass_1','pass_2','pass_3','pass_4','pass_5','mean_output_tokens'],...rs.map(r=>[r.model,r.prompt,r.n,r.questions,...r.pass,r.mean_output_tokens])]),'text/csv;charset=utf-8');
   }
  };
  el.onclick=action;
  if(el.tagName.toLowerCase()!=='button')el.onkeydown=e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();action();}};
 });
}
export function renderCodeStudy(s,env){
 environment=env;currentState=s;
 const root=env.root;
 if(!D){root.innerHTML='<h1>代码实验快照未构建</h1><p>请运行离线构建后重新打开系统。</p>';return;}
 if(s.view==='tokens' && s.k===0)s.k=1;
 const titles={sampling:'独立采样的收益',prompts:'提示策略与代码通过率',errors:'代码失败的来源',tokens:'输出开销与测试表现'};
 root.innerHTML=`<div class="research-heading"><div><h1>${titles[s.view]}</h1><p>193 道共同可评题 / 31 种提示 / 每条件 5 次独立生成</p></div><div class="publication-actions">${button('method','方法')}${button('svg',icon()+' SVG')}</div></div><nav class="code-view-nav" aria-label="代码生成视图">${Object.entries(VIEWS).map(([k,v])=>`<button data-code-view="${k}" aria-current="${s.view===k?'page':'false'}">${v}</button>`).join('')}</nav><div class="research-toolbar code-study-toolbar">${tools(s)}</div>${s.view==='sampling'?interact.playbackControls(s.step):''}<div class="publication-frame"><div class="publication-svg" id="code-publication" role="region" tabindex="0" aria-label="代码生成科学图表，可横向滚动查看完整图">${D.figures[figureKey(s)] || ''}</div><p class="publication-scroll-hint">横向滚动查看完整图 · 聚焦图表后可使用左右方向键</p></div><div class="research-caption"><span class="caption-index">发现</span><div id="code-finding">${caption(s)}</div></div>${s.view==='tokens'?interact.numericControls(s.brush,D.error_categories,ERROR_LABELS):''}<div class="research-foot"><span>code-generation · 90,210 条已保存回答 / 89,745 条进入统计 · 5 次独立采样</span><div class="code-source-actions">${button('records','评分记录')}${button('excluded','465 条环境排除')}</div></div><div class="code-keyboard-tools"><label for="code-keyboard-model">记录模型</label><select id="code-keyboard-model" class="form-select">${D.models.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('')}</select><label for="code-keyboard-prompt">记录提示</label><select id="code-keyboard-prompt" class="form-select">${D.prompts.map(p=>`<option value="${p}">${esc(label(p))}</option>`).join('')}</select><button class="text-action" id="code-keyboard-open">查看条件与评分</button></div>`;
 root.querySelectorAll('[data-code-view]').forEach(el=>el.onclick=()=>env.onChange({...s,view:el.dataset.codeView}));
 root.querySelectorAll('[data-code-model]:not([data-code-action])').forEach(el=>el.onclick=()=>env.onChange({...s,model:el.dataset.codeModel}));
 const change=(id,key)=>{const el=root.querySelector('#'+id);if(el)el.onchange=()=>env.onChange({...s,[key]:key==='k'?+el.value:el.value,...(key==='k'?{brush:null}:{})});};
 change('code-study-prompt','prompt');change('code-study-k','k');change('code-study-scope','scope');change('code-study-error','error');
 wireActions(root);
 root.querySelector('#code-keyboard-open').onclick=()=>condition({model:root.querySelector('#code-keyboard-model').value,prompt:root.querySelector('#code-keyboard-prompt').value,k:s.k || 1});
 const persist=(next,url=true)=>{currentState=next;env.onState(next,{url});};
 if(s.view==='sampling')interact.enhanceSampling(root,s,D,step=>{s.step=step;persist({...s});root.querySelector('#code-finding').innerHTML=caption(s);});
 if(s.view!=='tokens')interact.enhanceStatic(root);
 if(s.view==='tokens'){
  const updateSelection=(selected,brush)=>{
   s.brush=brush;root.querySelector("#code-finding").innerHTML=caption(s);const clear=root.querySelector('#code-clear-brush');if(clear)clear.hidden=!brush;
   const form=root.querySelector('#code-range-form');if(form){const b=brush || [0,700,0,100];['xmin','xmax','ymin','ymax'].forEach((key,i)=>{if(document.activeElement!==form.elements[key])form.elements[key].value=b[i];});}
  };
  interact.enhanceTokens(root,s,D,{onState:persist,onCondition:condition,onRecords:records,onSelection:updateSelection,onUnavailable:message=>{const note=root.querySelector('.code-gesture-note');if(note)note.textContent='框选未启用；可用下方精确范围筛选';}});
  root.querySelector('#code-clear-brush').onclick=()=>env.onChange({...s,brush:null});
  root.querySelector('#code-keyboard-error-open').onclick=()=>{const error=root.querySelector('#code-keyboard-error').value;records({conditions:interact.selectedConditions(),error},ERROR_LABELS[error]+' / 当前框选');};
  root.querySelector('#code-reset-range').onclick=()=>env.onChange({...s,brush:null});
  root.querySelector('#code-range-form').oninput=event=>{const f=event.currentTarget;f.elements.xmax.setCustomValidity('');f.elements.ymax.setCustomValidity('');};
  root.querySelector('#code-range-form').onsubmit=event=>{event.preventDefault();const f=event.currentTarget,b=['xmin','xmax','ymin','ymax'].map(k=>+f.elements[k].value);f.elements.xmax.setCustomValidity(b[1]>b[0]?'':'最多 token 应大于最少 token');f.elements.ymax.setCustomValidity(b[3]>b[2]?'':'最高通过率应大于最低通过率');if(f.reportValidity())env.onChange({...s,brush:b});};
 }
 const signature=JSON.stringify(s),frame=root.querySelector('.publication-frame');if(previousSignature && previousSignature!==signature && !libraries.reducedMotion())frame.animate([{opacity:.65},{opacity:1}],{duration:180,easing:'ease-out'});previousSignature=signature;

}
