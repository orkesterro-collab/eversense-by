/* The directory and its static overview also work without WebGL or remote tiles. */
(function () {
  "use strict";

  var BELARUS = [[23.15, 51.23], [32.77, 56.18]];
  var SHOP_ZOOM = 9;
  var locale = {
    "Map.Title": "Карта магазинов EVERSENSE",
    "NavigationControl.ZoomIn": "Приблизить",
    "NavigationControl.ZoomOut": "Отдалить",
    "AttributionControl.ToggleAttribution": "Источники карты",
    "CooperativeGesturesHandler.WindowsHelpText": "Для изменения масштаба удерживайте Ctrl и крутите колесо",
    "CooperativeGesturesHandler.MacHelpText": "Для изменения масштаба удерживайте ⌘ и крутите колесо",
    "CooperativeGesturesHandler.MobileHelpText": "Перемещайте карту двумя пальцами"
  };

  function pinLink(city, shop) {
    var link = document.createElement("a");
    var caption = document.createElement("span");
    link.className = "dealer-pin";
    link.setAttribute("role", "link");
    link.dataset.city = city.name;
    if (shop) link.dataset.partnerId = shop.id;
    link.href = shop ? "#shop-" + encodeURIComponent(shop.id) : city.href;
    var name = shop ? shop.name : city.name;
    link.setAttribute("aria-label", name + (shop ? " — открыть магазин" : " — показать магазины"));
    caption.className = "dealer-pin__caption";
    caption.textContent = name;
    link.appendChild(caption);
    return link;
  }

  function mount(container) {
    var map;
    var cities = [];
    var markers = [];
    var detailed = false;
    var localityFilter;
    var overview = document.getElementById("partners-map");
    var hint = document.getElementById("map-hint");

    function addPin(city, coordinates, shop) {
      var marker = new window.maplibregl.Marker({element: pinLink(city, shop), anchor: "center"})
        .setLngLat(coordinates).addTo(map);
      markers.push(marker);
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
      markers.forEach(function (marker) { marker.remove(); });
      markers = [];
      cities.forEach(function (city) {
        if (!detailed || !city.shops.length) {
          addPin(city, city.coordinates);
          return;
        }
        // Several shops can share a building. The shared pin opens the city directory.
        var addresses = new Map();
        city.shops.forEach(function (shop) {
          var key = shop.lng + "," + shop.lat;
          if (!addresses.has(key)) addresses.set(key, []);
          addresses.get(key).push(shop);
        });
        addresses.forEach(function (shops) {
          addPin(city, [shops[0].lng, shops[0].lat], shops.length === 1 ? shops[0] : null);
        });
      });
    }

    function switchMap(ready) {
      container.classList.toggle("is-ready", ready);
      container.inert = !ready;
      container.setAttribute("aria-hidden", String(!ready));
      overview.hidden = ready;
      hint.textContent = ready
        ? "Выберите метку, чтобы увидеть магазины. Приблизьте карту до улиц, чтобы выбрать отдельный магазин."
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
          button.textContent = "Вся Беларусь";
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
      map.on("webglcontextlost", function () { switchMap(false); });
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
