import {createRequire} from 'node:module';import {resolve} from 'node:path';import {readdir,readFile,writeFile} from 'node:fs/promises';import {createHash} from 'node:crypto';
import {routes,root,inspectRoute} from './inventory.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const rows=[],results=[],errors=[],failed=[];
const files=['app/index.html','app/explore.html','app/story.css','app/styles.css','app/site.css','app/deck.css','app/intro.css','app/templates/site-header.html','app/templates/deck-header.html','scripts/system/build_web_app.py',...(await readdir('app/src')).filter(x=>x.endsWith('.js')).map(x=>'app/src/'+x),'app/assets/fonts/lens-editorial-site-semibold.woff2','app/assets/fonts/lens-intro-semibold.woff2','app/assets/visual/lens-wordmark.webp','app/assets/visual/optical-study.webp','app/assets/vendor/motion-mini-14.9.0.min.js'];
const fingerprints={};for(const file of files){let b=await readFile(file);if(file.endsWith('.html'))b=Buffer.from(b.toString().replace(/\?v=[a-f0-9]+/g,'?v=BUILD'));if(file.endsWith('.css'))b=Buffer.from(b.toString().replace(/[ \t]+$/gm,''));fingerprints[file]=createHash('sha256').update(b).digest('hex');}
try{
 for(const [width,height] of [[1440,900],[390,844],[320,844],[768,960]]){
  const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});
  page.on('pageerror',e=>errors.push({url:page.url(),error:e.message}));page.on('requestfailed',r=>failed.push({url:r.url(),error:r.failure()}));
  for(const route of routes){
   const url=new URL(route.url,'http://127.0.0.1:8788/');url.searchParams.set('__review',route.key+'-'+width);await page.goto(url.href,{waitUntil:'load'});await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelector('.wordmark-logo.art-ready'));
   if(!route.section)await page.waitForFunction(()=>document.querySelector('main h1')&&document.querySelector('main svg,.chart-empty'));
   const state=await page.evaluate(inspectRoute,route);
   const passed=!!state.title&&!state.overflow&&state.selectedViewMatches&&!state.invalidValues&&state.artReady&&(route.empty?state.empty:state.svg>0)&&state.nav.length===5&&state.nav.every(n=>n.x>=0&&n.right<=width+.5)&&state.background==='rgb(244, 248, 250)'&&state.accent==='#147b7b'&&(!state.activeScroll||state.activeScroll.content<=state.activeScroll.width+1);
   results.push({name:route.key+' '+width+'px layout/current view',passed,detail:state});if(!passed)console.error('FAIL',route.key,width,JSON.stringify(state));
   if(width===1440||width===390){const device=width===1440?'desktop':'mobile';await page.screenshot({path:resolve(root,'after',route.key+'-'+device+'.png')});rows.push({key:route.key,device,url:route.url,...state});}
  }
  console.log(JSON.stringify({completedWidth:width,routes:routes.length,failures:results.filter(r=>!r.passed).length}));await page.close();
 }
 results.push({name:'No uncaught browser errors',passed:!errors.length,detail:errors},{name:'No failed resources',passed:!failed.length,detail:failed});
}finally{await browser.close();await writeFile(resolve(root,'after/page-audit.json'),JSON.stringify({rows,errors,failedRequests:failed},null,2)+'\n');await writeFile(resolve(root,'after/site-checks.json'),JSON.stringify({matrix:{routes:routes.map(r=>r.key),viewports:[320,390,768,1440]},fingerprints,results,errors,failedRequests:failed},null,2)+'\n');}
console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed).map(r=>r.name)}));if(results.some(r=>!r.passed))process.exitCode=1;
