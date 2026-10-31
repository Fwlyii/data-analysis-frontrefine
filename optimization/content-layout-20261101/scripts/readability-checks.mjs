import{createRequire}from'node:module';import{resolve}from'node:path';import{writeFile}from'node:fs/promises';import{routes,root,inspectRoute}from'./inventory.mjs';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
const fingerprints=await collect(),results=[],rows=[],baselines=new Map();
const group=r=>['question','collection','cleaning'].includes(r.section)?r.section:r.family;
const specs={
 question:[['#question .question-lead',18],['#question .question-points li>div>span',16],['#question .question-points strong',24]],
 collection:[['#collection .design-points li>div>span',16],['#collection .task-row h3',18],['#collection .task-row p',15]],
 cleaning:[['#cleaning .cleaning-steps li>span',16],['#cleaning .cleaning-steps strong',18],['#cleaning .schema-preview',14]],
 landscape:[['.model-switch button span',14],['.task-switch button',14],['.landscape-foot',15]],
 story:[['.finding-nav button',14],['.figure-heading p',14],['.evidence-line',17]],
 publication:[['#stage .research-heading p',16],['#stage .text-action',14],['#stage .research-toolbar button',14]],
 code:[['#stage .research-heading p',16],['#stage .code-view-nav button',14],['#stage .model-tabs button',14]],
 discovery:[['#stage .metric-detail',14],['#stage .subheader',14],['#stage .scene-context',14]],
 library:[['#stage .explore-controls label',14],['#stage .explore-controls select',14]]
};
function measure(spec){
 const shown=e=>e&&e.getClientRects().length&&getComputedStyle(e).display!=='none';
 const samples=spec.map(([selector,min])=>{const e=document.querySelector(selector);return shown(e)?{selector,min,size:parseFloat(getComputedStyle(e).fontSize),text:e.textContent.trim().slice(0,90),lineHeight:getComputedStyle(e).lineHeight}:null;}).filter(Boolean);
 const ui=[...document.querySelectorAll('.publication-actions button,.explore-controls select,.research-home,.figure-toolbar>.export-menu summary')].filter(shown).map(e=>{const r=e.getBoundingClientRect();return{text:e.textContent.trim(),left:r.left,right:r.right,width:r.width,height:r.height};});
 const panel=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');
 return{samples,ui,overflow:document.documentElement.scrollWidth>innerWidth,panelScrollWidth:panel.scrollWidth,panelWidth:panel.clientWidth,questionCards:[...document.querySelectorAll('#question.is-active .question-points li')].map(e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height};})};
}
try{
 for(const[width,height,device]of[[1440,900,'desktop'],[1920,1080,'fullhd']]){
  const before=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'}),page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});
  for(const route of routes.filter(r=>r.section!=='gateway')){
   const g=group(route),key=g+'-'+device;let baseline=baselines.get(key);
   if(!baseline){const u=new URL(route.url,'http://127.0.0.1:8829/');u.searchParams.set('__readingBaseline',g);await before.goto(u.href,{waitUntil:'networkidle'});baseline=await before.evaluate(measure,specs[g]);baselines.set(key,baseline);}
   const u=new URL(route.url,'http://127.0.0.1:8828/');u.searchParams.set('__readingRoute',route.key);await page.goto(u.href,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);const after=await page.evaluate(measure,specs[g]);
   const larger=after.samples.some(s=>{const b=baseline.samples.find(b=>b.selector===s.selector);return b&&s.size>=b.size*1.15;});
   const liveView=await page.evaluate(inspectRoute,route);const passed=liveView.selectedViewMatches&&after.samples.length>=2&&after.samples.every(s=>s.size>=s.min)&&larger&&!after.overflow&&after.ui.every(e=>e.left>=-.5&&e.right<=width+.5);
   rows.push({routeKey:route.key,device,group:g,before:baseline,after,liveView,passed});results.push({name:route.key+' '+device+' readable UI, real size increase and unclipped actions',passed});if(!passed)console.error('FAIL',route.key,device,JSON.stringify({baseline,after,larger}));
   if(g==='question')results.push({name:'Question '+device+' dimensions occupy meaningful readable modules',passed:after.questionCards.length===3&&after.questionCards.every(c=>c.w>=200&&c.h>=(240))});
  }await before.close();await page.close();
 }
}catch(e){results.push({name:'Reading audit completed',passed:false,detail:e.stack});console.error(e.stack);}finally{await browser.close();await writeFile(resolve(root,'after/readability-checks.json'),JSON.stringify({fingerprints,method:'Actual computed CSS sizes per uniquely loaded live route, with original-view identity asserted; original layout sampled once per shared layout/device. Each content route must have real 15%+ type improvement, explicit minimum reading sizes and no clipped header/filter/export actions. Scientific SVG text is protected and excluded from UI font targets.',results,rows},null,2)+'\n');}
console.log(JSON.stringify({checks:results.length,passed:results.filter(x=>x.passed).length,failed:results.filter(x=>!x.passed)}));if(results.some(r=>!r.passed))process.exitCode=1;
