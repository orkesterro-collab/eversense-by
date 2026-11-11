(function () {
  'use strict';
  function initialize() {
    var root = document.querySelector('[data-interior-stories]');
    if (!root || root.dataset.interiorReady === 'true') return;
    root.querySelectorAll('[data-interior-story]').forEach(function (story) {
      var scenes = Array.from(story.querySelectorAll('[data-story-scene]'));
      var selectors = Array.from(story.querySelectorAll('[data-story-select]'));
      var views = Array.from(story.querySelectorAll('[data-story-view]'));
      var status = story.querySelector('[data-story-status]');
      if (scenes.length < 2 || selectors.length !== scenes.length) return;
      var selected = scenes[0].dataset.storyScene;
      var view = 'room';

      function render(announce) {
        selectors.forEach(function (button) {
          button.setAttribute('aria-pressed', String(button.dataset.storySelect === selected));
        });
        views.forEach(function (button) {
          button.setAttribute('aria-pressed', String(button.dataset.storyView === view));
        });
        scenes.forEach(function (scene) {
          var active = scene.dataset.storyScene === selected;
          scene.hidden = !active;
          if (!active) return;
          var photo = scene.querySelector('[data-story-photo]');
          if (photo) {
            if (announce) photo.loading = 'eager';
            photo.src = view === 'detail' ? photo.dataset.detailSrc : photo.dataset.roomSrc;
            photo.alt = view === 'detail' ? photo.dataset.detailAlt : photo.dataset.roomAlt;
            photo.dataset.currentView = view;
          }
          if (announce && status) {
            var name = scene.querySelector('h3').textContent;
            status.textContent = (view === 'detail' ? 'Рисунок: ' : 'Интерьер: ') + name + ', ' + selected + '.';
          }
        });
      }

      selectors.forEach(function (button) {
        button.addEventListener('click', function () {
          selected = button.dataset.storySelect;
          render(true);
        });
      });
      views.forEach(function (button) {
        button.addEventListener('click', function () {
          view = button.dataset.storyView;
          render(true);
        });
      });
      render(false);
      story.querySelector('[data-story-options]').hidden = false;
      story.querySelector('[data-story-view-controls]').hidden = false;
    });
    root.dataset.interiorReady = 'true';
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, {once: true});
  else initialize();
}());
