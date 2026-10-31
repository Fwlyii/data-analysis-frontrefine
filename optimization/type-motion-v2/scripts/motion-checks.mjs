import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require = createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium} = require('playwright-core');
const root = resolve('optimization/type-motion-v2/after');
await mkdir(root, {recursive:true});
const base = process.env.PILOT_URL || 'http://127.0.0.1:8780/';
const browser = await chromium.launch({executablePath:'/snap/bin/chromium', headless:true, args:['--no-sandbox','--disable-dev-shm-usage']});
const results = [], errors = [], fonts = [];
function check(name, passed, detail) {results.push({name,passed,detail});if(!passed) console.error('FAIL',name,detail);}
async function sample(page) {
  return page.evaluate(()=>({
    ...window.LensMotionUI.inspect(),
    animations:document.getAnimations().filter(a=>a.playState==='running').length,
    titleTransform:getComputedStyle(document.querySelector('h1')).transform,
    plotTransform:getComputedStyle(document.querySelector('#plot')).transform,
    title:document.querySelector('h1').innerText,
    opacity:getComputedStyle(document.querySelector('.premise')).opacity,
    pageWidth:document.documentElement.scrollWidth,
    width:innerWidth
  }));
}
try {
  for(const reducedMotion of ['no-preference','reduce']) {
    const context = await browser.newContext({viewport:{width:1440,height:900},reducedMotion});
    const page = await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);
    check(`${reducedMotion}: decoded generated wordmark`,await page.locator('.wordmark-logo').evaluate(el=>el.classList.contains('art-ready')));
    const session = await context.newCDPSession(page);await session.send('DOM.enable');await session.send('CSS.enable');
    for(const chapter of ['concise','language','limits','position','repair']) {
      await page.locator(`[data-chapter="${chapter}"]`).click();
      const state = await sample(page);
      check(`${reducedMotion}: ${chapter} ${reducedMotion==='reduce'?'has no running animations':'has real browser animation'}`,reducedMotion==='reduce'?state.animations===0:state.animations>0,state);
      await page.evaluate(()=>document.fonts.ready);
      const {root:doc}=await session.send('DOM.getDocument');
      const {nodeId}=await session.send('DOM.querySelector',{nodeId:doc.nodeId,selector:'.finding h1'});
      const used=await session.send('CSS.getPlatformFontsForNode',{nodeId});
      fonts.push({mode:reducedMotion,chapter,...used});
      check(`${reducedMotion}: ${chapter} uses downloaded title font`,used.fonts.length>0&&used.fonts.every(font=>font.isCustomFont&&font.familyName==='LENS Editorial'),used.fonts);
      await page.waitForTimeout(720);
      const ended=await sample(page);
      check(`${reducedMotion}: ${chapter} settles`,ended.running===0&&ended.animations===0&&ended.opacity==='1',ended);
    }
    await page.locator('[data-chapter="language"]').click();
    await page.locator('#task').selectOption('gsm8k');
    const changed = await sample(page);
    check(`${reducedMotion}: filter feedback`,reducedMotion==='reduce'?changed.animations===0:changed.animations>0,changed);
    await page.waitForTimeout(720);
    // Rapid input uses the same live navigation and renderer as user interaction.
    await page.evaluate(()=>{for(let n=0;n<12;n++)document.querySelector(`[data-chapter="${['concise','language','limits','position','repair'][n%5]}"]`).click();});
    await page.waitForTimeout(800);
    const rapid=await sample(page);
    check(`${reducedMotion}: rapid switching releases animations`,rapid.running===0&&rapid.animations===0,rapid);
    check(`${reducedMotion}: final route remains correct`,new URL(page.url()).hash==='#language'&&rapid.title.includes('中文'),page.url());
    for(const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:900});await page.waitForTimeout(50);
      const marker=await page.evaluate(()=>{const a=document.querySelector('.chapter-nav [aria-current="page"]'),m=document.querySelector('.nav-marker');return{actual:m.getBoundingClientRect().left,expected:a.getBoundingClientRect().left+parseFloat(getComputedStyle(a).paddingLeft),overflow:document.documentElement.scrollWidth>innerWidth};});
      check(`${reducedMotion}: ${width}px underline alignment`,Math.abs(marker.actual-marker.expected)<1&&!marker.overflow,marker);
    }
    if(reducedMotion==='no-preference') {
      await page.locator('[data-chapter="repair"]').click();
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.waitForTimeout(100);
      const switched=await sample(page);
      check('Preference change stops active animations',switched.running===0&&switched.animations===0&&switched.opacity==='1',switched);
    }
    await context.close();
  }
  const context=await browser.newContext({reducedMotion:'reduce'});
  await context.route('**/lens-wordmark.webp',route=>route.abort());
  const page=await context.newPage();await page.goto(base,{waitUntil:'networkidle'});
  check('Generated image failure retains native brand',await page.locator('.wordmark-logo strong').evaluate(el=>getComputedStyle(el).opacity==='1'&&el.innerText==='LENS.'));
  check('Generated image failure retains working chart',await page.locator('#plot svg').count()===1);
  await context.close();
  check('No uncaught browser errors',errors.length===0,errors);
} finally {
  await writeFile(resolve(root,'motion-checks.json'),JSON.stringify({base,results,fonts,errors},null,2)+'\n');
  await browser.close();
}
console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed)}));
if(results.some(r=>!r.passed))process.exitCode=1;
