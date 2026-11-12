/* Shared EVERSENSE header. Loaded by price pages, local pages and promotions. */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var assets = new URL(".", script.src);
  var site = new URL("../", assets);
  var asset = function (path) { return new URL(path, assets).href; };
  var route = function (path) { return new URL(path, site).href; };
  var version = "20261111brandicons";

  function ensureStyle(filename, marker) {
    var url = asset(filename + "?v=" + version);
    var existing = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).find(function (link) {
      try { return new URL(link.href).pathname === new URL(url).pathname; }
      catch (_) { return false; }
    });
    if (existing) {
      existing.setAttribute(marker, "true");
      return;
    }
    var css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = url;
    css.setAttribute(marker, "true");
    document.head.appendChild(css);
  }

  function loadBuyerTools() {
    // Static pages explicitly own their deferred dependency sequence.
    if (document.documentElement.dataset.buyerStatic === "true" || window.__evBuyerLoaderPromise) return;
    var dependencies = [
      { filename: "products-data.js", ready: function () { return Array.isArray(window.EversenseCatalogData); } },
      { filename: "buyer-core.js", ready: function () { return !!window.EversenseBuyerCore; } },
      { filename: "buyer.js", ready: function () { return !!window.__eversenseBuyerStarted; } }
    ];
    function loadNext(dependency) {
      if (dependency.ready()) return Promise.resolve();
      return new Promise(function (resolve, reject) {
        var url = asset(dependency.filename + "?v=" + version);
        var existing = Array.from(document.scripts).find(function (item) {
          if (!item.src) return false;
          try { return new URL(item.src).pathname === new URL(url).pathname; }
          catch (_) { return false; }
        });
        var element = existing || document.createElement("script");
        if (element.dataset.evBuyerLoaded === "true") {
          resolve();
          return;
        }
        element.addEventListener("load", function () {
          element.dataset.evBuyerLoaded = "true";
          resolve();
        }, { once: true });
        element.addEventListener("error", function () {
          reject(new Error("Failed to load " + dependency.filename));
        }, { once: true });
        if (!existing) {
          element.src = url;
          element.async = false;
          element.dataset.evBuyerAsset = dependency.filename;
          document.head.appendChild(element);
        }
      });
    }
    // A subsequent script is appended only after the previous load completes.
    window.__evBuyerLoaderPromise = dependencies.reduce(function (sequence, dependency) {
      return sequence.then(function () { return loadNext(dependency); });
    }, Promise.resolve());
    window.__evBuyerLoaderPromise.catch(function (error) {
      if (window.console) console.warn("Eversense buyer tools:", error.message);
    });
  }

  ensureStyle("unified-header.css", "data-ev-header-css");
  ensureStyle("buyer.css", "data-ev-buyer-css");

  function mount() {
    if (!document.body || document.getElementById("ev-global-header")) return;

    var header = document.createElement("header");
    header.id = "ev-global-header";
    header.setAttribute("aria-label", "Навигация EVERSENSE");
    var menuGroups = [
      { title: "Выбрать", id: "choose", items: [
        ["Каталог", "catalog-ru/"],
        ["Помощь с выбором", "choose.html"],
        ["Интерьеры", "projects.html"],
        ["Избранное", "favorites.html"],
        ["Сравнение", "compare.html"],
        ["Калькулятор", "calculator.html"]
      ] },
      { title: "О продукте", id: "product", items: [
        ["О EVERSENSE", "about.html"],
        ["Укладка", "installation.html"],
        ["Уход", "care.html"],
        ["Гарантия", "warranty.html"],
        ["Вопросы и ответы", "faq.html"],
        ["Документы", "downloads.html"]
      ] },
      { title: "Купить", id: "buy", items: [
        ["Где купить", "where-to-buy.html"],
        ["Контакты", "contacts.html"]
      ] }
    ];
    var current = location.pathname.replace(/\/index\.html$/, "/");
    function menuLink(item) {
      var target = route(item[1]);
      var active = current.replace(/\/$/, "") === new URL(target).pathname.replace(/\/$/, "");
      return '<a href="' + target + '"' + (active ? ' aria-current="page"' : '') + '>' + item[0] + '</a>';
    }
    var menuHtml = menuGroups.map(function (group) {
      return '<section class="ev-header-menu-group" aria-labelledby="ev-menu-group-' + group.id + '">' +
        '<h2 id="ev-menu-group-' + group.id + '">' + group.title + '</h2>' +
        group.items.map(menuLink).join("") + '</section>';
    }).join("");
    header.innerHTML = '<div class="ev-header-inner">' +
      '<a class="ev-header-logo" href="' + route("") + '" aria-label="EVERSENSE, на главную">' +
      '<img src="' + asset("original-tilda/44ef8387add2-Frame_784.svg") + '" alt="EVERSENSE" width="158" height="58"></a>' +
      '<nav class="ev-header-quick" aria-label="Быстрый переход">' +
      menuLink(["Каталог", "catalog-ru/"]) + menuLink(["Где купить", "where-to-buy.html"]) + '</nav>' +
      '<button class="ev-header-toggle" type="button" aria-controls="ev-global-menu" aria-expanded="false" aria-label="Открыть меню">' +
      '<span class="ev-header-lines" aria-hidden="true"><span></span><span></span><span></span></span></button>' +
      '</div><nav class="ev-header-menu" id="ev-global-menu" aria-label="Главное меню" hidden>' + menuHtml + '</nav>';
    document.body.insertBefore(header, document.body.firstChild);
    document.body.classList.add("ev-has-global-header");
    document.dispatchEvent(new CustomEvent('eversense:header-ready'));

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
    header.addEventListener("focusin", function () {
      header.classList.remove("ev-header-hidden");
    });

    // The home page uses ordinary scrolling, including a stationary navigation bar.
    if (document.documentElement.classList.contains("ev-home-static")) return;
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
  function initialize() {
    // Brandbook p. 32: use the original 72h, class 34 and 30-year vector marks.
    // Only the homepage forest benefits block uses this white-on-photo treatment.
    [
      ["1744014501662", "water-72h.svg"],
      ["1744014502871", "class-34.svg"],
      ["1744014475697", "warranty-30.svg"]
    ].forEach(function (item) {
      document.querySelectorAll('#rec1003959231 [data-elem-id="' + item[0] + '"], #rec1040271661 [data-elem-id="' + item[0] + '"]').forEach(function (element) {
        var image = element.querySelector("img");
        if (!image) return;
        var url = asset("brand-icons/" + item[1]);
        image.setAttribute("src", url);
        image.setAttribute("data-original", url);
        element.classList.add("ev-brand-feature-icon");
      });
    });
    // The mirrored Russian footer used the manufacturer's /ru/#contacts.
    // Keep that existing label useful for the Belarus site on every page.
    document.querySelectorAll('a[href]').forEach(function (link) {
      var url;
      try { url = new URL(link.href); } catch (_) { return; }
      var legacy = new URL('ru/', site).pathname.replace(/\/$/, '');
      var path = url.pathname.replace(/\/index\.html$/, '/').replace(/\/$/, '');
      if (url.origin === site.origin && path === legacy && url.hash === '#contacts') link.href = route('contacts.html');
    });
    mount();
    loadBuyerTools();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, { once: true });
  else initialize();
})();
