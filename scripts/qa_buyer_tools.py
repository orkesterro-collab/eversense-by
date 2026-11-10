#!/usr/bin/env python3
"""Browser QA against staged _deploy; never contacts or changes the live store.

Run after installing Playwright + Chromium:
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
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEVICES = [("desktop", 1440, 1000), ("mobile", 390, 844), ("mobile360", 360, 800)]
FAVORITES = "eversense.favorites.v1"
COMPARE = "eversense.compare.v1"
SCREENSHOT_PAGES = {"catalog-ru/index.html", "choose.html", "about.html", "calculator.html", "compare.html"}


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
            {"c": [{"v": p["sku"]}, {"v": 45.90}, {"v": None}, {"v": None}, {"v": None}]}
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
                if storage_blocked:
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
                    font:getComputedStyle(document.body).fontFamily,fontStatus:document.fonts.status,
                    loadedFonts:[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family),
                    controls:controls.map(e=>({tag:e.tagName,text:e.getAttribute('aria-label')||e.innerText||e.name||'',
                      height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width,font:getComputedStyle(e).fontFamily,
                      fontSize:parseFloat(getComputedStyle(e).fontSize),disabled:e.disabled||false})),
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
                goto(page, "catalog-ru/")
                cards = page.locator("#ev-catalog-results .ev-card")
                require(cards.count() == 30, f"Catalog count is {cards.count()}")
                require(set(cards.evaluate_all("xs=>xs.map(x=>x.dataset.product)")) == set(by_sku), "Catalog SKU differs from data")
                loaded = images(page, "#ev-catalog-results .ev-card-image img:first-child", minimum=16)
                require(loaded["local"] == 30, "Expected 30 real local product images")
                page.locator('#ev-catalog-filters [name="q"]').fill("EL1052")
                require(cards.count() == 1 and cards.first.get_attribute("data-product") == "EL1052", "SKU filter returned wrong product")
                page.locator("#ev-catalog-filters [data-reset-filters]").click()
                page.locator('#ev-catalog-filters [name="design"]').select_option("stone")
                require(cards.count() == 2, f"Stone filter should show 2, got {cards.count()}")
                require(set(cards.evaluate_all("xs=>xs.map(x=>x.dataset.product)")) == {"EL1000", "EL1002"}, "Wrong stone SKU")
                page.locator("#ev-catalog-filters [data-reset-filters]").click()
                require(cards.count() == 30, "Reset does not restore catalog")
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
                page.evaluate("([a,b])=>{localStorage.setItem(a,'{bad JSON');localStorage.setItem(b,JSON.stringify(['EL1052','EL1052','UNKNOWN',null]));}", [FAVORITES, COMPARE])
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__eversenseBuyerStarted")
                require(page.locator("#ev-catalog-results .ev-card").count() == 30, "Corrupt storage broke catalog")
                page.locator('[data-ev-favorite="EL1052"]').click()
                require(json.loads(page.evaluate("key=>localStorage.getItem(key)", FAVORITES)) == ["EL1052"], "Storage did not recover")
                return {"corrupt_json_recovered": True}
            case("storage-corruption", bad_storage_test)

            def blocked_storage_test(page, context):
                goto(page, "catalog-ru/")
                require(page.evaluate("()=>{try{void localStorage;return false;}catch(e){return e.name==='SecurityError';}}"),
                        "Blocked-storage fixture did not take effect")
                selected = ["EL1052", "EL1000"]
                for sku in selected:
                    page.locator(f'[data-ev-favorite="{sku}"]').click()
                    page.locator(f'[data-ev-compare="{sku}"]').click()
                favorites_link = page.locator('main a[href*="favorites.html"]').first
                favorite_url = favorites_link.get_attribute("href")
                favorite_query = parse_qs(urlparse(favorite_url).query)
                require(favorite_query.get("ev-favorites", [""])[0].split(",") == selected,
                        "Favorites link did not carry selections when storage was blocked")
                require(favorite_query.get("ev-compare", [""])[0].split(",") == selected,
                        "Favorites navigation lost comparison fallback state")
                favorites_link.click()
                page.wait_for_selector("#ev-favorites .ev-card")
                require(page.locator("#ev-favorites .ev-card").count() == 2,
                        "Favorites were lost after navigation with blocked storage")
                compare_link = page.locator('main [data-compare-link]').first
                compare_url = compare_link.get_attribute("href")
                compare_query = parse_qs(urlparse(compare_url).query)
                require(compare_query.get("items", [""])[0].split(",") == selected,
                        "Comparison link lost items after fallback link synchronization")
                require(compare_query.get("ev-favorites", [""])[0].split(",") == selected,
                        "Comparison navigation lost favorites fallback state")
                compare_link.click()
                page.wait_for_selector("#ev-compare table")
                require(page.locator("#ev-compare thead th").count() == 3,
                        "Comparison lost its two products with storage blocked")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector("#ev-compare table")
                require(page.locator("#ev-compare thead th").count() == 3,
                        "URL fallback did not survive reload")
                page.locator('main a[href*="favorites.html"]').first.click()
                page.wait_for_selector("#ev-favorites .ev-card")
                restored = page.locator("#ev-favorites .ev-card").evaluate_all("els=>els.map(el=>el.dataset.product)")
                require(restored == selected, "Return from comparison erased favorite fallback selection")
                return {"storage_getter_throws": True, "selected": selected,
                        "favorites_url": favorite_url, "comparison_url": compare_url, "reload_preserved": True}
            case("storage-blocked-url-navigation", blocked_storage_test, storage_blocked=True)

            def compare_test(page, context, device):
                goto(page, "catalog-ru/")
                for sku in ["EL1000", "EL1052", "EL153", "EL750"]:
                    page.locator(f'[data-ev-compare="{sku}"]').click()
                chosen = json.loads(page.evaluate("key=>localStorage.getItem(key)", COMPARE))
                require(chosen == ["EL1000", "EL1052", "EL153"], "Comparison exceeded 3 or silently replaced an item")
                require("трёх" in page.locator("#ev-buyer-status").inner_text(), "Limit feedback missing")
                goto(page, "compare.html")
                require(page.locator("#ev-compare thead th").count() == 4, "Expected three comparison columns")
                row = page.locator("#ev-compare tbody tr").filter(has=page.locator('th[scope="row"]', has_text="Площадь упаковки"))
                areas = [numeric(t) for t in row.locator("td").all_inner_texts()]
                require(areas == [Decimal("2.54"), Decimal("1.99"), Decimal("1.99")], f"Wrong pack comparison: {areas}")
                require("ev-different" in (row.get_attribute("class") or ""), "Different pack areas are not marked")
                images(page, "#ev-compare img", minimum=16)
                shot(page, "compare-result-" + device)
                layout_metrics(page)
                remove = page.locator("#ev-compare [data-ev-compare]")
                while remove.count():
                    require(remove.first.inner_text().strip() == "Убрать", "Remove button misleadingly says selected")
                    remove.first.click()
                require("items" not in parse_qs(urlparse(page.url).query), "Deleted comparison remains in URL")
                require(page.locator("[data-share-compare]").is_disabled(), "Empty comparison can still be shared")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__eversenseBuyerStarted")
                require(page.locator("#ev-compare table").count() == 0, "Reload resurrected removed products")
                return {"limit": 3, "pack_areas": [str(a) for a in areas], "empty_reload": True}
            for device, width, height in DEVICES[:2]:
                case("comparison-" + device, lambda p, c, d=device: compare_test(p, c, d), width, height)

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

            def header_test(page, context, device):
                goto(page, "about.html")
                toggle = page.locator(".ev-header-toggle")
                toggle.focus()
                page.keyboard.press("Enter")
                menu = page.locator("#ev-global-menu")
                require(menu.is_visible() and toggle.get_attribute("aria-expanded") == "true", "Keyboard did not open menu")
                paths = {urlparse(href).path for href in menu.locator("a").evaluate_all("els=>els.map(a=>a.href)")}
                expected = {"/catalog-ru/", "/choose.html", "/favorites.html", "/compare.html", "/calculator.html", "/about.html", "/downloads.html", "/where-to-buy.html"}
                require(expected <= paths, f"Header is missing links: {expected-paths}")
                require(all(menu.locator("a").nth(i).is_visible() for i in range(menu.locator("a").count())), "Menu contains CSS-hidden navigation")
                shot(page, "menu-" + device, full=False)
                page.keyboard.press("Escape")
                require(not menu.is_visible() and toggle.get_attribute("aria-expanded") == "false", "Escape failed to close menu")
                require(toggle.evaluate("el=>el===document.activeElement"), "Escape did not restore toggle focus")
                return {"links": len(paths), "keyboard_open_and_escape": True}
            for device, width, height in DEVICES:
                case("header-" + device, lambda p, c, d=device: header_test(p, c, d), width, height)

            def layout_test(page, context, path, device):
                suffix = ""
                if path == "compare.html": suffix = "?items=EL1000,EL1052,EL153"
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

            def product_tools_metrics(page, product):
                sku = product["sku"]
                page.wait_for_selector("#ev-product-tools", state="attached", timeout=20000)
                require(page.locator("#ev-product-tools").count() == 1, f"{sku}: product tools missing or duplicated")
                favorite = page.locator("#ev-product-tools [data-ev-favorite]")
                comparison = page.locator("#ev-product-tools [data-ev-compare]")
                require(favorite.count() == 1 and favorite.get_attribute("data-ev-favorite") == sku,
                        f"{sku}: favorite tools mounted with wrong SKU")
                require(comparison.count() == 1 and comparison.get_attribute("data-ev-compare") == sku,
                        f"{sku}: comparison tools mounted with wrong SKU")
                calc_link = page.locator('#ev-product-tools a[href*="calculator.html"]')
                require(calc_link.count() == 1 and parse_qs(urlparse(calc_link.get_attribute("href")).query).get("sku") == [sku],
                        f"{sku}: product calculator lost SKU")
                price_panel = page.locator("#ev-product-price")
                require(price_panel.count() == 1 and price_panel.get_attribute("data-ev-sku") == sku,
                        f"{sku}: price panel points to a different product")
                page.wait_for_selector("#ev-product-price .ev-price-box strong")
                price = price_panel.locator(".ev-price-box strong").inner_text()
                require("45,90" in price and "BYN" in price, f"{sku}: mocked product price missing: {price}")
                page.evaluate("()=>{EversensePrices.render();EversensePrices.render();}")
                require(page.locator("#ev-product-tools").count() == 1, f"{sku}: price rerender duplicated product tools")
                return {"sku": sku, "tools_count": 1, "price": price, "calculator_link_has_sku": True}

            def mirrored_test(page, context, path, device, product=False):
                goto(page, path)
                tools = None
                if product:
                    tools = product_tools_metrics(page, by_sku["EL1052"])
                    page.locator('#ev-product-tools [data-ev-favorite="EL1052"]').click()
                    require("EL1052" in page.evaluate("key=>localStorage.getItem(key)", FAVORITES), "Mirrored product favorite is broken")
                loaded = images(page)
                page.evaluate("window.scrollTo(0,0)")
                shot(page, ("existing-product" if product else "existing-home") + "-" + device, full=False)
                return {"images": loaded, "layout": layout_metrics(page, check_style=False), "dynamic_product_tools": product, "product_tools": tools}
            for device, width, height in DEVICES[:2]:
                case("existing-home-" + device, lambda p, c, d=device: mirrored_test(p, c, "index.html", d), width, height)
                case("existing-product-" + device,
                     lambda p, c, d=device: mirrored_test(p, c, by_sku["EL1052"]["canonicalPath"], d, True), width, height)

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
