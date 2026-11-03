import {baseURL,chromiumPath} from './helpers.mjs';
import {routes} from './inventory.mjs';
import {fingerprints as collect} from './source-fingerprints.mjs';
import {createRequire} from 'node:module';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const require=createRequire(resolve('tests/package.json')),{chromium}=require('playwright-core');
const fingerprints=await collect(),before=process.env.MOTION_BASE_URL||'http://127.0.0.1:8770/';
const originalScience=JSON.parse(await readFile('tests/fixtures/scientific-comparison.json','utf8')).results;
const out=resolve('artifacts/motion-audit');await mkdir(out,{recursive:true});
const b=await chromium.launch({executablePath:chromiumPath,downloadsPath:resolve('artifacts/qa/downloads'),args:['--no-sandbox','--disable-dev-shm-usage']});
const results=[],errors=[],exportResults=[],normalResults=[];
const sha=s=>createHash('sha256').update(s).digest('hex');
const check=(name,passed,detail={})=>{const r={name,passed:!!passed,...detail};if(!passed)console.error('FAIL',name,JSON.stringify(detail));return r;};
async function page(width,motion){const p=await b.newPage({viewport:{width,height:width===1920?1080:900},reducedMotion:motion,acceptDownloads:true});p.on('pageerror',e=>errors.push({url:p.url(),error:e.message}));return p;}
async function open(p,base,route){
 // Each scientific fixture must start from its URL defaults. Hash-only goto can
 // retain a previous chapter's live controls rather than restoring a fresh route.
 await p.goto('about:blank');
 await p.goto(new URL(route.url||route,base).href,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);await p.waitForFunction(()=>!!window.LensInteractions);
 if((route.url||route).includes('chart=box'))await p.waitForSelector('.boxlayer path');
 if((route.url||route).includes('codeView=tokens'))await p.waitForSelector('#code-vega-scatter svg');
 if(route.key){const device=p.viewportSize().width===1920?'fullhd':'desktop',expected=originalScience.find(r=>r.name.startsWith(route.key+' '+device+' '))?.expectedGraphs;if(expected!=null)await p.waitForFunction(expected=>{const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');return [...root.querySelectorAll('svg')].filter(n=>!n.parentElement.closest('svg')&&n.getBoundingClientRect().width>=150).length===expected;},expected);}
 await p.waitForFunction(()=>[...document.querySelectorAll('#stage .chart')].every(e=>{const c=window.echarts?.getInstanceByDom(e);return !c||c.isDisposed()||c.getZr().animation.isFinished();}));
}
function normalizeSVG(s){
 // Renderer IDs are nondeterministic; preserve every path, number, attribute and text.
 const ids=[...s.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);for(const [i,id]of ids.entries())s=s.split(id).join('canonical-id-'+i);
 return s.replace(/zr\d+-(cls|pr)\d+/g,'zr-$1').replace(/trace[0-9a-f]{6}/g,'trace-id');
}
async function graphs(p){return p.evaluate(async()=>{
 const root=document.querySelector('.deck-panel.is-active')||document.querySelector('#stage');
 const svgs=[...root.querySelectorAll('svg')].filter(n=>!n.parentElement.closest('svg')&&n.getBoundingClientRect().width>=150);
 const keys=['font-family','font-size','font-weight','fill','fill-opacity','stroke','stroke-width','stroke-opacity','stroke-dasharray','opacity','visibility','text-anchor','dominant-baseline'];
 const hash=async data=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');
 const result=[];
 for(const svg of svgs){
  const r=svg.getBoundingClientRect(),copy=svg.cloneNode(true),styles=[];
  const original=[svg,...svg.querySelectorAll('*')],clones=[copy,...copy.querySelectorAll('*')];
  for(let i=0;i<original.length;i++){
   const style=getComputedStyle(original[i]),values=Object.fromEntries(keys.map(k=>[k,style.getPropertyValue(k)]));styles.push(values);
   for(const[k,v]of Object.entries(values))clones[i].style.setProperty(k,v.replace(/url\(["']?[^#)]*#([^"')]+)["']?\)/g,'url(#$1)'));
  }
  const width=Math.ceil(r.width),height=Math.ceil(r.height);copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.setAttribute('width',width);copy.setAttribute('height',height);
  const image=new Image(),url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml'}));image.src=url;await image.decode();
  const canvas=document.createElement('canvas');canvas.width=width;canvas.height=height;const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,width,height);URL.revokeObjectURL(url);
  result.push({markup:svg.outerHTML,styles,pixels:await hash(ctx.getImageData(0,0,width,height).data),width:r.width,height:r.height,x:r.x,y:r.y});
 }
 return result;
});}
try{
 const wanted=process.env.MOTION_EXPORT_KEYS?[]:routes.filter(r=>r.section!=='gateway'&&(!process.env.MOTION_SCIENCE_KEYS||process.env.MOTION_SCIENCE_KEYS.split(',').includes(r.key)));
 for(const width of[1440,1920]){
  const a=await page(width,'reduce'),p=await page(width,'reduce');
  for(const route of wanted){
   await open(a,before,route);await open(p,baseURL,route);
   const old=await graphs(a),now=await graphs(p);
   const comparisons=old.map((g,i)=>{const v=now[i];return{sameMarkup:!!v&&normalizeSVG(g.markup)===normalizeSVG(v.markup),sameStyles:!!v&&JSON.stringify(g.styles)===JSON.stringify(v.styles),sameCanonicalPixels:!!v&&g.pixels===v.pixels,sameBounds:!!v&&['x','y','width','height'].every(k=>Math.abs(g[k]-v[k])<.25),pixels:[g.pixels,v?.pixels],dimensions:[g.width,g.height,v?.width,v?.height]};});
   const passed=old.length===now.length&&comparisons.every(g=>g.sameMarkup&&g.sameStyles&&g.sameCanonicalPixels&&g.sameBounds);
   results.push(check(route.key+' '+width+' scientific preservation',passed,{key:route.key,width,expectedGraphs:old.length,actualGraphs:now.length,graphs:comparisons}));
   if(!passed){await writeFile(resolve(out,route.key+'-'+width+'-before.json'),JSON.stringify(old));await writeFile(resolve(out,route.key+'-'+width+'-after.json'),JSON.stringify(now));}
   console.log('science',width,route.key,passed?'PASS':'FAIL');
  }
  await a.close();await p.close();
 }
 // Verify final endpoints after real normal-motion draws, not only the reduced path.
 const a=await page(1920,'reduce'),p=await page(1920,'no-preference');
 for(const route of routes.filter(r=>!process.env.MOTION_EXPORT_KEYS&&r.chart&&!r.empty)){
  await open(a,before,route);await open(p,baseURL,route);await p.waitForTimeout(1250);
  const old=await graphs(a),now=await graphs(p);
  const detail=old.map((g,i)=>({sameMarkup:!!now[i]&&normalizeSVG(g.markup)===normalizeSVG(now[i].markup),sameStyles:!!now[i]&&JSON.stringify(g.styles)===JSON.stringify(now[i].styles),sameCanonicalPixels:!!now[i]&&g.pixels===now[i].pixels}));
  const pass=old.length===now.length&&detail.every(g=>g.sameMarkup&&g.sameStyles&&g.sameCanonicalPixels);
  normalResults.push(check(route.key+' normal final geometry/style/pixels',pass,{graphs:detail}));
  if(!pass){await writeFile(resolve(out,route.key+'-normal-before.json'),JSON.stringify(old));await writeFile(resolve(out,route.key+'-normal-after.json'),JSON.stringify(now));}
 }
 // Actual downloads from both live versions, including export during motion/selection.
 const fixtures=JSON.parse(await readFile('tests/fixtures/export-comparison.json','utf8')).results.filter(r=>!process.env.MOTION_EXPORT_KEYS||process.env.MOTION_EXPORT_KEYS.split(',').includes(r.name.split(' ')[0]));
 for(const fixture of fixtures){
  const kind=fixture.name.includes(' csv ')?'csv':'svg',key=fixture.name.split(' ')[0],files=[];
  for(const [base,page]of[[before,a],[baseURL,p]]){
   await open(page,base,fixture.route);
   let selector;
   if(fixture.route.startsWith('index')){await page.locator('.export-menu summary').click();selector='#download-'+kind;}
   else if(fixture.route.includes('#code'))selector='[data-code-action="svg"]';
   else if(fixture.route.includes('#budget')||fixture.route.includes('#position'))selector='[data-action="export-publication"]';
   else selector='[data-action="export-chart"]';
   if(base===baseURL)await page.evaluate(()=>{
    const host=document.querySelector('#library-main,#plot,#publication-root');
    if(host){host.focus({preventScroll:true});host.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));}
    const codePoint=document.querySelector('#code-publication [data-code-model]');codePoint?.dispatchEvent(new PointerEvent('pointerenter',{bubbles:false}));
    window.LensChartMotion?.beforeExport();
   });
   const wait=page.waitForEvent('download');await page.locator(selector).click();const download=await wait,file=resolve(out,key+'-'+(base===before?'main':'motion')+'.'+kind);await download.saveAs(file);files.push(await readFile(file,'utf8'));
  }
  const same=kind==='csv'?files[0]===files[1]:normalizeSVG(files[0])===normalizeSVG(files[1]);
  exportResults.push(check(fixture.name,same,{route:fixture.route,format:kind,hashes:files.map(sha)}));console.log('export',key,kind,same?'PASS':'FAIL');
 }
 await a.close();await p.close();
}catch(e){results.push(check('Scientific audit completes',false,{error:e.stack}));console.error(e.stack);}finally{
 await b.close();await writeFile(resolve(out,'science.json'),JSON.stringify({baseline:'7de85e836e8bc0f7c28c79188b71f1818c0aa234',fingerprints,base:baseURL,before,results,normalResults,exports:exportResults,errors},null,2)+'\n');
}
console.log(JSON.stringify({science:results.length,graphs:results.reduce((n,r)=>n+(r.actualGraphs||0),0),failed:[...results,...normalResults,...exportResults].filter(r=>!r.passed).map(r=>r.name),normal:normalResults.length,exports:exportResults.length,errors}));if([...results,...normalResults,...exportResults].some(r=>!r.passed)||errors.length)process.exitCode=1;
