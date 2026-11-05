/** Continuous defense page regression: BASE_URL=http://127.0.0.1:8771/ node tests/browser/defense.mjs. */
import {createRequire} from 'node:module';
import {mkdir,writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {execFileSync} from 'node:child_process';

const require=createRequire(resolve('tests/package.json'));
const {chromium}=require('playwright-core');
const AxeBuilder=require('@axe-core/playwright').default;
const base=process.env.BASE_URL||'http://127.0.0.1:8771/';
const out=resolve('artifacts/qa/defense');
const screenshotsOut=process.env.DEFENSE_PREVIEW_DIR?resolve(process.env.DEFENSE_PREVIEW_DIR):resolve(out,'screenshots');
await mkdir(out,{recursive:true});await mkdir(screenshotsOut,{recursive:true});await mkdir(resolve(out,'screenshots'),{recursive:true});
const chrome=process.env.CHROMIUM_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser=await chromium.launch({headless:true,executablePath:existsSync(chrome)?chrome:undefined,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',acceptDownloads:true});
const page=await context.newPage();
const checks=[],errors=[],missing=[],screenshots=[],accessibility=[];
const topics=['budget','scale','concise','limits','language','position','feedback'];
const chapters=['question','collection','cleaning','findings','conclusion'];
page.on('pageerror',error=>errors.push(error.message));
page.on('response',response=>{if(response.status()>=400&&!response.url().endsWith('favicon.ico'))missing.push({url:response.url(),status:response.status()});});
function assert(value,message){if(!value)throw Error(message);}
function record(name,pass,detail){checks.push({name,pass,detail});if(!pass)console.error('FAIL',name,JSON.stringify(detail));}
async function test(name,action){try{record(name,true,await action());}catch(error){record(name,false,{error:error.message});}}
async function ready(){await page.waitForFunction(()=>document.body.dataset.view&&document.querySelector('#main-content h1')&&!document.querySelector('.initial-loading'));}
async function open(query=''){await page.goto(new URL(query,base).href,{waitUntil:'domcontentloaded'});await ready();}
async function imagesReady(root='#main-content'){
  const images=page.locator(root+' img');
  for(let i=0;i<await images.count();i++){await images.nth(i).scrollIntoViewIfNeeded();await images.nth(i).evaluate(image=>image.decode());}
}
async function shot(name,file,{fullPage=false,target=null,artifact=false}={}){
  if(target){await imagesReady(target);await page.locator(target).evaluate(element=>window.scrollTo({top:element.getBoundingClientRect().top+scrollY-(document.querySelector('.site-header')?.getBoundingClientRect().height||0)-28,behavior:'instant'}));}
  else {await imagesReady();await page.evaluate(()=>window.scrollTo(0,0));}
  await page.evaluate(()=>document.fonts.ready);const path=resolve(artifact?resolve(out,'screenshots'):screenshotsOut,file);await page.screenshot({path,fullPage});screenshots.push({name,path});
}
async function axe(name){const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();const findings=result.violations.map(item=>({id:item.id,impact:item.impact,nodes:item.nodes.map(node=>({target:node.target,summary:node.failureSummary}))}));accessibility.push({name,violations:findings});record(name+' accessibility',findings.length===0,findings);}
async function assertChrome(){
  assert(await page.locator('.research-rail,aside[aria-label="当前研究路径"],.page-footer,#page-progress,.scene-next,.scene-previous').count()===0,'Old navigation remains in DOM');
  assert(await page.locator('#chapter-nav a').count()===5,'Chapter nav count differs');
  assert(await page.locator('.site-header a').count()===6,'Header has unrelated links');
  assert(await page.locator('#main-content a,#main-content button,#main-content select,#main-content details').count()===0,'Body exposes unnecessary actions or hidden disclosure');
}
try{
  await open();
  const catalog=await page.evaluate(async()=>await(await fetch('data/research-charts.json')).json());
  const content=await page.evaluate(async()=>await import('./src/research-content.js').then(module=>module.researchContent));
  await test('root opens exactly five orb links without chapter chrome or footer',async()=>{
    assert(await page.locator('.rh-orb:visible').count()===5,'Home does not expose exactly5 orbs');assert(!await page.locator('.site-header').isVisible(),'Chapter chrome appears on home');assert(await page.locator('.page-footer,#page-progress').count()===0,'Footer still exists');
    const visibleLinks=await page.locator('a:visible').evaluateAll(links=>links.filter(link=>{const b=link.getBoundingClientRect();return b.bottom>0&&b.right>0&&b.top<innerHeight&&b.left<innerWidth;}).map(link=>link.textContent.trim()));assert(visibleLinks.length===5,'Home exposes extra links');return visibleLinks;
  });
  await test('five orbs enter five chapters and brand restores home',async()=>{
    for(const chapter of chapters){await page.locator('[data-home-chapter="'+chapter+'"]').click();await page.waitForFunction(chapter=>document.body.dataset.chapter===chapter,chapter);await assertChrome();await page.locator('[data-home-link]').click();await page.locator('.rh-orb').first().waitFor();}return chapters;
  });
  await test('home and cleaning survive Back and refresh',async()=>{
    await page.locator('[data-home-chapter="cleaning"]').click();await page.locator('.rc-cleaning-figure').waitFor();const before=page.url();await page.reload();await page.locator('.rc-cleaning-figure').waitFor();assert(page.url()===before,'Refresh lost cleaning route');await page.goBack();await page.locator('.research-home').waitFor();await page.reload();await page.locator('.research-home').waitFor();return true;
  });
  await open('?chapter=question');
  await test('question directly shows three task examples without controls',async()=>{assert(await page.locator('.rc-task-example:visible').count()===3,'Tasks hidden behind tabs');await assertChrome();return await page.locator('.rc-task-example h3').allTextContents();});
  await open('?chapter=collection');
  await test('collection directly shows four dimensions,31 strategies and five experiments',async()=>{
    assert(await page.locator('.rc-dimension').count()===4,'Dimension count mismatch');assert(await page.locator('.rc-prompt-item:visible').count()===31,'Catalogue is not fully visible');assert(await page.locator('.rc-experiment-table tbody tr').count()===5,'Experiment count mismatch');await assertChrome();assert(content.totalRecords===248586,'Record total changed');return {dimensions:4,prompts:31,records:content.totalRecords};
  });
  await open('?chapter=cleaning');
  await test('cleaning is a static A/B/C/D figure without buttons, selects, links or disclosure',async()=>{
    await assertChrome();for(const selector of ['.rc-panel-a','.rc-panel-b','.rc-panel-c','.rc-storage-summary'])assert(await page.locator(selector).isVisible(),'Missing panel '+selector);assert(await page.locator('[data-rc-source]').count()===2,'Sources missing');assert(await page.locator('[data-rc-mapping]').count()===4,'Four mappings missing');return {sources:2,mappings:4,panels:4};
  });
  await test('all four source-name mappings are simultaneously visible and marked red',async()=>{
    for(const source of ['reasoning','document_qa']){const marks=page.locator('[data-rc-source="'+source+'"] .rc-field-token');assert(await marks.count()===4,'Four red source fields missing for '+source);const colors=await marks.evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).color));assert(colors.every(color=>{const [r,g,b]=color.match(/[0-9.]+/g).map(Number);return r>g*1.5&&r>b*1.2;}),'Source fields are not visually red: '+source);}
    for(const field of content.cleaning.fields){const mapping=page.locator('[data-rc-mapping="'+field.id+'"]');assert(await mapping.isVisible(),'Mapping is hidden: '+field.id);const text=await mapping.innerText();assert(text.includes(field.id),'Canonical field missing '+field.id);assert(text.includes(field.reasoningKey)&&text.includes(field.documentKey.split('.').at(-1)),'Source names missing '+field.id);const sourceText=await page.locator('[data-rc-source="document_qa"]').textContent();assert(sourceText.includes(field.documentKey),'Full API path missing '+field.id);}
    return content.cleaning.fields.map(field=>field.id);
  });
  await test('both unified records simultaneously match all nine saved keys',async()=>{
    const keys=['model_id','benchmark','input_tokens','output_tokens','finish_reason','metric_name','metric_value','document_count','evidence_position'];assert(await page.locator('.rc-combined-records [data-rc-record]').count()===2,'Two record columns missing');assert(await page.locator('[data-rc-saved-field]').count()===9,'Saved key count differs');
    for(const key of keys)for(const source of ['reasoning','document_qa']){const cell=page.locator('[data-rc-saved-field="'+key+'"] [data-source="'+source+'"]');assert(await cell.isVisible(),'Saved value hidden '+source+'/'+key);assert((await cell.innerText()).trim()===String(content.cleaning.records[source][key]),'Saved value differs '+source+'/'+key);}
    const storage=await page.locator('.rc-storage-summary').innerText();assert(storage.includes('all_records.csv.gz')&&storage.includes('21'),'Saved file/format not disclosed');return {keys:9,records:2};
  });
  await shot('static cleaning figure','滚动版_数据处理Figure.png',{fullPage:true});
  await open('?chapter=findings');
  await test('findings is one continuous article with four general and three task sections',async()=>{
    assert(await page.locator('.findings-long-page').count()===1,'Continuous findings article missing');const parts=page.locator('.findings-part');assert(await parts.count()===2,'General/specific grouping differs');assert(await parts.nth(0).locator('[data-topic]').count()===4&&await parts.nth(1).locator('[data-topic]').count()===3,'4+3 sections differ');assert(JSON.stringify(await page.locator('[data-topic]').evaluateAll(nodes=>nodes.map(node=>node.dataset.topic)))===JSON.stringify(topics),'Theme order changed');assert(await page.locator('.finding-group').nth(0).locator('li').count()===4&&await page.locator('.finding-group').nth(1).locator('li').count()===3,'Static overview count differs');await assertChrome();return topics;
  });
  await test('all37 charts are in the same DOM and decode during one continuous scroll',async()=>{
    const before=page.url(),plots=page.locator('.findings-long-page [data-chart-id]'),actual=await plots.evaluateAll(nodes=>nodes.map(node=>node.dataset.chartId));assert(actual.length===37&&new Set(actual).size===37,'Not37 unique plots');assert(catalog.charts.every(chart=>actual.includes(chart.id)),'Catalogue figure absent');assert(await page.locator('.main-figure img').count()===7&&await page.locator('.support-figure img').count()===30,'Main/support figure counts differ');
    await imagesReady('.findings-long-page');const loaded=await plots.locator('img').evaluateAll(images=>images.every(image=>image.complete&&image.naturalWidth>0));assert(loaded,'Image did not load');assert(page.url()===before,'Scrolling changed route');const height=await page.evaluate(()=>document.documentElement.scrollHeight);assert(height>10000,'Findings did not form a long article');return {charts:37,main:7,support:30,height,url:before};
  });
  await test('PageDown scrolls without changing chapter or hiding findings',async()=>{
    await page.evaluate(()=>window.scrollTo(0,0));await page.locator('#main-content h1').click();const before=page.url();await page.keyboard.press('PageDown');await page.waitForFunction(()=>scrollY>200);assert(page.url()===before,'Native scrolling changed route');assert(await page.locator('[data-topic]').count()===7,'Scroll replaced article content');return true;
  });
  await test('left and right arrow keys never navigate chapters',async()=>{
    for(const chapter of ['question','cleaning','findings','conclusion']){await open('?chapter='+chapter);await page.locator('#main-content h1').click();const before=page.url();await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowLeft');await page.waitForTimeout(60);assert(page.url()===before,'Arrow key changed '+chapter+' route');}return true;
  });
  await test('legacy topic URLs preserve all seven sections and37 charts',async()=>{
    for(const topic of ['budget','position','feedback']){await open('?chapter=findings&topic='+topic);assert(await page.locator('[data-topic]').count()===7&&await page.locator('[data-chart-id]').count()===37,'Legacy URL cut the article: '+topic);assert(await page.locator('.section-intro h1').innerText()==='先看总体关系，再进入具体任务。','Legacy topic replaced chapter heading');}return true;
  });
  await open('?chapter=findings');await shot('findings structure','滚动版_发现结构.png');await shot('budget graph in continuous article','滚动版_核心发现.png',{target:'#finding-budget'});assert(page.url().endsWith('?chapter=findings'),'Figure screenshot altered route');
  for(const width of [1440,1000,768,390]){
    await page.setViewportSize({width,height:width===390?844:1000});
    for(const chapter of ['home',...chapters]){
      await open(chapter==='home'?'':'?chapter='+chapter);
      await test(width+' no whole-page horizontal overflow '+chapter,async()=>{const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));assert(dimensions.scroll<=dimensions.viewport+1&&dimensions.body<=dimensions.viewport+1,JSON.stringify(dimensions));return dimensions;});
      await axe(width+' '+chapter);
    }
  }
  await open('?chapter=cleaning');await shot('static cleaning phone','静态清洗Figure_手机.png',{fullPage:true,artifact:true});
  await open('?chapter=findings');await shot('continuous article phone','长页核心发现_手机.png',{target:'#finding-budget',artifact:true});
  await page.setViewportSize({width:1440,height:1000});await open('?chapter=atlas');
  await test('separate archive retains37 editable plots and13 interactive chart types',async()=>{
    assert(await page.locator('.atlas-grid [data-chart-id]').count()===37,'Archive missing figures');await page.locator('[data-x-field="chart"]').waitFor({timeout:30000});assert(await page.locator('[data-x-field="chart"] option').count()===13,'Legacy13 chart types missing');const archive=await page.request.get(new URL('assets/research-svg.zip',base).href);assert(archive.ok(),'SVG archive missing');return {figures:37,interactiveTypes:13};
  });
  await test('scientific protection remains intact',async()=>execFileSync('python3',['scripts/system/check_reconstruction.py'],{encoding:'utf8'}).trim());
}catch(error){record('unexpected runner failure',false,{error:error.stack});}
finally{
  await browser.close();record('no uncaught browser errors',errors.length===0,errors);record('no missing resources',missing.length===0,missing);
  const report={baseURL:base,checks:checks.length,passed:checks.filter(check=>check.pass).length,failed:checks.filter(check=>!check.pass),errors,missing,accessibility,screenshots,results:checks};await writeFile(resolve(out,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({checks:report.checks,passed:report.passed,failed:report.failed.length,report:resolve(out,'report.json')}));if(report.failed.length)process.exitCode=1;
}
