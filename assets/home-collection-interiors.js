(function () {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function whenVisible(element, options, callback) {
    if (!('IntersectionObserver' in window)) {
      callback();
      return;
    }
    const observer = new IntersectionObserver(entries => {
      if (!entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= (options.threshold || 0))) return;
      observer.disconnect();
      callback();
    }, options);
    observer.observe(element);
  }

  document.querySelectorAll('.ev-interiors').forEach(gallery => {
    const board = gallery.parentElement;
    const sheet = gallery.querySelector('.ev-interiors__sheet');
    const preview = gallery.querySelector('.ev-interiors__preview');
    const opener = gallery.querySelector('.ev-interiors__opener');
    const hint = gallery.querySelector('.ev-interiors__hint');
    const track = gallery.querySelector('.ev-interiors__track');
    const slides = Array.from(track.children);
    const previous = gallery.querySelector('.ev-interiors__previous');
    const close = gallery.querySelector('.ev-interiors__close');
    const announcement = gallery.querySelector('.ev-interiors__announcement');
    let selected = 0;
    let scrollFrame = 0;
    let slideFrame = 0;

    function loadPreview() {
      if (!preview.hasAttribute('src')) preview.src = preview.dataset.src;
    }

    function loadSlide(index) {
      const slide = slides[index];
      if (!slide) return;
      const image = slide.querySelector('img');
      if (image.hasAttribute('src')) return;
      const mobileSource = slide.querySelector('source');
      image.addEventListener('load', () => slide.classList.add('is-loaded'), { once: true });
      mobileSource.srcset = mobileSource.dataset.srcset;
      image.srcset = image.dataset.srcset;
      image.src = image.dataset.src;
    }

    function selectSlide(index) {
      const outgoing = slides[selected];
      if (outgoing.contains(document.activeElement)) track.focus({ preventScroll: true });
      outgoing.setAttribute('aria-hidden', 'true');
      outgoing.inert = true;
      selected = index;
      slides[selected].setAttribute('aria-hidden', 'false');
      slides[selected].inert = false;
      loadSlide(selected);
      loadSlide(selected + 1);
      loadSlide(selected - 1);
      previous.disabled = selected === 0;
      announcement.textContent = slides[selected].querySelector('figcaption').textContent;
    }

    function stopSlideAnimation() {
      if (!slideFrame) return;
      cancelAnimationFrame(slideFrame);
      slideFrame = 0;
      track.classList.remove('is-animating');
    }

    function animateToSlide(index) {
      const style = getComputedStyle(sheet);
      const duration = parseFloat(style.transitionDuration) * 1000;
      // Use the opening transition's easing to drive the real scroll position.
      const timing = new Animation(new KeyframeEffect(null, [], {
        duration,
        easing: style.transitionTimingFunction,
        fill: 'both',
      }));
      const from = track.scrollLeft;
      const started = performance.now();
      if (slides[selected].contains(document.activeElement)) track.focus({ preventScroll: true });
      loadSlide(index);
      track.classList.add('is-animating');

      function step(now) {
        const elapsed = Math.max(0, now - started);
        timing.currentTime = elapsed;
        const progress = timing.effect.getComputedTiming().progress;
        const target = index * track.clientWidth;
        track.scrollTo({ left: from + (target - from) * progress, behavior: 'instant' });
        if (elapsed < duration) {
          slideFrame = requestAnimationFrame(step);
          return;
        }
        stopSlideAnimation();
        selectSlide(index);
      }

      slideFrame = requestAnimationFrame(step);
    }

    function move(direction, animate = false) {
      const index = selected + direction;
      if (!slides[index]) return;
      if (animate) {
        if (!slideFrame) animateToSlide(index);
        return;
      }
      stopSlideAnimation();
      track.scrollTo({ left: index * track.clientWidth, behavior: reducedMotion.matches ? 'instant' : 'smooth' });
    }

    opener.addEventListener('click', () => {
      loadPreview();
      track.scrollLeft = 0;
      selectSlide(0);
      sheet.inert = false;
      // Establish the starting transform before revealing the sheet.
      sheet.getBoundingClientRect();
      gallery.classList.add('is-open');
      opener.setAttribute('aria-expanded', 'true');
      hint.hidden = true;
      track.focus({ preventScroll: true });
      opener.hidden = true;
    });

    function closeGallery() {
      stopSlideAnimation();
      gallery.classList.remove('is-open');
      sheet.inert = true;
      announcement.textContent = '';
      opener.hidden = false;
      opener.setAttribute('aria-expanded', 'false');
      opener.focus({ preventScroll: true });
    }
    close.addEventListener('click', closeGallery);
    gallery.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || !gallery.classList.contains('is-open')) return;
      event.preventDefault();
      closeGallery();
    });

    track.addEventListener('scroll', () => {
      if (scrollFrame || slideFrame) return;
      scrollFrame = requestAnimationFrame(() => {
        scrollFrame = 0;
        if (slideFrame || !gallery.classList.contains('is-open') || !track.clientWidth) return;
        const index = Math.round(track.scrollLeft / track.clientWidth);
        if (slides[index] && index !== selected) selectSlide(index);
      });
    }, { passive: true });
    track.addEventListener('pointerdown', event => {
      if (event.pointerType === 'touch' && !event.target.closest('button')) stopSlideAnimation();
    }, { passive: true });
    track.addEventListener('wheel', event => {
      if (event.deltaX) stopSlideAnimation();
    }, { passive: true });
    track.addEventListener('keydown', event => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      move(event.key === 'ArrowRight' ? 1 : -1);
    });
    track.addEventListener('click', event => {
      if (event.target.closest('.ev-interiors__next')) move(1, true);
    });
    previous.addEventListener('click', () => move(-1, true));

    board.classList.add('ev-interiors-artboard');
    gallery.hidden = false;
    whenVisible(gallery, { rootMargin: '160px 0px' }, loadPreview);
    whenVisible(hint, { threshold: .95 }, () => gallery.classList.add('is-hinting'));
  });
}());
