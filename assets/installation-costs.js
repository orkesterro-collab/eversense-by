/* The installation estimate uses the same public workbook as product prices. */
(function () {
  'use strict';
  if (!document.getElementById('ev-calc-form') || window.EversenseInstallationCosts) return;

  var sheetUrl = 'https://docs.google.com/spreadsheets/d/1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY/gviz/tq';
  var storageKey = 'eversense.installation-costs.v1';
  var keys = ['gluePrice', 'underlayPricePerM2', 'glueCoverage', 'underlayCoverage', 'floatRate', 'glueRate'];
  var current = null;
  var request;

  function positive(value) {
    return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
  }

  try {
    var saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && saved.values && saved.savedAt <= Date.now() &&
        saved.savedAt > Date.now() - 7 * 24 * 3600 * 1000 &&
        keys.every(function (key) { return positive(saved.values[key]) !== null; })) {
      current = Object.assign({}, saved.values, {cached: true});
    }
  } catch (_) { /* The live feed also works when storage is disabled. */ }

  function notify() {
    window.dispatchEvent(new CustomEvent('ev-installation-costs-updated'));
  }

  function unavailable() {
    if (current) current.cached = true;
    notify();
  }

  window.EversenseInstallationCosts = {get: function () { return current; }};
  window.EversenseInstallationFeed = function (payload) {
    if (!payload || payload.status !== 'ok' || !payload.table || !Array.isArray(payload.table.rows)) {
      unavailable();
      return;
    }
    var next = {cached: false};
    keys.forEach(function (key) { next[key] = null; });
    payload.table.rows.forEach(function (row) {
      var values = (row.c || []).map(function (cell) { return cell && cell.v; });
      var glue = values[0] === 'На клей';
      if (!glue && values[0] !== 'На подложку') return;
      if (values[1] === 'Материал') {
        next[glue ? 'glueCoverage' : 'underlayCoverage'] = positive(values[2]);
        next[glue ? 'gluePrice' : 'underlayPricePerM2'] = positive(values[3]);
      } else if (values[1] === 'Работа') {
        next[glue ? 'glueRate' : 'floatRate'] = positive(values[3]);
      }
    });
    current = next;
    try {
      if (keys.every(function (key) { return next[key] !== null; })) {
        localStorage.setItem(storageKey, JSON.stringify({values: next, savedAt: Date.now()}));
      } else {
        localStorage.removeItem(storageKey);
      }
    } catch (_) {}
    notify();
  };

  function refresh() {
    if (request) request.remove();
    request = document.createElement('script');
    request.src = sheetUrl + '?' + new URLSearchParams({
      gid: '26112620', range: 'A4:H7', headers: '0', tq: 'select A,B,E,F',
      tqx: 'out:json;responseHandler:EversenseInstallationFeed', nonce: String(Date.now())
    });
    request.onerror = unavailable;
    document.head.appendChild(request);
  }
  refresh();
  setInterval(refresh, 15 * 60 * 1000);
})();
