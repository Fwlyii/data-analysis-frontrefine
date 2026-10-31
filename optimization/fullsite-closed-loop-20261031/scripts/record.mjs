import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {spawn} from 'node:child_process';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const root=resolve('optimization/fullsite-closed-loop-20261031/after'),frames=resolve(root,'video-frames');
await mkdir(frames,{recursive:true});
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1,reducedMotion:'no-preference'});
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
  await page.goto('http://127.0.0.1:8818/?intro=0',{waitUntil:'networkidle'});
  await session.send('Page.startScreencast',{format:'jpeg',quality:85,maxWidth:1440,maxHeight:900,everyNthFrame:1});
  await action('Click real replay control',()=>page.locator('#intro-replay').click());
  await page.waitForFunction(()=>!LensIntro.inspect().running);
  await page.waitForTimeout(650);
  async function point(selector){const r=await page.locator(selector).boundingBox();await page.mouse.move(r.x+r.width/2,r.y+r.height/2);await page.waitForTimeout(450);}
  await action('Hover actual glass sphere',()=>point('#gate-collection'));
  await page.screenshot({path:resolve(root,'hover-desktop.png')});
  await action('Sphere enters the lens and opens collection design',()=>page.locator('#gate-collection').click());
  await page.waitForFunction(()=>document.body.dataset.section==='collection');
  await action('Return to the live gateway',()=>page.locator('.research-home').click());
  await point('#gate-findings');await action('Enter original findings through its sphere',()=>page.locator('#gate-findings').click());
  await page.waitForFunction(()=>document.body.dataset.section==='findings');
  await action('Use the original evidence position chapter',()=>page.locator('[data-chapter="position"]').click());
  await action('Operate the original scientific slider with End',async()=>{await page.locator('#position').focus();await page.keyboard.press('End');});
  await action('Return and replay then skip without losing the scene',async()=>{await page.locator('.research-home').click();await page.locator('#intro-replay').click();await page.waitForTimeout(1000);await page.locator('.intro-skip').click();});
  await session.send('Page.stopScreencast');await Promise.all(writes);
} finally {await browser.close();}
let concat='';
for(let i=0;i<captures.length;i++){
  concat+=`file '${captures[i].file}'\nduration ${i+1<captures.length?Math.max(.016,captures[i+1].timestamp-captures[i].timestamp):1}\n`;
}
concat+=`file '${captures.at(-1).file}'\n`;
await writeFile(resolve(frames,'concat.txt'),concat);
await new Promise((done,fail)=>{const proc=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',resolve(frames,'concat.txt'),'-vsync','vfr','-c:v','libx264','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',resolve(root,'intro-demo.mp4')],{stdio:'inherit'});proc.on('error',fail);proc.on('exit',code=>code===0?done():fail(new Error('ffmpeg '+code)));});
await writeFile(resolve(root,'video-manifest.json'),JSON.stringify({source:'Actual Chromium CDP screencast; no generated/interpolated frames',viewport:{width:1440,height:900},reducedMotion:'no-preference',frameCount:captures.length,seconds:captures.at(-1).timestamp-captures[0].timestamp,actions},null,2)+'\n');
console.log(JSON.stringify({frameCount:captures.length,output:'after/intro-demo.mp4'}));
