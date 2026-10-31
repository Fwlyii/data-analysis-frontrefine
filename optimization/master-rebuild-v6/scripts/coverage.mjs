import {createRequire} from 'node:module';import{resolve}from'node:path';import{readFile,readdir,writeFile}from'node:fs/promises';import{createHash}from'node:crypto';import{routes,root,inspectRoute}from'./inventory.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));const{chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const rows=[],results=[],errors=[],failed=[];
const {fingerprints:collectFingerprints}=await import('./source-fingerprints.mjs');const fingerprints=await collectFingerprints();
const graphicReady=()=>{const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');const hosts=[...root.querySelectorAll('#plot,.overview-plot,#library-main,#library-side,.publication-svg,#code-vega-scatter,#code-linked-errors,.plot-content .chart')].filter(e=>e.getClientRects().length);if(!hosts.length)return [...root.querySelectorAll('svg')].some(s=>{const r=s.getBoundingClientRect();return r.width>=150&&r.height>=70&&s.querySelectorAll('path,rect,circle,line,polygon,polyline,use').length>=3;});return hosts.every(h=>[...h.querySelectorAll('svg')].some(s=>{const r=s.getBoundingClientRect();return r.width>=150&&r.height>=70&&s.querySelectorAll('path,rect,circle,line,polygon,polyline,use').length>=3;}));};
async function rendering(page,route){return page.evaluate(async route=>{
 const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');
 const opacity=e=>{let x=e,v=1;while(x&&x!==document.documentElement){v*=Number(getComputedStyle(x).opacity);if(getComputedStyle(x).visibility==='hidden'||getComputedStyle(x).display==='none')return 0;x=x.parentElement;}return v;};
 const images=[...document.images].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!=='none').map(e=>({src:e.currentSrc,complete:e.complete,naturalWidth:e.naturalWidth,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,opacity:opacity(e)}));
 const svgs=[...root.querySelectorAll('svg')].filter(s=>!s.parentElement.closest('svg')&&s.getBoundingClientRect().width>=150&&s.getBoundingClientRect().height>=70).map(s=>{
  const r=s.getBoundingClientRect();const shapes=[...s.querySelectorAll('path,rect,circle,line,polygon,polyline,ellipse,use,image')].filter(e=>!e.closest('defs,clipPath,mask'));let painted=0;
  for(const e of shapes){try{const b=e.getBBox(),style=getComputedStyle(e);if((b.width>0||b.height>0)&&opacity(e)>.05&&(style.fill!=='none'||style.stroke!=='none'||e.tagName==='image'))painted++;}catch{}}
  const refs=[...s.querySelectorAll('use')].map(u=>u.href.baseVal).filter(h=>h.startsWith('#')&&!s.querySelector('#'+CSS.escape(h.slice(1))));
  return{width:r.width,height:r.height,top:r.top,bottom:r.bottom,painted,interactionLayer:painted===0&&s.classList.contains('main-svg')&&!!s.querySelector(':scope>.hoverlayer'),opacity:opacity(s),unresolved:refs,invalid:/NaN|Infinity/.test(s.outerHTML)};
 });
 const decode=[];for(const src of new Set([...root.querySelectorAll('svg image')].map(e=>e.href.baseVal).filter(Boolean))){if(src.startsWith('#'))continue;try{const img=new Image();img.src=src;await img.decode();decode.push({source:src.startsWith('data:')?'embedded-svg-image':src,passed:img.naturalWidth>0});}catch{decode.push({source:src.slice(0,120),passed:false});}}
 const plot=root.querySelector('#plot>svg');const bounds=root.getBoundingClientRect();
 return{images,svgs,embeddedImages:decode,chartInFirstScreen:plot?plot.getBoundingClientRect().bottom<=bounds.bottom+1:null,rootViewport:{top:bounds.top,bottom:bounds.bottom},scrollable:root.scrollHeight>root.clientHeight,brandVisible:opacity(document.querySelector('.wordmark-logo strong,.brand strong'))>.9};
},route);}
try{
 for(const [width,height,motion]of[[1440,900,'reduce'],[390,844,'reduce'],[320,740,'reduce'],[768,960,'reduce'],[1366,768,'no-preference']]){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:motion});page.on('pageerror',e=>errors.push({url:page.url(),message:e.message}));page.on('requestfailed',r=>failed.push({url:r.url(),failure:r.failure()}));
 for(const route of routes){const url=new URL(route.url,'http://127.0.0.1:8788/');url.searchParams.set('__renderReview',route.key+'-'+width);await page.goto(url.href,{waitUntil:'load'});await page.evaluate(()=>document.fonts.ready);
  const hasGraph=route.family==='landscape'||route.family==='story'||!route.section;
  if(hasGraph&&!route.empty)await page.waitForFunction(graphicReady,null,{timeout:15000});
  if(motion==='no-preference')await page.waitForTimeout(650);
  const state=await page.evaluate(inspectRoute,route),render=await rendering(page,route);
  const passed=(route.empty?state.empty:(!hasGraph||render.svgs.some(s=>s.painted>=3)))&&!!state.title&&!state.overflow&&state.selectedViewMatches&&!state.invalidValues&&render.brandVisible&&state.nav.every(n=>n.x>=0&&n.right<=width+.5)&&(!state.activeScroll||state.activeScroll.content<=state.activeScroll.width+1)&&state.background==='rgb(245, 242, 235)'&&state.accent==='#a34f36'&&render.images.every(i=>i.complete&&i.naturalWidth>0&&i.width>0&&i.height>0)&&render.embeddedImages.every(i=>i.passed)&&render.svgs.every(s=>(s.painted>=3||s.interactionLayer)&&s.opacity>.95&&!s.invalid&&!s.unresolved.length)&&(!(width===1366&&route.family==='story')||render.chartInFirstScreen);
  results.push({name:`${route.key} ${width}×${height} ${motion} decoded/painted/layout`,passed,detail:{...state,...render}});if(!passed)console.error('FAIL',route.key,width,JSON.stringify({images:render.images.filter(i=>!i.complete||!i.naturalWidth),svgs:render.svgs,chartInFirstScreen:render.chartInFirstScreen,overflow:state.overflow}));
  if(width===1440||width===390){const device=width===1440?'desktop':'mobile';await page.screenshot({path:resolve(root,'after',route.key+'-'+device+'.png')});rows.push({key:route.key,device,url:route.url,...state,...render});}
 }
 console.log(JSON.stringify({width,height,motion,completed:routes.length,failures:results.filter(r=>!r.passed).length}));await page.close();}
 results.push({name:'No uncaught browser errors',passed:!errors.length,detail:errors},{name:'No failed ordinary resource requests',passed:!failed.length,detail:failed});
}catch(e){results.push({name:'Audit finished without exception',passed:false,detail:e.stack});console.error(e.stack);}
finally{await browser.close();await writeFile(resolve(root,'after/page-audit.json'),JSON.stringify({rows,errors,failedRequests:failed},null,2)+'\n');await writeFile(resolve(root,'after/site-checks.json'),JSON.stringify({matrix:{routes:routes.map(r=>r.key),viewports:[320,390,768,1366,1440],motion:['reduce','no-preference']},fingerprints,results},null,2)+'\n');}
console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length,failures:results.filter(r=>!r.passed).map(r=>r.name)}));if(results.some(r=>!r.passed))process.exitCode=1;
