/* The directory and its static overview also work without WebGL or remote tiles. */
(function () {
  "use strict";

  var BELARUS = [[23.15, 51.23], [32.77, 56.18]];
  var SHOP_ZOOM = 9;
  var english = document.documentElement.lang === "en";
  var locale = english ? {"Map.Title": "EVERSENSE stores in Belarus"} : {
    "Map.Title": "Карта магазинов EVERSENSE",
    "NavigationControl.ZoomIn": "Приблизить",
    "NavigationControl.ZoomOut": "Отдалить",
    "AttributionControl.ToggleAttribution": "Источники карты",
    "CooperativeGesturesHandler.WindowsHelpText": "Для изменения масштаба удерживайте Ctrl и крутите колесо",
    "CooperativeGesturesHandler.MacHelpText": "Для изменения масштаба удерживайте ⌘ и крутите колесо",
    "CooperativeGesturesHandler.MobileHelpText": "Перемещайте карту двумя пальцами"
  };

  function element(tag, className, text) {
    var node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function cityLink(city) {
    var link = element("a", "dealer-pin");
    link.setAttribute("role", "link");
    link.dataset.city = city.name;
    link.href = city.href;
    link.setAttribute("aria-label", english ? "Show stores in " + city.name : city.name + " — показать магазины");
    link.appendChild(element("span", "dealer-pin__caption", city.name));
    return link;
  }

  async function copyPhone(number) {
    try {
      await navigator.clipboard.writeText(number.textContent);
      return true;
    } catch (_) {
      // Some in-app browsers restrict the Clipboard API. Leave the number selected for manual copying if needed.
      var selection = window.getSelection();
      if (!selection || !number.isConnected) return false;
      var range = document.createRange();
      range.selectNodeContents(number);
      selection.removeAllRanges();
      selection.addRange(range);
      try {
        if (document.execCommand("copy")) {
          selection.removeAllRanges();
          return true;
        }
      } catch (_) {}
      return false;
    }
  }

  function phoneRow(phone) {
    var row = element("div", "dealer-contact__phone-row");
    var number = element("span", "dealer-contact__phone", phone);
    var copy = element("button", "dealer-contact__copy", english ? "Copy" : "Копировать");
    var status = element("span", "dealer-contact__status");
    copy.type = "button";
    copy.setAttribute("aria-label", english ? "Copy phone number" : "Скопировать номер");
    status.setAttribute("role", "status");
    copy.addEventListener("click", async function () {
      var copied = await copyPhone(number);
      if (copied) {
        copy.textContent = english ? "Copied" : "Скопировано";
        status.classList.add("sr-only");
        status.textContent = english ? "Phone number copied" : "Номер скопирован";
      } else {
        status.classList.remove("sr-only");
        status.textContent = english ? "Press and hold the number to copy it." : "Удерживайте номер и выберите «Копировать».";
      }
    });
    row.append(number, copy, status);
    return row;
  }

  function contactCard(shop) {
    var card = element("section", "dealer-contact");
    card.dataset.partnerId = shop.id;
    card.appendChild(element("h3", "dealer-contact__name", shop.name));
    if (shop.address) card.appendChild(element("p", "dealer-contact__address", shop.address));
    if (shop.phone && /\d/.test(shop.phone)) {
      // Keep extensions with their number. Separately listed numbers each have their own copy action.
      var phones = shop.phone.split(/\s*[,;\/\n]\s*/).filter(Boolean);
      if (!phones.every(function (part) { return part.replace(/\D/g, "").length >= 7; })) phones = [shop.phone];
      phones.forEach(function (phone) { card.appendChild(phoneRow(phone)); });
    } else {
      card.appendChild(element("p", "dealer-contact__unlisted", english ? "No phone number listed" : "Телефон не указан"));
    }
    var link = element("a", "dealer-contact__find", english ? "Find in list" : "Найти в списке");
    link.href = "#shop-" + encodeURIComponent(shop.id);
    link.dataset.city = shop.city;
    link.dataset.partnerId = shop.id;
    card.appendChild(link);
    return card;
  }

  function mount(container, placeLabels) {
    var map;
    var cities = [];
    var markers = [];
    var activePopup;
    var detailed = false;
    var localityFilter;
    var overview = document.getElementById("partners-map");
    var hint = document.getElementById("map-hint");

    function openContacts(pin, coordinates, shops) {
      var alreadyOpen = pin.getAttribute("aria-expanded") === "true";
      if (activePopup) activePopup.remove();
      if (alreadyOpen) return;

      var content = element("div", "dealer-contacts");
      var close = element("button", "dealer-contacts__close", "×");
      close.type = "button";
      close.setAttribute("aria-label", english ? "Close" : "Закрыть");
      content.appendChild(close);
      shops.forEach(function (shop) { content.appendChild(contactCard(shop)); });

      var point = map.project(coordinates);
      if (point.x < 0 || point.y < 0 || point.x >= container.clientWidth || point.y >= container.clientHeight) {
        map.jumpTo({center: coordinates});
      }
      var popup = new window.maplibregl.Popup({
        className: "dealer-popup", maxWidth: "280px", offset: 18, focusAfterOpen: false, closeButton: false
      }).setLngLat(coordinates).setDOMContent(content).addTo(map);
      activePopup = popup;
      var dialog = popup.getElement();
      dialog.id = "dealer-map-contact";
      dialog.tabIndex = -1;
      dialog.setAttribute("role", "dialog");
      dialog.setAttribute("aria-label", shops.map(function (shop) { return shop.name; }).join(", "));
      pin.setAttribute("aria-expanded", "true");
      pin.setAttribute("aria-controls", dialog.id);

      function dismiss() {
        popup.remove();
        pin.focus({preventScroll: true});
      }
      function escape(event) {
        if (event.key === "Escape") {
          event.preventDefault();
          dismiss();
        }
      }
      close.addEventListener("click", dismiss);
      document.addEventListener("keydown", escape);
      content.addEventListener("click", function (event) {
        if (event.target.closest(".dealer-contact__find") && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
          // Let the directory handler (or the top-level link in an embedded map) finish navigation first.
          window.setTimeout(function () { popup.remove(); }, 0);
        }
      });
      popup.on("close", function () {
        activePopup = null;
        pin.setAttribute("aria-expanded", "false");
        pin.removeAttribute("aria-controls");
        document.removeEventListener("keydown", escape);
      });
      dialog.focus({preventScroll: true});
    }

    function addPin(city, coordinates, shops) {
      var pin;
      if (shops) {
        var names = shops.map(function (shop) { return shop.name; }).join(" · ");
        pin = element("button", "dealer-pin dealer-pin--shop");
        pin.type = "button";
        pin.dataset.city = city.name;
        if (shops.length === 1) pin.dataset.partnerId = shops[0].id;
        pin.setAttribute("aria-haspopup", "dialog");
        pin.setAttribute("aria-expanded", "false");
        pin.setAttribute("aria-label", english ? "Store contacts: " + names : "Контакты — " + names);
        pin.appendChild(element("span", "dealer-pin__caption", names));
        pin.addEventListener("click", function (event) {
          event.stopPropagation();
          openContacts(pin, coordinates, shops);
        });
      } else {
        pin = cityLink(city);
      }
      markers.push(new window.maplibregl.Marker({element: pin, anchor: "center"})
        .setLngLat(coordinates).addTo(map));
    }

    function layoutShopLabels() {
      if (!detailed) return;
      var bounds = {left: 3, top: 3, right: container.clientWidth - 3, bottom: container.clientHeight - 3};
      var corners = container.getBoundingClientRect();
      var controls = Array.from(container.querySelectorAll(".maplibregl-ctrl"), function (control) {
        var rect = control.getBoundingClientRect();
        return {left: rect.left - corners.left, right: rect.right - corners.left,
          top: rect.top - corners.top, bottom: rect.bottom - corners.top};
      });
      var pins = [];
      markers.forEach(function (marker) {
        var link = marker.getElement();
        if (!link.classList.contains("dealer-pin--shop")) return;
        var point = map.project(marker.getLngLat());
        if (point.x < -20 || point.y < -20 || point.x > bounds.right + 20 || point.y > bounds.bottom + 20) return;
        pins.push({link: link, x: point.x, y: point.y, width: link.firstElementChild.offsetWidth,
          height: link.firstElementChild.offsetHeight, radius: 16, gap: 19, preferAbove: true});
      });
      placeLabels(pins, bounds, controls);
    }

    function updateLabels() {
      var source = map && map.getSource("dealer-cities");
      if (!source || !localityFilter) return;
      source.setData({type: "FeatureCollection", features: cities.map(function (city, index) {
        return {type: "Feature", geometry: {type: "Point", coordinates: city.coordinates},
          properties: {name: city.name, priority: index}};
      })});
      var names = cities.flatMap(function (city) { return [city.name, city.name.replace(/ё/g, "е")]; });
      // Reserve one label for each dealer city while its overview pin is shown.
      var filter = localityFilter;
      if (!detailed && names.length) {
        var aroundBelarus = {type: "Polygon", coordinates: [[[23, 51], [34, 51], [34, 57], [23, 57], [23, 51]]]};
        filter = ["all", localityFilter, ["!", ["all", ["within", aroundBelarus],
          ["in", ["coalesce", ["get", "name:ru"], ["get", "name"]], ["literal", names]]]]];
      }
      map.setFilter("localities", filter);
    }

    function drawPins() {
      if (!map) return;
      if (activePopup) activePopup.remove();
      markers.forEach(function (marker) { marker.remove(); });
      markers = [];
      cities.forEach(function (city) {
        if (!detailed || !city.shops.length) {
          addPin(city, city.coordinates);
          return;
        }
        // A shared address keeps a card, a phone and a directory link for each shop.
        var addresses = new Map();
        city.shops.forEach(function (shop) {
          var key = shop.lng + "," + shop.lat;
          if (!addresses.has(key)) addresses.set(key, []);
          addresses.get(key).push(shop);
        });
        addresses.forEach(function (shops) {
          addPin(city, [shops[0].lng, shops[0].lat], shops);
        });
      });
      layoutShopLabels();
    }

    function switchMap(ready) {
      container.classList.toggle("is-ready", ready);
      container.inert = !ready;
      container.setAttribute("aria-hidden", String(!ready));
      overview.hidden = ready;
      hint.textContent = ready
        ? "Приблизьте город и нажмите на название магазина, чтобы посмотреть телефон."
        : "Выберите город, чтобы увидеть его магазины.";
    }

    function padding() {
      return container.clientWidth < 650 ? 24 : 42;
    }

    function start() {
      var gl = window.maplibregl;
      if (!gl || map) return;
      try {
        map = new gl.Map({
          container: container,
          style: container.dataset.style,
          bounds: BELARUS,
          fitBoundsOptions: {padding: padding()},
          minZoom: 3, maxZoom: 18, maxPitch: 0,
          dragRotate: false, pitchWithRotate: false, touchPitch: false,
          renderWorldCopies: false, cooperativeGestures: true,
          attributionControl: {compact: true}, locale: locale
        });
      } catch (_) {
        return;
      }
      map.touchZoomRotate.disableRotation();
      map.keyboard.disableRotation();
      map.addControl(new gl.NavigationControl({showCompass: false}), "top-right");
      map.addControl({
        onAdd: function () {
          var group = document.createElement("div");
          var button = document.createElement("button");
          group.className = "maplibregl-ctrl map-home";
          button.type = "button";
          button.textContent = english ? "All of Belarus" : "Вся Беларусь";
          button.addEventListener("click", function () {
            map.fitBounds(BELARUS, {padding: padding(), duration: 0});
          });
          group.appendChild(button);
          return group;
        },
        onRemove: function () {}
      }, "top-left");
      map.on("style.load", function () {
        localityFilter = map.getFilter("localities");
        updateLabels();
      });
      map.on("moveend", layoutShopLabels);
      map.on("resize", layoutShopLabels);
      if (document.fonts) document.fonts.ready.then(layoutShopLabels);
      map.on("zoomend", function () {
        var next = map.getZoom() >= SHOP_ZOOM;
        if (next === detailed) return;
        detailed = next;
        updateLabels();
        drawPins();
      });

      // A style can finish loading even when the provider refuses every tile.
      function revealWhenDrawn() {
        if (!map.getLayer("borders")) return;
        if (!map.queryRenderedFeatures({layers: ["borders", "vegetation", "water", "main-roads"]}).length) return;
        switchMap(true);
        map.off("render", revealWhenDrawn);
      }
      map.on("render", revealWhenDrawn);
      map.on("webglcontextlost", function () {
        if (activePopup) activePopup.remove();
        switchMap(false);
      });
      map.on("webglcontextrestored", function () {
        map.off("render", revealWhenDrawn);
        map.on("render", revealWhenDrawn);
      });
      drawPins();
    }

    if (window.maplibregl) start();
    else document.getElementById("partners-map-library").addEventListener("load", start, {once: true});
    return function updateLocations(locations) {
      cities = locations;
      updateLabels();
      drawPins();
    };
  }

  window.EversenseShopMap = {mount: mount};
})();
