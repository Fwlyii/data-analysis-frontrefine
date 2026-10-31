import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=resolve('optimization/type-motion-v2'),toolDir=resolve(root,'tools');
const require=createRequire(resolve(toolDir,'package.json'));
const esbuild=require('esbuild');
const outfile=resolve('app/assets/vendor/motion-mini-14.9.0.min.js');
const result=await esbuild.build({stdin:{contents:'export { animate } from "motion/mini";',resolveDir:toolDir,sourcefile:'motion-mini-entry.js'},bundle:true,format:'iife',globalName:'LensMotion',minify:true,legalComments:'eof',metafile:true,outfile});
await writeFile(resolve(root,'research/motion-bundle-inputs.json'),JSON.stringify(result.metafile,null,2)+'\n');
let licenses='';
for(const pkg of ['motion','framer-motion','motion-dom','motion-utils']){
  licenses+=`\n===== ${pkg} =====\n`+await readFile(resolve(toolDir,'node_modules',pkg,'LICENSE.md'),'utf8');
}
await writeFile(resolve('app/assets/vendor/motion-mini-14.9.0-LICENSE.txt'),licenses);
const path=resolve('app/assets/vendor/visualization-libraries.json');
const manifest=JSON.parse(await readFile(path,'utf8'));
const bytes=await readFile(outfile),pkg=manifest.packages.find(pkg=>pkg.package==='motion/mini');
if(!pkg)throw new Error('Existing motion-mini metadata entry missing');
pkg.bytes=bytes.length;pkg.sha256=createHash('sha256').update(bytes).digest('hex');
await writeFile(path,JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({bytes:bytes.length,sha256:pkg.sha256}));
