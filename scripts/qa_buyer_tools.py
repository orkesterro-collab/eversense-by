#!/usr/bin/env python3
"""Browser QA against staged _deploy; never contacts or changes the live store.

Run after installing Playwright, Chromium and pypdf:
    python scripts/qa_buyer_tools.py
Optional: --site-dir _deploy --output buyer-qa --port 8765
All results and screenshots are written before a nonzero exit on failure.
The Google Sheets JSONP response is deterministic; other external failures are
recorded as diagnostics, not treated as application failures.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import sys
import threading
import time
import traceback
from decimal import Decimal
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEVICES = [("desktop", 1440, 1000), ("mobile", 390, 844), ("mobile360", 360, 800)]
FAVORITES = "eversense.favorites.v1"
SCREENSHOT_PAGES = {"catalog-ru/index.html", "choose.html", "about.html", "calculator.html"}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def numeric(text):
    return Decimal(re.sub(r"[^\d,.-]", "", text).replace(",", "."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_deploy")
    parser.add_argument("--output", type=Path, default=ROOT / "buyer-qa")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    site_dir, output = args.site_dir.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary = {"site_dir": str(site_dir), "base_url": f"http://127.0.0.1:{args.port}",
               "price_source": "Mocked Google Sheets JSONP: 45.90 BYN/m² for each catalog SKU",
               "checks": [], "screenshots": [], "fatal_error": None}
    server = None
    started = time.monotonic()
    base = summary["base_url"]

    def save():
        summary["passed"] = sum(row["status"] == "passed" for row in summary["checks"])
        summary["failed"] = sum(row["status"] == "failed" for row in summary["checks"])
        if "canonical_product_mobile_cases" in summary:
            passed_cases = {row["name"] for row in summary["checks"] if row["status"] == "passed"}
            summary["canonical_product_mobile_passed"] = sum(
                name in passed_cases for name in summary["canonical_product_mobile_cases"].values())
        if "canonical_product_mobile360_cases" in summary:
            passed_cases = {row["name"] for row in summary["checks"] if row["status"] == "passed"}
            summary["canonical_product_mobile360_passed"] = sum(
                name in passed_cases for name in summary["canonical_product_mobile360_cases"].values())
        summary["duration_seconds"] = round(time.monotonic() - started, 2)
        summary["ok"] = not summary["fatal_error"] and not summary["failed"]
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        require(site_dir.is_dir(), f"Staged site does not exist: {site_dir}")
        products = json.loads((site_dir / "assets/products-data.json").read_text(encoding="utf-8"))
        require(len(products) == 30, "Expected 30 staged catalog products")
        by_sku = {p["sku"]: p for p in products}
        require(len(by_sku) == 30, "Catalog contains duplicate SKU")
        require(by_sku["EL1052"]["packArea"] == 1.99, "Classic fixture must match the actual catalog")
        require(by_sku["EL1000"]["packArea"] == 2.54, "Large fixture must match the actual catalog")
        pages = sorted(str(p.relative_to(site_dir)) for p in site_dir.rglob("*.html")
                       if re.search(r'data-buyer-static\s*=\s*[\"\']true[\"\']', p.read_text(encoding="utf-8", errors="replace")))
        require(len(pages) >= 15, f"Expected all new buyer pages, found {len(pages)}")
        summary["new_pages"] = pages
        payload = {"status": "ok", "table": {"rows": [
            {"c": [{"v": p["sku"]}, {"v": 45.90}, {"v": None}, {"v": None}, {"v": None}, {"v": 100}]}
            for p in products]}}
        jsonp = "window.EversensePriceFeed(" + json.dumps(payload, ensure_ascii=False) + ");"
        server = ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(QuietHandler, directory=str(site_dir)))
        threading.Thread(target=server.serve_forever, daemon=True).start()

        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

            def new_context(width=1440, height=1000, feed="ok", storage_blocked=False):
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1,
                                              locale="ru-RU", timezone_id="Europe/Minsk", reduced_motion="reduce",
                                              ignore_https_errors=True)
                context.set_default_timeout(10000)
                context.set_default_navigation_timeout(30000)
                context.add_init_script("""
                    Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{
                      writeText: async text => { window.__qaCopied = text; }
                    }});
                """)
                if storage_blocked == "mixed-quota":
                    context.add_init_script("""
                        const originalSetItem = Storage.prototype.setItem;
                        Storage.prototype.setItem = function(key, value) {
                          const previous = this.getItem(key) || '';
                          if (key === 'eversense.favorites.v1' && value.length > 10 && value.length > previous.length)
                            throw new DOMException('Growing favorites exceed QA quota', 'QuotaExceededError');
                          return originalSetItem.call(this, key, value);
                        };
                    """)
                elif storage_blocked == "quota":
                    context.add_init_script("""
                        window.__qaStorageSetItem = Storage.prototype.setItem;
                        Storage.prototype.setItem = function() {
                          throw new DOMException('Storage write blocked by QA fixture', 'QuotaExceededError');
                        };
                    """)
                elif storage_blocked:
                    context.add_init_script("""
                        Object.defineProperty(window, 'localStorage', {configurable:true, get() {
                          throw new DOMException('Storage blocked by QA fixture', 'SecurityError');
                        }});
                    """)
                def feed_route(route):
                    if feed == "blocked":
                        route.abort("failed")
                    else:
                        route.fulfill(status=200, content_type="application/javascript; charset=utf-8",
                                      body=jsonp, headers={"Cache-Control": "no-store"})
                context.route("https://docs.google.com/spreadsheets/**/gviz/**", feed_route)
                return context

            def attach_logs(page):
                logs = {"page_errors": [], "local_failures": [], "external_failures": [], "cancelled_requests": []}
                def on_error(error):
                    logs["page_errors"].append({"message": str(error), "stack": getattr(error, "stack", "") or ""})
                def failed(request):
                    if request.failure and "ERR_ABORTED" in request.failure:
                        logs["cancelled_requests"].append({"url": request.url, "failure": request.failure})
                        return
                    key = "local_failures" if request.url.startswith(base + "/") else "external_failures"
                    if not request.url.endswith("/favicon.ico"):
                        logs[key].append({"url": request.url, "failure": request.failure})
                def response_error(response):
                    if response.url.startswith(base + "/") and response.status >= 400 and not response.url.endswith("/favicon.ico"):
                        logs["local_failures"].append({"url": response.url, "status": response.status})
                page.on("pageerror", on_error)
                page.on("requestfailed", failed)
                page.on("response", response_error)
                return logs

            def goto(page, path, prices=True, wait_fonts=True):
                response = page.goto(base + "/" + path.lstrip("/"), wait_until="domcontentloaded")
                require(response is not None and response.ok, f"Page returned non-success status: {path}")
                page.wait_for_selector("#ev-global-header", state="attached")
                page.wait_for_function("window.EversenseBuyerCore && window.__eversenseBuyerStarted")
                if prices:
                    page.wait_for_function("window.EversensePrices && window.EversensePrices.isLoaded()")
                if wait_fonts:
                    page.evaluate("async () => { await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,2500))]); }")

            def shot(page, name, full=True):
                path = output / (re.sub(r"[^a-zA-Z0-9_.-]", "-", name) + ".png")
                scroll = page.evaluate("({x:scrollX,y:scrollY})") if full else None
                if full:
                    page.evaluate("""async () => {
                      window.scrollTo({left:0,top:0,behavior:'instant'});
                      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                    }""")
                try:
                    page.screenshot(path=str(path), full_page=full, animations="disabled", timeout=30000)
                finally:
                    if scroll is not None:
                        page.evaluate("""async point => {
                          window.scrollTo({left:point.x,top:point.y,behavior:'instant'});
                          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                        }""", scroll)
                summary["screenshots"].append(path.name)
                return path.name

            def images(page, selector="img", minimum=1, local_only=False):
                page.locator(selector).evaluate_all("els => els.forEach(x => {x.loading='eager';})")
                page.wait_for_function("""args => [...document.querySelectorAll(args.selector)]
                  .filter(x => (x.currentSrc||x.src) && (!args.localOnly || (x.currentSrc||x.src).startsWith(args.origin)))
                  .every(x=>x.complete)""", arg={"selector": selector, "localOnly": local_only, "origin": base + "/"}, timeout=20000)
                result = page.locator(selector).evaluate_all("els => els.filter(x=>x.currentSrc||x.src).map(x=>({src:x.currentSrc||x.src,width:x.naturalWidth,height:x.naturalHeight,complete:x.complete}))")
                local = [image for image in result if image["src"].startswith(base + "/")]
                broken = [image for image in local if not image["complete"] or image["width"] < minimum]
                require(not broken, f"Broken local images: {broken[:6]}")
                return {"total": len(result), "local": len(local), "loaded_local": len(local) - len(broken)}

            def layout_metrics(page, check_style=True):
                metrics = page.evaluate("""() => {
                  const visible=e=>!!(e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
                  const controls=[...document.querySelectorAll('main button,main input,main select,#ev-global-header button')].filter(visible);
                  const headings=[...document.querySelectorAll('h1')].filter(e=>visible(e)&&(e.innerText||'').trim());
                  const heading=headings[0];
                  return {
                    viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,
                    title:document.title,h1:heading?.innerText||'',visibleH1Count:headings.length,
                    font:getComputedStyle(document.body).fontFamily,headingFont:heading?getComputedStyle(heading).fontFamily:null,fontStatus:document.fonts.status,
                    loadedFonts:[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family),
                    controls:controls.map(e=>{
                      // A native checkbox's associated wrapping label is its real touch target.
                      const label=e.matches('input[type="checkbox"],input[type="radio"]')?e.closest('label'):null;
                      const rect=(label||e).getBoundingClientRect();
                      return {tag:e.tagName,text:e.getAttribute('aria-label')||e.innerText||e.name||'',
                        height:rect.height,width:rect.width,font:getComputedStyle(e).fontFamily,
                        fontSize:parseFloat(getComputedStyle(e).fontSize),disabled:e.disabled||false};
                    }),
                    h1Width:heading?.getBoundingClientRect().width||0,
                    headerCount:document.querySelectorAll('#ev-global-header').length
                  };
                }""")
                require(metrics["headerCount"] == 1, "Expected exactly one unified header")
                require(metrics["documentWidth"] <= metrics["viewport"] + 1,
                        f"Document overflows: {metrics['documentWidth']} > {metrics['viewport']}")
                require(metrics["bodyWidth"] <= metrics["viewport"] + 1,
                        f"Body overflows: {metrics['bodyWidth']} > {metrics['viewport']}")
                require(bool(metrics["h1"].strip()), "Page is missing its primary heading")
                if check_style:
                    require("Manrope" in metrics["font"], f"Buyer page font CSS not applied: {metrics['font']}")
                    bad = [c for c in metrics["controls"] if c["height"] < 40 or c["width"] < 20 or c["fontSize"] < 10 or "Times" in c["font"]]
                    require(not bad, f"Unusable or unstyled controls: {bad[:6]}")
                return metrics

            def case(name, callback, width=1440, height=1000, feed="ok", storage_blocked=False):
                context = new_context(width, height, feed, storage_blocked)
                page = context.new_page()
                logs = attach_logs(page)
                row = {"name": name, "status": "passed"}
                begun = time.monotonic()
                try:
                    row["details"] = callback(page, context) or {}
                    local_js = [e for e in logs["page_errors"] if re.search(r"/(?:assets/)?(?:buyer(?:-core)?|prices|unified-header)\.js", e["stack"])]
                    require(not local_js, f"Buyer JavaScript errors: {local_js[:3]}")
                    require(not logs["local_failures"], f"Local assets failed: {logs['local_failures'][:6]}")
                except Exception as error:
                    row.update(status="failed", error=str(error), traceback=traceback.format_exc(limit=4))
                    try:
                        row["failure_screenshot"] = shot(page, "FAIL-" + name, full=False)
                    except Exception as screenshot_error:
                        row["screenshot_error"] = str(screenshot_error)
                finally:
                    row["diagnostics"] = {key: value[:30] for key, value in logs.items()}
                    row["duration_seconds"] = round(time.monotonic() - begun, 2)
                    summary["checks"].append(row)
                    context.close()
                    save()
                    print(f"{row['status']}: {name}", file=sys.stderr, flush=True)

            def catalog_test(page, context):
                goto(page, "catalog-ru/?sort=price-up")
                cards = page.locator("#ev-catalog-results .ev-card:visible")
                reset = page.locator("#ev-catalog-filters [data-reset-filters]")
                search = page.locator('#ev-catalog-filters [name="q"]')
                require(cards.count() == 30, f"Catalog count is {cards.count()}")
                fields = page.locator('#ev-catalog-filters [name]').evaluate_all("els=>els.map(el=>el.name)")
                require(fields == ["q", "tone", "design"], "Collection choices should only appear above the filters")
                require("sort" not in parse_qs(urlparse(page.url).query), "Old price sort is still applied")
                require(not reset.is_visible(), "Reset is visible without filters")
                require(set(cards.evaluate_all("xs=>xs.map(x=>x.dataset.product)")) == set(by_sku), "Catalog SKU differs from data")
                loaded = images(page, "#ev-catalog-results .ev-card-image img:first-child", minimum=16)
                require(loaded["local"] == 30, "Expected 30 real local product images")
                search.fill("EL1052")
                require(cards.count() == 1 and cards.first.get_attribute("data-product") == "EL1052", "SKU filter returned wrong product")
                require(reset.is_visible() and reset.inner_text() == "Сбросить фильтры", "Active filters need a visible reset link")
                search.fill("неизвестный артикул")
                require(cards.count() == 0 and page.locator("#ev-catalog-empty").is_visible(), "Empty result is unclear")
                reset.click()
                require(search.evaluate("el=>el===document.activeElement"), "Reset lost keyboard focus")
                page.locator('#ev-catalog-filters [name="design"]').select_option("stone")
                require(cards.count() == 2, f"Stone filter should show 2, got {cards.count()}")
                require(set(cards.evaluate_all("xs=>xs.map(x=>x.dataset.product)")) == {"EL1000", "EL1002"}, "Wrong stone SKU")
                reset.click()
                require(cards.count() == 30 and not reset.is_visible(), "Reset does not restore catalog")
                page.goto(base + "/catalog-ru/?collection=nature&q=EL2151", wait_until="commit")
                page.wait_for_url("**/catalog-ru/nature-aesthetic-ru/?q=EL2151", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelectorAll('#ev-catalog-results .ev-card:not([hidden])').length === 1")
                require(cards.first.get_attribute("data-product") == "EL2151", "Old collection links must preserve search")
                return {"cards": 30, "images": loaded, "stone": 2, "sku_search": "EL1052"}
            case("catalog-filter-real-images", catalog_test)

            def favorite_test(page, context):
                goto(page, "catalog-ru/")
                personal = ["EL1052", "EL1000", "EL153", "EL750"]
                for sku in personal:
                    page.locator(f'[data-ev-favorite="{sku}"]').click()
                require(json.loads(page.evaluate("key=>localStorage.getItem(key)", FAVORITES)) == personal, "Favorites did not store 4 products")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__eversenseBuyerStarted")
                for sku in personal:
                    require(page.locator(f'[data-ev-favorite="{sku}"]').get_attribute("aria-pressed") == "true", "Favorite did not survive reload")
                goto(page, "favorites.html")
                require(page.locator("#ev-favorites .ev-card").count() == 4, "Favorites page lost selections")
                page.locator("[data-share-selection]").click()
                page.wait_for_function("window.__qaCopied || document.querySelector('#ev-copy-fallback input')")
                shared = page.evaluate("window.__qaCopied || document.querySelector('#ev-copy-fallback input').value")
                require(parse_qs(urlparse(shared).query).get("items", [""])[0].split(",") == personal, "Shared URL lost selection")
                goto(page, "favorites.html?items=EL1036,EL1000,EL1036,UNKNOWN,%3Cscript%3E")
                require(page.locator("#ev-favorites .ev-card").count() == 2, "Shared URL was not sanitized")
                require(json.loads(page.evaluate("key=>localStorage.getItem(key)", FAVORITES)) == personal, "Viewing shared list overwrote personal favorites")
                require(page.locator("#ev-shared-note").is_visible(), "Shared selection not explained")
                page.locator("[data-save-shared]").click()
                saved = json.loads(page.evaluate("key=>localStorage.getItem(key)", FAVORITES))
                require(set(saved) == set(personal + ["EL1036"]) and len(saved) == 5, "Shared list did not merge uniquely")
                goto(page, "favorites.html")
                require(page.locator("#ev-favorites .ev-card").count() == 5, "Merged favorites missing after navigation")
                return {"personal": personal, "shared_sanitized": 2, "merged": 5, "copied_url": shared}
            case("favorites-reload-share-merge", favorite_test)

            def bad_storage_test(page, context):
                goto(page, "catalog-ru/")
                page.evaluate("key=>localStorage.setItem(key,'{bad JSON')", FAVORITES)
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__eversenseBuyerStarted")
                require(page.locator("#ev-catalog-results .ev-card").count() == 30, "Corrupt storage broke catalog")
                page.locator('[data-ev-favorite="EL1052"]').click()
                require(json.loads(page.evaluate("key=>localStorage.getItem(key)", FAVORITES)) == ["EL1052"], "Storage did not recover")
                return {"corrupt_json_recovered": True}
            case("storage-corruption", bad_storage_test)

            def blocked_storage_test(page, context, quota=False):
                goto(page, "catalog-ru/")
                if quota:
                    require(page.evaluate("()=>{try{localStorage.getItem('probe');}catch(e){return false;}try{localStorage.setItem('probe','1');return false;}catch(e){return e.name==='QuotaExceededError';}}"),
                            "Readable-but-unwritable storage fixture did not take effect")
                    page.evaluate("key=>{window.__qaStorageSetItem.call(localStorage,key,JSON.stringify(['EL750']));const u=new URL(location.href);u.searchParams.delete('ev-favorites');history.replaceState(null,'',u);}", FAVORITES)
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_selector('[data-ev-favorite="EL750"]')
                    page.locator('[data-ev-favorite="EL750"]').click()
                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_selector('[data-ev-favorite="EL750"]')
                    require(page.locator('[data-ev-favorite="EL750"]').get_attribute('aria-pressed') == 'false',
                            "Empty favorites fallback resurrected stale readable storage")
                else:
                    require(page.evaluate("()=>{try{void localStorage;return false;}catch(e){return e.name==='SecurityError';}}"),
                            "Blocked-storage fixture did not take effect")
                selected = ["EL1052", "EL1000"]
                for sku in selected:
                    page.locator(f'[data-ev-favorite="{sku}"]').click()
                page.evaluate("window.scrollTo(0,0)")
                favorite_link = page.locator('#ev-global-header [data-favorites-link]')
                favorite_url = favorite_link.get_attribute("href")
                require(parse_qs(urlparse(favorite_url).query).get("ev-favorites", [""])[0].split(",") == selected,
                        "Favorites link did not carry blocked-storage selections")
                favorite_link.click()
                page.wait_for_selector("#ev-favorites .ev-card")
                require(page.locator("#ev-favorites .ev-card").count() == 2,
                        "Favorites were lost after blocked-storage navigation")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector("#ev-favorites .ev-card")
                require(page.locator("#ev-favorites .ev-card").count() == 2,
                        "Blocked-storage favorites did not survive reload")
                return {"storage_blocked": True, "selected": selected, "favorites_url": favorite_url}
            case("storage-blocked-url-navigation", blocked_storage_test, storage_blocked=True)
            case("storage-quota-url-navigation", lambda p,c: blocked_storage_test(p,c,quota=True), storage_blocked="quota")

            def favorites_only_test(page, context, device):
                goto(page, "catalog-ru/")
                require(page.locator('[data-ev-compare],[data-compare-link],a[href*="compare.html"]').count() == 0,
                        "Comparison is still exposed in the catalog")
                require(page.locator('.ev-hero [data-favorites-link],.ev-hero .ev-eyebrow').count() == 0, "Catalog hero must be uncluttered")
                require(page.locator('#ev-catalog-results a[href*="calculator.html"]').count() == 0, "Catalog cards still link to calculation")
                require(page.locator('#ev-catalog-filters details,#ev-catalog-filters [name="sort"]').count() == 0, "Catalog still has a filter panel or sort control")
                hearts = page.locator('#ev-catalog-results [data-ev-favorite]')
                require(hearts.count() == 30, "Catalog must keep all 30 favorite buttons")
                require(hearts.first.locator('svg').evaluate("el=>getComputedStyle(el).fill") == 'none', "Empty card heart should be outlined")
                sizes = page.locator('#ev-catalog-results .ev-card-size').all_text_contents()
                expected_sizes = [f"{p['lengthMM']} × {p['widthMM']} × {p['thicknessMM']} мм" for p in products]
                require(sorted(sizes) == sorted(expected_sizes), "Catalog dimensions differ from product data")
                first_card = page.locator('#ev-catalog-results .ev-card').first
                heart_box = hearts.first.bounding_box()
                card_box = first_card.bounding_box()
                size_box = first_card.locator('.ev-card-size').bounding_box()
                price_box = first_card.locator('.ev-price-box').bounding_box()
                require(heart_box and card_box and size_box and price_box, "Missing catalog card details")
                require(heart_box['width'] >= 44 and heart_box['height'] >= 44, "Card heart touch target is too small")
                require(abs(heart_box['x'] + heart_box['width'] - card_box['x'] - card_box['width']) < 1
                        and heart_box['y'] + heart_box['height'] <= price_box['y'] + 1
                        and heart_box['y'] <= size_box['y'] < heart_box['y'] + heart_box['height'],
                        "Card heart should sit at the right edge beside the size and above the price")
                require(abs(price_box['x'] - card_box['x']) < 1, "Price should align with the card's left edge")
                hearts.first.click()
                require(hearts.first.get_attribute('aria-pressed') == 'true'
                        and hearts.first.locator('svg').evaluate("el=>getComputedStyle(el).fill") == 'rgb(240, 82, 82)',
                        "Adding favorite must fill the card heart")
                if device != 'desktop':
                    nav = page.locator('.ev-inline-nav')
                    require(nav.evaluate("el=>el.scrollWidth<=el.clientWidth+1"), "Collection choices must fit without horizontal scrolling")
                    require(nav.locator('a').count() == 4, "All collection choices must stay available")
                    for choice in nav.locator('a').all():
                        bounds = choice.bounding_box()
                        require(bounds and bounds['x'] >= 0 and bounds['x']+bounds['width'] <= page.viewport_size['width'], "Collection choice extends beyond phone")
                        require(choice.evaluate("el=>el.scrollWidth<=el.clientWidth+1"), "Collection name is clipped")
                header_favorite = page.locator('#ev-global-header [data-favorites-link]')
                badge = header_favorite.locator('[data-favorites-count]')
                require(header_favorite.count() == 1, "Header favorites shortcut missing")
                require(header_favorite.get_attribute('aria-label') == 'Избранное - 1 шт.', "Header accessible count is wrong")
                label_visible = header_favorite.locator('[data-favorites-summary]').is_visible()
                require(label_visible == (device == 'desktop'), "Header label should be desktop-only")
                require(badge.is_visible() == (device != 'desktop') and badge.text_content() == '1', "Phone header favorites count is missing")
                require(header_favorite.locator('svg').evaluate("el=>getComputedStyle(el).fill") == 'rgb(240, 82, 82)', "Nonempty header heart must be red")
                box = header_favorite.bounding_box()
                require(box and box['width'] >= 44 and box['height'] >= 44, "Header favorites touch target is too small")
                hearts.nth(1).click()
                require(header_favorite.get_attribute('aria-label') == 'Избранное - 2 шт.', "Header count must update to two")
                require(badge.text_content() == '2', "Phone header count must update to two")
                hearts.nth(1).click()
                hearts.first.click()
                require(header_favorite.get_attribute('aria-label') == 'Избранное - пока пусто', "Empty header label is wrong")
                require(not badge.is_visible(), "Empty badge should be hidden")
                require(header_favorite.locator('svg').evaluate("el=>getComputedStyle(el).fill") == 'none', "Empty header heart must be outlined")
                hearts.first.click()
                columns = page.locator('#ev-catalog-results').evaluate("el=>getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length")
                require(columns == (3 if device == "desktop" else 2), f"Wrong catalog columns: {columns}")

                goto(page, "catalog-ru/nature-aesthetic-ru/")
                tone = page.locator("#ev-tone").bounding_box()
                design = page.locator("#ev-design").bounding_box()
                require(tone and design and tone['y'] == design['y'] and tone['x'] < design['x'], "Catalog filters should sit side by side")
                cards = page.locator('#ev-catalog-results .ev-card')
                require(cards.count() == 10 and all('Природная эстетика' not in text
                        for text in cards.locator('.ev-card-meta').all_text_contents()), "Collection name should only appear in the page heading")
                sale_sku = cards.first.get_attribute('data-product')
                prices = {"status": "ok", "table": {"rows": [
                    {"c": [{"v": p["sku"]}, {"v": 65.66}, {"v": 50.96 if p["sku"] == sale_sku else None}, {"v": "2099-11-29"}]}
                    for p in products]}}
                page.evaluate("data=>window.EversensePriceFeed(data)", prices)
                sale = cards.first.locator('.ev-price-sale')
                normal = cards.nth(1).locator('.ev-price-normal')
                require(sale.evaluate("el=>getComputedStyle(el).color") == 'rgb(180, 58, 54)', "Sale price is not red")
                require(all(price.evaluate("el=>Number(getComputedStyle(el).fontWeight)") >= 700 for price in (sale, normal)), "Current prices must be bold")
                require(abs(sale.bounding_box()['y'] - normal.bounding_box()['y']) < 1, "Sale and regular prices should align")
                previous = cards.first.locator('.ev-price-box del')
                until = cards.first.locator('.ev-price-box small')
                require(sale.bounding_box()['y'] < previous.bounding_box()['y'] < until.bounding_box()['y'], "Sale details should sit below the current price")

                goto(page, "favorites.html")
                saved_card = page.locator('#ev-favorites [data-product="EL1036"]')
                saved_heart = saved_card.locator('button.ev-card-favorite[aria-pressed="true"]')
                require(saved_card.locator('button').count() == 1 and saved_heart.locator('svg').count() == 1,
                        "A saved card must have one active heart")
                require(saved_card.locator('.ev-card-actions, a[href*="calculator.html"]').count() == 0,
                        "Favorites still contain an action row")
                require(saved_card.locator('.ev-card-meta span').all_text_contents() ==
                        ['Природная эстетика', '1292 × 193 × 8 мм'], "Favorites details differ from the catalog")
                page.evaluate("data=>window.EversensePriceFeed(data)", prices)
                require(saved_card.locator('.ev-price-sale').evaluate("el=>getComputedStyle(el).color") ==
                        'rgb(180, 58, 54)', "Favorites discount price differs from the catalog")
                grid = page.locator('#ev-favorites .ev-grid')
                require(grid.count() == 1, "Favorites must use the same product grid as the catalog")
                fav_geometry = grid.evaluate("""el=>{
                    const image=el.querySelector('.ev-card-image'),box=image.getBoundingClientRect();
                    return {columns:getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length,
                            aspect:box.width/box.height,
                            rotation:getComputedStyle(image.querySelector('img:not(.ev-card-interior)')).transform}
                }""")
                require(fav_geometry["columns"] == (3 if device == "desktop" else 2),
                        f"Favorites grid differs from catalog: {fav_geometry}")
                require(abs(fav_geometry["aspect"] - 2/3) < .02,
                        f"Favorites sample is not upright: {fav_geometry}")
                require(fav_geometry["rotation"] != "none",
                        "Favorites material photo did not rotate vertically")
                require(page.locator('[data-ev-compare],[data-compare-link],a[href*="compare.html"]').count() == 0,
                        "Comparison is still exposed on favorites page")
                return {"comparison_removed": True, "columns": columns}
            for device, width, height in DEVICES:
                case("favorites-only-" + device, lambda p,c,d=device: favorites_only_test(p,c,d), width, height)

            def favorites_keyboard_test(page, context):
                goto(page, "catalog-ru/")
                for sku in ["EL1000", "EL1052"]:
                    page.locator(f'[data-ev-favorite="{sku}"]').click()
                goto(page, "favorites.html")
                page.locator('#ev-favorites [data-ev-favorite="EL1000"]').focus()
                page.keyboard.press("Enter")
                require(page.locator('#ev-favorites [data-ev-favorite="EL1052"]').evaluate("el=>el===document.activeElement"),
                        "Removing favorite lost keyboard focus")
                page.keyboard.press("Enter")
                require(page.locator('#ev-favorites a').evaluate("el=>el===document.activeElement"),
                        "Removing last favorite did not focus catalog link")
                return {"next_card_focus": True, "empty_catalog_link_focus": True}
            for device, width, height in DEVICES:
                case("favorites-keyboard-removal-" + device, favorites_keyboard_test, width, height)

            def favorites_print_test(page, context):
                # Long names and sale details exercise the taller printed cards.
                ordered = sorted(products, key=lambda p: -len(p["name"]))
                sale_feed = {"status": "ok", "table": {"rows": [
                    {"c": [{"v": p["sku"]}, {"v": 65.66}, {"v": 50.96}, {"v": "2099-11-29"}]}
                    for p in ordered]}}
                results = {}
                for count in (4, 9, len(ordered)):
                    selected = [p["sku"] for p in ordered[:count]]
                    goto(page, "favorites.html?items=" + ",".join(selected))
                    page.evaluate("data=>window.EversensePriceFeed(data)", sale_feed)
                    pdf = PdfReader(BytesIO(page.pdf(format="A4", prefer_css_page_size=True)))
                    batches = [selected[i:i + 4] for i in range(0, count, 4)]
                    require(len(pdf.pages) == len(batches), f"{count} favorites printed on {len(pdf.pages)} sheets")
                    for n, (sheet, batch) in enumerate(zip(pdf.pages, batches), 1):
                        content = "".join(sheet.extract_text().split())
                        printed = re.findall(r"EL[0-9]+", content)
                        require(sorted(printed) == sorted(batch), f"Sheet {n}: expected {batch}, found {printed}")
                        require(content.count("29.11.2099") == len(batch), f"Sale details missing on sheet {n}")
                    results[count] = [len(batch) for batch in batches]
                return results
            case("favorites-print-four-per-a4", favorites_print_test)

            def calc_values(page):
                return page.locator("#ev-calc-result").evaluate("el=>({packs:parseInt(el.querySelector('h2').innerText,10),values:Object.fromEntries([...el.querySelectorAll('dl > div')].map(d=>[d.querySelector('dt').innerText,d.querySelector('dd').innerText]))})")

            def calculate(page, sku, area, reserve):
                page.locator('#ev-calc-form [name="sku"]').select_option(sku)
                page.locator('#ev-calc-form [name="area"]').fill(area)
                page.locator('#ev-calc-form [name="reserve"]').fill(reserve)
                page.locator('#ev-calc-form button[type="submit"]').click()
                page.wait_for_selector("#ev-calc-result dl")
                return calc_values(page)

            def calculator_test(page, context, device):
                goto(page, "calculator.html")
                classic = calculate(page, "EL1052", "20", "10")
                require(classic["packs"] == 12, f"Classic pack count: {classic}")
                require(numeric(classic["values"]["В целых упаковках"]) == Decimal("23.88"), "Classic area wrong")
                require(numeric(classic["values"]["Стоимость материала"]) == Decimal("1096.09"), "Classic monetary total wrong")
                shot(page, "calculator-result-" + device)
                layout_metrics(page)
                large = calculate(page, "EL1000", "20", "10")
                require(large["packs"] == 9 and numeric(large["values"]["В целых упаковках"]) == Decimal("22.86"), "Large SKU reused Classic pack area")
                require(numeric(large["values"]["Стоимость материала"]) == Decimal("1049.27"), "Large total wrong")
                edge = calculate(page, "EL1052", "1,81", "10")
                require(edge["packs"] == 2, "Comma input or early area rounding lost a package")
                require(numeric(edge["values"]["С выбранным запасом"]) == Decimal("1.991"), "Reserve area rounded early")
                require(numeric(edge["values"]["Стоимость материала"]) == Decimal("182.68"), "Comma case price wrong")
                page.locator("[data-share-calculation]").click()
                page.wait_for_function("window.__qaCopied")
                copied = page.evaluate("window.__qaCopied")
                goto(page, urlparse(copied).path + "?" + urlparse(copied).query)
                require(calc_values(page)["packs"] == 2, "Shared calculator URL cannot restore comma input")
                for field, value in [("area", "0"), ("area", "-1"), ("area", "NaN"), ("reserve", "21")]:
                    page.locator('#ev-calc-form [name="area"]').fill("20")
                    page.locator('#ev-calc-form [name="reserve"]').fill("10")
                    page.locator(f'#ev-calc-form [name="{field}"]').fill(value)
                    page.locator('#ev-calc-form button[type="submit"]').click()
                    require(page.locator("#ev-calc-result [role='alert']").is_visible(), f"Invalid {field}={value} accepted")
                return {"classic": classic, "large": large, "comma_edge": edge, "invalid_inputs_rejected": 4}
            for device, width, height in DEVICES[:2]:
                case("calculator-" + device, lambda p, c, d=device: calculator_test(p, c, d), width, height)

            def no_price_test(page, context):
                goto(page, "calculator.html", prices=False)
                values = calculate(page, "EL1052", "20", "10")
                require(values["packs"] == 12, "Missing feed broke quantity calculation")
                require("Уточнить" in values["values"]["Стоимость материала"], "Missing price became a numeric or fake total")
                return values
            case("calculator-without-price-feed", no_price_test, feed="blocked")

            def late_price_update_test(page, context):
                feed_requests = []
                page.on("request", lambda request: feed_requests.append(request.url)
                        if "docs.google.com/spreadsheets/" in request.url and "/gviz/" in request.url else None)
                changed_payload = {"status": "ok", "table": {"rows": [
                    {"c": [{"v": p["sku"]}, {"v": 60}, {"v": None}, {"v": None}, {"v": None}]}
                    for p in products]}}
                goto(page, "catalog-ru/")
                price_box = page.locator('[data-buyer-price="EL1052"]')
                require("45,90" in price_box.inner_text(), "Initial mocked card price missing")
                requests_before = len(feed_requests)
                page.evaluate("data=>window.EversensePriceFeed(data)", changed_payload)
                page.wait_for_function("document.querySelector('[data-buyer-price=\"EL1052\"]').innerText.includes('60,00')")
                require(len(feed_requests) == requests_before, "Price update unexpectedly issued a feed request")
                require(page.locator("#ev-catalog-results [data-buyer-price]").evaluate_all(
                    "els=>els.length===30&&els.every(el=>el.innerText.includes('60,00'))"),
                    "Not all catalog cards responded to the late price event")
                goto(page, "calculator.html")
                before = calculate(page, "EL1052", "20", "10")
                require(numeric(before["values"]["Стоимость материала"]) == Decimal("1096.09"),
                        "Initial calculation does not use mocked starting price")
                requests_before = len(feed_requests)
                page.evaluate("data=>window.EversensePriceFeed(data)", changed_payload)
                page.wait_for_function("()=>document.querySelector('#ev-calc-result').innerText.replace(/\\s/g,'').includes('1432,80')")
                after = calc_values(page)
                require(after["packs"] == 12 and numeric(after["values"]["В целых упаковках"]) == Decimal("23.88"),
                        "Price-only update altered package quantities")
                require(numeric(after["values"]["Стоимость материала"]) == Decimal("1432.80"),
                        "Calculated total did not react to the new price")
                require(len(feed_requests) == requests_before, "Calculation refresh unexpectedly requested the feed")
                return {"updated_card_count": 30, "new_unit_price": 60, "before": before, "after": after,
                        "update_requested_network": False}
            case("late-price-event-updates-cards-and-calculation", late_price_update_test)

            def stock_feed_update_test(page, context):
                goto(page, by_sku["EL1052"]["canonicalPath"])
                for value in [250, None, 125]:
                    changed = json.loads(json.dumps(payload))
                    for row in changed["table"]["rows"]:
                        if row["c"][0]["v"] == "EL1052":
                            row["c"][5]["v"] = value
                    page.evaluate("data=>window.EversensePriceFeed(data)", changed)
                    stock = page.locator("#ev-product-tools p.ev-stock-plan")
                    if value is None:
                        require(stock.count() == 0, "Empty stock cell must hide planned stock")
                    else:
                        require(stock.count() == 1 and f"более {value} м²" in stock.inner_text(),
                                "Product stock did not update from its SKU row")
                    require("45,90" in page.locator("#ev-product-price .ev-price-box").inner_text(),
                            "Stock-only update changed product price")
                return {"stock_changes": [250, None, 125], "price_preserved": True}
            case("planned-stock-refresh-and-empty-cell", stock_feed_update_test, 390, 844)


            def storage_tabs_test(page, context):
                goto(page, "catalog-ru/")
                page.locator('[data-ev-favorite="EL1052"]').click()
                goto(page, "favorites.html")
                other = context.new_page()
                try:
                    goto(other, "catalog-ru/")
                    other.locator('[data-ev-favorite="EL1000"]').click()
                    page.wait_for_function("document.querySelectorAll('#ev-favorites .ev-card').length===2")
                    other.evaluate("localStorage.clear()")
                    page.wait_for_function("document.querySelectorAll('#ev-favorites .ev-card').length===0")
                finally:
                    other.close()
                return {"cross_tab_add": True, "cross_tab_clear": True}
            case("favorites-cross-tab-storage", storage_tabs_test)

            def finder_test(page, context):
                goto(page, "choose.html")
                page.locator('#ev-finder [name="design"]').select_option("stone")
                page.locator('#ev-finder [name="room"]').select_option("kitchen")
                page.locator('#ev-finder button[type="submit"]').click()
                require(page.locator("#ev-finder-results").is_visible(), "Finder results remain hidden")
                require(page.locator("#ev-finder-results .ev-card").count() == 2, "Finder returned wrong stone designs")
                require("кухни" in page.locator("#ev-finder-results").inner_text(), "Room-specific explanation missing")
                return {"matched": 2, "room_explanation": "kitchen"}
            case("finder-design-and-room", finder_test, 390, 844)

            def faq_expanded_test(page, context):
                goto(page, "faq.html")
                questions = page.locator("main details")
                require(questions.count() >= 2, "FAQ questions are missing")
                first = questions.first
                first.locator("summary").click()
                require(first.evaluate("el=>el.open"), "First FAQ item did not expand")
                require(first.locator("p").first.is_visible() and len(first.locator("p").first.inner_text().strip()) > 30,
                        "First FAQ answer is not visible")
                long_answer = questions.filter(has=page.locator("summary", has_text="тёплый пол")).first
                require(long_answer.count() == 1, "Expected long installation / underfloor-heating FAQ")
                long_answer.locator("summary").click()
                require(long_answer.evaluate("el=>el.open"), "Long installation FAQ did not expand")
                require(long_answer.locator("p").first.is_visible() and len(long_answer.locator("p").first.inner_text().strip()) > 180,
                        "Long installation answer is truncated or not visible")
                targets = []
                for answer in [first, long_answer]:
                    link = answer.locator("a[href]").first
                    require(link.count() == 1 and link.is_visible(), "Expanded FAQ is missing its useful next-step link")
                    target = link.get_attribute("href")
                    absolute = link.evaluate("el=>el.href")
                    require(absolute.startswith(base + "/"), f"FAQ points outside the staged site: {absolute}")
                    response = context.request.get(absolute, timeout=10000)
                    require(response.ok, f"Expanded FAQ link is broken: {target} ({response.status})")
                    targets.append(urlparse(absolute).path)
                metrics = layout_metrics(page)
                shot(page, "faq-expanded-mobile")
                return {"first_expanded": True, "long_answer_expanded": True, "valid_links": targets, "layout": metrics}
            case("faq-expanded-mobile", faq_expanded_test, 390, 844)

            def header_test(page, context, device):
                goto(page, "about.html")
                if device != "desktop":
                    page.evaluate("scrollTo({top:320, behavior:'instant'})")
                    page.wait_for_function("document.querySelector('#ev-global-header').getBoundingClientRect().bottom <= 0")
                    page.evaluate("""async () => {
                      for (let i = 0; i < 8; i++) {
                        scrollBy({top:-1, behavior:'instant'});
                        await new Promise(requestAnimationFrame);
                      }
                    }""")
                    page.wait_for_function("document.querySelector('#ev-global-header').getBoundingClientRect().top >= -1")
                toggle = page.locator(".ev-header-toggle")
                toggle.focus()
                page.keyboard.press("Enter")
                menu = page.locator("#ev-global-menu")
                require(menu.is_visible() and toggle.get_attribute("aria-expanded") == "true", "Keyboard did not open menu")
                paths = {urlparse(href).path for href in menu.locator("a").evaluate_all("els=>els.map(a=>a.href)")}
                expected = {"/catalog-ru/", "/choose.html", "/favorites.html", "/about.html", "/downloads.html", "/where-to-buy.html"}
                require(expected <= paths and "/compare.html" not in paths and "/calculator.html" not in paths, f"Header missing links or still has comparison: {expected-paths}")
                require(all(menu.locator("a").nth(i).is_visible() for i in range(menu.locator("a").count())), "Menu contains CSS-hidden navigation")
                shot(page, "menu-" + device, full=False)
                page.keyboard.press("Escape")
                require(not menu.is_visible() and toggle.get_attribute("aria-expanded") == "false", "Escape failed to close menu")
                require(toggle.evaluate("el=>el===document.activeElement"), "Escape did not restore toggle focus")
                stores = page.locator(".ev-header-inner").get_by_role("link", name="Где купить", exact=True)
                require(stores.count() == 1 and stores.is_visible(), "Store locator must be visible with the menu closed")
                require(stores.evaluate("a=>a.href") == base + "/where-to-buy.html", "Incorrect store locator destination")
                bounds = stores.bounding_box()
                require(bounds["width"] >= 44 and bounds["height"] >= 44, "Store locator tap target is too small")
                require(stores.locator("img").evaluate("async img => { await img.decode(); return img.naturalWidth === 24; }"),
                        "Storefront icon did not load")
                return {"links": len(paths), "keyboard_open_and_escape": True}
            for device, width, height in DEVICES:
                case("header-" + device, lambda p, c, d=device: header_test(p, c, d), width, height)

            def layout_test(page, context, path, device):
                suffix = ""
                if path == "favorites.html": suffix = "?items=EL1000,EL1052"
                if path == "calculator.html": suffix = "?sku=EL1052&area=20&reserve=10"
                goto(page, path + suffix)
                loaded = images(page)
                metrics = layout_metrics(page)
                if device == "mobile" or path in SCREENSHOT_PAGES:
                    shot(page, path.replace("/index.html", "").replace(".html", "") + "-" + device)
                return {"path": path, "device": device, "images": loaded, "layout": metrics}
            for device, width, height in DEVICES:
                for path in pages:
                    case("layout-" + device + "-" + path.replace("/", "-"),
                         lambda p, c, path=path, d=device: layout_test(p, c, path, d), width, height)

            def product_tools_metrics(page, product, check_hover=False):
                sku = product["sku"]
                page.wait_for_selector("#ev-product-tools", state="attached", timeout=20000)
                require(page.locator("#ev-product-tools").count() == 1, f"{sku}: product tools missing or duplicated")
                placement = page.evaluate("""() => {
                  const tools=document.getElementById('ev-product-tools'),previous=tools?.previousElementSibling;
                  const support=document.getElementById('ev-product-support'),footer=document.getElementById('t-footer');
                  return {
                    followsGallery:!!(previous?.matches('.t-rec')&&previous.querySelector('[role="img"]')),
                    previousId:previous?.id||null,supportCount:document.querySelectorAll('#ev-product-support').length,
                    footerCount:document.querySelectorAll('#t-footer').length,
                    supportBeforeFooter:!!(support&&footer&&(support.compareDocumentPosition(footer)&Node.DOCUMENT_POSITION_FOLLOWING))
                  };
                }""")
                require(placement["followsGallery"], f"{sku}: product tools are before the gallery or detached from it: {placement}")
                require(placement["supportCount"] == 1, f"{sku}: support section missing or duplicated")
                require(placement["footerCount"] == 1 and placement["supportBeforeFooter"],
                        f"{sku}: support content is after the Tilda footer: {placement}")
                viewport_width = page.viewport_size["width"]
                minimum_visible = viewport_width - 20 if viewport_width < 1000 else viewport_width * 0.9
                try:
                    geometry_handle = page.wait_for_function("""args=>{
                      const gallery=document.getElementById('ev-product-tools')?.previousElementSibling;
                      const artboard=gallery?.querySelector('.t396__artboard.rendered');
                      if(!artboard)return false;
                      const candidates=[...gallery.querySelectorAll('[role="img"]')].map(el=>{
                        const r=el.getBoundingClientRect();
                        return {left:r.left,right:r.right,width:r.width,height:r.height,
                          visibleWidth:Math.max(0,Math.min(innerWidth,r.right)-Math.max(0,r.left))};
                      }).filter(r=>r.height>0).sort((a,b)=>b.visibleWidth-a.visibleWidth);
                      const best=candidates[0];
                      if(!best||best.visibleWidth<args.minimum||Math.abs(best.left)>20){
                        window.__qaGalleryGeometry=null;
                        return false;
                      }
                      const signature=[best.left,best.width,best.right].map(n=>Math.round(n*10)).join(',');
                      const previous=window.__qaGalleryGeometry;
                      const stable=previous?.signature===signature?previous.stable+1:1;
                      window.__qaGalleryGeometry={signature,stable};
                      return stable>=3?{...best,viewport:innerWidth,stableFrames:stable,artboardRendered:true}:false;
                    }""", arg={"minimum": minimum_visible}, polling="raf", timeout=5000)
                    gallery_geometry = geometry_handle.json_value()
                    geometry_handle.dispose()
                except Exception as error:
                    diagnostics = page.evaluate("""()=>{
                      const gallery=document.getElementById('ev-product-tools')?.previousElementSibling;
                      const rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right};};
                      const info=el=>{
                        const css=getComputedStyle(el);
                        return {tag:el.tagName,id:el.id,className:el.className,rect:rect(el),style:el.getAttribute('style'),
                          computed:{width:css.width,minWidth:css.minWidth,maxWidth:css.maxWidth,height:css.height,
                            zoom:css.zoom,left:css.left,top:css.top,position:css.position,transform:css.transform,
                            display:css.display,overflow:css.overflow,boxSizing:css.boxSizing}};
                      };
                      return {viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},gallery:gallery?info(gallery):null,
                        artboards:[...(gallery?.querySelectorAll('.t396__artboard')||[])].map(el=>({
                          ...info(el),attributes:Object.fromEntries([...el.attributes].map(a=>[a.name,a.value]))})),
                        images:[...(gallery?.querySelectorAll('[role="img"]')||[])].map(el=>{
                          const chain=[];let parent=el;
                          for(let depth=0;parent&&depth<7;depth++,parent=parent.parentElement)chain.push(info(parent));
                          return {ancestors:chain};
                        })};
                    }""")
                    raise AssertionError(f"{sku}: gallery never reached stable full visible width >= {minimum_visible:.1f}px within 5s; "
                                         + json.dumps(diagnostics, ensure_ascii=False)) from error
                # Original Tilda body can legitimately retain its browser default.
                # Verify the visible product heading rather than inferring its font from body.
                heading_handle = page.wait_for_function("""()=>{
                  const h=[...document.querySelectorAll('h1')].find(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&(e.innerText||'').trim());
                  const font=h?getComputedStyle(h).fontFamily:'';
                  return font.includes('Manrope')?font:false;
                }""", timeout=10000)
                heading_font = heading_handle.json_value()
                heading_handle.dispose()
                favorite = page.locator("#ev-product-tools [data-ev-favorite]")
                comparison = page.locator("#ev-product-tools [data-ev-compare]")
                require(favorite.count() == 1 and favorite.get_attribute("data-ev-favorite") == sku,
                        f"{sku}: favorite tools mounted with wrong SKU")
                require(comparison.count() == 0, f"{sku}: comparison button remains on product page")
                calc_link = page.locator('#ev-product-tools a[href*="calculator.html"]')
                require(calc_link.count() == 1 and parse_qs(urlparse(calc_link.get_attribute("href")).query).get("sku") == [sku],
                        f"{sku}: product calculator lost SKU")
                heading = page.locator('.ev-product-heading h1')
                require(heading.count() == 1 and heading.inner_text().strip() == product['name'],
                        f"{sku}: heading must include the complete product name")
                heading_geometry = heading.evaluate("""el=>{
                  const range=document.createRange();range.selectNodeContents(el);
                  const text=range.getBoundingClientRect(),box=el.getBoundingClientRect();
                  const css=getComputedStyle(el),parent=el.closest('.ev-product-heading');
                  const sku=parent.querySelector('.ev-product-sku').getBoundingClientRect();
                  const crumbs=parent.previousElementSibling.getBoundingClientRect();
                  return {textWidth:text.width,width:box.width,height:box.height,lineHeight:parseFloat(css.lineHeight),
                    gap:sku.top-crumbs.bottom,left:box.left,right:box.right,viewport:innerWidth};
                }""")
                require(heading_geometry['textWidth'] <= heading_geometry['width'] + 1 and
                        heading_geometry['height'] <= heading_geometry['lineHeight'] + 1 and
                        heading_geometry['right'] <= heading_geometry['viewport'] + 1,
                        f"{sku}: heading wraps or overflows: {heading_geometry}")
                require(16 <= heading_geometry['gap'] <= 28,
                        f"{sku}: incorrect breadcrumb gap: {heading_geometry}")
                price_panel = page.locator("#ev-product-price")
                require(page.locator("#ev-product-tools #ev-product-price").count() == 1,
                        f"{sku}: price must be in the purchase block below the gallery")
                require(page.evaluate("""() => {
                  const price=document.getElementById('ev-product-price');
                  const actions=document.querySelector('#ev-product-tools .ev-actions');
                  return !!(price.compareDocumentPosition(actions)&Node.DOCUMENT_POSITION_FOLLOWING) &&
                    price.getBoundingClientRect().bottom <= actions.getBoundingClientRect().top + 1;
                }"""), f"{sku}: price must precede the purchase actions")
                require(price_panel.count() == 1 and price_panel.get_attribute("data-ev-sku") == sku,
                        f"{sku}: price panel points to a different product")
                page.wait_for_selector("#ev-product-price .ev-price-box strong")
                price = price_panel.locator(".ev-price-box strong").inner_text()
                require("45,90" in price and "BYN" in price, f"{sku}: mocked product price missing: {price}")
                page.evaluate("()=>{EversensePrices.render();EversensePrices.render();}")
                stock = price_panel.locator("p.ev-stock-plan")
                require(stock.count() == 1 and stock.inner_text() == "На складе в Минске планово поддерживается более 100 м².",
                        f"{sku}: planned stock from feed missing or duplicated")
                require(page.locator('#ev-product-tools a[href*="contacts.html"]').count() == 0,
                        f"{sku}: availability button still present")
                require(page.locator("#ev-product-tools").count() == 1, f"{sku}: price rerender duplicated product tools")
                styles = None
                if sku == "EL1052":
                    styles = page.locator("#ev-product-tools").evaluate("""el=>({
                      background:getComputedStyle(el).backgroundColor,
                      anchors:[...el.querySelectorAll('a')].map(a=>({text:a.innerText,color:getComputedStyle(a).color,background:getComputedStyle(a).backgroundColor}))
                    })""")
                    allowed_backgrounds = {"rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"}
                    require(styles["background"] in allowed_backgrounds, f"Product tools panel is not white: {styles}")
                    require(all(a["color"] == "rgb(52, 51, 51)" and a["background"] in allowed_backgrounds for a in styles["anchors"]),
                            f"Tilda styles override product tools link palette: {styles['anchors']}")
                    if check_hover:
                        primary = page.locator("#ev-product-tools a.ev-button--primary")
                        try:
                            primary.hover()
                            page.wait_for_function("""()=>{
                              const css=getComputedStyle(document.querySelector('#ev-product-tools a.ev-button--primary'));
                              return css.color==='rgb(255, 255, 255)'&&css.backgroundColor==='rgb(52, 51, 51)';
                            }""")
                            styles["primary_hover"] = primary.evaluate("el=>({color:getComputedStyle(el).color,background:getComputedStyle(el).backgroundColor})")
                        finally:
                            page.mouse.move(0, 0)
                return {"sku": sku, "tools_count": 1, "price": price, "calculator_link_has_sku": True,
                        "placement": placement, "gallery_geometry": gallery_geometry, "headingFont": heading_font, "styles": styles}

            def mirrored_test(page, context, path, device, product=False):
                goto(page, path)
                tools = None
                if product:
                    tools = product_tools_metrics(page, by_sku["EL1052"], check_hover=device == "desktop")
                    page.locator('#ev-product-tools [data-ev-favorite="EL1052"]').click()
                    require("EL1052" in page.evaluate("key=>localStorage.getItem(key)", FAVORITES), "Mirrored product favorite is broken")
                loaded = images(page)
                page.evaluate("window.scrollTo(0,0)")
                shot(page, ("existing-product" if product else "existing-home") + "-" + device, full=False)
                if product and device == "mobile":
                    page.mouse.move(0, 0)
                    for selector, label in [("#ev-product-tools", "tools"), ("#ev-product-support", "support")]:
                        page.locator(selector).evaluate("""async el=>{
                          const top=el.getBoundingClientRect().top+scrollY;
                          const header=document.getElementById('ev-global-header')?.getBoundingClientRect().height||0;
                          window.scrollTo({left:0,top:Math.max(0,top-header-12),behavior:'instant'});
                          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                        }""")
                        shot(page, "existing-product-" + label + "-mobile", full=False)
                    page.evaluate("window.scrollTo({left:0,top:0,behavior:'instant'})")
                return {"images": loaded, "layout": layout_metrics(page, check_style=False), "dynamic_product_tools": product, "product_tools": tools}
            for device, width, height in DEVICES[:2]:
                case("existing-home-" + device, lambda p, c, d=device: mirrored_test(p, c, "index.html", d), width, height)
                case("existing-product-" + device,
                     lambda p, c, d=device: mirrored_test(p, c, by_sku["EL1052"]["canonicalPath"], d, True), width, height)

            def collection_panels(page, path, device):
                cookie_ok = page.get_by_text('OK', exact=True)
                if cookie_ok.count() and cookie_ok.first.is_visible():
                    cookie_ok.first.click()
                records = (['1040271756', '1040271761', '1040271766'] if path.startswith('en/')
                           else ['1002600156', '1002600161', '1002600166'])
                result = []
                for record in records:
                    panel = page.locator('#rec' + record)
                    panel.scroll_into_view_if_needed()
                    photo = panel.locator('[data-elem-id="1742824688189"] .tn-atom')
                    photo.scroll_into_view_if_needed()
                    page.wait_for_timeout(300)
                    metrics = panel.evaluate("""panel=>{
                      const r=panel.getBoundingClientRect();
                      const within=el=>{const b=el.getBoundingClientRect();return b.width>0 && b.height>0 &&
                        b.top>=r.top-2 && b.bottom<=r.bottom+2 &&
                        b.left>=r.left-2 && b.right<=r.right+2;};
                      const photo=panel.querySelector('[data-elem-id="1742824688189"] .tn-atom');
                      const texts=[...panel.querySelectorAll('[data-elem-type="text"]')];
                      const buttons=[...panel.querySelectorAll('[data-elem-type="button"] a')]
                        .filter(el=>Number(getComputedStyle(el).opacity)>0 && within(el));
                      const p=photo.getBoundingClientRect();
                      const hit=document.elementFromPoint(p.x+p.width/2,p.y+p.height/2);
                      return {photoInside:within(photo),photoVisible:getComputedStyle(photo).opacity==='1',
                        photoLoaded:photo.classList.contains('loaded') && getComputedStyle(photo).backgroundImage!=='none',
                        photoUncovered:hit===photo || photo.contains(hit),
                        textInside:texts.every(within),buttons:buttons.map(a=>a.getAttribute('href'))};
                    }""")
                    require(metrics['photoInside'] and metrics['photoVisible'] and metrics['photoLoaded']
                            and metrics['photoUncovered'], f"Collection photo missing or clipped: {record}: {metrics}")
                    require(metrics['textInside'], f"Collection copy lies outside its panel: {record}")
                    require(len(metrics['buttons']) == 1 and '/catalog-' in metrics['buttons'][0],
                            f"Collection must have one visible catalog button: {record}: {metrics}")
                    button = panel.locator('[data-elem-type="button"] a').filter(visible=True)
                    # Tilda keeps a transparent alternate button off-canvas.
                    for candidate in button.all():
                        if candidate.evaluate("el=>getComputedStyle(el).opacity==='1'"):
                            candidate.scroll_into_view_if_needed()
                            if page.viewport_size['width'] < 960 and not path.startswith('en/'):
                                box, cover = candidate.bounding_box(), panel.bounding_box()
                                require(20 <= box['x'] - cover['x'] <= 28 and box['width'] <= 220 and box['height'] >= 44,
                                        f"Expected a compact left-aligned catalog button: {record}: {box}")
                            require(candidate.evaluate("""el=>{const r=el.getBoundingClientRect();
                              const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                              return hit===el || el.contains(hit);}"""), f"Catalog button is covered: {record}")
                    shot(page, 'collection-' + record + '-' + device, full=False)
                    result.append(metrics)
                return result

            def static_home_test(page, context, path, device):
                page.emulate_media(reduced_motion="no-preference")
                goto(page, path, prices=False)
                page.wait_for_function("document.documentElement.classList.contains('ev-home-static')")
                require(page.locator('[data-animate-sbs-event="scroll"], [data-animate-sbs-event="intoview"], [data-animate-style]').count() == 0,
                        "Home still contains scroll/reveal animation triggers")
                layer = '#rec1040271736' if path.startswith('en/') else '#rec1002600136'
                page.locator(layer).scroll_into_view_if_needed()
                page.wait_for_timeout(400)
                heading = page.locator(layer + ' .ev-m-layers h2:visible, ' + layer + ' [data-elem-id="1742894294619"]:visible')
                before = heading.evaluate("""el=>({
                  y:el.getBoundingClientRect().top+scrollY,opacity:getComputedStyle(el).opacity,
                  transform:getComputedStyle(el).transform})""")
                page.mouse.wheel(0, 240)
                page.wait_for_timeout(400)
                after = heading.evaluate("""el=>({
                  y:el.getBoundingClientRect().top+scrollY,opacity:getComputedStyle(el).opacity,
                  transform:getComputedStyle(el).transform})""")
                require(abs(after['y'] - before['y']) < 2 and after['opacity'] == '1'
                        and after['transform'] == before['transform'],
                        f"Layer heading moves or fades during scrolling: {before} -> {after}")
                if device == 'mobile' and not path.startswith('en/'):
                    assembly = page.locator(layer + ' .ev-m-assembly')
                    require(assembly.locator(':scope > img').count() == 4 and
                            assembly.evaluate("""el => Math.abs(el.getBoundingClientRect().right - innerWidth) < 1 &&
                              [...el.querySelectorAll('img')].every(img => img.naturalWidth > 0 &&
                                img.getBoundingClientRect().right > innerWidth)"""),
                            "The four original materials should extend past the right edge")
                    detail = page.locator('.ev-m-eco details').first
                    detail.locator('summary').click()
                    require(detail.locator('p').is_visible(), "The production detail did not open")
                    detail.locator('summary').click()
                    require(not detail.locator('p').is_visible(), "The production detail did not close")
                    download = page.get_by_role('link', name='Скачать текстуры', exact=True)
                    require('EVERSENSE.zip' in download.get_attribute('href') and
                            download.evaluate("el=>getComputedStyle(el).color !== getComputedStyle(el).backgroundColor"),
                            "The texture download should have a visible label and link to the archive")
                    require(page.locator('#ev-history-banner + #ev-home-footer').count() == 1,
                            "The production article should immediately precede the footer")
                overlap = page.locator(layer + ' [data-elem-type="text"]').evaluate_all("""els=>{
                  const boxes=els.map(el=>({r:el.getBoundingClientRect(),text:el.innerText})).filter(x=>x.r.width&&x.r.height);
                  return boxes.flatMap((a,i)=>boxes.slice(i+1).filter(b=>
                    Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>2 &&
                    Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>2
                  ).map(b=>[a.text,b.text]));
                }""")
                require(not overlap, f"Static layer descriptions overlap: {overlap}")
                if device == 'desktop':
                    original_viewport = dict(page.viewport_size)
                    try:
                        for width in (1440, 2048):
                            page.set_viewport_size({"width": width, "height": 1000})
                            page.wait_for_timeout(500)
                            spacing = page.locator(layer).evaluate("""el=>{
                              // Russian homes intentionally omit the old final slogan.
                              // In that case check the gap after the rendered artboard.
                              const summaryElement=el.querySelector('[data-elem-id="1742894294656"]') ||
                                el.querySelector('.t396__artboard');
                              if(!summaryElement) return null;
                              const summary=summaryElement.getBoundingClientRect();
                              let next=el.nextElementSibling;
                              while(next&&!next.classList.contains('uc-full1')) next=next.nextElementSibling;
                              return next?{gap:next.getBoundingClientRect().top-summary.bottom,
                                overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth}:null;
                            }""")
                            require(spacing and 0 <= spacing['gap'] <= 120 and not spacing['overflow'],
                                    f"Excessive or overlapping space after layers at {width}px: {spacing}")
                    finally:
                        page.set_viewport_size(original_viewport)
                        page.wait_for_timeout(500)
                header = page.locator('#ev-global-header')
                if device == 'desktop':
                    require(abs(header.bounding_box()['y']) <= 1, "Desktop home navigation moved")
                else:
                    require(header.evaluate('el=>el.getBoundingClientRect().bottom <= 0'),
                            "Mobile home navigation did not slide offscreen")
                    page.mouse.wheel(0, -10)
                    page.wait_for_function("document.querySelector('#ev-global-header').getBoundingClientRect().top >= -1")
                fixed = page.locator('#allrecords .tn-atom, #allrecords .t396__carrier').evaluate_all(
                    "els=>els.filter(el=>getComputedStyle(el).backgroundAttachment==='fixed').length")
                require(fixed == 0, "Fixed/parallax backgrounds remain on home")
                require(page.locator('#allrecords .t396__carrier').evaluate_all(
                    "els=>els.every(el=>getComputedStyle(el).position!=='fixed')"),
                    "Fixed background carriers remain on home")
                page.locator(layer).scroll_into_view_if_needed()
                shot(page, 'static-home-' + path.replace('/', '-') + '-' + device, full=False)
                panels = collection_panels(page, path, device)
                footer = page.locator('#ev-home-footer')
                require(footer.count() == 1, "Expected one compact homepage footer")
                require(page.locator('.ev-belarus-legal, #ev-belarus-contact-title, #rec1128306611, #rec1128311571').count() == 0,
                        "Duplicated homepage footer content remains")
                footer.scroll_into_view_if_needed()
                footer_layout = footer.evaluate("""el=>({height:el.getBoundingClientRect().height,
                  overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth,
                  links:[...el.querySelectorAll('a')].map(a=>({width:a.getBoundingClientRect().width,text:a.innerText}))})""")
                require(footer_layout['height'] < 500 and not footer_layout['overflow'],
                        f"Footer is too large or overflows: {footer_layout}")
                shot(page, 'footer-' + path.replace('/', '-') + '-' + device, full=False)
                return {"path": path, "scroll_effects": 0, "overlapping_descriptions": 0, "collections": panels}

            for device, width, height in DEVICES[:2]:
                for home_path in ('index.html', 'ru/index.html', 'en/index.html'):
                    case('static-home-' + home_path.replace('/', '-') + '-' + device,
                         lambda p, c, path=home_path, d=device: static_home_test(p, c, path, d), width, height)

            def compact_benefits_test(page, context, width, path='index.html'):
                goto(page, path, prices=False)
                root = page.locator('#rec445068037nlm')
                root.wait_for(state='visible')
                root.scroll_into_view_if_needed()
                result = []
                articles = [
                    ('102a0149d479-_1-min.webp', 'about.html#surface'),
                    ('9319855e8cff-_2-min.webp', 'warranty.html'),
                    ('8bdd7b9eaba5-_3-min.webp', 'water-resistance.html'),
                    ('ea69fbde8dca-_4-min.webp', 'laminate-classes.html#abrasion'),
                    ('e52e5803e60a-_5-min.webp', 'laminate-classes.html#impact-resistance'),
                ]
                for index, (original, article) in enumerate(articles, 1):
                    active = root.locator('.t-slds__item_active:not([aria-hidden="true"])')
                    active.locator(f'.ev-benefit-controls a[href="#bullet{index}"]').click()
                    page.wait_for_function("""index => document.querySelector(
                      '#rec445068037nlm .t-slds__items-wrapper').getAttribute('data-slider-pos') === String(index)""", arg=index)
                    page.wait_for_timeout(450)
                    link = active.locator('.ev-benefit-photo a')
                    link.locator('img').evaluate('img => img.decode()')
                    metrics = active.evaluate("""el => {
                      const root=el.closest('#rec445068037nlm'), r=root.getBoundingClientRect();
                      const controls=el.querySelector('.ev-benefit-controls'), n=controls.getBoundingClientRect();
                      const photo=el.querySelector('.ev-benefit-photo').getBoundingClientRect();
                      const caption=el.querySelector('.ev-benefit-copy'), copy=caption.getBoundingClientRect();
                      const w=document.documentElement.clientWidth, mobile=w<960;
                      const link=el.querySelector('.ev-benefit-photo a'), image=link.querySelector('img');
                      const imageBox=image.getBoundingClientRect();
                      const within=b=>b.top>=copy.top-2 && b.bottom<=Math.min(copy.bottom,n.top)+1 && b.left>=copy.left-2 && b.right<=copy.right+2;
                      let copyInside, overlap=[];
                      if (mobile) {
                        // Multiline inline links and titles can share a line. Measure the
                        // text on each line, including bold spans inside the original markup.
                        const walker=document.createTreeWalker(caption,NodeFilter.SHOW_TEXT);
                        const range=document.createRange(), lines=[];
                        while (walker.nextNode()) {
                          const node=walker.currentNode;
                          if (!node.textContent.trim() || !node.parentElement.checkVisibility({checkVisibilityCSS:true})) continue;
                          range.selectNodeContents(node);
                          lines.push(...Array.from(range.getClientRects()).filter(b=>b.width && b.height));
                        }
                        copyInside=lines.length>0 && lines.every(within);
                      } else {
                        const fields=[...caption.children].filter(e=>e.getClientRects().length && getComputedStyle(e).visibility!=='hidden');
                        const boxes=fields.map(e=>({text:e.innerText,r:e.getBoundingClientRect()}));
                        copyInside=boxes.every(b=>within(b.r));
                        overlap=boxes.flatMap((a,i)=>boxes.slice(i+1).filter(b=>
                          Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>2 &&
                          Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>2).map(b=>[a.text,b.text]));
                      }
                      const oldDesktopHeight=w>=1200?Math.max(innerHeight,550*w/1200):550*w/960;
                      const expected=mobile?innerHeight*.8:oldDesktopHeight*.75;
                      const hit=e=>{const b=e.getBoundingClientRect();
                        const target=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);
                        return target===e||e.contains(target);};
                      return {height:r.height,expected,
                        photoShare:mobile?photo.height/r.height:photo.width/r.width,centerError:Math.abs(n.x+n.width/2-r.x-r.width/2),
                        copyInside,overlap,
                        stacked:Math.abs(copy.top-r.top)<1 && Math.abs(photo.top-copy.bottom)<1 &&
                          Math.abs(photo.bottom-r.bottom)<1 && Math.abs(photo.width-r.width)<1,
                        filename:new URL(image.currentSrc).pathname.split('/').pop(), href:link.href,
                        linkedPhoto:image.naturalWidth>1 && hit(link) && image.alt.length>0 &&
                          Math.abs(imageBox.height-photo.height)<1 && Math.abs(imageBox.width-photo.width)<1,
                        navInside:n.top>=r.top&&n.bottom<=r.bottom+1,
                        arrows:[...el.querySelectorAll('.ev-benefit-prev,.ev-benefit-next')].map(e=>({
                          width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height,hit:hit(e)})),
                        overflow:document.documentElement.scrollWidth>w};
                    }""")
                    require(abs(metrics['height'] - metrics['expected']) < 3,
                            f"Benefits carousel height is incorrect at {width}: {metrics}")
                    require(metrics['filename'] == original and metrics['href'] == base + '/' + article and metrics['linkedPhoto'],
                            f"Wrong original or inactive article link on slide {index} at {width}: {metrics}")
                    if width < 960:
                        require(metrics['stacked'] and metrics['photoShare'] > .35,
                                f"Expected text above the mobile photograph on slide {index} at {width}: {metrics}")
                        if not path.startswith('en/'):
                            read_more = active.get_by_role('link', name=re.compile('^Узнать больше'))
                            require(read_more.get_attribute('href') == link.get_attribute('href')
                                    and read_more.bounding_box()['height'] >= 44,
                                    f"Missing mobile article button on slide {index}")
                    else:
                        require(abs(metrics['photoShare'] - .6) < .002,
                                f"Wrong desktop photo width on slide {index} at {width}: {metrics}")
                    require(metrics['copyInside'] and not metrics['overlap'],
                            f"Benefits copy clips or overlaps on slide {index} at {width}: {metrics}")
                    require(metrics['navInside'] and metrics['centerError'] < 2 and not metrics['overflow'],
                            f"Benefits controls are outside/beside the carousel at {width}: {metrics}")
                    require(all(a['width'] >= 44 and a['height'] >= 44 and a['hit'] for a in metrics['arrows']),
                            f"Benefits arrows cannot be clicked at {width}: {metrics}")
                    if index == 1:
                        shot(page, 'compact-benefits-' + path.replace('/', '-') + '-' + str(width), full=False)
                    if width == 390 and path == 'index.html':
                        with context.expect_page() as opened:
                            (read_more if index == 4 else link).click(modifiers=['Control'])
                        destination = opened.value
                        destination.wait_for_url(base + '/' + article, wait_until='domcontentloaded')
                        fragment = article.partition('#')[2]
                        require(destination.locator('#' + fragment if fragment else 'h1').first.is_visible(),
                                f'Missing article content for slide {index}: {article}')
                        destination.close()
                    result.append(metrics)
                active.locator('.ev-benefit-next').click()
                page.wait_for_function("document.querySelector('#rec445068037nlm .t-slds__items-wrapper').getAttribute('data-slider-pos') === '1'")
                page.wait_for_timeout(450)
                active.locator('.ev-benefit-prev').click()
                page.wait_for_function("document.querySelector('#rec445068037nlm .t-slds__items-wrapper').getAttribute('data-slider-pos') === '5'")
                return result

            for width, height in ((320, 568), (390, 844), (520, 800), (768, 1024), (1024, 1000), (1440, 1000), (2048, 1000)):
                case('compact-benefits-' + str(width),
                     lambda p, c, w=width: compact_benefits_test(p, c, w), width, height)
            for path in ('ru/index.html', 'en/index.html'):
                case('compact-benefits-' + path.split('/')[0] + '-320',
                     lambda p, c, path=path: compact_benefits_test(p, c, 320, path), 320, 1000)

            def collection_breakpoint_test(page, context, device):
                goto(page, 'index.html', prices=False)
                return collection_panels(page, 'index.html', device)

            for width in (320, 520, 768, 1024):
                case('collection-breakpoint-' + str(width),
                     lambda p, c, w=width: collection_breakpoint_test(p, c, str(w)), width, 900)

            def collection_interiors_test(page, context, device):
                mobile = device != 'desktop'
                if device == 'mobile':
                    page.emulate_media(reduced_motion='no-preference')
                goto(page, 'index.html' if mobile else 'ru/', prices=False)
                # The desktop page wrapper stays transparent briefly after DOMContentLoaded.
                page.wait_for_function("document.getElementById('allrecords').checkVisibility({checkOpacity: true})")
                cookie_ok = page.get_by_text('OK', exact=True)
                if cookie_ok.count() and cookie_ok.first.is_visible():
                    cookie_ok.first.click()
                galleries = page.locator('.ev-interiors')
                require(galleries.count() == 3, 'Expected three collection galleries')
                require(galleries.locator('img[src]').count() == 0, 'Interiors loaded before their collections approached the viewport')
                saved_sku = None
                cover_arrow_visible = """el => el.checkVisibility({checkOpacity:true, checkVisibilityCSS:true})
                    && el.getAnimations().length === 0"""
                for index, collection in enumerate(('nature', 'luxury', 'minimal')):
                    gallery = galleries.nth(index)
                    products_in_collection = [p for p in products if p['collectionID'] == collection]
                    slides = gallery.locator('.ev-interiors__slide')
                    require(set(slides.locator('figcaption').all_text_contents()) == {p['name'] for p in products_in_collection}
                            and slides.count() == len(products_in_collection), 'Interior captions do not match their collection')
                    require(all(slide.locator('.ev-interiors__next').count() == int(i < len(products_in_collection) - 1)
                                for i, slide in enumerate(slides.all())), 'Only the last interior should omit the next arrow')
                    require(gallery.locator('a').count() == 0, 'Interior captions should be plain text')
                    gallery.evaluate("el=>el.scrollIntoView({block:'center',behavior:'instant'})")
                    preview = gallery.locator('.ev-interiors__preview').element_handle()
                    page.wait_for_function('el=>el.complete&&el.naturalWidth>0', arg=preview)
                    require(slides.locator('img[src]').count() == 0, 'Full gallery images loaded before opening')
                    peek = gallery.evaluate("""el=>{
                      const box=el.getBoundingClientRect();
                      return (box.right-el.querySelector('.ev-interiors__sheet').getBoundingClientRect().left)/box.width;
                    }""")
                    require(abs(peek - .05) < .005, f'Incorrect closed gallery reveal: {peek}')
                    cta = gallery.locator('..').get_by_role('link', name='Перейти в коллекцию', exact=True)
                    require(cta.count() == 1, 'Expected one catalog link at each breakpoint')
                    expected_path = products_in_collection[0]['canonicalPath'].rsplit('/', 2)[0]
                    require(urlparse(cta.get_attribute('href')).path.rstrip('/') == expected_path,
                            f'Collection button should open {expected_path}')
                    cta_style = cta.evaluate("""el=>{
                      const css=getComputedStyle(el), reference=getComputedStyle(document.querySelector('.ev-m-textures a'));
                      const label=getComputedStyle(el.querySelector('.tn-atom__button-text'));
                      const properties=['backgroundColor','borderRadius','borderTopColor','borderTopWidth',
                        'paddingTop','paddingLeft','minHeight','fontFamily','fontSize','fontWeight','letterSpacing'];
                      const rect=el.getBoundingClientRect();
                      return {gap:el.closest('.ev-interiors-artboard').getBoundingClientRect().bottom-rect.bottom,
                        height:rect.height, background:css.backgroundColor, color:label.color,
                        differences:properties.filter(p=>css[p]!==reference[p]),
                        blur:getComputedStyle(el.parentElement).backdropFilter};
                    }""")
                    require(12 <= cta_style['gap'] <= 36 and cta_style['background'] == 'rgb(255, 255, 255)'
                            and cta_style['color'] == 'rgb(41, 38, 35)' and not cta_style['differences']
                            and abs(cta_style['height'] - 47) < 1
                            and cta_style['blur'] == 'none', f'Expected the light texture-download button style: {cta_style}')

                    hint = gallery.locator('.ev-interiors__hint').element_handle()
                    hint_box = hint.bounding_box()
                    require(hint.evaluate("el=>getComputedStyle(el).backgroundColor==='rgba(0, 0, 0, 0)'"), 'Opening arrow should not have a circle')
                    require(hint.evaluate(cover_arrow_visible), 'The collection cover should show a steady opening arrow')
                    opener = gallery.locator('.ev-interiors__opener')
                    opener.press('Enter')
                    track = gallery.locator('.ev-interiors__track')
                    require(track.evaluate('el=>el===document.activeElement'), 'Opening through the keyboard should focus the gallery')
                    sheet = gallery.locator('.ev-interiors__sheet').element_handle()
                    require(sheet.evaluate("el=>getComputedStyle(el).transitionDuration==='2s'"), 'Deliberate opening should take two seconds, including with reduced motion')
                    if index == 0:
                        page.wait_for_function("el=>{const x=el.getBoundingClientRect().left;return x > el.clientWidth*.1 && x < el.clientWidth*.8;}", arg=sheet)
                    page.wait_for_function("""el=>
                      Math.abs(el.getBoundingClientRect().left-el.parentElement.getBoundingClientRect().left)<1 &&
                      !el.getAnimations().some(animation=>animation.playState==='running')""", arg=sheet)
                    first = slides.first.locator('img').element_handle()
                    page.wait_for_function('el=>el.complete&&el.naturalWidth>0', arg=first)
                    require(('/collection-interiors/mobile/' in first.evaluate('el=>el.currentSrc')) == mobile,
                            'Gallery selected an incorrect image format for the viewport')
                    require(slides.locator('img[src]').count() == 2, 'Opening should load the first frame and its neighbor')
                    caption = slides.first.locator('figcaption')
                    require(caption.evaluate("el=>getComputedStyle(el).backgroundColor==='rgba(0, 0, 0, 0)'"),
                            'Interior name should appear directly on the photo')
                    if mobile:
                        require(caption.evaluate("el=>getComputedStyle(el).fontSize==='14px'"),
                                'Mobile interior names should be 14px')
                    else:
                        require(caption.evaluate("""el=>{
                          const heading=document.querySelector('#rec1002600151 h2.tn-atom');
                          const firstLine=node=>{
                            const range=document.createRange();
                            range.selectNodeContents(node);
                            return range.getClientRects()[0];
                          };
                          const title=firstLine(heading), name=firstLine(el);
                          const css=getComputedStyle(el), scale=parseFloat(css.getPropertyValue('--zoom')) || 1;
                          return Math.abs(title.left-name.left)<1.5 && Math.abs(parseFloat(css.fontSize)-(40*scale+2))<.1
                            && css.fontWeight===getComputedStyle(heading).fontWeight;
                        }"""), 'Desktop interior names should keep the heading alignment and gain 2px')
                        require(gallery.get_by_role('button', name='Предыдущий интерьер').count()==0,
                                'Desktop gallery should omit the upper back arrow')
                    close = gallery.locator('.ev-interiors__close')
                    close_box = close.bounding_box()
                    first_next = slides.first.locator('.ev-interiors__next')
                    next_box = first_next.bounding_box()
                    require(close_box and next_box and abs(close_box['x'] - next_box['x']) < 1,
                            'Close and next controls should share the same right inset')
                    next_center_y = next_box['y'] + next_box['height'] / 2
                    require(abs(next_center_y - hint_box['y'] - hint_box['height'] / 2) < 1,
                            'Next arrow should sit at the opening arrow height')
                    require(abs(next_center_y - close_box['y'] - close_box['height'] / 2 - 16 * 96 / 25.4) < 1,
                            'Close icon should sit 16 mm above the next arrow')
                    heart = slides.first.locator('[data-ev-favorite]').bounding_box()
                    require(heart and abs(heart['x'] + heart['width']/2 - next_box['x'] - next_box['width']/2) < 1
                            and abs(heart['y'] + heart['height']/2 - next_center_y - 16 * 96 / 25.4) < 1,
                            'Favorite should be the third control, directly below the next arrow')
                    if index == 0:
                        favorite = slides.first.locator('[data-ev-favorite]')
                        saved_sku = favorite.get_attribute('data-ev-favorite')
                        gallery.evaluate("el=>el.scrollIntoView({block:'center',behavior:'instant'})")
                        # A visible pointer tap does not programmatically scroll the snap gallery to the button.
                        page.wait_for_function("""el=>{const r=el.getBoundingClientRect();
                          return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}""",
                                               arg=favorite.element_handle())
                        heart_box = favorite.bounding_box()
                        page.mouse.click(heart_box['x'] + heart_box['width']/2, heart_box['y'] + heart_box['height']/2)
                        require(favorite.get_attribute('aria-pressed') == 'true' and favorite.locator('svg').count() == 1,
                                'Photo heart must save the decor and keep its icon')
                        require(gallery.evaluate('el=>Math.abs(el.getBoundingClientRect().left)<1'),
                                'Focusing the favorite must not pan the homepage sideways')

                    page.wait_for_function("""el=>{const r=el.getBoundingClientRect();
                      return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}""",
                                           arg=first_next.element_handle())
                    next_box = first_next.bounding_box()
                    started = time.monotonic()
                    page.mouse.click(next_box['x'] + next_box['width'] / 2, next_box['y'] + next_box['height'] / 2)
                    page.wait_for_function("""el=>el.scrollLeft>el.clientWidth*.1 &&
                      el.scrollLeft<el.clientWidth*.9""", arg=track.element_handle())
                    require(close.is_visible(), 'The close control should stay visible during the transition')
                    page.wait_for_function("""el=>Math.abs(el.scrollLeft-el.clientWidth)<1 &&
                      el.children[1].getAttribute('aria-hidden')==='false'""", arg=track.element_handle())
                    duration = time.monotonic() - started
                    require(1.8 <= duration <= 2.7, f'Arrow transition should take two seconds, took {duration:.2f}s')
                    require(slides.locator('img[src]').count() == 3, 'The next interior was not loaded on demand')
                    later_close_box = close.bounding_box()
                    require(later_close_box and abs(later_close_box['x'] - close_box['x']) < 1
                            and abs(later_close_box['y'] - close_box['y']) < 1,
                            'The close control should stay in place on later photos')
                    track.press('ArrowLeft')
                    page.wait_for_function("el=>el.scrollLeft<1 && el.children[0].getAttribute('aria-hidden')==='false'", arg=track.element_handle())
                    track.press('ArrowRight')
                    page.wait_for_function("""el=>Math.abs(el.scrollLeft-el.clientWidth)<1 &&
                      el.children[1].getAttribute('aria-hidden')==='false'""", arg=track.element_handle())

                    cta.scroll_into_view_if_needed()
                    require(cta.evaluate("""el=>{const r=el.getBoundingClientRect();
                      return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}"""),
                            'Opened interiors covered the catalog link')
                    require(cta.evaluate('el=>getComputedStyle(el).backgroundColor') == cta_style['background'],
                            'Catalog link gained a darker background over the photo')
                    close.press('Enter')
                    require(opener.get_attribute('aria-expanded') == 'false' and opener.evaluate('el=>el===document.activeElement'),
                            'Closing should return to the photo strip and restore focus')
                    page.wait_for_function("el=>getComputedStyle(el).visibility==='hidden'", arg=track.element_handle())
                    require(hint.evaluate(cover_arrow_visible), 'The opening arrow should be visible again after closing')
                goto(page, 'favorites.html')
                require(page.locator(f'#ev-favorites [data-product="{saved_sku}"]').count() == 1,
                        'The decor saved from the home gallery should appear in Favorites')
                return {'galleries': 3, 'captions': len(products), 'mobile_images': mobile}

            for device, width, height in DEVICES:
                case('collection-interiors-' + device, lambda p, c, d=device: collection_interiors_test(p, c, d), width, height)

            def senses_test(page, context, path, device):
                page.emulate_media(reduced_motion="no-preference")
                goto(page, path, prices=False)
                # A bottom cookie overlay can cover the narrow third mobile
                # panel and make Playwright scroll while retrying its click.
                cookie_ok = page.get_by_text('OK', exact=True)
                if cookie_ok.count() and cookie_ok.first.is_visible():
                    cookie_ok.first.click()
                root = page.locator('#ev-senses[data-enhanced="true"]')
                root.scroll_into_view_if_needed()
                require(root.count() == 1, "Expected one combined sensory block")
                buttons = root.locator('.ev-sense-toggle')
                require(buttons.count() == 3, "Expected three sensory panels")
                images(page, '#ev-senses img', minimum=3, local_only=True)
                # The surrounding legacy artboards finish measuring after the
                # buyer scripts are ready. Start only after their layout settles.
                page.wait_for_timeout(1200)
                root.scroll_into_view_if_needed()
                active_size, collapsed_size = (70, 15) if page.viewport_size['width'] <= 639 else (80, 10)
                expected_states = [tuple(active_size if i == active else collapsed_size for i in range(3))
                                   for active in range(3)]
                transition_samples = {}

                def sample_transition(index, preference):
                    sample = buttons.nth(index).evaluate("""button => new Promise((resolve, reject) => {
                      const panel=button.closest('.ev-sense-panel'), root=panel.parentElement;
                      const width=()=>100*panel.getBoundingClientRect().width/root.getBoundingClientRect().width;
                      const result={before:width()}, started=performance.now();
                      const midpoint=setTimeout(()=>{result.mid=width();},700);
                      const timeout=setTimeout(()=>{
                        panel.removeEventListener('transitionend',finish);
                        clearTimeout(midpoint);
                        reject(new Error('Panel resize did not finish with a transition event'));
                      },4500);
                      function finish(event) {
                        if(event.target!==panel || event.propertyName!=='flex-grow') return;
                        clearTimeout(timeout);
                        clearTimeout(midpoint);
                        panel.removeEventListener('transitionend',finish);
                        result.final=width();
                        result.duration=event.elapsedTime;
                        result.wallTime=performance.now()-started;
                        resolve(result);
                      }
                      panel.addEventListener('transitionend',finish);
                      button.click();
                    })""")
                    require(abs(sample['before']-collapsed_size) < .2,
                            f"Panel did not start collapsed ({preference}): {sample}")
                    require(collapsed_size+1 < sample.get('mid', 0) < active_size-1,
                            f"Panel jumps instead of resizing gradually ({preference}): {sample}")
                    require(abs(sample['final']-active_size) < .2 and 1.8 <= sample['duration'] <= 2.2,
                            f"Panel resize does not finish at the requested size in two seconds ({preference}): {sample}")
                    transition_samples[preference] = sample

                states = []
                for index, proportions in enumerate(expected_states):
                    # Exclude Playwright's own scroll-to-target from the check.
                    buttons.nth(index).scroll_into_view_if_needed()
                    before_y = page.evaluate('scrollY')
                    # Native click avoids Playwright auto-scroll during responsive artboard changes.
                    if path == 'index.html' and device == 'mobile' and index == 1:
                        sample_transition(index, 'no-preference')
                    else:
                        buttons.nth(index).evaluate("button => button.click()")
                    page.wait_for_function("""expected => {
                      const root=document.querySelector('#ev-senses');
                      const panels=[...root.querySelectorAll('.ev-sense-panel')];
                      return panels.every((p,i)=>Math.abs(Number(getComputedStyle(p).flexGrow)-expected[i])<.01)
                        && getComputedStyle(root.querySelector('.is-active .ev-sense-copy')).opacity==='1';
                    }""", arg=proportions)
                    metrics = root.evaluate("""el=>{
                      const r=el.getBoundingClientRect(), vertical=getComputedStyle(el).flexDirection==='column';
                      const panels=[...el.querySelectorAll('.ev-sense-panel')];
                      return {vertical,width:r.width,height:r.height,viewport:document.documentElement.clientWidth,
                        panels:panels.map(p=>{const b=p.getBoundingClientRect(),copy=p.querySelector('.ev-sense-copy'),
                          c=copy.getBoundingClientRect(),label=p.querySelector('.ev-sense-label').getBoundingClientRect(),
                          button=p.querySelector('button');return {
                          proportion:100*(vertical?b.height/r.height:b.width/r.width),
                          expanded:button.getAttribute('aria-expanded'),hidden:copy.getAttribute('aria-hidden'),
                          visible:getComputedStyle(copy).visibility==='visible' && getComputedStyle(copy).opacity==='1',
                          copyInside:c.left>=b.left && c.right<=b.right+1 && c.top>=b.top && c.bottom<=b.bottom+1,
                          labelInside:label.left>=b.left && label.right<=b.right+1 && label.top>=b.top && label.bottom<=b.bottom+1,
                          transition:getComputedStyle(p).transitionDuration};})};
                    }""")
                    require(abs(metrics['width']-metrics['viewport']) < 2, f"Sensory block is not full width: {metrics}")
                    require(metrics['height'] <= 660, f"Sensory block is too tall: {metrics}")
                    require(not metrics['vertical'], "Sensory panels must stay horizontal at every screen width")
                    after_y = page.evaluate('scrollY')
                    require(abs(after_y-before_y) < 2,
                            f"Selecting sensory panel {index} moved the page: {before_y} -> {after_y}")
                    for i, panel in enumerate(metrics['panels']):
                        active = i == index
                        require(abs(panel['proportion']-proportions[i]) < .2, f"Wrong panel proportions: {metrics}")
                        require(panel['expanded'] == str(active).lower() and panel['hidden'] == str(not active).lower(),
                                "Sensory panel accessibility state is inconsistent")
                        require(panel['visible'] == active, "Inactive sensory copy is visible")
                        require(not active or panel['copyInside'], f"Sensory copy is clipped: {metrics}")
                        require(active or panel['labelInside'], f"Collapsed sensory label is clipped: {metrics}")
                        require(float(panel['transition'].removesuffix('s')) >= 1.8,
                                "Panel resizing is too fast")
                    states.append(metrics)
                    shot(page, 'senses-' + path.replace('/', '-') + '-' + device + '-' + str(index), full=False)
                buttons.nth(2).press('Home')
                require(root.get_attribute('data-active') == '0', "Home key did not select the first panel")
                buttons.nth(0).press('ArrowRight')
                require(root.get_attribute('data-active') == '1', "Arrow key did not select the next panel")
                buttons.nth(1).press('End')
                require(root.get_attribute('data-active') == '2', "End key did not select the last panel")
                buttons.nth(0).press('Enter')
                require(root.get_attribute('data-active') == '0', "Enter did not activate a sensory panel")
                page.emulate_media(reduced_motion='reduce')
                if path == 'index.html' and device == 'mobile':
                    page.wait_for_function("""expected => [...document.querySelectorAll('#ev-senses .ev-sense-panel')]
                      .every((p,i)=>Math.abs(Number(getComputedStyle(p).flexGrow)-expected[i])<.01)""",
                      arg=expected_states[0])
                    sample_transition(1, 'reduce')
                else:
                    buttons.nth(1).evaluate("button => button.click()")
                require(root.locator('.ev-sense-panel').evaluate_all(
                    "els=>els.every(el=>getComputedStyle(el).transitionDuration==='2s')"),
                    "User-triggered panel resizing must stay slow with either motion preference")
                require(root.locator('.ev-sense-copy, .ev-sense-label, .ev-sense-curve').evaluate_all(
                    "els=>els.every(el=>getComputedStyle(el).transitionDuration==='0s')"),
                    "Decorative sensory motion ignores reduced-motion preference")
                return {'path': path, 'states': states, 'keyboard': True, 'reduced_motion': True,
                        'transition_samples': transition_samples}

            for device, width, height in DEVICES[:2]:
                for home_path in ('index.html', 'ru/index.html', 'en/index.html'):
                    case('senses-' + home_path.replace('/', '-') + '-' + device,
                         lambda p, c, path=home_path, d=device: senses_test(p, c, path, d), width, height)
            for width in (320, 768):
                case('senses-breakpoint-' + str(width),
                     lambda p, c, w=width: senses_test(p, c, 'index.html', str(w)), width, 900)

            def senses_fallback_test(page, context):
                context.route('**/home-senses.js*', lambda route: route.fulfill(
                    status=200, content_type='application/javascript', body='/* script unavailable */'))
                goto(page, 'index.html', prices=False)
                root = page.locator('#ev-senses')
                require(root.get_attribute('data-enhanced') is None, "Fallback test unexpectedly loaded the script")
                require(root.locator('.ev-sense-copy').evaluate_all(
                    "els=>els.length===3 && els.every(el=>getComputedStyle(el).visibility==='visible' && getComputedStyle(el).opacity==='1')"),
                    "Content disappears when the sensory script is unavailable")
                require(root.locator('.ev-sense-toggle').evaluate_all(
                    "els=>els.every(el=>getComputedStyle(el).display==='none')"),
                    "Fallback shows non-functional controls")
                return {'all_three_captions_visible': True}

            case('senses-script-fallback', senses_fallback_test, 390, 844)

            # EL1052 already has this complete mobile coverage in the existing
            # mirrored-product case above. Check the remaining 29 without a
            # duplicate visit, and expose an exact SKU-to-case map in the report.
            summary["canonical_product_mobile_cases"] = {
                product["sku"]: ("existing-product-mobile" if product["sku"] == "EL1052"
                                 else "canonical-product-mobile-" + product["sku"])
                for product in products}

            def canonical_mobile_test(page, context, product):
                goto(page, product["canonicalPath"], wait_fonts=False)
                tools = product_tools_metrics(page, product)
                loaded = images(page, local_only=True)
                metrics = layout_metrics(page, check_style=False)
                return {"sku": product["sku"], "canonical_path": product["canonicalPath"],
                        "product_tools": tools, "images": loaded, "layout": metrics}

            for product in products:
                if product["sku"] == "EL1052":
                    continue
                case(summary["canonical_product_mobile_cases"][product["sku"]],
                     lambda p, c, product=product: canonical_mobile_test(p, c, product), 390, 844)
            summary["canonical_product_mobile360_cases"] = {
                product["sku"]: "canonical-product-mobile360-" + product["sku"] for product in products}
            for product in products:
                case(summary["canonical_product_mobile360_cases"][product["sku"]],
                     lambda p, c, product=product: canonical_mobile_test(p, c, product), 360, 800)
            browser.close()
    except Exception as error:
        summary["fatal_error"] = {"message": str(error), "traceback": traceback.format_exc(limit=8)}
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        save()
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
