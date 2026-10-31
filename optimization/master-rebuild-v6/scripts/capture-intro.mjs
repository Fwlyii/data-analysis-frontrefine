import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const stage=process.argv[2]||'iterations/round-1',width=+(process.argv[3]||1440);
const height=width===1440?900:width===768?1024:width===390?844:740;
const out=resolve('optimization/master-rebuild-v6',stage);await mkdir(out,{recursive:true});
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,reducedMotion:'no-preference'});
const page=await context.newPage(),errors=[],captures=[];page.on('pageerror',e=>errors.push(e.message));
const cdp=await context.newCDPSession(page);
try{
 await page.goto('http://127.0.0.1:8788/?intro=1',{waitUntil:'domcontentloaded'});
 for(const [label,time] of [['awakening',450],['flow',1500],['lens',2700],['insights',3500],['brand',4800],['transfer',5530]]){
  await page.waitForFunction(time=>window.LensIntro?.inspect().elapsed>=time,time);
  const shot=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await writeFile(resolve(out,`${width}-${label}.png`),Buffer.from(shot.data,'base64'));
  const sample={width,label,targetMilliseconds:time,stateAfterScreenshot:await page.evaluate(()=>{const s=LensIntro.inspect();return{elapsed:s.elapsed,phase:s.phase,running:s.running,error:s.error};})};captures.push(sample);console.log(JSON.stringify(sample));
 }
 await page.waitForFunction(()=>window.LensIntro&&!LensIntro.inspect().running);
 await page.screenshot({path:resolve(out,`${width}-complete.png`)});
 const state=await page.evaluate(()=>({intro:LensIntro.inspect(),svg:!!document.querySelector('#plot svg'),introLocked:document.documentElement.classList.contains('intro-active'),inert:document.querySelectorAll('[data-intro-inert]').length,overflow:document.documentElement.scrollWidth>innerWidth,focus:document.activeElement.id,resources:performance.getEntriesByType('resource').map(r=>new URL(r.name).pathname)}));
 await writeFile(resolve(out,`${width}-capture.json`),JSON.stringify({state,errors,captures},null,2)+'\n');console.log(JSON.stringify({width,errors,state:state.intro.history.at(-1),overflow:state.overflow}));
}finally{await browser.close();}
