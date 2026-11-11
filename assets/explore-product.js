/* Accessible progressive enhancement for the four-layer construction guide. */
(function () {
  'use strict';
  function start() {
    document.querySelectorAll('[data-layer-explorer]').forEach(function (root) {
      if (root.dataset.layerReady) return;
      var controls = Array.from(root.querySelectorAll('[data-layer-control]'));
      var panels = Array.from(root.querySelectorAll('[data-layer-panel]'));
      var images = Array.from(root.querySelectorAll('[data-layer-image]'));
      var list = root.querySelector('[data-layer-controls]');
      if (controls.length !== 4 || panels.length !== 4 || images.length !== 4 || !list) return;

      function select(index, focus) {
        var selected = controls[index];
        if (!selected) return;
        var id = selected.dataset.layerControl;
        controls.forEach(function (control) {
          var active = control === selected;
          control.setAttribute('aria-selected', String(active));
          control.tabIndex = active ? 0 : -1;
        });
        panels.forEach(function (panel) { panel.hidden = panel.dataset.layerPanel !== id; });
        images.forEach(function (img) { img.classList.toggle('is-active', img.dataset.layerImage === id); });
        if (focus) selected.focus();
      }

      list.setAttribute('role', 'tablist');
      controls.forEach(function (control, index) {
        control.setAttribute('role', 'tab');
        control.setAttribute('aria-controls', 'ev-layer-panel-' + control.dataset.layerControl);
        control.addEventListener('click', function (event) {
          event.preventDefault();
          select(index, false);
        });
        control.addEventListener('keydown', function (event) {
          var next = index;
          if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (index + 1) % controls.length;
          else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (index + controls.length - 1) % controls.length;
          else if (event.key === 'Home') next = 0;
          else if (event.key === 'End') next = controls.length - 1;
          else if (event.key !== ' ' && event.key !== 'Enter') return;
          event.preventDefault();
          select(next, true);
        });
      });
      panels.forEach(function (panel) {
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', 'ev-layer-control-' + panel.dataset.layerPanel);
        panel.tabIndex = 0;
      });
      root.classList.add('is-enhanced');
      root.dataset.layerReady = 'true';

      function followFragment() {
        var index = panels.findIndex(function (panel) { return '#' + panel.id === window.location.hash; });
        if (index >= 0) select(index, false);
        return index;
      }
      select(0, false);
      followFragment();
      window.addEventListener('hashchange', followFragment);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
