#!/usr/bin/env python3
"""Check the history reading journey against local files, never the live site."""
import argparse
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=root)
    parser.add_argument('--output', type=Path, default=root / 'buyer-qa/history')
    parser.add_argument('--executable', default=None)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=str(args.site_dir.resolve()))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    results = []
    try:
        with sync_playwright() as p:
            options = {'headless': True}
            if args.executable:
                options['executable_path'] = args.executable
            browser = p.chromium.launch(**options)
            for width in (1440, 768, 390, 360):
                context = browser.new_context(viewport={'width': width, 'height': 950}, reduced_motion='reduce')
                context.route('https://**/*', lambda route: route.abort())
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base + '/history.html', wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                assert page.locator('h1').count() == 1
                assert page.locator('.chapter').count() == 5
                assert page.locator('.production-route li').count() == 6
                hero_image = page.locator('.hero-img img').get_attribute('src')
                assert hero_image == 'assets/history/factory-gagarin.webp'
                assert page.locator('.launch-gallery img').count() == 2
                article_text = page.locator('main').inner_text().lower()
                assert 'egger' not in article_text and 'эггер' not in article_text and 'шуя' not in article_text
                assert 'продукт года' in article_text and 'best for life design' in article_text
                assert page.locator('a[href*="eversense-technical-certificate"]').count() >= 1
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                assert not overflow, f'History page overflows at {width}px'
                page.screenshot(path=str(args.output / f'history-{width}-top.png'))
                for image in page.locator('main img').all():
                    image.scroll_into_view_if_needed()
                    page.wait_for_function('(img) => img.complete && img.naturalWidth > 0', arg=image.element_handle())
                page.locator('.timeline-nav a[href="#roots"]').click()
                page.wait_for_function('document.querySelector(".timeline-nav a[aria-current=true]").hash === "#roots"')
                page.screenshot(path=str(args.output / f'history-{width}-roots.png'))
                page.locator('#roots .ref').first.click()
                page.wait_for_function('document.querySelector("#sources").open')
                page.goto(base + '/index.html', wait_until='domcontentloaded')
                banner = page.locator('#ev-history-banner')
                banner.scroll_into_view_if_needed()
                assert banner.count() == 1
                assert banner.evaluate('(el) => el.nextElementSibling.id === "ev-home-footer"')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), f'Homepage overflows at {width}px'
                assert page.locator('#ev-home-footer').inner_text().find('192608003') >= 0
                image = banner.locator('img')
                assert image.get_attribute('src') == hero_image
                page.wait_for_function('(img) => img.complete && img.naturalWidth > 0', arg=image.element_handle())
                banner.screenshot(path=str(args.output / f'banner-{width}.png'))
                banner.get_by_role('link').click()
                page.wait_for_url('**/history.html')
                assert not errors, errors
                results.append({'width': width, 'status': 'passed'})
                context.close()
            context = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
            page = context.new_page()
            page.goto(base + '/history.html')
            assert page.locator('.chapter').count() == 5
            page.locator('#sources summary').click()
            assert page.locator('#source-8').is_visible()
            results.append({'javascript': False, 'status': 'passed'})
            context.close()
            browser.close()
    finally:
        server.shutdown()
        (args.output / 'summary.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
