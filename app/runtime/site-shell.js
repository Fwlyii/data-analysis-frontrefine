/* Common brand and library presentation. Scientific renderers own their data. */
(() => {
  'use strict';
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Map(), byElement = new WeakMap();
  const metrics = {played: 0, renders: 0, dialogs: 0};
  function cancel(element) {
    const previous = byElement.get(element);
    if (!previous) return;
    // cancel() works for a node that has just become hidden or detached.
    previous.cancel(); running.delete(previous); byElement.delete(element);
  }
  function play(element, frames, options = {}) {
    if (!element || preference.matches || document.hidden || document.documentElement.matches('.intro-pending,.intro-active') || !window.LensMotion?.animate) return;
    cancel(element);
    const controls = window.LensMotion.animate(element, frames, {duration: .4, ease: [.16, 1, .3, 1], ...options});
    byElement.set(element, controls); running.set(controls, element); metrics.played++;
    controls.finished.then(() => {
      running.delete(controls);
      if (byElement.get(element) === controls) byElement.delete(element);
    }).catch(() => running.delete(controls));
  }
  function settle() {
    for (const [controls, element] of running) {
      if (element.isConnected && element.getClientRects().length) { controls.complete(); controls.stop(); }
      else controls.cancel();
      byElement.delete(element);
    }
    running.clear();
  }
  const art = document.querySelector('.wordmark-art');
  art?.decode().then(() => { art.parentElement.classList.add('art-ready'); play(art, {opacity: [.7, 1]}, {duration: .35}); }).catch(() => {});
  preference.addEventListener('change', settle);
  document.addEventListener('visibilitychange', () => { if (document.hidden) settle(); });
  const stage = document.querySelector('#stage');
  if (!stage) return;
  const nav = document.querySelector('.lens-primary-nav');
  const marker = document.createElement('span');
  marker.className = 'lens-nav-marker'; marker.setAttribute('aria-hidden', 'true'); nav?.append(marker);
  let initial = true, resizeFrame;
  function moveMarker(instant = false) {
    const active = nav?.querySelector('[aria-current="page"]'); if (!active) return;
    const inset = parseFloat(getComputedStyle(active).paddingLeft);
    marker.style.width = Math.max(16, active.offsetWidth - inset * 2) + 'px';
    const transform = `translateX(${active.getBoundingClientRect().left - nav.getBoundingClientRect().left + nav.scrollLeft + inset}px)`;
    if (instant || preference.matches) { cancel(marker); marker.style.transform = transform; }
    else play(marker, {transform}, {duration: .42});
    nav.classList.add('has-shared-marker');
  }
  function onRender() {
    // A new renderer has replaced the previous page: release old detached targets.
    for (const [controls, element] of running) if (!element.isConnected) { controls.cancel(); running.delete(controls); }
    metrics.renders++; moveMarker(initial); initial = false;
    stage.querySelectorAll('.plot-content').forEach(region => {
      region.tabIndex = 0; region.setAttribute('role', 'region');
      region.setAttribute('aria-label', '图表，可使用方向键横向滚动');
    });
    play(stage.querySelector('h1'), {transform: ['translateY(10px)', 'translateY(0px)']}, {duration: .5});
    play(stage.querySelector('.explore-controls,.research-toolbar'), {opacity: [.85, 1], transform: ['translateY(6px)', 'translateY(0px)']}, {duration: .35});
    play(stage.querySelector('.plot-surface,.publication-frame'), {transform: ['translateY(12px)', 'translateY(0px)']}, {duration: .5});
  }
  new MutationObserver(onRender).observe(stage, {childList: true});
  const inspector = document.querySelector('#inspector');
  if (inspector) new MutationObserver(() => {
    if (inspector.hidden) { cancel(inspector); return; }
    metrics.dialogs++; play(inspector, {opacity: [.85, 1], transform: ['translateX(24px)', 'translateX(0px)']}, {duration: .28});
  }).observe(inspector, {attributes: true, attributeFilter: ['hidden']});
  preference.addEventListener('change', () => moveMarker(true));
  addEventListener('resize', () => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(() => moveMarker(true)); });
  nav?.addEventListener('scroll', () => moveMarker(true), {passive: true});
  window.LensSiteUI = {settle, inspect: () => ({...metrics, reduced: preference.matches, running: running.size})};
  onRender();
})();
