import {readFile,writeFile,readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
export const root=resolve('optimization/cinematic-intro');
const source=await readFile('app/src/app.js','utf8');
const libraryBlock=source.match(/const library = \{([\s\S]*?)\n\};/)[1];
const library=[...libraryBlock.matchAll(/(\w+): "([^"]+)"/g)].map(m=>({key:m[1],label:m[2]}));
const storySource=await readFile('app/src/story.js','utf8');
const story=[...storySource.match(/const titles=\{(.*?)\};/)[1].matchAll(/(\w+):/g)].map(m=>m[1]);
const codeSource=await readFile('app/src/code-study.js','utf8');
const codeViews=[...codeSource.match(/const VIEWS = \{(.*?)\};/)[1].matchAll(/(\w+):/g)].map(m=>m[1]);
const chapterCount=[...source.match(/const chapters = \[(.*?)\];/)[1].matchAll(/"[^"]+"/g)].length;
const routes=[
 ...story.map(key=>({key:'story-'+key,family:'story',url:'index.html#'+key})),
 ...['gsm8k','mmlu'].map(task=>({key:'story-language-'+task,family:'story',url:'index.html?task='+task+'#language'})),
 {key:'efficiency',family:'publication',url:'explore.html#budget'},
 {key:'efficiency-prompts',family:'publication',url:'explore.html?view=prompts#budget'},
 {key:'position-matrix',family:'publication',url:'explore.html#position'},
 {key:'position-profile',family:'publication',url:'explore.html?figure=profile#position'},
 ...codeViews.map(key=>({key:'code-'+key,family:'code',url:'explore.html?codeView='+key+'#code'})),
 ...Array.from({length:chapterCount},(_,n)=>({key:'discovery-'+(n+1),family:'discovery',url:'explore.html#case-'+(n+1)})),
 ...library.map(({key,label})=>({key:'chart-'+key,label,family:'library',url:'explore.html?mode=explore&chart='+key+(['position','timeline','tree','flow'].includes(key)?'&dataset=document_qa':'')+'#case-1'})),
 {key:'chart-flow-empty',family:'library',empty:true,url:'explore.html?mode=explore&chart=flow&dataset=reasoning#case-1'}
];
export {routes};
if(process.argv[1]===new URL(import.meta.url).pathname){
 const documents=(await readdir('app/dist')).filter(name=>name.endsWith('.html')).sort();
 if(documents.join(',')!=='explore.html,index.html')throw new Error('Unclassified production HTML: update route inventory and coverage before delivery');
 for(const name of documents){
  const markup=await readFile('app/dist/'+name,'utf8');
  for(const match of markup.matchAll(/href="([^"?#]+\.html)(?:[?#][^"]*)?"/g)){
   if(!match[1].includes('://')&&!documents.includes(match[1]))throw new Error('Unclassified linked page: '+match[1]);
  }
 }
 const modes=[...source.matchAll(/\["[\w-]+-mode", "(\w+)"\]/g)].map(m=>m[1]).sort();
 if(modes.join(',')!=='code,demo,explore,overview,position')throw new Error('New mode needs explicit route coverage');
 const result={baseCommit:'f353a186cfaf2ef8696afd137b74dcc8041ca30d',entryDocuments:['app/index.html','app/explore.html'],routeCount:routes.length,routes,viewports:[320,390,768,1440],overlays:['publication-method','code-method','condition-records','anonymous-record-detail'],excluded:['PDF/CSV/SVG downloads are documents, not application screens','Archived optimization galleries are evidence, not production navigation'],discovery:'Entry HTML hrefs, mode navigation, source library keys, code VIEWS and discovery chapter arrays; browser inventory checks source keys are covered.'};
 await writeFile(resolve(root,'site-inventory.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({routes:routes.length,libraryCharts:library.length}));
}
