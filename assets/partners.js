/* EVERSENSE Беларусь. Dealer directory is read from the public Google Sheets "partners" tab.
 * No credentials or demo partner contacts are embedded in this JavaScript.
 */
(function () {
  "use strict";

  var SHEET_ID = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY";
  var REFRESH_MS = 15 * 60 * 1000;
  var el = function (id) { return document.getElementById(id); };
  var locale = new Intl.Collator("ru", { sensitivity: "base" });
  var partners = [];
  var map = null;
  var markers = new Map();
  var layer = null;
  var selectedId = null;
  var loaded = false;
  var initialCity = "";
  var initialQuery = "";
  var liveTimer = null;
  var feedTimeout = null;

  function escapeHTML(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function cell(row, i) {
    var c = (row && row.c && row.c[i]) || null;
    return c && c.v != null ? c.v : "";
  }
  function toNumber(value) {
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
    return /^\+375\d{9}$/.test(number) ? "tel:" + number : null;
  }
  function validCoords(lat, lng) {
    return lat !== null && lng !== null && lat >= 51 && lat <= 57 && lng >= 23 && lng <= 33.5;
  }
  function parseRow(row) {
    var p = {
      id: trim(cell(row, 0)),
      order: toNumber(cell(row, 1)),
      city: trim(cell(row, 2)),
      district: trim(cell(row, 3)),
      name: trim(cell(row, 4)),
      website: trim(cell(row, 5)),
      phone: trim(cell(row, 6)),
      address: trim(cell(row, 7)),
      hours: trim(cell(row, 8)),
      lat: toNumber(cell(row, 9)),
      lng: toNumber(cell(row, 10)),
      active: toBool(cell(row, 11), true),
      demo: toBool(cell(row, 12), false)
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
    var q = trim(el("partners-search").value).toLocaleLowerCase("ru");
    var city = el("partners-city").value;
    return partners.filter(function (p) {
      if (city && city !== p.city) return false;
      if (!q) return true;
      return [p.id, p.city, p.district, p.name, p.address, p.hours]
        .some(function (part) { return part.toLocaleLowerCase("ru").includes(q); });
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
      '</span><span class="chevron" aria-hidden="true"></span></summary>' +
      '<div class="partner-card__body">' +
        '<dl>' +
          '<div class="partner-card__row"><dt>Адрес</dt><dd>' + escapeHTML(p.address || "Уточняется") + '</dd></div>' +
          '<div class="partner-card__row"><dt>Телефон</dt><dd>' + phoneMarkup + '</dd></div>' +
          '<div class="partner-card__row"><dt>Сайт</dt><dd>' + siteMarkup + '</dd></div>' +
          '<div class="partner-card__row"><dt>Режим работы</dt><dd>' + escapeHTML(p.hours || "Уточняется") + '</dd></div>' +
        '</dl>' +
        '<div class="partner-card__foot">' +
        (validCoords(p.lat, p.lng) ? '<button type="button" class="partner-card__showmap" data-map-id="' + key + '">Показать на карте ↗</button>' : '') +
        '</div>' +
      '</div></details>';
  }
  function districtMarkup(cityRecords) {
    var all = new Map();
    cityRecords.forEach(function (p) {
      var name = p.district || "Район не указан";
      if (!all.has(name)) all.set(name, []);
      all.get(name).push(p);
    });
    var districts = Array.from(all.keys()).sort(function (a, b) {
      var ra = all.get(a).slice().sort(orderByRank)[0];
      var rb = all.get(b).slice().sort(orderByRank)[0];
      return orderByRank(ra, rb) || locale.compare(a, b);
    });
    // District names and their dealer cards are always visible.
    // Only individual dealer contact details require a click.
    return '<div class="district-grid">' + districts.map(function (district) {
      var records = all.get(district).slice().sort(orderByRank);
      var title = district === "Район не указан" ? district : district + " район";
      return '<section class="district-group" aria-label="' + escapeHTML(title) + '">' +
        '<div class="district-group__heading"><h3 class="district-group__name">' +
          escapeHTML(title) + '</h3></div>' +
        '<div class="district-group__body"><div class="partner-list">' +
          records.map(partnerMarkup).join("") + '</div></div></section>';
    }).join("") + "</div>";
  }
  function renderList(items) {
    var root = el("partners-groups");
    var cities = cityNames(items);
    var allExpanded = !!(trim(el("partners-search").value) || el("partners-city").value);
    if (!items.length) {
      root.innerHTML = '<div class="no-results">По вашему запросу партнёры не найдены. Измените фильтр или сбросьте поиск.</div>';
      return;
    }
    root.innerHTML = cities.map(function (city) {
      var records = items.filter(function (p) { return p.city === city; }).sort(orderByRank);
      var minsk = city.toLocaleLowerCase("ru") === "минск";
      var body = minsk ? districtMarkup(records) : '<div class="partner-list">' +
        records.map(partnerMarkup).join("") + "</div>";
      var title = '<span class="city-group__name">' + escapeHTML(city) + '</span>';
      if (minsk) {
        return '<section class="city-group city-group--minsk" data-city="' + escapeHTML(city) +
          '" aria-label="Партнёры Минска по районам">' +
          '<div class="city-group__heading">' + title + '</div>' +
          '<div class="city-group__body">' + body + '</div></section>';
      }
      return '<details class="city-group" data-city="' + escapeHTML(city) + '"' +
        (allExpanded ? " open" : "") + '><summary>' + title +
        '<span class="chevron" aria-hidden="true"></span></summary>' +
        '<div class="city-group__body">' + body + "</div></details>";
    }).join("");
  }
  function icon(p, selected) {
    return window.L.divIcon({
      className: "ev-pin " + (p.demo ? "ev-pin--demo " : "") + (selected ? "ev-pin--selected" : ""),
      html: '<span class="ev-pin__dot"></span>',
      iconSize: [30, 30], iconAnchor: [15, 15]
    });
  }
  function popupMarkup(p) {
    return '<div class="ev-popup"><p class="ev-popup__name">' + escapeHTML(p.name) + '</p>' +
      '<p class="ev-popup__meta">' + escapeHTML(locationLabel(p)) + '</p>' +
      (p.demo ? '<div class="ev-popup__note">Условная демо-точка, не действующий дилер</div>' : "") +
      "</div>";
  }
  function setupMap() {
    if (map || !window.L) return !!map;
    var target = el("partners-map");
    target.innerHTML = "";
    map = window.L.map(target, { zoomControl: false, scrollWheelZoom: false });
    window.L.control.zoom({ position: "bottomright" }).addTo(map);
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a target="_blank" rel="noopener" href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    layer = window.L.layerGroup().addTo(map);
    map.setView([53.65, 27.88], 6);
    window.setTimeout(function () { map.invalidateSize(); }, 300);
    return true;
  }
  function renderMap(items) {
    if (!setupMap()) {
      el("partners-map").innerHTML = '<div class="map-skeleton">Карта временно недоступна. Полный список партнёров приведён ниже.</div>';
      return;
    }
    layer.clearLayers();
    markers.clear();
    var coords = [];
    items.forEach(function (p) {
      if (!validCoords(p.lat, p.lng)) return;
      var m = window.L.marker([p.lat, p.lng], { icon: icon(p, p.id === selectedId), title: p.name });
      m.bindPopup(popupMarkup(p), { closeButton: true, autoPanPadding: [28, 35] });
      m.on("click", function () { focusPartner(p.id, true); });
      m.addTo(layer);
      markers.set(p.id, m);
      coords.push([p.lat, p.lng]);
    });
    if (!coords.length) return;
    if (coords.length === 1) {
      map.setView(coords[0], 12, { animate: false });
    } else {
      map.fitBounds(coords, { padding: [24, 24], maxZoom: el("partners-city").value ? 12 : 7, animate: false });
    }
    window.setTimeout(function () { map.invalidateSize(); }, 80);
  }
  function focusPartner(id, fromMap) {
    var p = partners.find(function (entry) { return entry.id === id; });
    if (!p) return;
    selectedId = p.id;
    document.querySelectorAll(".partner-card--selected").forEach(function (card) {
      card.classList.remove("partner-card--selected");
    });
    var cards = Array.from(document.querySelectorAll(".partner-card"));
    var card = cards.find(function (item) { return item.dataset.partnerId === id; });
    if (card) {
      var n = card.parentElement;
      while (n && n !== document.body) {
        if (n.tagName === "DETAILS") n.open = true;
        n = n.parentElement;
      }
      card.open = true;
      card.classList.add("partner-card--selected");
      if (fromMap) {
        card.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
    markers.forEach(function (marker, markerId) {
      var item = partners.find(function (entry) { return entry.id === markerId; });
      if (item) marker.setIcon(icon(item, markerId === selectedId));
    });
    var marker = markers.get(id);
    if (marker && map) {
      map.flyTo([p.lat, p.lng], Math.max(map.getZoom(), 11), { duration: 0.5 });
      marker.openPopup();
      if (!fromMap) {
        el("partners-map").scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }
  function render() {
    var list = filtered();
    el("partners-reset").hidden = !(trim(el("partners-search").value) || el("partners-city").value);
    renderList(list);
    renderMap(list);
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
  window.EversensePartnersFeed = function (payload) {
    window.clearTimeout(feedTimeout);
    if (!payload || payload.status !== "ok" || !payload.table || !Array.isArray(payload.table.rows)) {
      if (!loaded) setError("Не удалось прочитать лист partners. Проверьте доступ Google Sheets «Все, у кого есть ссылка → Читатель».");
      return;
    }
    var next = payload.table.rows.map(parseRow).filter(Boolean);
    var seen = new Set();
    next = next.filter(function (p) {
      if (seen.has(p.id)) return false;
      seen.add(p.id);
      return true;
    });
    partners = next;
    loaded = true;
    refreshCities();
    setReady();
    render();
  };
  function loadFeed() {
    var old = el("partners-jsonp");
    if (old) old.remove();
    var script = document.createElement("script");
    script.id = "partners-jsonp";
    var params = new URLSearchParams({
      tqx: "out:json;responseHandler:EversensePartnersFeed",
      sheet: "partners",
      headers: "1",
      tq: "select A,B,C,D,E,F,G,H,I,J,K,L,M",
      _: String(Date.now())
    });
    script.src = "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/gviz/tq?" + params.toString();
    script.onerror = function () {
      if (!loaded) setError("Не удалось загрузить список партнёров из Google Sheets. Попробуйте обновить страницу.");
    };
    document.head.appendChild(script);
    window.clearTimeout(feedTimeout);
    feedTimeout = window.setTimeout(function () {
      if (!loaded) setError("Google Sheets не ответил. Проверьте публичный доступ к таблице.");
    }, 22000);
  }
  function init() {
    el("partners-search").addEventListener("input", render);
    el("partners-city").addEventListener("change", render);
    el("partners-reset").addEventListener("click", function () {
      el("partners-search").value = "";
      el("partners-city").value = "";
      render();
    });
    el("partners-map-reset").addEventListener("click", function () {
      if (map && markers.size) renderMap(filtered());
    });
    el("partners-groups").addEventListener("click", function (event) {
      var btn = event.target.closest("button[data-map-id]");
      if (btn) {
        event.preventDefault();
        focusPartner(btn.dataset.mapId, false);
        return;
      }
      var summary = event.target.closest(".partner-card > summary");
      if (summary && summary.parentElement) {
        var card = summary.parentElement;
        var id = card.dataset.partnerId;
        // Native details toggle handles expanding contacts; centre the map marker.
        var p = partners.find(function (entry) { return entry.id === id; });
        if (p && markers.has(id)) {
          selectedId = id;
          var marker = markers.get(id);
          marker.setIcon(icon(p, true));
          marker.openPopup();
        }
      }
    });
    loadFeed();
    liveTimer = window.setInterval(loadFeed, REFRESH_MS);
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