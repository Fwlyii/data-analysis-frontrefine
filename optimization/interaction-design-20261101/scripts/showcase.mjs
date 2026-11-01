import{createRequire}from'node:module';import{resolve}from'node:path';import{writeFile}from'node:fs/promises';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core');const b=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox']});const root=resolve('optimization/interaction-design-20261101/after'),fingerprints=await collect(),results=[];
try{for(const[width,height]of[[1440,900],[1920,1080]]){const p=await b.newPage({viewport:{width,height},reducedMotion:'reduce'});
 for(const[route,selector,name]of[
 ['?intro=0#question','#question .ix-card-hit','question-selected'],
 ['?intro=0#collection','#collection .task-row .ix-card-hit','collection-selected'],
 ['?intro=0#cleaning','#cleaning .cleaning-steps li:nth-child(3) .ix-card-hit','pipeline-selected'],
 ['?intro=0&finding=concise#findings','#findings [data-ix-guide]','findings-guide'],
 ['explore.html?mode=explore&chart=heatmap','#stage [data-ix-guide]','library-guide'],
 ['explore.html?codeView=tokens#code','#stage [data-ix-focus]','code-focus']]){
 const u=new URL(route,'http://127.0.0.1:8838/');u.searchParams.set('__showcase',name);await p.goto(u.href,{waitUntil:'networkidle'});await p.evaluate(()=>document.fonts.ready);if(name==='code-focus')await p.waitForFunction(()=>document.querySelector('#code-vega-scatter svg')&&document.querySelector('#code-linked-errors svg'));
 await p.locator(selector).first().click();await p.waitForTimeout(100);await p.evaluate(()=>{window.scrollTo(0,0);const p=document.querySelector('.deck-panel.is-active');if(p)p.scrollTop=0;});await p.screenshot({path:resolve(root,name+'-'+width+'.png')});
 const state=await p.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,key:LensInteractions.inspect().key,focus:LensInteractions.inspect().focus}));results.push({name:name+' '+width+' actual expanded-state capture',passed:!state.overflow,detail:state});
 }await p.close();}}finally{await b.close();await writeFile(resolve(root,'showcase-checks.json'),JSON.stringify({fingerprints,results},null,2)+'\n');}console.log({checks:results.length,passed:results.filter(r=>r.passed).length});if(results.some(r=>!r.passed))process.exitCode=1;
