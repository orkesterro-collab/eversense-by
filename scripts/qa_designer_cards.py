#!/usr/bin/env python3
"""Check all thirty designer cards at desktop and mobile widths on the staged site.

Uses Playwright's bundled Chromium and a temporary loopback HTTP server.
Screenshots and a machine-readable summary go to buyer-qa/designer-cards.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEVICES = [(1440, 1000), (360, 800)]
PRODUCT_COUNT = 30
SELECTOR = "#ev-designer-card"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def inspect_card(page):
    return page.locator(SELECTOR).evaluate(r"""s => {
        const text = el => el.textContent.replace(/\s+/g, ' ').trim();
        const palette = s.querySelector('.ev-designer-card__materials');
        const interior = s.querySelector('.ev-designer-card__interior');
        const sr = s.getBoundingClientRect();
        const next = s.nextElementSibling;
        // Tilda renders the label and its clickable background as separate nodes.
        const catalogHeading = next && [...next.querySelectorAll('h1,h2,h3,h4,a')]
            .find(el => /^В каталог$/i.test(text(el)));
        const catalogLink = next && [...next.querySelectorAll('a[href]')].find(a => {
            const url = new URL(a.getAttribute('href'), document.baseURI);
            return url.origin === location.origin &&
                url.pathname.replace(/\/index\.html$/, '/').replace(/\/+$/, '') === '/catalog-ru';
        });
        const visible = el => {
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0 &&
                getComputedStyle(el).visibility !== 'hidden';
        };
        const overflow = [...s.querySelectorAll('*')].filter(visible).filter(el => {
            const r = el.getBoundingClientRect();
            return r.left < sr.left - 1 || r.right > sr.right + 1 ||
                (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1);
        }).map(el => ({tag: el.tagName, class: el.className}));
        return {
            sku: s.dataset.floorSku,
            sectionCount: document.querySelectorAll('#ev-designer-card').length,
            stylesheetCount: document.querySelectorAll('#ev-designer-card-css').length,
            title: text(s.querySelector('h2')),
            floor: text(s.querySelector('.ev-designer-card__floor')),
            swatchCount: s.querySelectorAll('.ev-designer-card__swatch').length,
            interiorImageCount: interior.querySelectorAll('img').length,
            names: [...palette.querySelectorAll('h4')].map(text),
            codes: [...palette.querySelectorAll('.ev-designer-card__code')].map(text),
            images: [...s.querySelectorAll('img')].map(el => {
                const url = new URL(el.currentSrc || el.src, document.baseURI);
                return {src: url.pathname, local: url.origin === location.origin,
                    loaded: el.complete && el.naturalWidth > 0 && el.naturalHeight > 0,
                    width: el.naturalWidth, height: el.naturalHeight};
            }),
            columns: getComputedStyle(palette).gridTemplateColumns.trim().split(/\s+/).length,
            interiorBelow: interior.getBoundingClientRect().top >=
                palette.getBoundingClientRect().bottom - 1,
            withinViewport: sr.left >= -1 && sr.right <= innerWidth + 1,
            ownWidth: s.clientWidth,
            ownScrollWidth: s.scrollWidth,
            overflow,
            navigationRecord: next && next.id,
            navigationHeading: catalogHeading && text(catalogHeading),
            navigationHref: catalogLink && catalogLink.getAttribute('href'),
            beforeNavigation: Boolean(next && next.matches('.r.t-rec') &&
                catalogHeading && visible(catalogHeading) && catalogLink && visible(catalogLink) &&
                next.getBoundingClientRect().top >= sr.bottom - 1 &&
                catalogHeading.getBoundingClientRect().top >= sr.bottom - 1 &&
                catalogLink.getBoundingClientRect().top >= sr.bottom - 1),
            documentWidth: document.documentElement.scrollWidth,
            viewport: innerWidth
        };
    }""")


def check_card(page, product, width, base, local_failures):
    response = page.goto(base + "/" + product["page"].lstrip("/"),
                         wait_until="domcontentloaded", timeout=45000)
    require(response is not None and response.ok, "Could not open " + product["page"])
    section = page.locator(SELECTOR)
    require(section.count() == 1, f"Expected one designer block, found {section.count()}")
    require(section.is_visible(), "Designer block is hidden")
    require(section.locator('.ev-designer-card__materials').count() == 1,
            "Expected one materials palette")
    require(section.locator('.ev-designer-card__interior').count() == 1,
            "Expected one interior figure")
    require(section.locator('img').count() == 5, "Expected four swatches and one interior image")
    # Force the block's lazy images to load even when it is below the fold.
    section.locator('img').evaluate_all("els => els.forEach(el => { el.loading = 'eager'; })")
    section.locator('img').last.scroll_into_view_if_needed(timeout=20000)
    page.wait_for_function("""selector => [...document.querySelectorAll(selector + ' img')]
        .every(el => el.complete)""", arg=SELECTOR, timeout=20000)
    page.evaluate("""async () => {
        await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 3000))]);
    }""")
    # Tilda's desktop entrance fade starts after DOMContentLoaded. is_visible()
    # alone accepts opacity:0, so wait for the actual page content to appear.
    page.wait_for_function("""selector => {
        for (let el = document.querySelector(selector); el; el = el.parentElement) {
            const style = getComputedStyle(el);
            if (Number(style.opacity) < 0.99 || style.visibility === 'hidden' ||
                style.display === 'none') return false;
        }
        return true;
    }""", arg=SELECTOR, timeout=15000)
    section.locator('img').evaluate_all("els => Promise.all(els.map(el => el.decode()))")
    details = inspect_card(page)
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    materials = product['materials']
    expected_images = [m['image']['src'] for m in materials] + [product['interior']['src']]
    check(details['sku'] == product['sku'], "Wrong floor SKU")
    check(details['sectionCount'] == details['stylesheetCount'] == 1,
          "Designer block or stylesheet is duplicated/missing")
    check(details['title'] == 'Дизайнерская карта', "Wrong section title")
    check(details['floor'] == product['name'] + ' ' + product['sku'], "Wrong floor name")
    check(details['swatchCount'] == 4 and details['interiorImageCount'] == 1,
          "Expected four swatches and one interior image")
    check(details['names'] == [m['name'] for m in materials], "Wrong material names or order")
    check(details['codes'] == [m['code'] for m in materials], "Wrong material codes or order")
    check([img['src'] for img in details['images']] == expected_images,
          "Image paths do not match the product manifest")
    check(all(img['local'] and img['loaded'] for img in details['images']),
          "An image is external or did not load")
    check(not local_failures, "A designer-card resource failed to load")
    check(details['columns'] == (4 if width == 1440 else 2), "Wrong number of palette columns")
    check(details['interiorBelow'], "Interior image is not below the palette")
    check(details['withinViewport'], "Designer block extends beyond the viewport")
    check(details['ownScrollWidth'] <= details['ownWidth'] + 1 and not details['overflow'],
          "Content overflows the designer block")
    check(details['beforeNavigation'], "Designer block is not before the catalog navigation")
    return details, errors


def screenshot_card(page, path, timeout=30000):
    """Capture the whole card at its tested width, clear of fixed page overlays."""
    section = page.locator(SELECTOR)
    height = math.ceil(section.bounding_box()['height'])
    # Functional checks use the original viewport. Only the capture is taller,
    # allowing all card pixels to paint and leaving room for the header/cookies.
    page.set_viewport_size({'width': page.viewport_size['width'], 'height': height + 320})
    section.evaluate("""el => {
        document.documentElement.style.scrollBehavior = 'auto';
        document.body.style.scrollBehavior = 'auto';
        window.scrollTo({top: el.getBoundingClientRect().top + scrollY - 100, behavior: 'instant'});
    }""")
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    section.screenshot(path=str(path), animations='disabled', timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=ROOT / '_deploy')
    parser.add_argument('--output', type=Path, default=ROOT / 'buyer-qa/designer-cards')
    args = parser.parse_args()
    site_dir = args.site_dir.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    summary = {'checks': [], 'screenshots': [], 'fatal_error': None,
               'site_dir': str(site_dir), 'expected_checks': PRODUCT_COUNT * len(DEVICES)}
    server = None
    server_thread = None

    def save():
        summary['passed'] = sum(row['status'] == 'passed' for row in summary['checks'])
        summary['failed'] = sum(row['status'] == 'failed' for row in summary['checks'])
        summary['ok'] = (summary['passed'] == summary['expected_checks'] and
                         summary['failed'] == 0 and summary['fatal_error'] is None)
        summary['duration_seconds'] = round(time.monotonic() - started, 2)
        (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                                             encoding='utf-8')

    try:
        require(site_dir.is_dir(), f"Staged site does not exist: {site_dir}")
        products = json.loads((ROOT / 'content/designer-cards.json').read_text(encoding='utf-8'))['products']
        require(len(products) == PRODUCT_COUNT, f"Expected {PRODUCT_COUNT} designer products, found {len(products)}")
        require(len({p['sku'] for p in products}) == PRODUCT_COUNT, "Duplicate product SKUs in manifest")
        require(len({p['page'] for p in products}) == PRODUCT_COUNT, "Duplicate product pages in manifest")
        for product in products:
            require(len(product['materials']) == 4, f"{product['sku']} needs exactly four materials")
            page_path = (site_dir / product['page'].lstrip('/')).resolve()
            require(page_path.is_relative_to(site_dir) and page_path.is_file(),
                    f"Missing staged product page: {product['page']}")
        summary['products'] = [p['sku'] for p in products]
        server = ThreadingHTTPServer(('127.0.0.1', 0),
            functools.partial(QuietHandler, directory=str(site_dir)))
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for width, height in DEVICES:
                    context = browser.new_context(viewport={'width': width, 'height': height},
                        device_scale_factor=1, reduced_motion='reduce', locale='ru-RU')
                    context.set_default_timeout(15000)
                    try:
                        for product in products:
                            page = context.new_page()
                            row = {'sku': product['sku'], 'width': width, 'status': 'failed'}
                            local_failures = []

                            def relevant(url):
                                return url.startswith(base + '/') and urlsplit(url).path.startswith('/assets/designer-card')

                            page.on('requestfailed', lambda request: local_failures.append(
                                {'url': request.url, 'error': request.failure}) if relevant(request.url) else None)
                            page.on('response', lambda response: local_failures.append(
                                {'url': response.url, 'status': response.status})
                                if relevant(response.url) and response.status >= 400 else None)
                            try:
                                row['details'], errors = check_card(page, product, width, base, local_failures)
                                require(not errors, '; '.join(errors))
                                screenshot = f"{product['sku']}-{width}.png"
                                screenshot_card(page, output / screenshot)
                                row.update(status='passed', screenshot=screenshot)
                                summary['screenshots'].append(screenshot)
                            except Exception as error:
                                row.update(error=str(error), traceback=traceback.format_exc(limit=5))
                                screenshot = f"{product['sku']}-{width}-failure.png"
                                try:
                                    if page.locator(SELECTOR).count() == 1 and page.locator(SELECTOR).is_visible():
                                        screenshot_card(page, output / screenshot, timeout=15000)
                                    else:
                                        page.screenshot(path=str(output / screenshot), animations='disabled', timeout=15000)
                                    row['screenshot'] = screenshot
                                    summary['screenshots'].append(screenshot)
                                except Exception as screenshot_error:
                                    row['screenshot_error'] = str(screenshot_error)
                            finally:
                                row['local_failures'] = local_failures
                                summary['checks'].append(row)
                                save()
                                print(json.dumps({'sku': row['sku'], 'width': width, 'status': row['status'],
                                    **({'error': row['error']} if 'error' in row else {})}, ensure_ascii=False), flush=True)
                                page.close()
                    finally:
                        context.close()
            finally:
                browser.close()
    except Exception as error:
        summary['fatal_error'] = {'message': str(error), 'traceback': traceback.format_exc(limit=8)}
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if server_thread is not None:
            server_thread.join(timeout=2)
        save()
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
