const inflight = new Map();
const specs = {
 d3:{file:'d3-7.9.0.min.js',global:'d3'},
 vega:{file:'vega-5.30.0.min.js',global:'vega'},
 vegaLite:{file:'vega-lite-5.23.0.min.js',global:'vegaLite'},
 plotly:{file:'plotly-cartesian-3.1.1.min.js',global:'Plotly'},
};
function ready(name,value){return name==='vegaLite'?typeof value?.compile==='function':name==='vega'?typeof value?.parse==='function':name==='d3'?typeof value?.select==='function':typeof value?.newPlot==='function';}
export function load(name){
 const spec=specs[name];
 if(!spec)return Promise.reject(new Error('未知图形组件'));
 if(ready(name,window[spec.global]))return Promise.resolve(window[spec.global]);
 if(!inflight.has(name))inflight.set(name,new Promise((resolve,reject)=>{
  const script=document.createElement('script');script.src='assets/vendor/'+spec.file;script.async=true;
  script.onload=()=>{if(ready(name,window[spec.global]))resolve(window[spec.global]);else{inflight.delete(name);script.remove();reject(new Error('图形组件未完成加载'));}};
  script.onerror=()=>{inflight.delete(name);script.remove();reject(new Error('本地图形组件未找到，请重新启动系统'));};
  document.head.append(script);
 }));
 return inflight.get(name);
}
export function reducedMotion(){return window.matchMedia('(prefers-reduced-motion: reduce)').matches;}
