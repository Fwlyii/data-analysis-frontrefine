import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {spawn} from 'node:child_process';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const root=resolve('optimization/color-unification-20261101/after'),frames=resolve(root,'video-frames');
await mkdir(frames,{recursive:true});
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,reducedMotion:'no-preference'});
const page=await context.newPage(),session=await context.newCDPSession(page);
const captures=[],writes=[],actions=[];
session.on('Page.screencastFrame',event=>{
  const file=resolve(frames,String(captures.length).padStart(5,'0')+'.jpg');
  captures.push({file,timestamp:event.metadata.timestamp});
  writes.push(writeFile(file,Buffer.from(event.data,'base64')));
  session.send('Page.screencastFrameAck',{sessionId:event.sessionId}).catch(()=>{});
});
async function action(label,fn){actions.push({label,at:Date.now()});await fn();await page.waitForTimeout(900);}
try {
  await page.goto('http://127.0.0.1:8838/?intro=0',{waitUntil:'networkidle'});
  await session.send('Page.startScreencast',{format:'jpeg',quality:90,maxWidth:1920,maxHeight:1080,everyNthFrame:1});
  await action('Replay the actual opening',()=>page.locator('#intro-replay').click());
  await page.waitForFunction(()=>!LensIntro.inspect().running);await page.waitForTimeout(600);
  async function point(selector){const r=await page.locator(selector).boundingBox();await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.waitForTimeout(300);}
  async function enter(route,label,hold=1500){
    if(await page.evaluate(()=>document.body.dataset.section!=='gateway'))await page.locator('.research-home').click();
    await point('#gate-'+route);actions.push({label,at:Date.now()});await page.locator('#gate-'+route).click();
    await page.waitForFunction(route=>document.body.dataset.section===route,route);await page.waitForTimeout(hold);
  }
  await enter('question','Read the redesigned research-question composition',2200);
  await enter('collection','Show principles, experiment flow and task cohorts',1800);
  await enter('cleaning','Show the code specimen, process and quality summary',1800);
  await enter('landscape','Compare actual task and model evidence',1600);
  await action('Switch the original scientific matrix',()=>page.locator('[data-overview-view="heatmap"]').click());
  await enter('findings','Read the conclusion and evidence callout',1500);
  await action('Open the original evidence-position finding',()=>page.locator('[data-chapter="position"]').click());
  await action('Use the actual evidence-position slider',async()=>{await page.locator('#position').focus();await page.keyboard.press('End');});
  await action('Read the expanded real example',async()=>{await page.locator('#actual-example>summary').click();await page.locator('#actual-example').scrollIntoViewIfNeeded();});
  await page.locator('.research-home').click();await page.locator('.topbar-actions a').click();await page.waitForLoadState('networkidle');
  await page.locator('#library-main svg').waitFor();await page.waitForTimeout(1500);actions.push({label:'Read the large chart-library filters with the original scientific graph',at:Date.now()});
  await action('Open code-generation research',()=>page.locator('#code-mode').click());
  await action('Switch to the actual output-cost view',()=>page.locator('[data-code-view="tokens"]').click());
  await action('Open the original output-efficiency publication',()=>page.locator('#overview-mode').click());
  await action('Show the redesigned discovery KPI layout',()=>page.locator('#demo-mode').click());
  await action('Return to the entrance without replaying automatically',async()=>{await page.locator('.story-home').click();await page.waitForLoadState('networkidle');});
  await session.send('Page.stopScreencast');await Promise.all(writes);
} finally {await browser.close();}
let concat='';
for(let i=0;i<captures.length;i++){
  concat+=`file '${captures[i].file}'\nduration ${i+1<captures.length?Math.max(.016,captures[i+1].timestamp-captures[i].timestamp):1}\n`;
}
concat+=`file '${captures.at(-1).file}'\n`;
await writeFile(resolve(frames,'concat.txt'),concat);
await new Promise((done,fail)=>{const proc=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',resolve(frames,'concat.txt'),'-vsync','vfr','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',resolve(root,'intro-demo.mp4')],{stdio:'inherit'});proc.on('error',fail);proc.on('exit',code=>code===0?done():fail(new Error('ffmpeg '+code)));});
await writeFile(resolve(root,'video-manifest.json'),JSON.stringify({source:'Actual Chromium CDP screencast; no generated/interpolated frames',viewport:{width:1920,height:1080},reducedMotion:'no-preference',frameCount:captures.length,seconds:captures.at(-1).timestamp-captures[0].timestamp,actions},null,2)+'\n');
console.log(JSON.stringify({frameCount:captures.length,output:'after/intro-demo.mp4'}));
