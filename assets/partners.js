/* EVERSENSE Беларусь. Dealer directory is read from the public Google Sheets "partners" tab.
 * No credentials or demo partner contacts are embedded in this JavaScript.
 */
(function () {
  "use strict";

  var SHEET_ID = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY";
  var CSV_URL = "https://docs.google.com/spreadsheets/d/" + SHEET_ID + "/export?format=csv&gid=24681103&range=A%3AN";
  // Approximate city centres for the overview only. Directions use each shop's own coordinates or address.
  var CITY_CENTRES = new Map([["береза", [52.53, 24.98]], ["слуцк", [53.02, 27.54]]]);
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
  var updateMapLocations;
  var loaded = false;
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
  function cityGroupId(city) {
    return "city-" + city.replace(/\s+/g, "-");
  }
  function directionsMarkup(p) {
    if (p.demo || (!p.address && !validCoords(p.lat, p.lng))) return "";
    var url = new URL("https://yandex.by/maps/");
    var label;
    if (validCoords(p.lat, p.lng)) {
      url.searchParams.set("rtext", "~" + p.lat + "," + p.lng);
      url.searchParams.set("rtt", "auto");
      label = 'Построить маршрут<span class="sr-only"> в Яндекс Картах</span>';
    } else {
      url.searchParams.set("text", ["Беларусь", p.city, p.address].join(", "));
      label = "Найти адрес в Яндекс Картах";
    }
    return '<div class="partner-card__foot"><a class="partner-card__route" target="_blank" rel="noopener noreferrer" href="' +
      escapeHTML(url.href) + '">' + label + '</a></div>';
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
    return '<details class="partner-card" id="shop-' + key + '" data-partner-id="' + key + '">' +
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
        directionsMarkup(p) +
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
        return '<section class="city-group city-group--minsk" id="' + escapeHTML(cityGroupId(city)) + '" data-city="' + escapeHTML(city) +
          '" aria-label="Магазины Минска">' +
          '<h3 class="city-group__heading" tabindex="-1">' + title + '</h3>' +
          '<div class="city-group__body">' + body + '</div></section>';
      }
      return '<details class="city-group" id="' + escapeHTML(cityGroupId(city)) + '" data-city="' + escapeHTML(city) + '" open><summary>' + title +
        '<span class="chevron" aria-hidden="true"></span></summary>' +
        '<div class="city-group__body">' + body + "</div></details>";
    }).join("");
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
  // Equirectangular extent around Belarus. Both layers use the same percentage coordinates.
  function project(lat, lng) {
    return { x: (lng - 22.7) / 10.5 * 100, y: (56.45 - lat) / 5.4 * 100 };
  }
  function overlapArea(a, b) {
    return Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
      * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  }
  function layoutMapLabels() {
    var layer = el("map-cities");
    if (!layer.clientWidth) return;
    var bounds = { left: 1, top: 1, right: layer.clientWidth - 1, bottom: layer.clientHeight - 1 };
    var pins = Array.from(layer.children, function (link) {
      return { link: link, x: link.offsetLeft, y: link.offsetTop,
        width: link.firstElementChild.offsetWidth, height: link.firstElementChild.offsetHeight };
    });
    var occupied = pins.map(function (pin) {
      return { left: pin.x - 6, right: pin.x + 6, top: pin.y - 6, bottom: pin.y + 6 };
    });
    pins.forEach(function (pin) {
      var w = pin.width, h = pin.height;
      var gap = pin.link.classList.contains("map-city--capital") ? 11 : 7;
      var positions = [[gap, -h / 2], [-w - gap, -h / 2], [-w / 2, -h - gap],
        [-w / 2, gap], [gap, -h - 4], [-w - gap, -h - 4], [gap, 4], [-w - gap, 4]];
      var best, bestScore = Infinity;
      for (var offset of positions) {
        var left = pin.x + offset[0], top = pin.y + offset[1];
        var box = { left: left, top: top, right: left + w, bottom: top + h };
        var score = (w * h - overlapArea(box, bounds)) * 10;
        occupied.forEach(function (other) { score += overlapArea(box, other); });
        if (score < bestScore) { best = box; bestScore = score; }
        if (score === 0) break;
      }
      pin.link.style.setProperty("--label-x", (best.left - pin.x) + "px");
      pin.link.style.setProperty("--label-y", (best.top - pin.y) + "px");
      occupied.push({ left: best.left - 2, top: best.top - 2, right: best.right + 2, bottom: best.bottom + 2 });
    });
  }
  function renderMap() {
    var links = document.createDocumentFragment();
    var locations = [];
    cityNames(partners).forEach(function (city) {
      var located = partners.filter(function (p) { return p.city === city && validCoords(p.lat, p.lng); });
      var centre = CITY_CENTRES.get(searchable(city));
      if (located.length) {
        var lat = 0, lng = 0;
        located.forEach(function (p) { lat += p.lat; lng += p.lng; });
        centre = [lat / located.length, lng / located.length];
      }
      if (!centre) return;
      var point = project(centre[0], centre[1]);
      var link = document.createElement("a");
      link.className = searchable(city) === "минск" ? "map-city map-city--capital" : "map-city";
      link.dataset.city = city;
      link.href = "#" + encodeURIComponent(cityGroupId(city));
      link.setAttribute("aria-label", document.documentElement.lang === "en" ? "Show stores in " + city : city + " — показать магазины");
      link.style.left = point.x + "%";
      link.style.top = point.y + "%";
      var label = document.createElement("span");
      label.className = "map-city__label";
      label.textContent = city;
      link.appendChild(label);
      links.appendChild(link);
      locations.push({name: city, coordinates: [centre[1], centre[0]], href: link.getAttribute("href"), shops: located});
    });
    var layer = el("map-cities");
    layer.replaceChildren(links);
    el("map-hint").hidden = !layer.childElementCount;
    if (updateMapLocations) updateMapLocations(locations);
    layoutMapLabels();
  }
  function showCity(city) {
    var filterCity = el("partners-city").value;
    if (el("partners-search").value || (filterCity && filterCity !== city)) resetFilters();
    var group = el(cityGroupId(city));
    if (!group) return;
    if (group.tagName === "DETAILS") group.open = true;
    group.scrollIntoView({ block: "start" });
    group.firstElementChild.focus({ preventScroll: true });
  }
  function openMapLocation(city, shopId) {
    if (!shopId) {
      showCity(city);
      return;
    }
    if (!cardById(shopId)) resetFilters();
    var card = cardById(shopId);
    if (!card) return;
    var group = el(cityGroupId(city));
    if (group.tagName === "DETAILS") group.open = true;
    card.open = true;
    card.scrollIntoView({block: "start"});
    card.firstElementChild.focus({preventScroll: true});
  }
  function openLinkedLocation() {
    var hash = location.hash;
    if (hash.startsWith("#shop-")) {
      var item = partners.find(function (p) { return "#shop-" + encodeURIComponent(p.id) === hash; });
      if (item) openMapLocation(item.city, item.id);
      return;
    }
    var link = Array.from(el("map-cities").children).find(function (item) { return item.hash === hash; });
    if (link) showCity(link.dataset.city);
  }
  function setupMap() {
    if (document.documentElement.lang === "en") {
      el("partners-map-panel").setAttribute("aria-label", "EVERSENSE stores in Belarus");
      el("map-cities").setAttribute("aria-label", "Find stores by city");
    }
    var path = COUNTRY_OUTLINE.map(function (coords) {
      var point = project(coords[0], coords[1]);
      return point.x.toFixed(3) + "," + point.y.toFixed(3);
    });
    el("country-outline").setAttribute("d", "M" + path.join(" L") + " Z");
    el("partners-map-panel").addEventListener("click", function (event) {
      var link = event.target.closest("a[data-city]");
      if (document.documentElement.classList.contains("map-embed")) return;
      if (!link || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (location.hash !== link.hash) history.pushState(null, "", link.hash);
      openMapLocation(link.dataset.city, link.dataset.partnerId);
    });
    if (window.EversenseShopMap) updateMapLocations = window.EversenseShopMap.mount(el("partners-basemap"));
    window.addEventListener("hashchange", openLinkedLocation);
    if (window.ResizeObserver) new ResizeObserver(layoutMapLabels).observe(el("partners-map"));
    else window.addEventListener("resize", layoutMapLabels);
    if (document.fonts) document.fonts.ready.then(layoutMapLabels);
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
    var firstLoad = !loaded;
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
    if (firstLoad && location.hash) openLinkedLocation();
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
    el("partners-search").addEventListener("input", render);
    el("partners-city").addEventListener("change", render);
    el("partners-reset").addEventListener("click", resetFilters);
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
