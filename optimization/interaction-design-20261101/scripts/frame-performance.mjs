import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const profiles=[{width:1440,height:900},{width:1920,height:1080},{width:2560,height:1440},{width:1366,height:768},{width:1920,height:1080,dpr:2},{width:1920,height:1080,cpu:4}],runs=[];
try{
 for(const profile of profiles){
  const context=await browser.newContext({viewport:{width:profile.width,height:profile.height},deviceScaleFactor:profile.dpr||1,reducedMotion:'no-preference'}),page=await context.newPage();
  if(profile.cpu){const session=await context.newCDPSession(page);await session.send('Emulation.setCPUThrottlingRate',{rate:profile.cpu});}
  await page.goto('http://127.0.0.1:8838/?intro=1',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>!!document.querySelector('#plot svg'));
  const dataReady=await page.evaluate(()=>({elapsed:LensIntro.inspect().elapsed,introRunning:LensIntro.inspect().running}));
  await page.waitForFunction(()=>LensIntro.inspect().history.length>0&&!LensIntro.inspect().running);
  const state=await page.evaluate(()=>LensIntro.inspect());
  runs.push({profile,dataReady,run:state.history.at(-1),idlePixels:state.canvasPixels,idleRAF:state.raf});console.log(JSON.stringify(runs.at(-1)));
  await context.close();
 }
}finally{await browser.close();}
await writeFile(resolve('optimization/interaction-design-20261101/after/frame-performance.json'),JSON.stringify({method:'Six sequential real-time browser playbacks, no screenshots or screencast during measurement. Headless Chromium on this host; viewport/DPR/CPU emulation does not establish real hardware GPU performance. FPS is measured draw intervals; draw cost is JavaScript scene work and excludes GPU/compositor cost.',runs},null,2)+'\n');
