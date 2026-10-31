import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {spawn} from 'node:child_process';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const root=resolve('optimization/type-motion-v2/after'),frames=resolve(root,'video-frames');
await mkdir(frames,{recursive:true});
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1280,height:800},deviceScaleFactor:1,reducedMotion:'no-preference'});
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
  await session.send('Page.startScreencast',{format:'jpeg',quality:85,maxWidth:1280,maxHeight:800,everyNthFrame:1});
  await action('Cold entry',()=>page.goto(process.env.PILOT_URL||'http://127.0.0.1:8780/',{waitUntil:'networkidle'}));
  await action('Language chapter and moving navigation marker',()=>page.locator('[data-chapter="language"]').click());
  await action('Task filter',()=>page.locator('#task').selectOption('gsm8k'));
  await action('Position chapter',()=>page.locator('[data-chapter="position"]').click());
  await action('Scroll reveal of evidence',()=>page.locator('.evidence-section').evaluate(el=>el.scrollIntoView({behavior:'smooth',block:'start'})));
  await action('Return to top',()=>page.evaluate(()=>scrollTo({top:0,behavior:'smooth'})));
  await action('Repair chapter',()=>page.locator('[data-chapter="repair"]').click());
  await action('Existing repair playback with visual feedback',()=>page.locator('#play').click());
  await page.waitForTimeout(2800);
  await session.send('Page.stopScreencast');await Promise.all(writes);
} finally {await browser.close();}
let concat='';
for(let i=0;i<captures.length;i++){
  concat+=`file '${captures[i].file}'\nduration ${i+1<captures.length?Math.max(.016,captures[i+1].timestamp-captures[i].timestamp):1}\n`;
}
concat+=`file '${captures.at(-1).file}'\n`;
await writeFile(resolve(frames,'concat.txt'),concat);
await new Promise((done,fail)=>{const proc=spawn('ffmpeg',['-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',resolve(frames,'concat.txt'),'-vsync','vfr','-c:v','libx264','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',resolve(root,'motion-preview.mp4')],{stdio:'inherit'});proc.on('error',fail);proc.on('exit',code=>code===0?done():fail(new Error('ffmpeg '+code)));});
await writeFile(resolve(root,'video-manifest.json'),JSON.stringify({source:'Actual Chromium CDP screencast; no generated/interpolated frames',viewport:{width:1280,height:800},reducedMotion:'no-preference',frameCount:captures.length,seconds:captures.at(-1).timestamp-captures[0].timestamp,actions},null,2)+'\n');
console.log(JSON.stringify({frameCount:captures.length,output:'after/motion-preview.mp4'}));
