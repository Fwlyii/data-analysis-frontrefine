import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(new URL('../tools/package.json',import.meta.url));
const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const out=resolve('optimization/homepage-pilot/after');
await mkdir(out,{recursive:true});
const checks=[];
const consoleErrors=[],httpErrors=[];
try {
  for(const width of [320,390,768,1440]) {
    const context=await browser.newContext({viewport:{width,height:900},deviceScaleFactor:1,reducedMotion:'reduce'});
    const page=await context.newPage();const requests=[];
    page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text());});
    page.on('response',response=>{if(response.status()>=400)httpErrors.push({url:response.url(),status:response.status()});});
    page.on('request',request=>requests.push(request.url()));
    await page.goto('http://127.0.0.1:8780/',{waitUntil:'networkidle'});
    const nav=await page.locator('[data-chapter]').evaluateAll(elements=>elements.map(el=>{const r=el.getBoundingClientRect();return {text:el.textContent,left:r.left,right:r.right,visible:r.left>=0&&r.right<=innerWidth};}));
    checks.push({name:`${width}px all chapter entries visible`,passed:nav.every(n=>n.visible),navigation:nav});
    const hasArt=requests.some(url=>url.includes('optical-study.webp'));
    checks.push({name:`${width}px decorative image media selection`,passed:hasArt===(width>850),hasArt});
    if(width===390) {
      await page.goto('http://127.0.0.1:8780/#limits',{waitUntil:'networkidle'});
      await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:resolve(out,'limits-mobile-full.png'),fullPage:true,animations:'disabled'});
      await page.goto('http://127.0.0.1:8780/?repairModel=qwen3&round=4#repair',{waitUntil:'networkidle'});
      await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:resolve(out,'repair-mobile-full.png'),fullPage:true,animations:'disabled'});
    }
    if(width===1440) {
      const client=await context.newCDPSession(page);await client.send('DOM.enable');await client.send('CSS.enable');
      const {root}=await client.send('DOM.getDocument');
      const fonts={};
      for(const selector of ['.finding h1','.finding .premise']) {
        const {nodeId}=await client.send('DOM.querySelector',{nodeId:root.nodeId,selector});
        fonts[selector]=(await client.send('CSS.getPlatformFontsForNode',{nodeId})).fonts;
      }
      checks.push({name:'Actual screenshot fonts recorded',passed:true,fonts});
      const alpha=await page.evaluate(async()=>{
        const image=new Image();image.src='assets/visual/optical-study.webp';await image.decode();
        const canvas=document.createElement('canvas');canvas.width=image.naturalWidth;canvas.height=image.naturalHeight;
        const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
        let transparent=0,partial=0;for(let i=3;i<data.length;i+=4){if(data[i]===0)transparent++;else if(data[i]<255)partial++;}
        return {width:canvas.width,height:canvas.height,transparentPixels:transparent,partialAlphaPixels:partial,pixels:canvas.width*canvas.height};
      });
      checks.push({name:'Independent asset retains real alpha',passed:alpha.transparentPixels>0&&alpha.partialAlphaPixels>0,...alpha});
      await page.goto('http://127.0.0.1:8780/?position=20&ci=1#position',{waitUntil:'networkidle'});
      await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:resolve(out,'position-desktop-full.png'),fullPage:true,animations:'disabled'});
      await page.goto('http://127.0.0.1:8780/explore.html?mode=explore#case-1',{waitUntil:'networkidle'});
      await page.locator('#stage .loading').waitFor({state:'detached'});
    }
    await context.close();
  }
  checks.push({name:'No console errors in homepage states and chart-library smoke check',passed:consoleErrors.length===0,consoleErrors});
  checks.push({name:'No HTTP 4xx/5xx resources in checked pages',passed:httpErrors.length===0,httpErrors});
  await writeFile(resolve(out,'extra-checks.json'),JSON.stringify({checks},null,2)+'\n');
  console.log(JSON.stringify({checks:checks.length,passed:checks.filter(c=>c.passed).length,failed:checks.filter(c=>!c.passed)}));
  if(checks.some(c=>!c.passed))process.exitCode=1;
} finally {await browser.close();}
