import {createRequire} from 'node:module';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {routes,root} from './inventory.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const stage=process.argv[2]||'before';
const subset=process.argv.slice(3);
const base=process.env.SITE_URL||'http://127.0.0.1:'+(stage==='before'?'8785':'8780')+'/';
const out=resolve(root,stage);await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--force-color-profile=srgb']});
const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1,reducedMotion:'reduce'});
const page=await context.newPage(),errors=[],requests=[],rows=[];
page.on('pageerror',e=>errors.push({url:page.url(),error:e.message}));
page.on('requestfailed',r=>requests.push({url:r.url(),error:r.failure()?.errorText}));
try{
 for(const route of routes.filter(r=>!subset.length||subset.includes(r.key))){
  for(const [device,width,height] of [['desktop',1440,900],['mobile',390,844]]){
   await page.setViewportSize({width,height});
   // A hash-only goto can reuse the old document without rerunning its renderer.
   // Force a fresh document and independently verify the selected view below.
   const url=new URL(route.url,base);url.searchParams.set('__visual_audit',route.key+'-'+device+'-'+Date.now());
   await page.goto(url.href,{waitUntil:'networkidle'});
   await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(180);
   await page.screenshot({path:resolve(out,route.key+'-'+device+'.png'),animations:'disabled'});
   const audit=await page.evaluate(()=>({title:document.querySelector('main h1')?.innerText,width:innerWidth,pageWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,svg:document.querySelectorAll('main svg').length,controls:document.querySelectorAll('main button,main select,main input').length,bodyFont:getComputedStyle(document.body).fontFamily,background:getComputedStyle(document.body).backgroundColor,accent:getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),header:getComputedStyle(document.querySelector('header')).height,resources:performance.getEntriesByType('resource').map(r=>({path:new URL(r.name).pathname,bytes:r.transferSize})),text:document.querySelector('main')?.innerText.slice(0,180)}));
   const selected=route.family==='discovery'?await page.locator(`#chapter-nav [data-chapter="${Number(route.key.split('-')[1])-1}"][aria-current="page"]`).count()===1:route.family==='code'?await page.locator(`[data-code-view="${route.key.slice(5)}"][aria-current="page"]`).count()===1:route.family==='library'?(await page.locator('#library-chart').inputValue())===(route.key==='chart-flow-empty'?'flow':route.key.slice(6)):true;
   rows.push({key:route.key,device,url:route.url,selectedViewMatches:selected,...audit});
  }
  console.log(route.key);
 }
 let retained=[];
 if(subset.length){try{retained=JSON.parse(await readFile(resolve(out,'page-audit.json'),'utf8')).rows.filter(row=>!subset.includes(row.key));}catch{}}
 await writeFile(resolve(out,'page-audit.json'),JSON.stringify({base,rows:[...retained,...rows],errors,failedRequests:requests},null,2)+'\n');
 console.log(JSON.stringify({screens:rows.length,overflows:rows.filter(r=>r.overflow).map(r=>r.key+'-'+r.device),errors,failedRequests:requests}));
}finally{await browser.close();}
