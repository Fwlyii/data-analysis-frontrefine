import {createRequire}from'node:module';import{resolve}from'node:path';import{writeFile}from'node:fs/promises';import{routes,root}from'./inventory.mjs';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core'),axe=require.resolve('axe-core/axe.min.js');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox']});const results=[],fingerprints=await collect();const check=(name,passed,detail)=>{results.push({name,passed:!!passed,detail});if(!passed)console.error('FAIL',name,JSON.stringify(detail));};
const inspect=()=>{
 const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage'),v=e=>e.getClientRects().length>0;
 const ids=new Map();for(const e of document.querySelectorAll('[id]'))ids.set(e.id,(ids.get(e.id)||0)+1);
 const bar=root.querySelector('.ix-reading');
 const numbering=[...root.querySelectorAll('.question-points>li,.cleaning-steps>li,.finding-nav>button')].map(e=>({text:(()=>{const c=e.cloneNode(true);c.querySelectorAll('[data-ix-owned]').forEach(x=>x.remove());return c.textContent.trim().replace(/\s+/g,' ').slice(0,100);})(),before:getComputedStyle(e,'::before').content}));
 return {duplicates:[...ids].filter(([k,n])=>n>1).map(([k,n])=>({id:k,count:n})),numbering,headings:[...root.querySelectorAll('h1,h2')].filter(v).map(e=>e.textContent.trim()),activePanels:document.querySelectorAll('.deck-panel:not([hidden])').length,guideCount:root.querySelectorAll('.ix-reading').length,bar:bar?{rect:JSON.parse(JSON.stringify(bar.getBoundingClientRect())),buttons:[...bar.querySelectorAll('button')].map(e=>({label:e.getAttribute('aria-label')||e.textContent.trim(),controls:e.getAttribute('aria-controls'),exists:!e.getAttribute('aria-controls')||!!document.getElementById(e.getAttribute('aria-controls'))}))}:null,plot:root.querySelector('#plot')?JSON.parse(JSON.stringify(root.querySelector('#plot').getBoundingClientRect())):null,width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,images:[...document.images].filter(v).map(i=>({src:i.getAttribute('src'),decoded:i.complete&&i.naturalWidth>0})),keys:[...root.querySelectorAll('[data-ix-owned][id]')].map(e=>e.id)};
};
try{for(const [width,height]of [[1440,900],[1920,1080]]){
 const pages=await Promise.all([8849,8838].map(()=>browser.newPage({viewport:{width,height},reducedMotion:'reduce'})));
 for(const route of routes){
  const state=[];
  for(let i=0;i<2;i++){await pages[i].goto(new URL(route.url,'http://127.0.0.1:'+(i?8838:8849)+'/').href,{waitUntil:'networkidle'});await pages[i].evaluate(()=>document.fonts.ready);state.push(await pages[i].evaluate(inspect));}
  const [a,b]=state,existingDuplicates=JSON.stringify(a.duplicates)===JSON.stringify(b.duplicates),headings=JSON.stringify(a.headings)===JSON.stringify(b.headings);
  const numbering=JSON.stringify(a.numbering)===JSON.stringify(b.numbering);
  const plots=!a.plot||a.plot.bottom>a.height+1||!!b.plot&&b.plot.bottom<=b.height+1;
  check(route.key+' '+width+' heading/numbering/IDs/alignment/original first-screen plot',existingDuplicates&&headings&&numbering&&!b.overflow&&b.images.every(i=>i.decoded)&&(!route.section||b.activePanels===1)&&(!b.bar||b.bar.buttons.every(x=>x.exists&&x.label.length>0))&&plots&&new Set(b.keys).size===b.keys.length,{baseline:a,current:b,originalFirstScreenRetained:plots});
 }
 for(const p of pages)await p.close();
 console.log('layout '+width+' complete');
}
// Whole-page WCAG comparison: retain all baseline issues and fail on newly introduced violations.
const sampleKeys=['deck-gateway','deck-question','deck-collection','deck-cleaning','landscape-reasoning-qwen-heatmap','story-concise-baseline','story-position','efficiency','position-matrix','code-sampling','code-tokens','discovery-1','chart-heatmap','chart-box','chart-behavior'];
const pages=await Promise.all([8849,8838].map(()=>browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'})));
for(const key of sampleKeys){const r=routes.find(r=>r.key===key),audits=[];for(let i=0;i<2;i++){await pages[i].goto(new URL(r.url,'http://127.0.0.1:'+(i?8838:8849)+'/').href,{waitUntil:'networkidle'});await pages[i].addScriptTag({path:axe});audits.push(await pages[i].evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,html:n.html,failure:n.failureSummary}))}));}));}
 const before=new Map(audits[0].map(v=>[v.id,v.nodes.length]));const added=audits[1].filter(v=>!before.has(v.id)||v.nodes.length>before.get(v.id));check(key+' automated WCAG introduces no new failures',added.length===0,{before:audits[0],after:audits[1],added});}
for(const p of pages)await p.close();
}finally{await browser.close();await writeFile(resolve(root,'after/layout-review.json'),JSON.stringify({fingerprints,results},null,2)+'\n');}console.log(JSON.stringify({checks:results.length,passed:results.filter(x=>x.passed).length}));if(results.some(r=>!r.passed))process.exitCode=1;
