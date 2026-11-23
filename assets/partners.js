/* EVERSENSE Беларусь. Dealer directory is read from the public Google Sheets "partners" tab.
 * No credentials or demo partner contacts are embedded in this JavaScript.
 */
(function () {
  "use strict";

  var SHEET_ID = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY";
  var CSV_URL = "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/export?format=csv&gid=24681103&range=A%3AN";
  var COUNTRY_BOUNDS = [[51.18, 23.12], [56.22, 32.82]];
  // Belarus boundary, simplified from Natural Earth Admin 0 Countries (1:50m, public domain).
  var COUNTRY_OUTLINE = [
    [52.101, 31.763], [52.077, 31.079], [51.895, 30.755], [51.596, 30.533], [51.355, 30.633],
    [51.265, 30.545], [51.326, 30.333], [51.400, 30.309], [51.478, 30.161], [51.383, 29.346],
    [51.628, 29.102], [51.540, 28.850], [51.433, 28.731], [51.457, 28.648], [51.543, 28.599],
    [51.608, 28.184], [51.560, 28.011], [51.592, 27.859], [51.478, 27.700], [51.572, 27.690],
    [51.597, 27.296], [51.752, 27.142], [51.924, 25.786], [51.931, 25.067], [51.868, 24.362],
    [51.591, 23.978], [51.641, 23.707], [51.610, 23.609], [51.518, 23.605], [51.710, 23.545],
    [51.809, 23.626], [52.040, 23.652], [52.287, 23.175], [52.516, 23.411], [52.664, 23.845],
    [52.770, 23.915], [53.112, 23.859], [53.599, 23.599], [53.940, 23.485], [53.950, 24.191],
    [53.893, 24.318], [53.975, 24.768], [54.145, 24.870], [54.133, 25.046], [54.293, 25.461],
    [54.215, 25.527], [54.160, 25.510], [54.157, 25.749], [54.260, 25.748], [54.332, 25.547],
    [54.564, 25.725], [54.718, 25.722], [54.919, 25.859], [55.003, 26.175], [55.140, 26.292],
    [55.130, 26.601], [55.273, 26.776], [55.342, 26.458], [55.668, 26.594], [55.709, 26.822],
    [55.831, 27.053], [55.799, 27.577], [55.912, 27.642], [56.076, 27.896], [56.146, 28.118],
    [56.056, 28.284], [56.092, 28.564], [55.943, 28.795], [56.022, 29.032], [55.939, 29.375],
    [55.784, 29.353], [55.685, 29.482], [55.845, 29.937], [55.845, 30.234], [55.570, 30.907],
    [55.397, 30.901], [55.307, 30.811], [55.050, 30.978], [54.915, 30.830], [54.783, 30.799],
    [54.625, 31.152], [54.492, 31.075], [54.453, 31.185], [54.196, 31.404], [54.031, 31.826],
    [53.810, 31.754], [53.781, 32.200], [53.693, 32.450], [53.547, 32.470], [53.419, 32.706],
    [53.336, 32.704], [53.091, 32.142], [53.106, 31.850], [53.201, 31.668], [53.196, 31.418],
    [53.017, 31.259], [52.759, 31.565], [52.699, 31.519], [52.546, 31.616], [52.312, 31.577],
    [52.101, 31.763]
  ];
  var REFRESH_MS = 15 * 60 * 1000;
  var el = function (id) { return document.getElementById(id); };
  var locale = new Intl.Collator("ru", { sensitivity: "base" });
  var partners = [];
  var map = null;
  var markers = new Map();
  var layer = null;
  var selectedId = null;
  var loaded = false;
  var overview = true;
  var coarsePointer = window.matchMedia("(pointer: coarse)").matches;
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var feedTimeout = null;
  var loading = false;

  function escapeHTML(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function toNumber(value) {
    if (!trim(value)) return null;
    var x = Number(String(value).replace(",", ".").trim());
    return Number.isFinite(x) ? x : null;
  }
  function toBool(value, fallback) {
    if (typeof value === "boolean") return value;
    if (value === "" || value == null) return fallback;
    return !/^(false|0|no|нет)$/i.test(String(value).trim());
  }
  function trim(value) {
    return String(value == null ? "" : value).trim();
  }
  function searchable(value) {
    return trim(value).toLocaleLowerCase("ru").replace(/ё/g, "е");
  }
  function toWebsite(raw) {
    var value = trim(raw);
    if (!value) return null;
    try {
      var link = new URL(value);
      if (link.protocol !== "http:" && link.protocol !== "https:") return null;
      return link.href;
    } catch (_) {
      return null;
    }
  }
  function phoneLink(raw) {
    var number = trim(raw).replace(/[()\s-]/g, "");
    return /^\+?375\d{9}$/.test(number) ? "tel:+" + number.replace(/^\+/, "") : null;
  }
  function validCoords(lat, lng) {
    return lat !== null && lng !== null && lat >= 51 && lat <= 57 && lng >= 23 && lng <= 33.5;
  }
  function parseRow(cells) {
    var p = {
      id: trim(cells[0]),
      order: toNumber(cells[1]),
      city: trim(cells[2]),
      district: trim(cells[3]),
      name: trim(cells[4]),
      website: toWebsite(cells[5]) || toWebsite(cells[13]) || "",
      phone: trim(cells[6]),
      address: trim(cells[7]),
      hours: trim(cells[8]),
      lat: toNumber(cells[9]),
      lng: toNumber(cells[10]),
      active: toBool(cells[11], true),
      demo: toBool(cells[12], false)
    };
    return p.id && p.city && p.name && p.active ? p : null;
  }
  function orderByRank(a, b) {
    return (a.order == null ? 999999 : a.order) - (b.order == null ? 999999 : b.order)
      || locale.compare(a.name, b.name) || locale.compare(a.id, b.id);
  }
  function cityNames(source) {
    return Array.from(new Set(source.map(function (p) { return p.city; }))).sort(function (a, b) {
      if (a.toLocaleLowerCase("ru") === "минск") return -1;
      if (b.toLocaleLowerCase("ru") === "минск") return 1;
      return locale.compare(a, b);
    });
  }
  function locationLabel(p) {
    return p.city.toLocaleLowerCase("ru") === "минск" && p.district ? p.city + " · " + p.district + " район" : p.city;
  }
  function filtered() {
    var q = searchable(el("partners-search").value);
    var city = el("partners-city").value;
    return partners.filter(function (p) {
      if (city && city !== p.city) return false;
      if (!q) return true;
      return [p.id, p.city, p.district, p.name, p.address, p.hours]
        .some(function (part) { return searchable(part).includes(q); });
    });
  }
  function partnerMarkup(p) {
    var key = escapeHTML(p.id);
    var demo = p.demo ? '<span class="demo-tag">ДЕМО</span>' : "";
    var displayName = p.demo ? p.name.replace(/^ДЕМО\s*[•·-]\s*/i, "") : p.name;
    var site = toWebsite(p.website);
    var siteMarkup = p.demo ? escapeHTML(p.website || "Не указан") + " (пример)"
      : site ? '<a target="_blank" rel="noopener noreferrer" href="' + escapeHTML(site) + '">'
        + escapeHTML(p.website.replace(/^https?:\/\//, "")) + "</a>"
      : "Не указан";
    var tel = phoneLink(p.phone);
    var phoneMarkup = p.demo ? escapeHTML(p.phone || "Не указан") + " (пример)"
      : tel ? '<a href="' + escapeHTML(tel) + '">' + escapeHTML(p.phone) + "</a>"
      : escapeHTML(p.phone || "Не указан");
    return '<details class="partner-card" data-partner-id="' + key + '">' +
      '<summary><span class="partner-card__head">' +
        '<span class="partner-card__name">' + escapeHTML(displayName) + demo + '</span>' +
        (p.address ? '<span class="partner-card__address">' + escapeHTML(p.address) + '</span>' : '') +
      '</span><span class="chevron" aria-hidden="true"></span></summary>' +
      '<div class="partner-card__body">' +
        '<dl>' +
          '<div class="partner-card__row"><dt>Телефон</dt><dd>' + phoneMarkup + '</dd></div>' +
          '<div class="partner-card__row"><dt>Сайт</dt><dd>' + siteMarkup + '</dd></div>' +
          '<div class="partner-card__row"><dt>Режим работы</dt><dd>' + escapeHTML(p.hours || "Уточняется") + '</dd></div>' +
        '</dl>' +
        '<div class="partner-card__foot">' +
        (map && validCoords(p.lat, p.lng) ? '<button type="button" class="partner-card__showmap" data-map-id="' + key + '">Показать на карте ↗</button>' : '') +
        '</div>' +
      '</div></details>';
  }
  function renderList(items) {
    var root = el("partners-groups");
    var cities = cityNames(items);
    if (!items.length) {
      root.innerHTML = "";
      return;
    }
    root.innerHTML = cities.map(function (city) {
      var records = items.filter(function (p) { return p.city === city; }).sort(orderByRank);
      var minsk = city.toLocaleLowerCase("ru") === "минск";
      var body = '<div class="partner-list">' +
        records.map(partnerMarkup).join("") + "</div>";
      var title = '<span class="city-group__name">' + escapeHTML(city) + '</span>';
      if (minsk) {
        return '<section class="city-group city-group--minsk" data-city="' + escapeHTML(city) +
          '" aria-label="Магазины Минска">' +
          '<h3 class="city-group__heading">' + title + '</h3>' +
          '<div class="city-group__body">' + body + '</div></section>';
      }
      return '<details class="city-group" data-city="' + escapeHTML(city) + '" open><summary>' + title +
        '<span class="chevron" aria-hidden="true"></span></summary>' +
        '<div class="city-group__body">' + body + "</div></details>";
    }).join("");
  }
  function icon(p, selected) {
    return window.L.divIcon({
      className: "ev-pin " + (p.demo ? "ev-pin--demo " : "") + (selected ? "ev-pin--selected" : ""),
      html: '<span class="ev-pin__dot" aria-hidden="true"></span>',
      iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -9]
    });
  }
  function popupMarkup(p) {
    var tel = p.demo ? null : phoneLink(p.phone);
    return '<div class="ev-popup"><p class="ev-popup__name">' + escapeHTML(p.name.replace(/^ДЕМО\s*[•·-]\s*/i, "")) + '</p>' +
      '<p class="ev-popup__meta">' + escapeHTML(locationLabel(p)) + '</p>' +
      (p.address ? '<p class="ev-popup__address">' + escapeHTML(p.address) + '</p>' : '') +
      (tel ? '<a class="ev-popup__phone" href="' + escapeHTML(tel) + '">' + escapeHTML(p.phone) + '</a>' : '') +
      (p.hours ? '<p class="ev-popup__meta">' + escapeHTML(p.hours) + '</p>' : '') +
      (p.demo ? '<div class="ev-popup__note">Условная демо-точка, не действующий дилер</div>' : '') +
      '<button type="button" class="ev-popup__details" data-list-id="' + escapeHTML(p.id) + '">Все контакты</button></div>';
  }
  function cardById(id) {
    return Array.from(el("partners-groups").querySelectorAll(".partner-card")).find(function (card) {
      return card.dataset.partnerId === id;
    });
  }
  function resetFilters() {
    el("partners-search").value = "";
    el("partners-city").value = "";
    render();
  }
  function showPartnerInList(id) {
    var card = cardById(id);
    if (!card) {
      resetFilters();
      card = cardById(id);
    }
    if (!card) return;
    var parent = card.parentElement;
    while (parent && parent !== document.body) {
      if (parent.tagName === "DETAILS") parent.open = true;
      parent = parent.parentElement;
    }
    card.open = true;
    card.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "center" });
    card.querySelector("summary").focus({ preventScroll: true });
  }
  function showCountry() {
    if (!map) return;
    map.closePopup();
    markSelected(null);
    map.fitBounds(COUNTRY_BOUNDS, { padding: [20, 18], animate: false });
    overview = true;
    el("partners-map-reset").hidden = true;
    if (coarsePointer) map.dragging.disable();
  }
  function setupMap() {
    var target = el("partners-map");
    if (!window.L) {
      target.innerHTML = '<div class="map-skeleton">Карта временно недоступна. Адреса магазинов — ниже.</div>';
      return;
    }
    target.innerHTML = "";
    map = window.L.map(target, {
      zoomControl: false, scrollWheelZoom: false, zoomSnap: 0.25, dragging: !coarsePointer
    });
    window.L.control.zoom({ position: "bottomright" }).addTo(map);
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a target="_blank" rel="noopener" href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    var world = [[-85, -180], [-85, 180], [85, 180], [85, -180]];
    var countryOverlay = window.L.layerGroup([
      window.L.polygon([world, COUNTRY_OUTLINE], {
        interactive: false, stroke: false, fillColor: "#f1eee7", fillOpacity: 0.82
      }),
      window.L.polygon(COUNTRY_OUTLINE, {
        interactive: false, className: "country-outline", color: "#817b69", weight: 1.4, opacity: 0.85,
        fillColor: "#d6c79f", fillOpacity: 0.13
      })
    ]);
    function updateCountryOverlay() {
      if (map.getZoom() <= 8) countryOverlay.addTo(map);
      else countryOverlay.remove();
    }
    map.on("zoomend", updateCountryOverlay);
    layer = window.L.layerGroup().addTo(map);
    map.on("dragstart zoomstart", function () {
      overview = false;
      el("partners-map-reset").hidden = false;
      if (coarsePointer) map.dragging.enable();
    });
    map.on("resize", function () { if (overview) showCountry(); });
    showCountry();
  }
  function renderMap() {
    if (!map) return;
    var openId = selectedId && markers.get(selectedId) && markers.get(selectedId).isPopupOpen() ? selectedId : null;
    layer.clearLayers();
    markers.clear();
    partners.forEach(function (p) {
      if (!validCoords(p.lat, p.lng)) return;
      var marker = window.L.marker([p.lat, p.lng], { icon: icon(p, p.id === selectedId), title: p.name });
      marker.bindPopup(popupMarkup(p), { closeButton: true, autoPanPadding: [20, 24] });
      marker.on("click", function () { focusPartner(p.id, true); });
      marker.addTo(layer);
      markers.set(p.id, marker);
    });
    if (openId && markers.has(openId)) markers.get(openId).openPopup();
    if (!markers.has(selectedId)) selectedId = null;
  }
  function markSelected(id) {
    var previous = markers.get(selectedId);
    if (previous && previous.getElement()) previous.getElement().classList.remove("ev-pin--selected");
    selectedId = id;
    var next = markers.get(id);
    if (next && next.getElement()) next.getElement().classList.add("ev-pin--selected");
  }
  function focusPartner(id, fromMap) {
    var marker = markers.get(id);
    if (!marker) return;
    markSelected(id);
    map.setView(marker.getLatLng(), Math.max(map.getZoom(), 13), { animate: false });
    marker.openPopup();
    if (!fromMap) {
      el("partners-map").scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "center" });
      marker.getElement().focus({ preventScroll: true });
    }
  }
  function render() {
    var list = filtered();
    el("partners-reset").hidden = !(trim(el("partners-search").value) || el("partners-city").value);
    el("partners-empty").hidden = !loaded || list.length > 0;
    renderList(list);
  }
  function refreshCities() {
    var select = el("partners-city");
    var previous = select.value;
    select.replaceChildren(new Option("Все города", ""));
    cityNames(partners).forEach(function (city) {
      select.add(new Option(city, city));
    });
    if (cityNames(partners).includes(previous)) select.value = previous;
  }
  function setError(message) {
    var area = el("partners-status");
    area.hidden = false;
    area.classList.add("error");
    area.textContent = message;
  }
  function setReady() {
    var area = el("partners-status");
    area.hidden = true;
    area.classList.remove("error");
  }
  function applyRows(rows) {
    var seen = new Set();
    var next = rows.map(parseRow).filter(function (p) {
      if (!p || seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });
    setReady();
    if (loaded && JSON.stringify(partners) === JSON.stringify(next)) return;
    var expanded = Array.from(document.querySelectorAll(".partner-card[open]"), function (card) {
      return card.dataset.partnerId;
    });
    var collapsed = new Set(Array.from(document.querySelectorAll("details.city-group:not([open])"), function (group) {
      return group.dataset.city;
    }));
    partners = next;
    loaded = true;
    refreshCities();
    render();
    expanded.forEach(function (id) {
      var card = cardById(id);
      if (card) card.open = true;
    });
    document.querySelectorAll("details.city-group").forEach(function (group) {
      if (collapsed.has(group.dataset.city)) group.open = false;
    });
    renderMap();
  }
  // The raw CSV preserves dealer URLs in columns with mixed cell types.
  function csvRows(text) {
    var rows = [];
    var row = [];
    var field = "";
    var quoted = false;
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (ch === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i++; }
        else quoted = !quoted;
      } else if (!quoted && ch === ",") {
        row.push(field);
        field = "";
      } else if (!quoted && (ch === "\n" || ch === "\r")) {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(field);
        rows.push(row);
        row = [];
        field = "";
      } else {
        field += ch;
      }
    }
    if (row.length || field) rows.push(row.concat(field));
    if (quoted || !rows.length || rows[0][0].replace(/^\uFEFF/, "") !== "partner_id") {
      throw new Error("Invalid partner directory CSV");
    }
    return rows.slice(1);
  }
  function feedFailed() {
    window.clearTimeout(feedTimeout);
    loading = false;
    if (!loaded) setError("Не удалось загрузить магазины. Обновите страницу или позвоните по номеру +375 29 671-39-71.");
  }
  // Keep the previous public feed available to browsers that block the CSV export.
  window.EversensePartnersFeed = function (payload) {
    if (!payload || payload.status !== "ok" || !payload.table || !Array.isArray(payload.table.rows)) {
      feedFailed();
      return;
    }
    window.clearTimeout(feedTimeout);
    loading = false;
    applyRows(payload.table.rows.map(function (row) {
      return (row.c || []).map(function (cell) { return cell && cell.v; });
    }));
  };
  function loadJsonp() {
    var old = el("partners-jsonp");
    if (old) old.remove();
    var script = document.createElement("script");
    script.id = "partners-jsonp";
    var params = new URLSearchParams({
      tqx: "out:json;responseHandler:EversensePartnersFeed", sheet: "partners", headers: "1",
      tq: "select A,B,C,D,E,F,G,H,I,J,K,L,M,N where A is not null", _: String(Date.now())
    });
    script.src = "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/gviz/tq?" + params;
    script.onerror = feedFailed;
    feedTimeout = window.setTimeout(feedFailed, 15000);
    document.head.appendChild(script);
  }
  async function loadFeed() {
    if (loading) return;
    loading = true;
    var controller = new AbortController();
    var deadline = window.setTimeout(function () { controller.abort(); }, 8000);
    try {
      var response = await fetch(CSV_URL, { signal: controller.signal, credentials: "omit", cache: "no-store" });
      if (!response.ok) throw new Error("Partner export HTTP " + response.status);
      applyRows(csvRows(await response.text()));
      loading = false;
    } catch (_) {
      loadJsonp();
    } finally {
      window.clearTimeout(deadline);
    }
  }
  function init() {
    setupMap();
    el("partners-map").addEventListener("click", function (event) {
      var button = event.target.closest("button[data-list-id]");
      if (button) showPartnerInList(button.dataset.listId);
    });
    el("partners-search").addEventListener("input", render);
    el("partners-city").addEventListener("change", render);
    el("partners-reset").addEventListener("click", resetFilters);
    el("partners-map-reset").addEventListener("click", showCountry);
    el("partners-groups").addEventListener("click", function (event) {
      var button = event.target.closest("button[data-map-id]");
      if (button) focusPartner(button.dataset.mapId, false);
    });
    loadFeed();
    window.setInterval(loadFeed, REFRESH_MS);
    window.EversensePartners = {
      reload: loadFeed,
      all: function () { return partners.slice(); },
      visible: filtered,
      isLoaded: function () { return loaded; }
    };
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
