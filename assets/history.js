(() => {
  const progress = document.querySelector('.reading-progress');
  const chapters = [...document.querySelectorAll('.chapter[id]')];
  const links = [...document.querySelectorAll('.timeline-nav a')];
  let scheduled = false;
  function update() {
    scheduled = false;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (progress) progress.style.transform = `scaleX(${max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0})`;
    let active = chapters[0];
    for (const chapter of chapters) if (chapter.getBoundingClientRect().top <= 190) active = chapter;
    for (const link of links) {
      if (active && link.hash === '#' + active.id) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    }
  }
  function schedule() { if (!scheduled) { scheduled = true; requestAnimationFrame(update); } }
  function openSource() {
    const id = decodeURIComponent(location.hash.slice(1));
    if (!/^source-\d+$/.test(id)) return;
    const target = document.getElementById(id);
    const details = document.getElementById('sources');
    if (target && details) { details.open = true; requestAnimationFrame(() => target.scrollIntoView()); }
  }
  window.addEventListener('scroll', schedule, {passive:true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', openSource);
  window.addEventListener('load', () => { update(); openSource(); });
  update();
})();
