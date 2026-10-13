/* «Где купить»: переключение список/карта, фильтр по городу, Яндекс Карта. */
(function () {
	'use strict';

	var root = document.querySelector('[data-where]');
	var dataEl = document.getElementById('ev-map-data');
	if (!root || !dataEl) return;

	var data = JSON.parse(dataEl.textContent || '{}');
	var map = null;
	var placemarks = [];

	function initMap() {
		if (map || !window.ymaps) return;
		ymaps.ready(function () {
			map = new ymaps.Map('ev-map', {
				center: data.center,
				zoom: data.zoom,
				controls: ['zoomControl', 'fullscreenControl']
			});
			map.behaviors.disable('scrollZoom');
			(data.points || []).forEach(function (p) {
				var body = [p.address, p.phone ? '<a href="tel:' + p.phone.replace(/[^0-9+]/g, '') + '">' + p.phone + '</a>' : '', p.hours ? data.i18n.hours + ': ' + p.hours : '', p.site ? '<a href="' + p.site + '" target="_blank" rel="noopener">' + data.i18n.site + '</a>' : '']
					.filter(Boolean).join('<br>');
				var pm = new ymaps.Placemark(p.coords, {
					balloonContentHeader: p.title,
					balloonContentBody: body,
					hintContent: p.title
				}, {
					preset: 'islands#circleDotIcon',
					iconColor: '#C0A58C'
				});
				pm.properties.set('city', p.city);
				placemarks.push(pm);
				map.geoObjects.add(pm);
			});
			fit();
		});
	}

	function fit(city) {
		if (!map) return;
		var visible = placemarks.filter(function (pm) {
			var on = !city || pm.properties.get('city') === city;
			pm.options.set('visible', on);
			return on;
		});
		if (visible.length > 1) {
			var coll = new ymaps.GeoObjectCollection();
			visible.forEach(function (pm) { coll.add(new ymaps.Placemark(pm.geometry.getCoordinates())); });
			map.setBounds(coll.getBounds(), { checkZoomRange: true, zoomMargin: 40 });
		} else if (visible.length === 1) {
			map.setCenter(visible[0].geometry.getCoordinates(), 14);
		}
	}

	root.querySelectorAll('[data-view]').forEach(function (btn) {
		btn.addEventListener('click', function () {
			var view = btn.getAttribute('data-view');
			root.querySelectorAll('[data-view]').forEach(function (b) {
				var on = b === btn;
				b.classList.toggle('is-active', on);
				b.setAttribute('aria-selected', on ? 'true' : 'false');
			});
			root.querySelectorAll('[data-panel]').forEach(function (p) {
				p.hidden = p.getAttribute('data-panel') !== view;
			});
			if (view === 'map') {
				initMap();
				if (map) map.container.fitToViewport();
			}
		});
	});

	var select = root.querySelector('[data-city]');
	if (select) {
		select.addEventListener('change', function () {
			var city = select.value;
			root.querySelectorAll('[data-city-group]').forEach(function (g) {
				g.hidden = !!city && g.getAttribute('data-city-group') !== city;
			});
			fit(city);
		});
	}
})();
