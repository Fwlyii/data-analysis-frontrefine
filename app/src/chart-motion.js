/* Chart-local effects. interaction.js owns scenes; original controllers own all data. */
(() => {
  'use strict';
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const preference=matchMedia('(prefers-reduced-motion: reduce)');
  const entries=new Map(), effects=new Map(), native=new Map(), seen=new Set(), listeners=[];
  const watchers=new Map();
  const counters=new Map(), transient=new Set();
  let disposed=false, scene='', played=0, hoverCount=0, frame=0, transition=null, tip=null, locked=null;
  const ease='cubic-bezier(.22,1,.36,1)';
  const on=(el,type,fn,opts)=>{el.addEventListener(type,fn,opts);return ()=>el.removeEventListener(type,fn,opts);};
  const active=()=>!disposed&&!document.hidden&&!document.documentElement.matches('.intro-active,.intro-pending')&&(!$('.deck')||document.body.dataset.section!=='gateway');
  const visible=el=>{const r=el.getBoundingClientRect();return !!r.width&&!!r.height&&r.bottom>0&&r.top<innerHeight&&r.right>0&&r.left<innerWidth;};
  const number=n=>Number.isFinite(+n)?(+n).toLocaleString('en-US',{maximumFractionDigits:3}):'未记录';
  function identity(p){return JSON.stringify([p.seriesIndex,p.dataIndex,p.axisIndex??null]);}
  function kind(){return $('#library-chart')?.value||$('.finding-nav [aria-current=page]')?.dataset.chapter||$('[data-code-view][aria-current=page]')?.dataset.codeView||document.body.dataset.section||location.hash;}
  function animate(el,values,duration=360,delay=0){
    if(!el||!active()||preference.matches||!visible(el))return;
    for(const item of [...effects.values()])if(item.el===el)item.finish();
    const original=el.getAttribute('style');
    const reset=()=>{if(original===null)el.removeAttribute('style');else el.setAttribute('style',original);};
    let control;const finish=()=>{const item=effects.get(control);if(!item)return;clearTimeout(item.timer);effects.delete(control);try{control.cancel();}catch{}reset();};
    try{
      control=!(el instanceof SVGElement)&&window.LensMotion?.animate?LensMotion.animate(el,values,{duration:duration/1000,delay:delay/1000,ease:[.22,1,.36,1]}):el.animate(values,{duration,delay,easing:ease,fill:'both'});
      effects.set(control,{el,finish,timer:setTimeout(finish,duration+delay+60)});played++;
      Promise.resolve(control.finished||control).then(finish,finish);
    }catch{reset();}
  }
  function finishNative(c){
    try{
      if(c.isDisposed())return;
      c.dispatchAction({type:'downplay'});c.dispatchAction({type:'hideTip'});c.dispatchAction({type:'updateAxisPointer',currTrigger:'leave'});
      const zr=c.getZr();zr.storage.traverse(el=>{el.stopAnimation?.(null,true);el.getTextContent?.()?.stopAnimation?.(null,true);el.getClipPath?.()?.stopAnimation?.(null,true);el.clearStates?.(true);const text=el.getTextContent?.();text?.clearStates?.(true);});
      zr.animation.clear();zr.flush();
    }catch{}
  }
  function clearVisual(){
    $$('.cm-marker,.cm-reference,.cm-matrix-band').forEach(n=>n.remove());
    if(tip)tip.hidden=true;
    for(const c of native.keys())try{if(!c.isDisposed()){c.dispatchAction({type:'downplay'});c.dispatchAction({type:'hideTip'});}}catch{}
  }
  function settle({players=false}={}){
    for(const item of [...effects.values()])item.finish();
    for(const item of [...counters.values()])item.finish();
    for(const c of native.keys())finishNative(c);
    transient.forEach(n=>n.remove());transient.clear();clearVisual();
    if(transition){transition.skipTransition();transition=null;}
    if(players){window.LensStoryPlayback?.pause();window.LensCodePlayback?.pause();}
  }
  function beforeExport(){settle({players:true});window.LensInteractions?.settle();window.LensMotionUI?.settle();window.LensSiteUI?.settle();}
  function configure(id,option){
    const type=(option.series||[]).find(s=>!s.silent)?.type||'chart';
    const key=kind()+':'+id+':'+type,update=seen.has(key);seen.add(key);
    const element=document.getElementById(id),allowed=active()&&!preference.matches&&(!element||visible(element));
    option.animation=allowed;
    option.animationDuration=allowed?(update?320:720):0;
    option.animationDurationUpdate=allowed?320:0;
    option.animationEasing='cubicOut';option.animationEasingUpdate='cubicInOut';
    option.animationDelay=i=>allowed?Math.min(update?100:260,i*(type==='heatmap'?9:24)):0;
    option.animationDelayUpdate=0;
    for(const s of option.series||[]){
      // Only temporal and emphasis options: values, geometry, axis and normal styles stay native.
      s.emphasis={...s.emphasis,focus:s.emphasis?.focus||(s.type==='line'?'series':'self')};
      if(s.type==='custom'&&s.data?.some(r=>r.raw?.started_at)){
        const times=s.data.map(r=>Date.parse(r.raw.started_at)).filter(Number.isFinite).sort((a,b)=>a-b);
        s.animationDelay=i=>Math.min(280,Math.max(0,times.indexOf(Date.parse(s.data[i]?.raw?.started_at)))*280/Math.max(1,times.length-1));
      }
      if(s.type==='tree'){
        const depths=[];const visit=(node,depth)=>{depths.push(depth);(node.children||[]).forEach(child=>visit(child,depth+1));};(s.data||[]).forEach(node=>visit(node,0));
        s.animationDelay=i=>allowed?Math.min(260,(depths[i]||0)*65):0;
      }
    }
    return option;
  }
  function pointBox(c,seriesIndex,dataIndex,dataType){
    try{const series=c.getModel().getSeriesByIndex(seriesIndex),data=dataType==='edge'?series.getEdgeData():series.getData(),el=data.getItemGraphicEl(dataIndex);if(!el)return null;
      const r=el.getBoundingRect().clone();r.applyTransform(el.getComputedTransform());return r;
    }catch{return null;}
  }
  function overlay(className,box){
    if(!box||box.width>innerWidth*1.1||box.height>innerHeight*1.5)return;
    const right=Math.min(innerWidth,box.x+Math.max(8,box.width)),bottom=Math.min(innerHeight,box.y+Math.max(8,box.height));
    box={x:Math.max(0,box.x),y:Math.max(0,box.y),width:right-Math.max(0,box.x),height:bottom-Math.max(0,box.y)};if(box.width<=0||box.height<=0)return;
    const el=document.createElement('span');el.className=className;el.setAttribute('aria-hidden','true');
    Object.assign(el.style,{left:box.x+'px',top:box.y+'px',width:Math.max(8,box.width)+'px',height:Math.max(8,box.height)+'px'});document.body.append(el);return el;
  }
  function showLabel(text,event,host){
    if(!tip){tip=document.createElement('div');tip.className='cm-mark-tip';tip.id='cm-mark-tooltip';tip.setAttribute('role','tooltip');document.body.append(tip);}
    tip.textContent=text;tip.hidden=false;
    const r=host.getBoundingClientRect(),x=event?.clientX??r.x+Math.min(r.width/2,200),y=event?.clientY??r.y+40;
    tip.style.left=Math.max(8,Math.min(x+16,innerWidth-tip.offsetWidth-12))+'px';tip.style.top=Math.max(8,Math.min(y+18,innerHeight-tip.offsetHeight-12))+'px';
  }
  function focusNative(entry,p,event){
    if(!active()||!p||entry.c.isDisposed()||!entry.host.isConnected)return;clearVisual();hoverCount++;
    const {c,host}=entry,local=pointBox(c,p.seriesIndex,p.dataIndex,p.dataType),r=host.getBoundingClientRect();
    const box=local?{x:r.x+local.x-3,y:r.y+local.y-3,width:local.width+6,height:local.height+6}:null;
    overlay('cm-marker',box);
    const option=c.getOption(),series=option.series[p.seriesIndex],data=series?.data?.[p.dataIndex];
    try{c.dispatchAction({type:'highlight',seriesIndex:p.seriesIndex,dataIndex:p.dataIndex,dataType:p.dataType});if(series?.type!=='parallel')c.dispatchAction({type:'showTip',seriesIndex:p.seriesIndex,dataIndex:p.dataIndex,dataType:p.dataType});}catch{}
    if(series?.type==='heatmap'&&box){
      const x=p.value?.[0]??data?.value?.[0],y=p.value?.[1]??data?.value?.[1];
      for(const [i,d]of (series.data||[]).entries())if(d.value?.[0]===x||d.value?.[1]===y){const b=pointBox(c,p.seriesIndex,i);if(b)overlay('cm-matrix-band',{x:r.x+b.x,y:r.y+b.y,width:b.width,height:b.height});}
    }
    if(['line','scatter','custom'].includes(series?.type)&&box&&local?.width<80){
      const area=c.getModel().getSeriesByIndex(p.seriesIndex).coordinateSystem?.getArea?.();
      overlay('cm-reference',{x:box.x+box.width/2,y:r.y+(area?.y??Math.max(12,r.height*.1)),width:1,height:area?.height??r.height*.74});
    }
    if(series?.type==='parallel'){
      const axes=option.parallelAxis.map(a=>a.name);showLabel([series.name,data?.name,...(data?.value||data||[]).map((v,i)=>axes[i]+'：'+number(v))].join('\n'),event,host);
    }
    if(kind()==='distribution'){
      const name=series?.type==='pie'?data?.name:series?.name;
      for(const [other,info]of native)if(other!==c&&info.host.id.startsWith('library-')){
        const opt=other.getOption();opt.series.forEach((s,si)=>{if(s.name===name)(s.data||[]).forEach((_,di)=>other.dispatchAction({type:'highlight',seriesIndex:si,dataIndex:di}));else(s.data||[]).forEach((d,di)=>{if(d.name===name)other.dispatchAction({type:'highlight',seriesIndex:si,dataIndex:di});});});
      }
    }
  }
  function nativeRows(c){
    const rows=[];c.getOption().series.forEach((s,si)=>{if(s.silent)return;(s.data||[]).forEach((data,di)=>{if(data==='-'||data==null)return;rows.push({seriesIndex:si,dataIndex:di,data,value:data.value??data,name:data.name||'',seriesType:s.type});});if(s.type==='sankey')(s.links||[]).forEach((data,di)=>rows.push({seriesIndex:si,dataIndex:di,dataType:'edge',data,value:data.value,seriesType:s.type}));});return rows;
  }
  function register(c,host,onClick){
    if(!c||!host||disposed||native.has(c))return;prune();
    const entry={c,host,duration:c.getOption().animationDuration,rows:()=>nativeRows(c),index:0,cleanups:[]};native.set(c,entry);
    const over=p=>{if(!p.componentType||p.componentType==='series')focusNative(entry,p,p.event?.event);},out=()=>{if(locked?.host!==host)clearVisual();else focusNative(entry,locked.p);};
    const click=p=>{if((p.componentType&&p.componentType!=='series')||!p.data||c.isDisposed()||!host.isConnected)return;const same=locked?.host===host&&identity(locked.p)===identity(p);locked=same?null:{host,p};if(same)clearVisual();else focusNative(entry,p,p.event?.event);};
    c.on('mouseover',over);c.on('mouseout',out);c.on('click',click);
    entry.cleanups.push(()=>{if(!c.isDisposed()){c.off('mouseover',over);c.off('mouseout',out);c.off('click',click);}});
    const oldTab=host.getAttribute('tabindex');if(oldTab===null)host.tabIndex=0;
    entry.cleanups.push(()=>{if(oldTab===null)host.removeAttribute('tabindex');});
    entry.cleanups.push(on(host,'keydown',event=>{
      if(event.target!==host||!['ArrowLeft','ArrowRight','Home','End','Enter',' '].includes(event.key))return;
      const rows=entry.rows();if(!rows.length)return;event.preventDefault();event.stopPropagation();
      if(['Enter',' '].includes(event.key)){const p=rows[entry.index];locked={host,p};focusNative(entry,p);if(p.data?.meta)onClick?.(p.data.meta);return;}
      entry.index=event.key==='Home'?0:event.key==='End'?rows.length-1:(entry.index+(event.key==='ArrowLeft'?rows.length-1:1))%rows.length;focusNative(entry,rows[entry.index]);
    }));
    requestAnimationFrame(()=>{
      if(c.isDisposed()||!active()||preference.matches||!visible(host))return;
      const opt=c.getOption();opt.series.forEach((s,si)=>{
        if(s.type==='radar'&&!s.silent){
          const ds=c.getModel().getSeriesByIndex(si).getData();ds.each(i=>{const symbols=ds.getItemGraphicEl(i)?.children?.().find(el=>el.type==='group');symbols?.children?.().forEach((el,vertex)=>el.animateFrom({style:{opacity:0}},{duration:320,delay:Math.min(260,vertex*45),scope:'lens-chart'}));});
        }
        if(!['heatmap','parallel','custom','sankey'].includes(s.type))return;
        const series=c.getModel().getSeriesByIndex(si),ds=s.type==='sankey'?series.getEdgeData():series.getData();
        ds.each(i=>{const el=ds.getItemGraphicEl(i);if(!el)return;el.animateFrom({style:{opacity:0}},{duration:640,delay:Math.min(260,i*260/Math.max(1,ds.count()-1)),scope:'lens-chart'});played++;});
      });
      if(opt.series.some(s=>s.type==='sankey'))animate($('svg',host),{clipPath:['inset(0 100% 0 0)','inset(0 0% 0 0)']},720);
    });
    // Run after the owner's resize. Attached native text animators can be cancelled
    // by resize mid-fade; SVG WAAPI leaves no residual attributes on those labels.
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(c.isDisposed()||!active()||preference.matches||!visible(host))return;
      const labels=new Set();c.getOption().series.forEach((s,si)=>{if(s.silent||!['bar','scatter'].includes(s.type))return;const ds=c.getModel().getSeriesByIndex(si).getData();ds.each(i=>{const text=ds.getItemGraphicEl(i)?.getTextContent?.()?.style?.text;if(text!=null)labels.add(String(text));});});
      $$('svg text',host).filter(n=>labels.has(n.textContent)).forEach((n,i)=>animate(n,{opacity:[0,Number(getComputedStyle(n).opacity)]},440,Math.min(180,i*28)));
    }));
    watchVisibility(host);
  }
  function beforeDispose(){for(const [c,entry]of native){finishNative(c);entry.cleanups.forEach(f=>f());visibility.unobserve(entry.host);observed.delete(entry.host);}native.clear();locked=null;clearVisual();}
  function resize(c){const entry=native.get(c);c.resize({animation:{duration:active()&&!preference.matches&&(!entry||visible(entry.host))?(entry&&!entry.resized?entry.duration:320):0,easing:'cubicOut'}});if(entry)entry.resized=true;}
  function plotly(host){
    svg(host,{key:'box'});const entry=entries.get(host);if(!entry)return;
    const hover=event=>{const p=event.points?.[0];if(!p)return;clearVisual();const categories=[...new Set((p.data?.x||[]).map(String))],boxes=$$('.boxlayer .trace',host)[p.curveNumber]?.querySelectorAll('.box'),index=categories.indexOf(String(p.x));const node=boxes?.length===categories.length&&index>=0?boxes[index]:null;if(node){const r=node.getBoundingClientRect();overlay('cm-marker',{x:r.x-3,y:r.y-3,width:r.width+6,height:r.height+6});}hoverCount++;};
    host.on('plotly_hover',hover);host.on('plotly_unhover',clearVisual);
    entry.cleanups.push(()=>{host.removeListener?.('plotly_hover',hover);host.removeListener?.('plotly_unhover',clearVisual);});
  }
  function progress(slider,index,total){
    if(!slider)return;const parent=slider.parentElement;let track=$('.cm-progress',parent);
    if(!track){track=document.createElement('span');track.className='cm-progress';track.setAttribute('aria-hidden','true');parent.append(track);}
    const box=slider.getBoundingClientRect(),outer=parent.getBoundingClientRect();
    Object.assign(track.style,{left:(box.x-outer.x+8)+'px',top:(box.y-outer.y+box.height/2-5)+'px',width:Math.max(0,box.width-16)+'px'});
    track.replaceChildren(...Array.from({length:total},(_,i)=>{const dot=document.createElement('i');if(i===index)dot.setAttribute('aria-current','step');return dot;}));
  }
  function codeDiff(root){
    const nodes=$$('.answer-content.code',root).filter(n=>n.closest('.prompt-comparison'));if(nodes.length!==2||nodes[0].dataset.cmDiff)return;
    const rows=nodes.map(n=>n.textContent.split('\n')),a=rows[0],b=rows[1];
    const dp=Array.from({length:a.length+1},()=>Array(b.length+1).fill(0));
    for(let i=a.length-1;i>=0;i--)for(let j=b.length-1;j>=0;j--)dp[i][j]=a[i]===b[j]?1+dp[i+1][j+1]:Math.max(dp[i+1][j],dp[i][j+1]);
    const same=[new Set(),new Set()];let i=0,j=0;
    while(i<a.length&&j<b.length){if(a[i]===b[j]){same[0].add(i++);same[1].add(j++);}else if(dp[i+1][j]>=dp[i][j+1])i++;else j++;}
    nodes.forEach((node,k)=>{const original=node.textContent;node.dataset.cmDiff='';node.replaceChildren(...rows[k].map((line,index)=>{const span=document.createElement('span');span.textContent=line+(index<rows[k].length-1?'\n':'');if(!same[k].has(index))span.className=k?'cm-code-added':'cm-code-removed';return span;}));if(node.textContent!==original)throw Error('Code annotation changed evidence');});
  }
  function svgLabel(node){
    const own=node.querySelector?.('title')?.textContent||node.getAttribute('aria-label')||node.dataset.codeLabel;
    if(own)return own;
    let next=node.nextElementSibling;for(let i=0;i<2&&next;i++,next=next.nextElementSibling)if(next.tagName.toLowerCase()==='title')return next.textContent;
    if(node.closest('#plot')&&kind()==='concise'&&!$('[data-view=cross][aria-pressed=true]')){
      const circles=$$('#plot circle'),row=window.LENS_STORY?.baseline[circles.indexOf(node)%3];if(row)return `${row.prompt}\n评分 ${number(row.score_pct)}%\n平均返回 ${number(row.mean_tokens)} token\n${row.questions} 道同题`;
    }
    if(node.closest('#plot')&&kind()==='language'){
      const task=$('#research [data-task][aria-pressed=true]')?.dataset.task;
      const row=window.LENS_STORY?.chinese.filter(r=>r.task===task)[[92,154,216,278].indexOf(+node.getAttribute('cy'))];
      if(row)return `${row.model} · ${task}\nDefaultCoT ${row.default_score_pct}% → ChineseCoT ${row.chinese_score_pct}%\n${row.default_tokens} → ${row.chinese_tokens} output token`;
    }
    return '';
  }
  function focusSVG(entry,node,event){
    clearVisual();if(!active()||!node?.isConnected)return;
    const r=node.getBoundingClientRect();overlay('cm-marker',{x:r.x-3,y:r.y-3,width:r.width+6,height:r.height+6});
    const text=svgLabel(node);if(text&&!node.closest('#code-publication')&&!node.matches('.radial-bar'))showLabel(text,event,entry.host);
    if(node.matches('circle,use')&&r.width<35)overlay('cm-reference',{x:r.x+r.width/2,y:entry.svg.getBoundingClientRect().y+36,width:1,height:Math.max(0,entry.svg.getBoundingClientRect().height-80)});
    hoverCount++;
  }
  function svg(host,options={}){
    prune();
    const source=host?.querySelector('svg');if(!source||!active()||host.querySelector('#code-vega-scatter'))return;
    let entry=entries.get(host);const first=!entry||entry.key!==options.key;
    if(entry?.svg===source)return;
    if(entry)for(const item of [...effects.values()])if(entry.svg.contains(item.el))item.finish();
    entry?.cleanups.forEach(f=>f());
    const targets=$$('[data-profile-prompt],[data-pub-prompt],[data-efficiency-model],.radial-bar,[data-code-action],[role="graphics-symbol"][aria-label],circle,rect[data-record]',source).filter(n=>svgLabel(n)&&!n.closest('defs')&&!n.parentElement.closest('[data-profile-prompt],[data-code-action]'));
    entry={host,svg:source,key:options.key,targets,index:0,cleanups:[]};entries.set(host,entry);
    const pick=target=>targets.find(n=>n===target||n.contains(target));
    entry.cleanups.push(on(host,'pointerover',e=>{const n=pick(e.target);if(n)focusSVG(entry,n,e);}));
    entry.cleanups.push(on(host,'pointerout',()=>{if(locked?.host!==host)clearVisual();}));
    entry.cleanups.push(on(host,'click',e=>{const node=pick(e.target);if(!node)return;locked=locked?.node===node?null:{host,node};if(locked)focusSVG(entry,node,e);else clearVisual();}));
    const oldTab=host.getAttribute('tabindex');if(oldTab===null)host.tabIndex=0;
    entry.cleanups.push(()=>{if(oldTab===null)host.removeAttribute('tabindex');});
    entry.cleanups.push(on(host,'keydown',e=>{
      if(e.target!==host||!targets.length||!['ArrowLeft','ArrowRight','Home','End','Enter',' '].includes(e.key))return;e.preventDefault();e.stopPropagation();
      if(['Enter',' '].includes(e.key)){const node=targets[entry.index];node.dispatchEvent(new MouseEvent('click',{bubbles:true}));return;}
      entry.index=e.key==='Home'?0:e.key==='End'?targets.length-1:(entry.index+(e.key==='ArrowLeft'?targets.length-1:1))%targets.length;focusSVG(entry,targets[entry.index]);
    }));
    if(first&&!preference.matches){
      const curve=$$('path',source).filter(n=>getComputedStyle(n).stroke!=='none'&&getComputedStyle(n).fill==='none'&&!n.closest('defs,[id^="matplotlib.axis_"]')&&n.getTotalLength?.()>25);
      curve.slice(0,40).forEach((n,i)=>{const length=n.getTotalLength();animate(n,{strokeDasharray:[`${length} ${length}`,`${length} ${length}`],strokeDashoffset:[length,0],opacity:[.15,1]},680,Math.min(180,i*22));});
      const cells=$$('[data-profile-prompt] rect',source);
      (cells.length?cells:targets).slice(0,150).forEach((n,i)=>animate(n,{opacity:[0,Number(getComputedStyle(n).opacity)]},440,Math.min(260,i*(cells.length?5:20))));
      // Plotly boxes retain their single exact path: reveal from median outward, never recompute quartiles.
      $$('.boxlayer .box',source).forEach((n,i)=>{const median=+(n.getAttribute('d').match(/^M[^,]+,([-\d.]+)/)?.[1]),box=n.getBBox();if(!Number.isFinite(median)||!box.height)return;const pct=(median-box.y)/box.height*100;animate(n,{clipPath:[`inset(${Math.max(0,pct-.4)}% 0 ${Math.max(0,100-pct-.4)}% 0)`,'inset(0% 0 0% 0)'],opacity:[.3,1]},720,Math.min(160,i*35));});
    }
    if(options.step!=null){
      const focused=$$('circle[r="7"]',source).filter(n=>n.nextElementSibling?.tagName.toLowerCase()==='title');
      focused.forEach(n=>animate(n,{opacity:[.4,1]},180));
    }
    watchVisibility(host);
  }
  const observed=new WeakSet();
  const visibility=new IntersectionObserver(items=>{for(const item of items)if(!item.isIntersecting){
    for(const effect of [...effects.values()])if(item.target.contains(effect.el))effect.finish();
    for(const [c,entry]of native)if(entry.host===item.target)finishNative(c);
  }},{threshold:0});
  function watchVisibility(host){if(!observed.has(host)){observed.add(host);visibility.observe(host);}}
  function count(el){
    const original=el.textContent,match=original.match(/[\d,]+(?:\.\d+)?(?=[^\d]*$)/);if(!match)return;
    const target=+match[0].replaceAll(',','');if(!Number.isFinite(target)||target<100)return;
    const style=el.getAttribute('style'),width=el.getBoundingClientRect().width;el.style.minWidth=width+'px';
    let id;const finish=()=>{cancelAnimationFrame(id);el.textContent=original;if(style===null)el.removeAttribute('style');else el.setAttribute('style',style);counters.delete(el);};
    const start=performance.now();let previous=0;
    const tick=now=>{if(!active()||!el.isConnected||now-start>=660){finish();return;}if(now-previous>32){previous=now;const v=Math.round(target*(1-Math.pow(1-(now-start)/660,3)));el.textContent=original.slice(0,match.index)+number(v)+original.slice(match.index+match[0].length);}id=requestAnimationFrame(tick);};
    counters.set(el,{finish});id=requestAnimationFrame(tick);
  }
  function prune(){for(const effect of [...effects.values()])if(!effect.el.isConnected)effect.finish();if(locked&&(!locked.host.isConnected||(locked.node&&!locked.node.isConnected)))locked=null;for(const [host,entry]of entries)if(!host.isConnected){for(const effect of [...effects.values()])if(entry.svg.contains(effect.el))effect.finish();entry.cleanups.forEach(f=>f());entries.delete(host);visibility.unobserve(host);observed.delete(host);}for(const [c,entry]of native)if(!entry.host.isConnected||c.isDisposed()){entry.cleanups.forEach(f=>f());native.delete(c);visibility.unobserve(entry.host);observed.delete(entry.host);}for(const [host,observer]of watchers)if(!host.isConnected){observer.disconnect();watchers.delete(host);}}
  function refresh(root,key){
    if(!active()){settle({players:true});return;}prune();
    const changed=key!==scene;scene=key;
    for(const host of $$('#plot,.overview-plot,#publication-root,#code-publication,#anomaly-waffle,#library-main[data-renderer=plotly]',root)){
      if(host.id==='plot'&&entries.has(host))continue;svg(host,{key});
      if(!watchers.has(host)){
        const observer=new MutationObserver(()=>{if(!host.isConnected)return;svg(host,{key});});observer.observe(host,{childList:true});watchers.set(host,observer);
      }
    }
    if(changed&&key==='collection'&&!preference.matches)$$('.task-row>strong,.special-studies>div>span:last-child',root).forEach(count);
    if(changed&&key==='collection')$$('.experiment-flow>i',root).forEach((n,i)=>animate(n,{opacity:[0,1]},400,80+i*150));
    if(changed&&key==='cleaning')$$('.cleaning-steps>li>strong',root).forEach((n,i)=>animate(n,{opacity:[.4,1]},280,i*170));
    if(key==='repair')codeDiff(root);
    if($('#round'))progress($('#round'),+$('#round').value,5);
    if($('#position'))progress($('#position'),+$('#position').value,9);
    if($('#code-sample-step'))progress($('#code-sample-step'),+$('#code-sample-step').value-1,5);
  }
  function transitionChart(render){
    if(!active()||preference.matches||!document.startViewTransition){render();return;}
    transition?.skipTransition();const host=$('#library-main');if(!host){render();return;}
    host.style.viewTransitionName='lens-chart-layout';
    try{transition=document.startViewTransition(()=>{render();const next=$('#library-main');if(next)next.style.viewTransitionName='lens-chart-layout';});transition.finished.catch(()=>{}).finally(()=>{$$('#library-main').forEach(n=>n.style.removeProperty('view-transition-name'));transition=null;});}catch{host.style.removeProperty('view-transition-name');render();}
  }
  listeners.push(on(document,'pointerover',e=>{
    if(!active())return;const card=e.target.closest('#question .question-points>li');if(!card)return;
    $$('path,circle',card.querySelector('.point-icon')).forEach(n=>animate(n,{opacity:[.45,1]},160));
  }));
  listeners.push(on(document,'pointerover',e=>{
    const legend=e.target.closest('.legend-item');if(!legend||!active())return;const name=legend.textContent.trim(),model=window.COURSE_SUMMARY?.models.find(m=>m.name===name)?.id;
    clearVisual();for(const [c]of native){if(c.isDisposed())continue;c.getOption().series.forEach((s,si)=>(s.data||[]).forEach((d,di)=>{if(s.name===name||d.name===name||(model&&d.meta?.model===model))c.dispatchAction({type:'highlight',seriesIndex:si,dataIndex:di});}));}
  }));
  listeners.push(on(document,'pointerout',e=>{if(e.target.closest('.legend-item'))clearVisual();}));
  listeners.push(on(document,'click',e=>{
    if(!active())return;
    const step=e.target.closest('#cleaning .cleaning-steps>li');
    if(step&&step.nextElementSibling&&!preference.matches){const dot=document.createElement('i');dot.className='cm-pipeline-dot';dot.setAttribute('aria-hidden','true');step.append(dot);transient.add(dot);animate(dot,{opacity:[0,1,0],transform:['translateY(0px)',`translateY(${Math.max(0,step.offsetHeight-43)}px)`]},650);setTimeout(()=>{dot.remove();transient.delete(dot);},750);}
    const card=e.target.closest('#question .question-points>li');if(card)$$('.point-icon path,.point-icon circle',card).forEach(n=>{const len=n.getTotalLength?.();if(len)animate(n,{strokeDasharray:[`${len} ${len}`,`${len} ${len}`],strokeDashoffset:[len,0]},350);});
  }));
  listeners.push(on(document,'pointerdown',e=>{const host=e.target.closest('#code-vega-scatter');if(host)for(const item of [...effects.values()])if(host.contains(item.el))item.finish();}));
  listeners.push(on(document,'change',e=>{if(active()&&e.target.matches('select,input[type=checkbox]')){locked=null;clearVisual();animate(e.target,{boxShadow:['0 0 0 0 #789aad00','0 0 0 3px #789aad66','0 0 0 0 #789aad00']},300);}},true));
  listeners.push(on(document,'click',e=>{if(e.target.closest('#download-svg,#download-csv,[data-action^="export-"],[data-code-action="svg"],[data-code-action="export-summary"],#code-export-records'))beforeExport();},true));
  listeners.push(on(document,'keydown',e=>{if(e.key==='Escape'){locked=null;clearVisual();}}));
  listeners.push(on(document,'scroll',()=>clearVisual(),true));listeners.push(on(window,'resize',clearVisual));
  listeners.push(on(document,'visibilitychange',()=>{if(document.hidden)settle({players:true});}));
  listeners.push(on(preference,'change',()=>settle({players:true})));
  const dispose=()=>{if(disposed)return;settle({players:true});beforeDispose();disposed=true;visibility.disconnect();for(const entry of entries.values())entry.cleanups.forEach(f=>f());entries.clear();for(const observer of watchers.values())observer.disconnect();watchers.clear();listeners.splice(0).forEach(f=>f());tip?.remove();if(frame)cancelAnimationFrame(frame);};
  listeners.push(on(window,'pagehide',dispose));
  window.LensChartMotion={configure,register,svg,plotly,resize,refresh,progress,beforeDispose,beforeExport,settle,animate,transition:transitionChart,handles:node=>!!node.querySelector('#plot,.overview-plot,svg')||node.matches('#plot,.overview-plot'),inspect:()=>({version:1,scene,played,hoverCount,running:effects.size,detachedEffects:[...effects.values()].filter(item=>!item.el.isConnected).length,counters:counters.size,nativeRunning:[...native.keys()].filter(c=>!c.isDisposed()&&!c.getZr().animation.isFinished()).length,nativeCharts:native.size,svgCharts:entries.size,locked:!!locked,reduced:preference.matches,disposed}),dispose};
})();
