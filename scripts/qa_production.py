"""Verify the production article, image loading and both homepage entry points."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'buyer-qa' / 'production'
OUT.mkdir(parents=True, exist_ok=True)
server = ThreadingHTTPServer(('127.0.0.1', 8771), partial(SimpleHTTPRequestHandler, directory=str(ROOT / '_deploy')))
Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:8771'
results = []
try:
    with sync_playwright() as p:
        launch = {'executable_path': os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']} if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE') else {}
        browser = p.chromium.launch(**launch)
        for width in (360, 390, 768, 1440):
            page = browser.new_page(viewport={'width': width, 'height': 1000}, device_scale_factor=1)
            failures = []
            page.on('pageerror', lambda err: failures.append(str(err)))
            page.goto(base + '/production.html', wait_until='networkidle')
            assert page.evaluate('async () => (await document.fonts.load(\'16px "EVERSENSE Manrope"\')).length') > 0
            assert page.locator('h1').count() == 1
            assert page.locator('.ev-production-story').count() == 1
            images = page.locator('main img')
            image_count = images.count()
            assert image_count >= 5, 'Article should contain a substantial photo story'
            for image in images.all():
                image.scroll_into_view_if_needed()
                image.evaluate('(el) => el.decode()')
                assert image.evaluate('(el) => el.naturalWidth > 0 && !!el.alt')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Article overflow'
            for anchor in page.locator('.ev-production-toc a').all():
                anchor.click()
                page.wait_for_timeout(350)
                fragment = page.url.split('#')[-1]
                assert page.locator('#' + fragment).count() == 1
            page.evaluate('scrollTo(0,0)')
            page.screenshot(path=str(OUT / f'article-{width}.png'), full_page=True)
            for href in page.locator('main a[href$=".pdf"]').evaluate_all('(es) => es.map(e => e.getAttribute("href"))'):
                if not href.startswith('http'):
                    response = page.request.get(base + '/' + href.lstrip('/'))
                    assert response.ok and response.body().startswith(b'%PDF-'), href
            assert not failures, failures
            for route in ('/', '/ru/'):
                page.goto(base + route, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)  # Original Tilda records settle after initialization.
                feature = page.locator('#ev-production-feature')
                assert feature.count() == 1
                feature.scroll_into_view_if_needed()
                feature.locator('img').evaluate('(el) => el.decode()')
                button = feature.locator('.ev-production-feature-button')
                button.click(trial=True)  # Verify it is actually visible and receives pointer events.
                box = feature.bounding_box()
                assert box['x'] >= 0 and box['width'] <= width
                assert feature.evaluate('(el) => el.scrollWidth <= el.clientWidth'), 'Feature overflow'
                if route == '/':
                    feature.screenshot(path=str(OUT / f'home-feature-{width}.png'))
                if route == '/':
                    button.click()
                else:
                    button.focus()
                    page.keyboard.press('Enter')
                page.wait_for_url('**/production.html')
                assert page.locator('h1').is_visible()
            results.append({'width': width, 'article': 'passed', 'images': image_count, 'home_routes': 2})
            page.close()
        context = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 900})
        page = context.new_page()
        page.goto(base + '/production.html')
        assert page.locator('h1').is_visible() and page.locator('.ev-production-toc a').count() >= 5
        results.append({'without_javascript': 'article and navigation accessible'})
        browser.close()
finally:
    server.shutdown()
    (OUT / 'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(json.dumps(results), flush=True)
