import{createRequire}from'node:module';import{resolve}from'node:path';import{writeFile,stat}from'node:fs/promises';import{fingerprints as collect}from'./source-fingerprints.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
const fingerprints=await collect(),results=[],errors=[],base='http://127.0.0.1:8838/';
const check=(name,passed,detail)=>{results.push({name,passed:!!passed,detail});if(!passed)console.error('FAIL',name,JSON.stringify(detail));};
try{
 for(const width of[1440,1366,768,390,320]){
  const context=await browser.newContext({viewport:{width,height:width===1366?768:width===768?960:width===1440?900:width===390?844:740},reducedMotion:'reduce'}),page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'?intro=0',{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);
  check(width+' generated atmosphere decodes behind native interactive text',await page.evaluate(async()=>{const img=document.querySelector('.gate-atmosphere');await img.decode();return img.complete&&img.naturalWidth>=1000&&img.alt===''&&img.closest('[aria-hidden=true]')&&document.querySelectorAll('.gate-orb[href]').length===5&&[...document.querySelectorAll('.orb-title')].every(e=>e.textContent.trim().length>0);}));
  check(width+' captions remain inside the viewport and clear of footer',await page.evaluate(()=>{const footer=document.querySelector('.gate-foot').getBoundingClientRect();return[...document.querySelectorAll('.orb-title,.orb-description,.orb-english')].filter(e=>e.getClientRects().length).every(e=>{const range=document.createRange();range.selectNodeContents(e);const r=range.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=footer.top;});}));
  if(width<700)check(width+' mobile presents five separated touch rows',await page.evaluate(()=>{const r=[...document.querySelectorAll('.gate-orb')].map(e=>e.getBoundingClientRect());return r.every((a,i)=>a.width>240&&a.height>=70&&(!i||a.top>=r[i-1].bottom+8));}));
  await context.route('**/gateway-atmosphere.webp',route=>route.abort());await page.reload({waitUntil:'networkidle'});
  await page.locator('#gate-collection').click();await page.waitForFunction(()=>document.body.dataset.section==='collection');
  check(width+' image delivery failure leaves native navigation and full-screen research usable',await page.evaluate(()=>{const r=document.querySelector('#collection').getBoundingClientRect();return r.x===0&&r.y===0&&r.width===innerWidth&&r.height===innerHeight&&!!document.querySelector('#collection-title')&&getComputedStyle(document.querySelector('.research-home')).display!=='none';}));await context.close();
 }
 for(const width of[1440,390]){
  const context=await browser.newContext({viewport:{width,height:width===1440?900:844},reducedMotion:'no-preference'}),page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'?intro=1',{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>window.LensIntro?.inspect().elapsed>=3500);
  const tones=await page.locator('.gate-orb').evaluateAll(nodes=>nodes.map(e=>getComputedStyle(e).getPropertyValue('--tone').trim()));
  await page.waitForFunction(()=>!LensIntro.inspect().running);
  check(width+' five individual glass tints survive opening reparenting',await page.locator('.gate-orb').evaluateAll((nodes,tones)=>new Set(tones).size===5&&nodes.every((e,i)=>getComputedStyle(e).getPropertyValue('--tone').trim()===tones[i]),tones));
  const tone=await page.locator('#gate-collection').evaluate(e=>getComputedStyle(e).getPropertyValue('--tone').trim());
  const r=await page.locator('#gate-collection').boundingBox();await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.waitForTimeout(400);await page.locator('#gate-collection').click();await page.waitForTimeout(100);
  check(width+' selected glass retains its color during focus flight',await page.locator('.gate-flight-layer #gate-collection').evaluate((e,tone)=>getComputedStyle(e).getPropertyValue('--tone').trim()===tone,tone));await page.waitForFunction(()=>document.body.dataset.section==='collection');
  await page.screenshot({path:`optimization/color-unification-20261101/after/fullscreen-collection-${width}.png`});await context.close();
 }
 check('Generated runtime atmosphere remains below 50 KiB',(await stat('app/assets/visual/gateway-atmosphere.webp')).size<50*1024);
 check('No uncaught optical review errors',!errors.length,errors);
}catch(e){check('Optical review completed',false,e.stack);}finally{await browser.close();await writeFile('optimization/color-unification-20261101/after/optical-checks.json',JSON.stringify({fingerprints,results,errors},null,2)+'\n');}
console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed)}));if(results.some(r=>!r.passed))process.exitCode=1;
