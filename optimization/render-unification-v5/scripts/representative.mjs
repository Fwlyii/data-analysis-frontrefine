import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {writeFile} from 'node:fs/promises';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const rows=[];
try{
 for(const [device,width,height] of [['desktop',1366,768],['mobile',390,844]]){
  const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});
  for(const [key,path] of [['question','index.html#question'],['collection','index.html#collection'],['cleaning','index.html#cleaning'],['landscape','index.html#landscape'],['findings','index.html?finding=concise#findings'],['library','explore.html?mode=explore#case-1']]){
   await page.goto('http://127.0.0.1:8788/'+path,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);
   await page.screenshot({path:`optimization/render-unification-v5/after/${key}-${device}.png`});
   rows.push(await page.evaluate(({key,device})=>({key,device,section:document.body.dataset.section,title:document.title,background:getComputedStyle(document.body).backgroundColor,overflow:document.documentElement.scrollWidth>innerWidth,headings:[...document.querySelectorAll('h1,h2')].filter(x=>x.getClientRects().length).map(x=>x.textContent)}),{key,device}));
  }await page.close();
 }
}finally{await browser.close();}
await writeFile('optimization/render-unification-v5/after/audit.json',JSON.stringify(rows,null,2));console.log(JSON.stringify({screenshots:rows.length,overflows:rows.filter(r=>r.overflow)}));
