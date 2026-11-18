/* Load decorative media when it approaches the viewport. */
(function () {
  'use strict';
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var smallScreen = window.matchMedia('(max-width: 959px)');

  function background(element) {
    element.style.backgroundImage = 'url(' + JSON.stringify(element.dataset.evBackground) + ')';
    element.removeAttribute('data-ev-background');
    element.classList.add('loaded');
  }

  function prepareVideo(video) {
    if (video.dataset.evLoaded) return;
    var useMobileSource = smallScreen.matches || (navigator.connection && navigator.connection.saveData);
    video.defaultMuted = true;
    video.muted = true;
    video.playsInline = true;
    video.querySelectorAll('source[data-ev-src]').forEach(function (source) {
      var mobileSource = useMobileSource && source.dataset.evMobileSrc;
      source.src = mobileSource || source.dataset.evSrc;
      source.removeAttribute('data-ev-src');
    });
    video.dataset.evLoaded = 'true';
    video.load();
  }

  function play(video) {
    if (document.hidden) return;
    video.autoplay = !reducedMotion.matches;
    prepareVideo(video);
    if (!video.autoplay) {
      video.controls = true;
      return;
    }
    var promise = video.play();
    if (promise) {
      promise.then(function () {
        video.controls = false;
      }, function (error) {
        if (video.autoplay && error.name !== 'AbortError') video.controls = true;
      });
    }
  }

  function pause(video) {
    video.autoplay = false;
    video.pause();
  }

  function start() {
    var videos = Array.from(document.querySelectorAll('video[data-ev-lazy-video]'));
    var backgrounds = document.querySelectorAll('[data-ev-background]');
    if (!('IntersectionObserver' in window)) {
      backgrounds.forEach(background);
      videos.forEach(play);
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
        if (!entry.isIntersecting) { pause(video); return; }
        // Tilda moves zero blocks after parsing. Recheck their settled
        // geometry so a temporary position at y=0 cannot fetch an entire MP4.
        video.evVisibilityTimer = setTimeout(function () {
          var rect = video.getBoundingClientRect();
          if (!rect.width || !rect.height || rect.bottom <= 0 || rect.top >= window.innerHeight) return;
          video.dataset.evVisible = 'true';
          play(video);
        }, 250);
      });
    }, { threshold: [0, 0.01] });
    videos.forEach(function (video) {
      var board = video.closest('.t396__artboard');
      if (board && !board.classList.contains('rendered')) {
        board.addEventListener('artBoardRendered', function () { playback.observe(video); }, { once: true });
      } else playback.observe(video);
    });
    document.addEventListener('visibilitychange', function () {
      videos.forEach(function (video) {
        if (document.hidden) pause(video);
        else if (video.dataset.evVisible === 'true') play(video);
      });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
}());
