/* Display motion for the latest five-part deck; data and routes stay upstream. */
(() => {
  'use strict';
  const preference=matchMedia('(prefers-reduced-motion: reduce)');
  const running=new Map(), byElement=new WeakMap();
  const metrics={played:0,chapterTransitions:0,plotUpdates:0,sectionTransitions:0};
  let chapter=null, plotObserver=null;
  const canPlay=()=>!preference.matches&&!document.hidden&&!document.documentElement.matches('.intro-pending,.intro-active');
  function cancel(el){const c=byElement.get(el);if(c){c.cancel();running.delete(c);byElement.delete(el);}}
  function play(el,frames,options={}){
    if(!el?.getClientRects().length||!canPlay()||!window.LensMotion?.animate)return;
    cancel(el);
    const c=window.LensMotion.animate(el,frames,{duration:.45,ease:[.16,1,.3,1],...options});
    running.set(c,el);byElement.set(el,c);metrics.played++;
    c.finished.then(()=>{running.delete(c);if(byElement.get(el)===c)byElement.delete(el);}).catch(()=>running.delete(c));
  }
  function settle(){for(const [c,el] of running){if(el.isConnected&&el.getClientRects().length){c.complete();c.stop();}else c.cancel();byElement.delete(el);}running.clear();}
  function moveMarker(nav,rail,instant=false){
    const active=nav?.querySelector('[aria-current="page"]');
    if(!active?.getClientRects().length)return;
    let marker=nav.querySelector('.deck-nav-marker');
    if(!marker){marker=document.createElement('span');marker.className='deck-nav-marker';marker.setAttribute('aria-hidden','true');nav.append(marker);}
    const a=active.getBoundingClientRect(),n=nav.getBoundingClientRect(),vertical=rail&&innerWidth>900;
    marker.style.width=vertical?'2px':a.width+'px';marker.style.height=vertical?Math.max(20,a.height-20)+'px':'2px';
    marker.classList.toggle('is-vertical',vertical);
    const transform=vertical?`translateY(${a.top-n.top+10}px)`:`translateX(${a.left-n.left+nav.scrollLeft}px)`;
    if(instant||!canPlay()){cancel(marker);marker.style.transform=transform;}else play(marker,{transform},{duration:.42});
    nav.classList.add('has-deck-marker');
  }
  function markers(instant=false){moveMarker(document.querySelector('.chapter-rail-nav'),true,instant);moveMarker(document.querySelector('.finding-nav'),false,instant);}
  function onSection(section,changed){
    settle();
    markers(!changed);
    if(!changed)return;
    metrics.sectionTransitions++;
    const panel=document.getElementById(section);
    play(panel?.querySelector('.panel-header,.question-copy'),{opacity:[.65,1],transform:['translateY(14px)','translateY(0px)']},{duration:.5});
    play(panel?.querySelector('.collection-layout,.cleaning-layout,#landscape-scene,.finding-stage,.question-scale'),{opacity:[.8,1],transform:['translateY(16px)','translateY(0px)']},{duration:.52,delay:.04});
  }
  function onRender(next){
    plotObserver?.disconnect();
    const changed=chapter!==next;chapter=next;
    markers(!changed);
    for(const [c,el] of running)if(!el.isConnected){c.cancel();running.delete(c);}
    if(changed){metrics.chapterTransitions++;play(document.querySelector('.finding-intro'),{opacity:[.75,1],transform:['translateY(12px)','translateY(0px)']},{duration:.5});play(document.querySelector('.figure-sheet'),{transform:['translateY(14px)','translateY(0px)']},{duration:.5,delay:.04});}
    const plot=document.querySelector('#plot');
    if(plot){plotObserver=new MutationObserver(()=>{metrics.plotUpdates++;play(plot,{opacity:[.8,1]},{duration:.22});});plotObserver.observe(plot,{childList:true});}
  }
  const overview=document.querySelector('.overview-plot');
  if(overview)new MutationObserver(()=>{metrics.plotUpdates++;play(overview,{opacity:[.8,1],transform:['translateY(5px)','translateY(0px)']},{duration:.28});}).observe(overview,{childList:true});
  // narrative.js creates the overview after this deferred module initializes.
  const scene=document.getElementById('landscape-scene');
  if(scene)new MutationObserver(records=>{if(records.some(r=>r.target.matches?.('.overview-plot'))){metrics.plotUpdates++;play(scene.querySelector('.overview-plot'),{opacity:[.82,1]},{duration:.24});}}).observe(scene,{childList:true,subtree:true});
  preference.addEventListener('change',()=>{settle();markers(true);});
  let resizeFrame=0;
  addEventListener('resize',()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{resizeFrame=0;markers(true);});});
  document.querySelector('.finding-nav')?.addEventListener('scroll',()=>markers(true),{passive:true});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)settle();});
  document.addEventListener('lens:intro-finished',settle);
  window.LensMotionUI={onRender,onSection,settle,inspect:()=>({...metrics,reduced:preference.matches,running:running.size})};
})();
