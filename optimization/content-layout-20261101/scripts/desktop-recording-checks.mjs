import{createRequire}from'node:module';import{resolve}from'node:path';import{writeFile}from'node:fs/promises';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core'),Axe=require('@axe-core/playwright').default;
const b=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']}),results=[],fingerprints=await collect();
const cases=[['question','?intro=0#question'],['collection','?intro=0#collection'],['cleaning','?intro=0#cleaning'],['landscape','?intro=0#landscape'],['findings','?intro=0#findings'],['library','explore.html?mode=explore&chart=model'],['code','explore.html#code'],['publication','explore.html#budget'],['discovery','explore.html#case-1']];
try{for(const[width,height]of[[1920,1080],[2560,1440]]){
 const context=await b.newContext({viewport:{width,height},reducedMotion:'reduce'}),p=await context.newPage();
 for(const[key,url]of cases){const target=new URL(url,'http://127.0.0.1:8828/');target.searchParams.set('__wideReview',key+'-'+width);await p.goto(target.href,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);
  const bounds=await p.locator('.publication-actions button,.explore-controls select,.research-home').evaluateAll(es=>es.filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return{label:e.textContent.trim(),x:r.x,right:r.right,h:r.height};}));
  const axe=await new Axe({page:p}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  const serious=axe.violations.filter(v=>['serious','critical'].includes(v.impact));const passed=!serious.length&&bounds.every(r=>r.x>=0&&r.right<=width+1&&r.h>=40);
  results.push({name:key+' '+width+' recording viewport readable actions and accessibility',passed,detail:{bounds,violations:serious.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,reason:n.failureSummary}))}))}});
  if(!passed)console.error('FAIL',key,width,JSON.stringify(results.at(-1).detail));
  await p.screenshot({path:'optimization/content-layout-20261101/after/'+key+'-'+width+'.png'});
 }await context.close();}
}finally{await b.close();await writeFile('optimization/content-layout-20261101/after/desktop-recording-checks.json',JSON.stringify({fingerprints,results},null,2)+'\n');}
console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length}));if(results.some(r=>!r.passed))process.exitCode=1;
