/** Defense flow regression: BASE_URL=http://127.0.0.1:8771/ node tests/browser/defense.mjs. */
import {createRequire} from 'node:module';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {resolve} from 'node:path';
import {execFileSync} from 'node:child_process';

const require=createRequire(resolve('tests/package.json'));
const {chromium}=require('playwright-core');
const AxeBuilder=require('@axe-core/playwright').default;
const base=process.env.BASE_URL||'http://127.0.0.1:8771/';
const out=resolve('artifacts/qa/defense');
const screenshotsOut=process.env.DEFENSE_PREVIEW_DIR?resolve(process.env.DEFENSE_PREVIEW_DIR):resolve(out,'screenshots');
await mkdir(out,{recursive:true});await mkdir(screenshotsOut,{recursive:true});
const chrome=process.env.CHROMIUM_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const browser=await chromium.launch({headless:true,executablePath:existsSync(chrome)?chrome:undefined,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',acceptDownloads:true});
const page=await context.newPage();
const checks=[],errors=[],missing=[],screenshots=[],accessibility=[];
page.on('pageerror',error=>errors.push(error.message));
page.on('response',response=>{if(response.status()>=400&&!response.url().endsWith('favicon.ico'))missing.push({url:response.url(),status:response.status()});});
function assert(value,message){if(!value)throw Error(message);}
function record(name,pass,detail){checks.push({name,pass,detail});if(!pass)console.error('FAIL',name,JSON.stringify(detail));}
async function test(name,action){try{record(name,true,await action());}catch(error){record(name,false,{error:error.message});}}
async function ready(){await page.waitForFunction(()=>document.body.dataset.view&&document.querySelector('#main-content h1')&&!document.querySelector('.initial-loading'));}
async function open(query=''){await page.goto(new URL(query,base).href,{waitUntil:'domcontentloaded'});await ready();}
async function imagesReady(){
  const images=page.locator('#main-content img');
  for(let i=0;i<await images.count();i++){await images.nth(i).scrollIntoViewIfNeeded();await images.nth(i).evaluate(image=>image.decode());}
}
async function primaryReady(){await page.locator('#primary-figure > svg').waitFor();}
async function shot(name,file){await imagesReady();await page.evaluate(()=>window.scrollTo(0,0));await page.evaluate(()=>document.fonts.ready);const path=resolve(screenshotsOut,file);await page.screenshot({path});screenshots.push({name,path});}
async function axe(name){const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();const findings=result.violations.map(item=>({id:item.id,impact:item.impact,nodes:item.nodes.map(node=>({target:node.target,summary:node.failureSummary}))}));accessibility.push({name,violations:findings});record(name+' accessibility',findings.length===0,findings);}
const scenes=[['question'],['collection'],['cleaning'],['findings','overview'],...['budget','scale','concise','limits','language','position','feedback'].map(topic=>['findings',topic]),['conclusion']];
const query=([chapter,topic])=>'?chapter='+chapter+(topic&&topic!=='overview'?'&topic='+topic:'');

try{
  await open();
  const catalog=await page.evaluate(async()=>await(await fetch('data/research-charts.json')).json());
  const content=await page.evaluate(async()=>await import('./src/research-content.js').then(module=>module.researchContent));
  await test('root opens five-orb home with chapter chrome hidden',async()=>{
    assert(await page.locator('.rh-orb:visible').count()===5,'Home does not expose exactly5 orbs');
    assert(!await page.locator('.site-header').isVisible()&&!await page.locator('.page-footer').isVisible(),'Chapter chrome appears on home');
    const visibleLinks=await page.locator('a:visible').evaluateAll(links=>links.filter(link=>{const b=link.getBoundingClientRect();return b.bottom>0&&b.right>0&&b.top<innerHeight&&b.left<innerWidth;}).map(link=>link.textContent.trim()));
    assert(visibleLinks.length===5,'Home shows links outside its5 chapter orbs');return visibleLinks;
  });
  await test('five orbs enter five chapters and brand restores home',async()=>{
    const chapters=['question','collection','cleaning','findings','conclusion'];
    for(const chapter of chapters){await page.locator('[data-home-chapter="'+chapter+'"]').click();await page.waitForFunction(chapter=>document.body.dataset.chapter===chapter,chapter);assert(await page.locator('#main-content h1').isVisible(),chapter+' title missing');await page.locator('[data-home-link]').click();await page.locator('.rh-orb').first().waitFor();}
    return chapters;
  });
  await test('home and chapter survive Back and refresh',async()=>{
    await page.locator('[data-home-chapter="cleaning"]').click();await page.locator('[data-rc-cleaning]').waitFor();const before=page.url();await page.reload();await page.locator('[data-rc-cleaning]').waitFor();assert(page.url()===before,'Refresh lost cleaning route');await page.goBack();await page.locator('.research-home').waitFor();await page.reload();await page.locator('.research-home').waitFor();return true;
  });
  await axe('home desktop');await shot('home','答辩版_首页.png');
  await open('?chapter=question');
  await test('question shows all three task examples without controls or cross-chapter CTA',async()=>{
    assert(await page.locator('.rc-task-example:visible').count()===3,'Tasks are hidden behind tabs');
    assert(await page.locator('#main-content button,#main-content a').count()===0,'Question has unnecessary interactive CTA');
    assert(await page.locator('.rc-task-example h3').count()===3,'Three task names missing');return await page.locator('.rc-task-example h3').allTextContents();
  });
  await axe('question desktop');await shot('question','答辩版_研究问题.png');
  await open('?chapter=collection');
  await test('collection shows four dimensions and31 strategies directly',async()=>{
    assert(await page.locator('.rc-dimension').count()===4,'Dimension count mismatch');assert(await page.locator('.rc-prompt-item:visible').count()===31,'Strategy catalogue is not fully visible');assert(await page.locator('#main-content details,#main-content button,#main-content a').count()===0,'Collection content is hidden or exposes detours');assert(await page.locator('.rc-experiment-table tbody tr').count()===5,'Experiment ledger count mismatch');return {dimensions:4,prompts:31,records:content.totalRecords};
  });
  await open('?chapter=cleaning');
  await test('cleaning exposes only four field switches and one record source',async()=>{
    assert(await page.locator('#main-content button').count()===4,'Unexpected cleaning buttons');assert(await page.locator('#main-content select').count()===1,'Unexpected cleaning select');assert(await page.locator('#main-content a').count()===0,'Cleaning has cross links');return true;
  });
  await test('all four mappings and saved nine keys match both frozen records',async()=>{
    const keys=['model_id','benchmark','input_tokens','output_tokens','finish_reason','metric_name','metric_value','document_count','evidence_position'];
    for(const field of content.cleaning.fields){await page.locator('[data-rc-field="'+field.id+'"]').click();await page.locator('[data-rc-cleaning][data-field="'+field.id+'"]').waitFor();assert(await page.locator('.rc-source-fragment .rc-field-token.is-active').count()===2,'Two source fields not marked for '+field.id);assert(await page.locator('.rc-saved-table tr.is-active code').innerText()===field.id,'Wrong saved field is selected');}
    for(const source of ['reasoning','document_qa']){
      await page.locator('[data-rc-saved-source]').selectOption(source);
      const rows=await page.locator('.rc-saved-table tbody tr').evaluateAll(rows=>rows.map(row=>[row.querySelector('code').textContent,row.cells[1].textContent.trim()]));
      assert(rows.length===9,'Saved key count is not9');
      for(const [index,[key,value]]of rows.entries()){assert(key===keys[index],'Key order differs');assert(value===String(content.cleaning.records[source][key]),source+' saved '+key+' differs');}
    }
    await page.locator('[data-rc-field="output_tokens"]').click();await page.locator('[data-rc-saved-source]').selectOption('reasoning');return {fields:4,sources:2,keys:9};
  });
  await axe('cleaning desktop');await shot('cleaning','答辩版_数据处理.png');
  await open('?chapter=findings');
  await test('findings overview shows static four general and three specific findings',async()=>{
    const groups=page.locator('.finding-group');assert(await groups.count()===2,'Findings groups missing');assert(await groups.nth(0).locator('li').count()===4&&await groups.nth(1).locator('li').count()===3,'4+3 structure changed');assert(await page.locator('#main-content a,#main-content button').count()===0,'Overview contains detours');return {general:4,specific:3};
  });
  await axe('overview desktop');
  await test('sequential defense path reaches all seven themes with all37 inline figures',async()=>{
    let figures=0;const ids=[];
    for(const topic of ['budget','scale','concise','limits','language','position','feedback']){
      await page.locator('.scene-next').click();await page.waitForFunction(topic=>new URLSearchParams(location.search).get('topic')===topic,topic);await primaryReady();
      assert(await page.locator('.main-figure').count()===1,'Missing main plot '+topic);
      assert(await page.locator('#main-content button,#main-content select,#main-content a').count()===0,'Theme '+topic+' exposes unnecessary controls');
      await imagesReady();const displayed=await page.locator('[data-chart-id]').evaluateAll(plots=>plots.map(plot=>plot.dataset.chartId));
      const expected=catalog.charts.filter(chart=>chart.topic===topic).map(chart=>chart.id);assert(expected.every(id=>displayed.includes(id))&&displayed.length===expected.length,'Theme '+topic+' lost charts');
      figures+=displayed.length;ids.push(...displayed);
    }
    assert(figures===37&&new Set(ids).size===37,'Complete theme flow does not show37 figures');
    await page.locator('.scene-next').click();await page.locator('.rc-conclusion').waitFor();return {themes:7,figures};
  });
  await test('chapter chrome has five links, brand and exactly two sequential links',async()=>{
    assert(await page.locator('.research-rail,aside[aria-label="当前研究路径"]').count()===0,'Sidebar still exists');assert(await page.locator('#chapter-nav a').count()===5,'Chapter nav count differs');assert(await page.locator('.site-header a').count()===6,'Header has unrelated links');assert(await page.locator('.page-footer a').count()===2,'Footer has unrelated links');assert(await page.locator('#main-content a,#main-content button').count()===0,'Conclusion contains unnecessary actions');return true;
  });
  await axe('conclusion desktop');
  await open('?chapter=findings&topic=budget');await primaryReady();await axe('budget desktop');await shot('budget','答辩版_核心发现.png');
  await test('left and right arrows advance sequentially from body focus',async()=>{
    await page.locator('h1').click();await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>new URLSearchParams(location.search).get('topic')==='scale');await primaryReady();await page.locator('h1').click();await page.keyboard.press('ArrowLeft');await page.waitForFunction(()=>new URLSearchParams(location.search).get('topic')==='budget');await primaryReady();return true;
  });
  for(const width of [1440,1000,768,390]){
    await page.setViewportSize({width,height:width===390?844:1000});
    for(const route of ['',...scenes.map(query)]){
      await open(route);if(route.includes('&topic='))await primaryReady();
      await test(width+' no whole-page horizontal overflow '+(route||'home'),async()=>{const dimensions=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth,body:document.body.scrollWidth}));assert(dimensions.scroll<=dimensions.viewport+1&&dimensions.body<=dimensions.viewport+1,JSON.stringify(dimensions));return dimensions;});
    }
  }
  await open();await axe('home phone');await shot('home phone','答辩版_首页_手机.png');
  await open('?chapter=cleaning');await axe('cleaning phone');await shot('cleaning phone','答辩版_数据处理_手机.png');
  await open('?chapter=findings&topic=budget');await primaryReady();await axe('budget phone');await shot('budget phone','答辩版_核心发现_手机.png');
  await page.setViewportSize({width:1440,height:1000});
  await open('?chapter=atlas');
  await test('separate archive retains37 editable plots and legacy interactive explorer',async()=>{
    assert(await page.locator('.atlas-grid [data-chart-id]').count()===37,'Archive is missing figures');
    await page.locator('[data-x-field="chart"]').waitFor({timeout:30000});assert(await page.locator('[data-x-field="chart"] option').count()===13,'Legacy13 chart types missing');
    const archive=await page.request.get(new URL('assets/research-svg.zip',base).href);assert(archive.ok(),'SVG archive missing');return {figures:37,interactiveTypes:13};
  });
  await test('scientific protection remains intact',async()=>execFileSync('python3',['scripts/system/check_reconstruction.py'],{encoding:'utf8'}).trim());
}catch(error){record('unexpected runner failure',false,{error:error.stack});}
finally{
  await browser.close();record('no uncaught browser errors',errors.length===0,errors);record('no missing resources',missing.length===0,missing);
  const report={baseURL:base,checks:checks.length,passed:checks.filter(check=>check.pass).length,failed:checks.filter(check=>!check.pass),errors,missing,accessibility,screenshots,results:checks};
  await writeFile(resolve(out,'report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({checks:report.checks,passed:report.passed,failed:report.failed.length,report:resolve(out,'report.json')}));
  if(report.failed.length)process.exitCode=1;
}
