import {spawn} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve('optimization/homepage-pilot');
const cli=resolve(root,'tools/node_modules/lighthouse/cli/index.js');
const runs=[
  ['before','mobile','http://127.0.0.1:8781/','lighthouse-mobile-controlled.json'],
  ['before','desktop','http://127.0.0.1:8781/','lighthouse-desktop.json'],
  ['after','mobile','http://127.0.0.1:8780/','lighthouse-mobile.json'],
  ['after','desktop','http://127.0.0.1:8780/','lighthouse-desktop.json']
];
const afterOnly=process.argv.includes('--after-only');
const summary=afterOnly?JSON.parse(await readFile(resolve(root,'after/performance-summary.json'),'utf8')).runs.filter(run=>run.stage==='before'):[];
for(const [stage,device,url,filename] of runs.filter(run=>!afterOnly||run[0]==='after')) {
  const path=resolve(root,stage,filename);
  const args=[cli,url,'--only-categories=performance,accessibility,best-practices','--throttling-method=devtools','--output=json','--output-path='+path,'--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage','--quiet'];
  if(device==='desktop')args.push('--preset=desktop','--screenEmulation.width=1440','--screenEmulation.height=900');
  else args.push('--screenEmulation.width=390','--screenEmulation.height=844','--screenEmulation.deviceScaleFactor=1');
  await new Promise((resolve,reject)=>{
    const child=spawn(process.execPath,args,{env:{...process.env,CHROME_PATH:'/snap/bin/chromium'},stdio:'inherit'});
    child.on('error',reject);child.on('exit',code=>code===0?resolve():reject(new Error('Lighthouse exited '+code)));
  });
  const report=JSON.parse(await readFile(path,'utf8'));
  const row={stage,device,url,report:stage+'/'+filename,scores:Object.fromEntries(Object.entries(report.categories).map(([k,v])=>[k,Math.round(v.score*100)])),metrics:Object.fromEntries(['first-contentful-paint','largest-contentful-paint','total-blocking-time','cumulative-layout-shift','speed-index','total-byte-weight'].map(k=>[k,report.audits[k]?.numericValue])),lcpElement:report.audits['lcp-breakdown-insight']?.details?.items?.find(item=>item.type==='node')?.selector,warnings:report.runWarnings};
  summary.push(row);console.log(JSON.stringify(row));
  await writeFile(resolve(root,'after/performance-summary.json'),JSON.stringify({method:'Four sequential Lighthouse runs with actual DevTools throttling; same local host, browser, viewport, network/CPU settings and installed fonts. Baseline dist is extracted unchanged from commit 069033c. Earlier simulated-throttling reports are retained under iterations/performance-simulation because LCP graph inference was unstable across first-paint timing. Single-run results are diagnostic, not a statistical benchmark.',runs:summary},null,2)+'\n');
}
