/* Load decorative media when it approaches the viewport. */
(function () {
  'use strict';
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var saveData = navigator.connection && navigator.connection.saveData;

  function background(element) {
    element.style.backgroundImage = 'url(' + JSON.stringify(element.dataset.evBackground) + ')';
    element.removeAttribute('data-ev-background');
    element.classList.add('loaded');
  }

  function prepareVideo(video) {
    if (video.dataset.evLoaded) return;
    video.querySelectorAll('source[data-ev-src]').forEach(function (source) {
      source.src = source.dataset.evSrc;
      source.removeAttribute('data-ev-src');
    });
    video.dataset.evLoaded = 'true';
    video.muted = true;
    video.load();
  }

  function play(video) {
    if (document.hidden || reducedMotion.matches || saveData) return;
    var promise = video.play();
    if (promise) promise.catch(function () { video.controls = true; });
  }

  function start() {
    var videos = Array.from(document.querySelectorAll('video[data-ev-lazy-video]'));
    var backgrounds = document.querySelectorAll('[data-ev-background]');
    if (!('IntersectionObserver' in window)) {
      backgrounds.forEach(background);
      videos.forEach(function (video) { prepareVideo(video); video.controls = true; });
      return;
    }
    var images = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        background(entry.target);
        images.unobserve(entry.target);
      });
    }, { rootMargin: '600px 0px' });
    backgrounds.forEach(function (element) {
      var board = element.closest('.t396__artboard');
      if (board && !board.classList.contains('rendered')) {
        board.addEventListener('artBoardRendered', function () { images.observe(element); }, { once: true });
      } else images.observe(element);
    });
    var playback = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var video = entry.target;
        clearTimeout(video.evVisibilityTimer);
        video.dataset.evVisible = 'false';
        if (!entry.isIntersecting) { video.pause(); return; }
        // Tilda moves zero blocks after parsing. Recheck their settled
        // geometry so a temporary position at y=0 cannot fetch an entire MP4.
        video.evVisibilityTimer = setTimeout(function () {
          var rect = video.getBoundingClientRect();
          if (!rect.width || !rect.height || rect.bottom < -200 || rect.top > innerHeight + 200) return;
          video.dataset.evVisible = 'true';
          prepareVideo(video);
          if (reducedMotion.matches || saveData) video.controls = true;
          else play(video);
        }, 250);
      });
    }, { rootMargin: '200px 0px' });
    videos.forEach(function (video) {
      var board = video.closest('.t396__artboard');
      if (board && !board.classList.contains('rendered')) {
        board.addEventListener('artBoardRendered', function () { playback.observe(video); }, { once: true });
      } else playback.observe(video);
    });
    document.addEventListener('visibilitychange', function () {
      videos.forEach(function (video) {
        if (document.hidden) video.pause();
        else if (video.dataset.evVisible === 'true') play(video);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
}());
