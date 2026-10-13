/* EVERSENSE — поведение страниц. Без зависимостей. */
(function () {
	'use strict';

	var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

	/* Шапка поверх первого экрана: становится белой после прокрутки. */
	var header = document.querySelector('[data-header]');
	if (header && document.body.classList.contains('ev-has-hero')) {
		var onScroll = function () {
			header.classList.toggle('is-scrolled', window.scrollY > 40);
		};
		window.addEventListener('scroll', onScroll, { passive: true });
		onScroll();
	}

	/* Мобильное меню. */
	var drawer = document.querySelector('[data-drawer]');
	var opener = document.querySelector('[data-drawer-open]');
	if (drawer && opener) {
		var open = function () {
			drawer.hidden = false;
			opener.setAttribute('aria-expanded', 'true');
			document.body.style.overflow = 'hidden';
			var first = drawer.querySelector('[data-drawer-close]');
			if (first) first.focus();
		};
		var close = function () {
			drawer.hidden = true;
			opener.setAttribute('aria-expanded', 'false');
			document.body.style.overflow = '';
			opener.focus();
		};
		opener.addEventListener('click', open);
		drawer.addEventListener('click', function (e) {
			if (e.target === drawer || e.target.closest('[data-drawer-close]')) close();
		});
		document.addEventListener('keydown', function (e) {
			if (e.key === 'Escape' && !drawer.hidden) close();
		});
	}

	/* Слайдеры: [data-slider] > [data-slide], кнопки [data-prev]/[data-next], точки [data-dots]. */
	document.querySelectorAll('[data-slider]').forEach(function (root) {
		var slides = Array.prototype.slice.call(root.querySelectorAll('[data-slide]'));
		if (slides.length < 2) return;
		var dotsBox = root.querySelector('[data-dots]');
		var dots = [];
		var index = 0;
		var timer = null;
		var delay = parseInt(root.getAttribute('data-autoplay'), 10) || 0;

		var go = function (i) {
			index = (i + slides.length) % slides.length;
			slides.forEach(function (s, n) {
				var on = n === index;
				s.classList.toggle('is-active', on);
				s.setAttribute('aria-hidden', on ? 'false' : 'true');
				s.querySelectorAll('a, button').forEach(function (el) { el.tabIndex = on ? 0 : -1; });
			});
			dots.forEach(function (d, n) { d.setAttribute('aria-current', n === index ? 'true' : 'false'); });
		};
		var restart = function () {
			if (!delay || reduce) return;
			clearInterval(timer);
			timer = setInterval(function () { go(index + 1); }, delay);
		};

		if (dotsBox) {
			slides.forEach(function (s, n) {
				var b = document.createElement('button');
				b.type = 'button';
				b.setAttribute('aria-label', (n + 1) + ' / ' + slides.length);
				b.addEventListener('click', function () { go(n); restart(); });
				dotsBox.appendChild(b);
				dots.push(b);
			});
		}
		var prev = root.querySelector('[data-prev]');
		var next = root.querySelector('[data-next]');
		if (prev) prev.addEventListener('click', function () { go(index - 1); restart(); });
		if (next) next.addEventListener('click', function () { go(index + 1); restart(); });

		// Свайп на телефоне.
		var x0 = null;
		root.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
		root.addEventListener('touchend', function (e) {
			if (x0 === null) return;
			var dx = e.changedTouches[0].clientX - x0;
			if (Math.abs(dx) > 50) { go(index + (dx < 0 ? 1 : -1)); restart(); }
			x0 = null;
		}, { passive: true });

		root.addEventListener('mouseenter', function () { clearInterval(timer); });
		root.addEventListener('mouseleave', restart);
		go(0);
		restart();
	});

	/* Появление блоков при прокрутке и запуск видео, когда оно на экране. */
	if ('IntersectionObserver' in window) {
		var revealer = new IntersectionObserver(function (entries) {
			entries.forEach(function (e) {
				if (e.isIntersecting) {
					e.target.classList.add('is-in');
					revealer.unobserve(e.target);
				}
			});
		}, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
		document.querySelectorAll('[data-reveal]').forEach(function (el) { revealer.observe(el); });

		var videos = new IntersectionObserver(function (entries) {
			entries.forEach(function (e) {
				var v = e.target;
				if (e.isIntersecting) {
					if (v.preload === 'none') v.preload = 'auto';
					var p = v.play();
					if (p && p.then) p.then(function () { v.classList.add('is-playing'); }).catch(function () {});
				} else {
					v.pause();
				}
			});
		}, { threshold: 0.2 });
		if (!reduce) document.querySelectorAll('video[data-autoplay]').forEach(function (v) { videos.observe(v); });
	} else {
		document.querySelectorAll('[data-reveal]').forEach(function (el) { el.classList.add('is-in'); });
	}

	/* «Вернуться назад»: если пришли с этого же сайта — назад по истории. */
	document.querySelectorAll('[data-back]').forEach(function (a) {
		a.addEventListener('click', function (e) {
			if (document.referrer && document.referrer.indexOf(location.host) !== -1 && history.length > 1) {
				e.preventDefault();
				history.back();
			}
		});
	});

	/* Плашка cookie. */
	var cookie = document.querySelector('[data-cookie]');
	if (cookie) {
		var KEY = 'ev_cookie_ok';
		var seen = false;
		try { seen = localStorage.getItem(KEY) === '1'; } catch (e) {}
		if (!seen) cookie.hidden = false;
		var ok = cookie.querySelector('[data-cookie-ok]');
		if (ok) ok.addEventListener('click', function () {
			cookie.hidden = true;
			try { localStorage.setItem(KEY, '1'); } catch (e) {}
		});
	}
})();
