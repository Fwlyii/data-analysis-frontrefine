import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {root} from './inventory.mjs';
const cli=resolve('optimization/homepage-pilot/tools/node_modules/lighthouse/cli/index.js');
const onlyHome=process.argv.includes('--after-home');
const summary=onlyHome?JSON.parse(await readFile(resolve(root,'after/performance-summary.json'),'utf8')).runs.filter(r=>!(r.surface==='home'&&r.stage==='after')):[];
for(const surface of ['home','library'])for(const device of ['mobile','desktop'])for(const stage of ['before','after']){
 if(onlyHome&&!(surface==='home'&&stage==='after'))continue;
 const url=`http://127.0.0.1:${stage==='before'?8792:8788}/${surface==='home'?'index.html?intro=0':'explore.html?mode=explore&chart=model'}`;
 const filename=`lighthouse-${surface}-${device}.json`,path=resolve(root,stage,filename);
 // The library already loads ~13 MiB of raw scientific snapshots. Use an
 // explicitly unthrottled local diagnostic, not a fictitious weak-network score.
 const args=[cli,url,'--only-categories=performance,accessibility,best-practices','--throttling-method=provided','--output=json','--output-path='+path,'--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage','--quiet'];
 if(device==='desktop')args.push('--preset=desktop','--screenEmulation.width=1440','--screenEmulation.height=900');
 else args.push('--screenEmulation.width=390','--screenEmulation.height=844','--screenEmulation.deviceScaleFactor=1');
 await new Promise((done,fail)=>{const proc=spawn(process.execPath,args,{env:{...process.env,CHROME_PATH:'/snap/bin/chromium'},stdio:'inherit'});proc.on('error',fail);proc.on('exit',code=>code===0?done():fail(new Error('Lighthouse '+code)));});
 const report=JSON.parse(await readFile(path,'utf8'));
 const row={surface,device,stage,report:`${stage}/${filename}`,scores:Object.fromEntries(Object.entries(report.categories).map(([k,v])=>[k,Math.round(v.score*100)])),metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index','total-byte-weight'].map(k=>[k,report.audits[k]?.numericValue])),warnings:report.runWarnings};
 summary.push(row);console.log(JSON.stringify(row));
 await writeFile(resolve(root,'after/performance-summary.json'),JSON.stringify({targetedHomeRerun:onlyHome,method:'Eight paired cold-load Lighthouse profiles; home-only after profiles can be rerun after a home-only change while retaining unchanged baseline/library measurements. Runs on the same local host and Chromium. Provided throttling: NO simulated weak network or CPU throttling. Home is explicitly intro=0 to compare the underlying system; the finite intro gets separate frame/CPU diagnostics. Phone/desktop viewports only, not real mobile hardware. Baseline is the frozen aa3116d build captured before the gateway, served independently on port8792. Same data and route inventory. Do not compare these scores to v2 DevTools-throttled scores. Single-run diagnostics, not a statistical benchmark.',runs:summary},null,2)+'\n');
}
