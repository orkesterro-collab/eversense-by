(function () {
  "use strict";
  var root = document.getElementById("ev-senses");
  if (!root) return;
  var panels = Array.from(root.querySelectorAll(".ev-sense-panel"));
  var buttons = panels.map(function (panel) { return panel.querySelector(".ev-sense-toggle"); });
  var swipeStart = null;

  function adjacentIndex(index, direction) {
    return (index + direction + panels.length) % panels.length;
  }

  function select(index, focus) {
    root.dataset.active = String(index);
    panels.forEach(function (panel, i) {
      var active = i === index;
      panel.classList.toggle("is-active", active);
      buttons[i].setAttribute("aria-expanded", String(active));
      panel.querySelector(".ev-sense-copy").setAttribute("aria-hidden", String(!active));
    });
    if (focus) buttons[index].focus({ preventScroll: true });
  }

  buttons.forEach(function (button, index) {
    button.addEventListener("click", function () { select(index, false); });
    button.addEventListener("keydown", function (event) {
      var next;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = adjacentIndex(index, 1);
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = adjacentIndex(index, -1);
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = panels.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      select(next, true);
    });
  });

  root.addEventListener("touchstart", function (event) {
    var touch = event.touches[0];
    swipeStart = event.touches.length === 1
      ? { id: touch.identifier, x: touch.clientX, y: touch.clientY }
      : null;
  }, { passive: true });

  root.addEventListener("touchmove", function (event) {
    if (!swipeStart) return;
    var touch = event.touches[0];
    var dx = Math.abs(touch.clientX - swipeStart.x);
    var dy = Math.abs(touch.clientY - swipeStart.y);
    if (event.touches.length !== 1 || (dy > 12 && dy > dx)) swipeStart = null;
  }, { passive: true });

  root.addEventListener("touchcancel", function () { swipeStart = null; }, { passive: true });
  root.addEventListener("touchend", function (event) {
    var start = swipeStart;
    swipeStart = null;
    if (!start || event.touches.length || event.changedTouches.length !== 1) return;
    var end = event.changedTouches[0];
    if (end.identifier !== start.id) return;
    var dx = end.clientX - start.x;
    var dy = end.clientY - start.y;
    if (Math.abs(dx) < 40 || Math.abs(dx) <= Math.abs(dy) * 1.25) return;

    // A swipe must not also click the panel under the finger.
    event.preventDefault();
    select(adjacentIndex(Number(root.dataset.active), dx < 0 ? 1 : -1), false);
  }, { passive: false });

  function selectAnchor() {
    var index = panels.findIndex(function (panel) { return "#" + panel.id === location.hash; });
    if (index >= 0) select(index, false);
  }
  select(0, false);
  root.dataset.enhanced = "true";
  selectAnchor();
  window.addEventListener("hashchange", selectAnchor);
}());
