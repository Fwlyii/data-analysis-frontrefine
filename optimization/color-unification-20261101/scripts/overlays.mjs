import{readFile,writeFile,mkdir}from'node:fs/promises';import{createRequire}from'node:module';import{resolve}from'node:path';import{routes,root}from'./inventory.mjs';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json')),{chromium}=require('playwright-core');const stage=process.argv[2]||'before',base=stage==='before'?'http://127.0.0.1:8839/':'http://127.0.0.1:8838/';
await mkdir(resolve(root,stage,'overlays'),{recursive:true});const browser=await chromium.launch({executablePath:'/snap/bin/chromium',args:['--no-sandbox']});const states=[],errors=[];
const cases=[
 ['collection-prompts','index.html?intro=0#collection',async p=>p.locator('#collection .inline-details summary').click()],
 ['field-definitions','index.html?intro=0#cleaning',async p=>p.locator('#cleaning .inline-details summary').click()],
 ['landscape-keyboard-cell','index.html?intro=0&overviewView=heatmap#landscape',async p=>{await p.locator('[data-profile-prompt="BeConcise"]').first().focus();await p.keyboard.press('Enter');}],
 ['real-example','index.html?intro=0&finding=position#findings',async p=>p.locator('#actual-example>summary').click()],
 ['figure-data','index.html?intro=0&finding=position#findings',async p=>p.locator('#data-table summary').click()],
 ['method-scope','index.html?intro=0&finding=position#findings',async p=>p.locator('summary').filter({hasText:/method|scope/i}).last().click()],
 ['export-menu','index.html?intro=0&finding=position#findings',async p=>p.locator('.export-menu summary').click()],
 ['publication-method','explore.html#budget',async p=>p.locator('[data-action="publication-method"]').click()],
 ['condition-records','explore.html#position',async p=>{await p.locator('[data-pub-prompt]').first().click();await p.locator('#inspector tbody tr').first().waitFor();}],
 ['anonymous-record-detail','explore.html#position',async p=>{await p.locator('[data-pub-prompt]').first().click();await p.locator('#inspector [data-record]').first().click();}],
 ['code-method','explore.html?codeView=sampling#code',async p=>p.locator('[data-code-action="method"]').click()],
 ['code-scoring-detail','explore.html?codeView=errors#code',async p=>{await p.locator('[data-code-action="records"]').first().click();await p.locator('#inspector [data-code-record]').first().click();}],
 ['code-numeric-filter','explore.html?codeView=tokens#code',async p=>p.locator('.code-numeric-filter summary').click()]
];
try{for(const[width,height,device]of[[1920,1080,'fullhd']]){const page=await browser.newPage({viewport:{width,height},reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
async function open(url){const target=new URL(url,base);target.searchParams.set('__capture',String(Date.now()));await page.goto(target.href,{waitUntil:'networkidle'});await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>Promise.all([...document.images].filter(i=>i.getClientRects().length).map(i=>i.decode().catch(()=>{}))));}
async function shot(key,url,kind,detail={}){const path=`optimization/color-unification-20261101/${stage}/overlays/${key}-${device}.png`;await page.screenshot({path});states.push({key,device,url,kind,screenshot:path,...detail});}
for(const[key,url,act]of cases){await open(url);await act(page);await shot(key,url,'expanded');const modal=await page.locator('#inspector').isVisible().catch(()=>false);const sc=modal?'#inspector':'.deck-panel.is-active';const scroll=await page.locator(sc).evaluate(el=>{const max=el.scrollHeight-el.clientHeight;el.scrollTop=max;return{max,actual:el.scrollTop};}).catch(()=>({max:0}));await shot(key+'-bottom',url,'expanded-bottom',{scroll});}
for(const route of routes){await open(route.url);const target=route.section?'.deck-panel.is-active':'html';const measured=await page.locator(target).evaluate(el=>({max:el.scrollHeight-el.clientHeight,client:el.clientHeight}));{for(const[position,factor]of[['middle',.5],['bottom',1]]){await page.locator(target).evaluate((el,f)=>el.scrollTop=f*(el.scrollHeight-el.clientHeight),factor);await shot(route.key+'-'+position,route.url,'scroll',{scroll:{...measured,position}});}}
}await page.close();console.log(device+' overlay/scroll captures complete');}}finally{await browser.close();await writeFile(resolve(root,stage,'overlays.json'),JSON.stringify({states,errors},null,2)+'\n');}if(errors.length)process.exitCode=1;
