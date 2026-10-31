/* Presentation-only motion. Research data, routes and controls remain in story.js. */
(() => {
  'use strict';
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Set();
  const byElement = new WeakMap();
  const easing = [.16, 1, .3, 1];
  let chapter = null, observer = null, plotObserver = null;
  let frame = 0;
  const metrics = {played: 0, chapterTransitions: 0, plotUpdates: 0, reveals: 0};
  const nav = document.querySelector('.chapter-nav');
  const marker = document.createElement('span');
  marker.className = 'nav-marker';
  marker.setAttribute('aria-hidden', 'true');
  nav?.append(marker);

  function play(element, keyframes, options = {}) {
    if (!element || preference.matches || document.hidden || !window.LensMotion?.animate) return;
    const previous = byElement.get(element);
    if (previous) { previous.stop(); running.delete(previous); }
    const controls = window.LensMotion.animate(element, keyframes, {duration: .45, ease: easing, ...options});
    byElement.set(element, controls);
    running.add(controls);
    metrics.played++;
    controls.finished.then(() => {
      running.delete(controls);
      if (byElement.get(element) === controls) byElement.delete(element);
    }).catch(() => running.delete(controls));
    return controls;
  }

  function settle() {
    for (const controls of running) { controls.complete(); controls.stop(); }
    running.clear();
  }

  function moveMarker(instant = false) {
    const active = nav?.querySelector('[aria-current="page"]');
    if (!active) return;
    const a = active.getBoundingClientRect(), n = nav.getBoundingClientRect();
    const inset = parseFloat(getComputedStyle(active).paddingLeft);
    const x = a.left - n.left + nav.scrollLeft + inset;
    marker.style.width = Math.max(16, a.width - inset * 2) + 'px';
    const transform = `translateX(${x}px)`;
    if (instant || preference.matches) {
      const previous = byElement.get(marker);
      if (previous) { previous.stop(); running.delete(previous); byElement.delete(marker); }
      marker.style.transform = transform;
    } else play(marker, {transform}, {duration: .42});
    nav.classList.add('has-motion-marker');
  }

  function revealSections() {
    observer?.disconnect();
    if (preference.matches || !('IntersectionObserver' in window)) return;
    observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        metrics.reveals++;
        play(entry.target, {opacity: [.82, 1], transform: ['translateY(14px)', 'translateY(0px)']}, {duration: .5});
        observer.unobserve(entry.target);
      }
    }, {threshold: .12});
    document.querySelectorAll('.evidence-section,.support-section,.chapter-footer').forEach(el => observer.observe(el));
  }

  function onRender(nextChapter) {
    observer?.disconnect();
    plotObserver?.disconnect();
    const changed = chapter !== nextChapter;
    const first = chapter === null;
    chapter = nextChapter;
    moveMarker(first);
    if (changed) {
      metrics.chapterTransitions++;
      play(document.querySelector('.finding h1'), {transform: ['translateY(14px)', 'translateY(0px)']}, {duration: .55});
      play(document.querySelector('.finding .premise'), {opacity: [.82, 1], transform: ['translateY(10px)', 'translateY(0px)']}, {delay: .04});
      play(document.querySelector('.evidence-line'), {opacity: [.82, 1], transform: ['translateY(10px)', 'translateY(0px)']}, {delay: .08});
      play(document.querySelector('.figure-sheet'), {transform: ['translateY(16px)', 'translateY(0px)']}, {duration: .55, delay: .04});
    } else {
      metrics.plotUpdates++;
      play(document.querySelector('#plot'), {opacity: [.8, 1], transform: ['translateY(5px)', 'translateY(0px)']}, {duration: .28});
    }
    const plot = document.querySelector('#plot');
    if (plot) {
      plotObserver = new MutationObserver(() => {
        metrics.plotUpdates++;
        play(plot, {opacity: [.82, 1]}, {duration: .22});
      });
      plotObserver.observe(plot, {childList: true});
    }
    revealSections();
  }

  preference.addEventListener('change', () => {
    settle();
    moveMarker(true);
    revealSections();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) settle(); });
  addEventListener('resize', () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => moveMarker(true));
  });
  nav?.addEventListener('scroll', () => moveMarker(true), {passive: true});
  window.LensMotionUI = {onRender, settle, inspect: () => ({...metrics, reduced: preference.matches, running: running.size})};
})();
