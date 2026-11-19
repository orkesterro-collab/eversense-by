/* Load decorative media when it approaches the viewport. */
(function () {
  'use strict';
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

  function showLoop(video) {
    var image = video.evLoopImage;
    if (!image.naturalWidth || document.hidden || video.dataset.evVisible !== 'true') return;
    video.autoplay = false;
    video.pause();
    video.hidden = true;
    image.hidden = false;
  }

  function useLoop(video) {
    if (!video.autoplay || document.hidden || video.evLoopImage) return;
    var source = video.querySelector('source[data-ev-loop-src]');
    if (!source) {
      video.controls = true;
      return;
    }
    // Some Android browsers reject even muted inline playback. The same
    // silent sequence can play as an animated image without a media gesture.
    var image = new Image();
    image.className = 'ev-video-loop';
    image.alt = '';
    image.style.cssText = video.style.cssText;
    image.hidden = true;
    image.onload = function () { showLoop(video); };
    image.onerror = function () {
      image.remove();
      video.evLoopImage = null;
      video.controls = true;
    };
    video.evLoopImage = image;
    video.after(image);
    image.src = source.dataset.evLoopSrc;
  }

  function play(video) {
    if (document.hidden) return;
    if (video.evLoopImage) {
      showLoop(video);
      return;
    }
    video.autoplay = true;
    prepareVideo(video);
    var promise = video.play();
    if (promise) {
      promise.then(function () {
        video.controls = false;
      }, function () {
        if (video.paused) useLoop(video);
      });
    }
  }

  function pause(video) {
    video.autoplay = false;
    video.pause();
    if (video.evLoopImage) {
      video.evLoopImage.hidden = true;
      video.hidden = false;
    }
  }

  function start() {
    var videos = Array.from(document.querySelectorAll('video[data-ev-lazy-video]'));
    var backgrounds = document.querySelectorAll('[data-ev-background]');
    videos.forEach(function (video) {
      // Source failures need not reject the pending play() promise.
      video.addEventListener('error', function () { useLoop(video); }, true);
      video.addEventListener('pause', function () {
        if (video.paused) useLoop(video);
      });
    });
    if (!('IntersectionObserver' in window)) {
      backgrounds.forEach(background);
      videos.forEach(function (video) {
        video.dataset.evVisible = 'true';
        play(video);
      });
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
        var wrapper = entry.target;
        var video = wrapper.querySelector('video');
        clearTimeout(video.evVisibilityTimer);
        video.dataset.evVisible = 'false';
        if (!entry.isIntersecting) { pause(video); return; }
        // Tilda moves zero blocks after parsing. Recheck their settled
        // geometry so a temporary position at y=0 cannot fetch an entire MP4.
        video.evVisibilityTimer = setTimeout(function () {
          var rect = wrapper.getBoundingClientRect();
          if (!rect.width || !rect.height || rect.bottom <= 0 || rect.top >= window.innerHeight) return;
          video.dataset.evVisible = 'true';
          play(video);
        }, 250);
      });
    }, { threshold: [0, 0.01] });
    videos.forEach(function (video) {
      var board = video.closest('.t396__artboard');
      if (board && !board.classList.contains('rendered')) {
        board.addEventListener('artBoardRendered', function () { playback.observe(video.parentElement); }, { once: true });
      } else playback.observe(video.parentElement);
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
