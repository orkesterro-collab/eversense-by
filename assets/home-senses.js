(function () {
  "use strict";
  var root = document.getElementById("ev-senses");
  if (!root) return;
  var panels = Array.from(root.querySelectorAll(".ev-sense-panel"));
  var buttons = panels.map(function (panel) { return panel.querySelector(".ev-sense-toggle"); });

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
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % panels.length;
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + panels.length - 1) % panels.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = panels.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      select(next, true);
    });
  });

  function selectAnchor() {
    var index = panels.findIndex(function (panel) { return "#" + panel.id === location.hash; });
    if (index >= 0) select(index, false);
  }
  select(0, false);
  root.dataset.enhanced = "true";
  selectAnchor();
  window.addEventListener("hashchange", selectAnchor);
}());
