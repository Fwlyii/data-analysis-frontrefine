import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve('optimization/type-motion-v2');
const cli=resolve('optimization/homepage-pilot/tools/node_modules/lighthouse/cli/index.js');
const runs=[['before','mobile',8783],['before','desktop',8783],['after','mobile',8780],['after','desktop',8780]];
const summary=[];
for(const [stage,device,port] of runs){
  const path=resolve(root,stage,`lighthouse-${device}.json`),url=`http://127.0.0.1:${port}/`;
  const args=[cli,url,'--only-categories=performance,accessibility,best-practices','--throttling-method=devtools','--output=json','--output-path='+path,'--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage','--quiet'];
  if(device==='desktop')args.push('--preset=desktop','--screenEmulation.width=1440','--screenEmulation.height=900');
  else args.push('--screenEmulation.width=390','--screenEmulation.height=844','--screenEmulation.deviceScaleFactor=1');
  await new Promise((done,fail)=>{const proc=spawn(process.execPath,args,{env:{...process.env,CHROME_PATH:'/snap/bin/chromium'},stdio:'inherit'});proc.on('error',fail);proc.on('exit',code=>code===0?done():fail(new Error('Lighthouse '+code)));});
  const report=JSON.parse(await readFile(path,'utf8'));
  const row={stage,device,report:`${stage}/lighthouse-${device}.json`,scores:Object.fromEntries(Object.entries(report.categories).map(([k,v])=>[k,Math.round(v.score*100)])),metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index','total-byte-weight'].map(k=>[k,report.audits[k]?.numericValue])),warnings:report.runWarnings};
  summary.push(row);console.log(JSON.stringify(row));
  await writeFile(resolve(root,'after/performance-summary.json'),JSON.stringify({method:'Four sequential single-run Lighthouse diagnostics, actual DevTools throttling, same Chromium, host and screen profiles. Baseline is unchanged dist from 2344eb5. No parallel browser tests. Not a statistical speed benchmark.',runs:summary},null,2)+'\n');
}
