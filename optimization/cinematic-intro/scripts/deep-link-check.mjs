import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const require=createRequire(resolve('optimization/homepage-pilot/tools/package.json'));
const {chromium}=require('playwright-core');
const browser=await chromium.launch({executablePath:'/snap/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'no-preference'});
try{
 await page.goto('http://127.0.0.1:8780/?intro=1&position=20&ci=1#position/example',{waitUntil:'domcontentloaded'});
 await page.waitForFunction(()=>window.LensIntro?.inspect().history.length>0&&!LensIntro.inspect().running);
 const state=await page.evaluate(()=>({hash:location.hash,query:location.search,scroll:scrollY,exampleTop:document.querySelector('#actual-example').getBoundingClientRect().top,position:document.querySelector('#position').value,ci:document.querySelector('#ci').checked,inert:document.querySelectorAll('[data-intro-inert]').length,history:LensIntro.inspect().history}));
 const passed=state.hash==='#position/example'&&state.position==='8'&&state.ci&&state.scroll>0&&Math.abs(state.exampleTop-132)<5&&!state.inert;
 await writeFile(resolve('optimization/cinematic-intro/after/deep-link-check.json'),JSON.stringify({results:[{name:'Forced intro preserves example anchor, evidence position and CI',passed,detail:state}]},null,2)+'\n');
 console.log(JSON.stringify({passed,state}));if(!passed)process.exitCode=1;
}finally{await browser.close();}
