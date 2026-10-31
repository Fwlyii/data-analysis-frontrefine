import {createRequire} from 'node:module';
import {mkdir, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require = createRequire(new URL('../tools/package.json', import.meta.url));
const {chromium} = require('playwright-core');
const AxeBuilder = require('@axe-core/playwright').default;
const mode = process.argv[2] || 'capture';
const label = process.argv[3] || 'before';
const base = process.env.PILOT_URL || 'http://127.0.0.1:8780';
const output = resolve('optimization/homepage-pilot', label);
await mkdir(output, {recursive: true});
const downloadsPath = '/home/codex/snap/chromium/common/lens-pilot-downloads';
await mkdir(downloadsPath, {recursive:true});
const browser = await chromium.launch({executablePath: '/snap/bin/chromium', headless: true, downloadsPath, args: ['--no-sandbox', '--disable-dev-shm-usage', '--force-color-profile=srgb']});
const errors = [], failedRequests = [], results = [];
const context = await browser.newContext({viewport: {width:1440, height:900}, deviceScaleFactor:1, reducedMotion:'reduce', acceptDownloads:true});
const page = await context.newPage();
page.on('pageerror', error=>errors.push(error.message));
page.on('requestfailed', request=>failedRequests.push({url:request.url(), error:request.failure()?.errorText}));
async function open(route='') {
  await page.goto(base+'/'+route, {waitUntil:'networkidle'});
  await page.locator('#plot svg').waitFor();
  await page.evaluate(()=>document.fonts.ready);
}
async function geometry() {
  return page.evaluate(()=>({
    viewport:{width:innerWidth,height:innerHeight},
    pageWidth:document.documentElement.scrollWidth,
    horizontalOverflow:document.documentElement.scrollWidth>innerWidth,
    sections:[...document.querySelectorAll('.masthead,.chapter-nav,.finding,.figure-sheet,.evidence-section,.support-section,.page-footer')].map(el=>{
      const r=el.getBoundingClientRect(),c=getComputedStyle(el);
      return {className:el.className,x:r.x,y:r.y,width:r.width,height:r.height,font:c.fontFamily,fontSize:c.fontSize,color:c.color,background:c.backgroundColor};
    }),
    heading:document.querySelector('h1')?.innerText,
    navigation:[...document.querySelectorAll('[data-chapter]')].map(el=>({text:el.textContent,href:el.getAttribute('href')})),
    buttonLabels:[...document.querySelectorAll('button')].map(el=>el.getAttribute('aria-label')||el.textContent.trim()),
    tableText:document.querySelector('#actual-example table')?.innerText,
    images:[...document.images].map(el=>({src:el.getAttribute('src'),width:el.naturalWidth,height:el.naturalHeight})),
    plotSVGCount:document.querySelectorAll('#plot svg').length,
    resources:performance.getEntriesByType('resource').map(r=>({name:new URL(r.name).pathname,bytes:r.transferSize,duration:r.duration})),
    domNodes:document.querySelectorAll('*').length,
    navigationTiming:performance.getEntriesByType('navigation').map(n=>({domContentLoaded:n.domContentLoadedEventEnd,load:n.loadEventEnd,bytes:n.transferSize}))
  }));
}
try {
  if(mode==='capture') {
    for(const [name,viewport] of [['desktop',{width:1440,height:900}],['mobile',{width:390,height:844}]]) {
      await page.setViewportSize(viewport);await open();
      await page.screenshot({path:resolve(output,name+'.png'),animations:'disabled'});
      await page.screenshot({path:resolve(output,name+'-full.png'),fullPage:true,animations:'disabled'});
      results.push({name,...await geometry()});
    }
    await writeFile(resolve(output,'page-audit.json'),JSON.stringify({results,errors,failedRequests},null,2)+'\n');
    console.log(JSON.stringify({mode,label,errors,failedRequests,viewports:results.map(r=>({name:r.name,overflow:r.horizontalOverflow,nodes:r.domNodes}))}));
  } else if(mode==='regression') {
    const check=(name,passed,detail)=>{results.push({name,passed,detail});if(!passed)console.error('FAIL',name,detail)};
    for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:740},{width:768,height:1024}]) {
      await page.setViewportSize(viewport);
      for(const chapter of ['concise','language','limits','position','repair']) {
        await open('#'+chapter);const g=await geometry();
        check(`${viewport.width}px ${chapter}: native SVG`,g.plotSVGCount===1);
        check(`${viewport.width}px ${chapter}: no page overflow`,!g.horizontalOverflow,g.pageWidth);
        await page.locator('#download-svg').scrollIntoViewIfNeeded();
        const occlusion=await page.locator('#download-svg').evaluate(el=>{const r=el.getBoundingClientRect(),top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return !!top&&(top===el||el.contains(top));});
        check(`${viewport.width}px ${chapter}: export button unobstructed`,occlusion);
      }
    }
    await page.setViewportSize({width:1440,height:900});await open();
    const initialTable=await page.locator('#actual-example table').innerText();
    await page.getByRole('button',{name:'跨任务复现',exact:true}).click();
    check('Cross-task control changes URL',new URL(page.url()).searchParams.get('view')==='cross');
    check('Cross-task control displays 17 real rows',await page.locator('#actual-example tbody tr').count()===17);
    await page.reload({waitUntil:'networkidle'});
    check('Cross-task state survives reload',await page.getByRole('button',{name:'跨任务复现',exact:true}).getAttribute('aria-pressed')==='true');
    await page.getByRole('button',{name:'同题对照',exact:true}).click();
    check('Baseline data preserved on return',(await page.locator('#actual-example table').innerText())===initialTable);
    const csvEvent=page.waitForEvent('download');await page.locator('#download-csv').click();const csv=await csvEvent;
    await csv.saveAs(resolve(output,'export-baseline.csv'));check('CSV download works',csv.suggestedFilename()==='lens-concise.csv');
    const svgEvent=page.waitForEvent('download');await page.locator('#download-svg').click();const svg=await svgEvent;
    await svg.saveAs(resolve(output,'export-baseline.svg'));check('SVG download works',svg.suggestedFilename()==='concise-baseline.svg');
    await page.locator('#data-table summary').click();check('Native data disclosure opens',await page.locator('#data-table').getAttribute('open')!==null);
    await page.locator('.support-section details').nth(1).locator('summary').click();check('Method disclosure opens',await page.locator('.support-section details').nth(1).getAttribute('open')!==null);
    await page.locator('.chapter-nav a[data-chapter="language"]').click();await page.locator('#task').selectOption('gsm8k');
    check('Language task selection',new URL(page.url()).searchParams.get('task')==='gsm8k'&&(await page.locator('h1').innerText()).includes('基础算术'));
    await page.locator('.chapter-nav a[data-chapter="limits"]').click();await page.locator('#model').selectOption('qwen3');await page.locator('#task').selectOption('mmlu');await page.locator('#family').selectOption('CharLimit');
    check('Limit controls update state',['model=qwen3','task=mmlu','family=CharLimit'].every(x=>page.url().includes(x)));
    await page.locator('.chapter-nav a[data-chapter="position"]').click();
    await page.locator('#position').fill('8');await page.locator('#position').dispatchEvent('input');await page.locator('#ci').check();
    check('Position slider reaches position 20',(await page.locator('#position-label').innerText()).includes('20')&&page.url().includes('position=20'));
    check('Position CI toggle',await page.locator('#plot').evaluate(el=>el.classList.contains('show-intervals')));
    await page.reload({waitUntil:'networkidle'});check('Position and CI survive reload',await page.locator('#position').inputValue()==='8'&&await page.locator('#ci').isChecked());
    await page.locator('.chapter-nav a[data-chapter="repair"]').click();await page.locator('#round').fill('0');await page.locator('#round').dispatchEvent('input');
    check('Repair initial version',(await page.locator('#round-label').innerText())==='初稿');
    await page.locator('#play').click();await page.waitForFunction(()=>document.querySelector('#round')?.value==='4',null,{timeout:15000});
    check('Playback reaches revision 4',(await page.locator('#point-readout').innerText()).includes('141/164'));
    await page.locator('#repair-model').selectOption('qwen');check('Repair model switching',page.url().includes('repairModel=qwen'));
    await page.locator('#present').click();check('Fullscreen control remains available',await page.locator('#present').count()===1);
    await page.evaluate(()=>document.fullscreenElement?document.exitFullscreen():null);
    await open();await page.locator('.header-actions a').click();await page.waitForURL('**/explore.html?mode=explore#case-1');await page.locator('#stage .loading').waitFor({state:'detached'});
    check('Chart library navigation',page.url().includes('explore.html')&&(await page.locator('#stage').innerText()).length>100);
    await page.getByRole('link',{name:'返回研究展页',exact:true}).click();await page.locator('#plot svg').waitFor();check('Return from chart library',!page.url().includes('explore.html'));
    const accessibility=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    await writeFile(resolve(output,'accessibility.json'),JSON.stringify({violations:accessibility.violations,incomplete:accessibility.incomplete},null,2)+'\n');
    check('No serious or critical accessibility violations',!accessibility.violations.some(v=>['serious','critical'].includes(v.impact)),accessibility.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length})));
    check('No uncaught browser errors',errors.length===0,errors);check('No failed resource requests',failedRequests.length===0,failedRequests);
    await writeFile(resolve(output,'regression.json'),JSON.stringify({results,errors,failedRequests},null,2)+'\n');
    console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.passed).length,failed:results.filter(r=>!r.passed)}));
    if(results.some(r=>!r.passed))process.exitCode=1;
  }
} finally {await browser.close();}
