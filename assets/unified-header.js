/* Shared EVERSENSE header. Loaded by price pages, local pages and promotions. */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var assets = new URL(".", script.src);
  var site = new URL("../", assets);
  var asset = function (path) { return new URL(path, assets).href; };
  var route = function (path) { return new URL(path, site).href; };

  function mount() {
    if (!document.body || document.getElementById("ev-global-header")) return;
    var css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = asset("unified-header.css?v=20261104a");
    css.dataset.evHeaderCss = "true";
    if (!document.querySelector('link[data-ev-header-css]')) document.head.appendChild(css);

    var header = document.createElement("header");
    header.id = "ev-global-header";
    header.setAttribute("aria-label", "Навигация EVERSENSE");
    var menuItems = [
      ["Главная", ""],
      ["Каталог", "catalog-ru/"],
      ["О бренде", "about.html"],
      ["Где купить", "where-to-buy.html"],
      ["Укладка и уход", "installation.html"],
      ["Контакты", "#contacts"]
    ];
    var current = location.pathname.replace(/\/index\.html$/, "/");
    var menuHtml = menuItems.map(function (item) {
      var target = item[1] === "#contacts" ? route("") + "#contacts" : route(item[1]);
      var active = item[1] !== "#contacts" && current === new URL(target).pathname;
      return '<a href="' + target + '"' + (active ? ' aria-current="page"' : '') + '>' + item[0] + '</a>';
    }).join("");
    header.innerHTML = '<div class="ev-header-inner">' +
      '<a class="ev-header-logo" href="' + route("") + '" aria-label="EVERSENSE, на главную">' +
      '<img src="' + asset("original-tilda/44ef8387add2-Frame_784.svg") + '" alt="EVERSENSE" width="158" height="58"></a>' +
      '<button class="ev-header-toggle" type="button" aria-controls="ev-global-menu" aria-expanded="false" aria-label="Открыть меню">' +
      '<span class="ev-header-lines" aria-hidden="true"><span></span><span></span><span></span></span></button>' +
      '</div><nav class="ev-header-menu" id="ev-global-menu" aria-label="Главное меню" hidden>' + menuHtml + '</nav>';
    document.body.insertBefore(header, document.body.firstChild);
    document.body.classList.add("ev-has-global-header");

    var toggle = header.querySelector(".ev-header-toggle");
    var menu = header.querySelector(".ev-header-menu");
    function closeMenu(restoreFocus) {
      if (menu.hidden) return;
      menu.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Открыть меню");
      if (restoreFocus) toggle.focus();
    }
    toggle.addEventListener("click", function () {
      var open = menu.hidden;
      menu.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
      if (open) header.classList.remove("ev-header-hidden");
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu(true);
    });
    document.addEventListener("click", function (event) {
      if (!header.contains(event.target)) closeMenu(false);
    });
    menu.addEventListener("click", function (event) {
      if (event.target.closest("a")) closeMenu(false);
    });

    var lastY = Math.max(0, window.scrollY);
    var travel = 0, direction = 0;
    window.addEventListener("scroll", function () {
      var y = Math.max(0, window.scrollY);
      var delta = y - lastY;
      lastY = y;
      if (y <= 24) {
        header.classList.remove("ev-header-hidden");
        travel = 0;
        direction = 0;
        return;
      }
      if (!menu.hidden || Math.abs(delta) < 2) return;
      var next = delta > 0 ? 1 : -1;
      if (direction !== next) { direction = next; travel = 0; }
      travel += Math.abs(delta);
      if (next > 0 && y > 110 && travel >= 16) header.classList.add("ev-header-hidden");
      if (next < 0 && travel >= 10) header.classList.remove("ev-header-hidden");
    }, { passive: true });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, { once: true });
  else mount();
})();
