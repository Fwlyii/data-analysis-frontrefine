import{createRequire}from'node:module';import{resolve}from'node:path';import{writeFile}from'node:fs/promises';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core');const b=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox']});const results=[],fingerprints=await collect();
try{for(const width of[320,390,768,1366,1440]){
 const p=await b.newPage({viewport:{width,height:900},reducedMotion:'reduce'});await p.goto('http://127.0.0.1:8838/explore.html?mode=explore',{waitUntil:'networkidle'});
 for(const id of['overview-mode','position-mode','code-mode','demo-mode','explore-mode']){
  await p.locator('#'+id).focus();await p.waitForTimeout(80);const state=await p.locator('#'+id).evaluate(e=>{const r=e.getBoundingClientRect(),n=e.closest('nav').getBoundingClientRect();return{x:r.x,right:r.right,navLeft:n.x,navRight:n.right,focused:document.activeElement===e,font:parseFloat(getComputedStyle(e).fontSize)};});
  const passed=state.focused&&state.x>=Math.max(0,state.navLeft)-1&&state.right<=Math.min(width,state.navRight)+1&&state.font>=14;
  results.push({name:width+' readable native navigation focuses and scrolls '+id,passed,detail:state});if(!passed)console.error('FAIL',width,id,state);
 }await p.close();}
}finally{await b.close();await writeFile('optimization/color-unification-20261101/after/nav-access-checks.json',JSON.stringify({fingerprints,results},null,2)+'\n');}console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length}));if(results.some(r=>!r.passed))process.exitCode=1;
