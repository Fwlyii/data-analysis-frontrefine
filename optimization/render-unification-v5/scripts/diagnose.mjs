import {createRequire} from 'node:module';import {resolve} from 'node:path';import {writeFile} from 'node:fs/promises';
import {routes} from '../../master-migration-v4/scripts/inventory.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const rows=[],errors=[];
try{
 for(const [width,height] of [[1366,768],[390,844]]){
 const page=await browser.newPage({viewport:{width,height},reducedMotion:'no-preference'});page.on('pageerror',e=>errors.push({url:page.url(),error:e.message}));
 const selected=routes.filter(r=>r.family!=='landscape'&&!(r.finding==='limits'&&r.key!=='story-limits-deepseek-math500-WordLimit'));
 for(const r of selected){
  const url=new URL(r.url,'http://127.0.0.1:8788/');url.searchParams.set('__render',r.key+'-'+width);await page.goto(url.href,{waitUntil:'networkidle'});await page.waitForTimeout(700);
  const state=await page.evaluate(()=>{
   const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');
   const rect=e=>{const r=e.getBoundingClientRect();return{x:r.x,y:r.y,w:r.width,h:r.height};};
   const images=[...document.images].map(e=>({src:e.currentSrc,complete:e.complete,naturalWidth:e.naturalWidth,...rect(e),visible:!!e.getClientRects().length}));
   const plots=[...root.querySelectorAll('#plot,.overview-plot,.plot-content,.publication-frame,#code-vega-scatter,.code-plotly')].map(e=>({selector:e.id||e.className,...rect(e),opacity:getComputedStyle(e).opacity,svgs:[...e.querySelectorAll('svg')].map(s=>({viewBox:s.getAttribute('viewBox'),...rect(s),shapes:s.querySelectorAll('path,rect,circle,line,polygon,polyline').length,invalid:/NaN|Infinity/.test(s.outerHTML)})),canvas:[...e.querySelectorAll('canvas')].map(c=>({width:c.width,height:c.height,...rect(c)})),text:e.textContent.slice(0,70)}));
   return{images,plots,root:rect(root),scrollHeight:root.scrollHeight,clientHeight:root.clientHeight,overflow:document.documentElement.scrollWidth>innerWidth,animations:document.getAnimations().filter(a=>a.playState==='running').length};
  });rows.push({key:r.key,width,height,...state});
  if(['deck-question','deck-collection','deck-cleaning','story-concise-baseline','story-position','code-tokens','chart-model','chart-radar'].includes(r.key))await page.screenshot({path:`optimization/render-unification-v5/before/${r.key}-${width}.png`});
 }await page.close();}
}finally{await browser.close();await writeFile('optimization/render-unification-v5/before/render-audit.json',JSON.stringify({rows,errors},null,2)+'\n');}
console.log(JSON.stringify({states:rows.length,errors,broken:rows.flatMap(r=>r.images.filter(i=>i.visible&&(!i.complete||!i.naturalWidth||!i.w||!i.h)).map(i=>({key:r.key,width:r.width,image:i}))),badPlots:rows.flatMap(r=>r.plots.filter(p=>p.w<50||p.h<25||p.opacity==='0'||p.svgs.some(s=>s.invalid)).map(p=>({key:r.key,width:r.width,plot:p})))}));
