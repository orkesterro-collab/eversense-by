"""Check article layout, anchor navigation and original PDF downloads."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import hashlib
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'buyer-qa' / 'laminate-classes'
OUT.mkdir(parents=True, exist_ok=True)
server = ThreadingHTTPServer(('127.0.0.1', 8767), partial(SimpleHTTPRequestHandler, directory=str(ROOT / '_deploy')))
Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:8767'
results = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width in (360, 390, 1440):
            page = browser.new_page(viewport={'width': width, 'height': 900}, accept_downloads=True)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(base + '/laminate-classes.html', wait_until='networkidle')
            assert page.locator('h1').count() == 1
            assert page.locator('table').count() == 2
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Article overflow'
            page.screenshot(path=str(OUT / f'article-{width}.png'), full_page=True)
            for fragment in ('classes', 'impact-resistance'):
                page.locator(f'.ev-install-toc a[href="#{fragment}"]').click()
                page.wait_for_timeout(600)
                assert page.url.endswith('#' + fragment)
                top = page.locator('#' + fragment).bounding_box()['y']
                assert 0 <= top < 250, (fragment, top)
            for i in range(2):
                link = page.locator('#test-results a[download]').nth(i)
                local = ROOT / '_deploy' / link.get_attribute('href').lstrip('/')
                with page.expect_download() as download:
                    link.click()
                received = Path(download.value.path()).read_bytes()
                assert received.startswith(b'%PDF-')
                assert hashlib.sha256(received).digest() == hashlib.sha256(local.read_bytes()).digest()
            assert not errors, errors
            for route in ('/', '/ru/'):
                page.goto(base + route, wait_until='domcontentloaded')
                page.wait_for_timeout(1500)
                # The looping Tilda carousel clones slides; verify the original records.
                links = page.locator('#rec1003959231 .ev-home-article-link, #rec1028577716 .ev-home-article-link, #rec1028577721 .ev-home-article-link')
                assert links.count() == 7, links.evaluate_all('(es) => es.map(e => ({text: e.textContent, href: e.href}))')
                targets = links.evaluate_all('(es) => es.map(e => new URL(e.href).hash)')
                assert targets.count('#classes') == 4 and targets.count('#impact-resistance') == 3
                # The visible class link above the carousel must remain a real click target.
                visible = page.locator('#rec1003959231 .ev-home-article-link')
                visible.click()
                page.wait_for_url('**/laminate-classes.html#classes')
            results.append({'width': width, 'article': 'passed', 'downloads': 2, 'home_routes': 2})
            page.close()
        browser.close()
finally:
    server.shutdown()
    (OUT / 'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(json.dumps(results), flush=True)
