#!/usr/bin/env python3
"""Desktop/mobile browser smoke tests of the live Eversense Belarus website."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE = "https://eversense.by"
CASES = [
    ("/", "home"),
    ("/catalog-ru/", "catalog"),
    ("/catalog-ru/quiet-luxury-ru/natural-victoria-oak-ru/", "product"),
    ("/black-friday/", "promotion"),
]
OUT = Path("hoster-browser-qa")
OUT.mkdir(exist_ok=True)
results = []
failures = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    for device, width, height in [("desktop", 1440, 900), ("mobile", 390, 844)]:
        context = browser.new_context(viewport={"width": width, "height": height},
                                      ignore_https_errors=False, device_scale_factor=1)
        for path, label in CASES:
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)[:200]))
            row = {"device": device, "path": path, "label": label}
            try:
                response = page.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
                status = response.status if response else None
                row["status"] = status
                if status != 200:
                    failures.append(f"{device} {path}: HTTP {status}")
                page.wait_for_timeout(2500)
                row["title"] = page.title()[:130]
                row["internal_catalog_anchors"] = page.locator('a[href="/catalog-ru"],a[href="/catalog-ru/"]').count()
                row["price_boxes"] = page.locator(".ev-price-box").count()
                row["images_loaded"] = page.evaluate(
                    "() => [...document.images].filter(i=>i.complete&&i.naturalWidth>0).length")
                row["images_total"] = page.locator("img").count()
                if label in ("home","catalog") and row["internal_catalog_anchors"] == 0:
                    failures.append(f"{device} {path}: no local catalog link")
                if label in ("catalog", "product"):
                    try:
                        page.wait_for_function(
                            "() => !!(window.EversensePrices && window.EversensePrices.isLoaded())",
                            timeout=22000)
                        row["price_feed_loaded"] = True
                    except PlaywrightTimeout:
                        row["price_feed_loaded"] = False
                        failures.append(f"{device} {path}: browser did not load Google price feed")
                    row["price_boxes"] = page.locator(".ev-price-box").count()
                    if row["price_boxes"] == 0:
                        failures.append(f"{device} {path}: price widgets were not rendered")
                if label == "product":
                    row["has_expected_price"] = ("65,66" in page.locator("body").inner_text())
                    if not row["has_expected_price"]:
                        failures.append(f"{device} {path}: expected sample price 65,66 BYN is absent")
                row["page_errors"] = errors[:8]
                page.screenshot(path=str(OUT / (label + "-" + device + ".png")),
                                full_page=False, animations="disabled", timeout=30000)
                if label == "home":
                    anchors = page.locator('a[href="/catalog-ru"],a[href="/catalog-ru/"]')
                    stats = [a.evaluate("""a => {
                        const r=a.getBoundingClientRect();
                        return {y:Math.round(r.y), bottom:Math.round(r.bottom), x:Math.round(r.x),
                                h:Math.round(r.height), text:a.textContent.trim().slice(0,35)}
                    }""") for a in anchors.all()]
                    print("HOME_CATALOG_LINK_POSITIONS", device, json.dumps(stats,ensure_ascii=False), flush=True)
                    visible = [a for a in anchors.all() if a.is_visible() and
                               a.evaluate("a => {const r=a.getBoundingClientRect();return r.bottom>2 && r.height>0}")]
                    row["visible_catalog_links"] = len(visible)
                    if visible:
                        first = visible[0]
                        diagnostic = first.evaluate("""a => {
                            const r=a.getBoundingClientRect();
                            const x=Math.min(innerWidth-1,Math.max(0,r.left+r.width/2));
                            const y=Math.min(innerHeight-1,Math.max(0,r.top+r.height/2));
                            return {tag:a.outerHTML.slice(0,300),rect:{x:r.x,y:r.y,w:r.width,h:r.height},
                                pointer:getComputedStyle(a).pointerEvents,
                                covering:document.elementFromPoint(x,y)?.outerHTML.slice(0,300)}
                        }""")
                        print("HOME_CATALOG_LINK_DIAGNOSTICS", device, json.dumps(diagnostic,ensure_ascii=False), flush=True)
                        try:
                            first.click(timeout=5500)
                            page.wait_for_url("**/catalog-ru*", timeout=15000)
                            row["catalog_click_reached"] = page.url
                        except Exception as exc:
                            print("HOME_CATALOG_CLICK_ERROR", device, str(exc)[:2000], flush=True)
                            failures.append(f"{device} homepage catalog click failed: {str(exc)[:170]}")
                    elif device == "desktop":
                        failures.append("Desktop homepage has no visible catalog navigation link")
            except Exception as exc:
                row["exception"] = str(exc)[:300]
                failures.append(f"{device} {path}: {str(exc)[:180]}")
            print(json.dumps(row, ensure_ascii=False), flush=True)
            results.append(row)
            page.close()
        context.close()
    browser.close()
(OUT / "results.json").write_text(json.dumps({"checks": results, "failures": failures},
                                              ensure_ascii=False, indent=2), encoding="utf-8")
print("BROWSER_QA checks:", len(results), "failures:", len(failures), flush=True)
for failure in failures:
    print("BROWSER_QA FAIL:", failure, flush=True)
if failures:
    raise SystemExit(1)
print("BROWSER_QA PASS: desktop/mobile catalog, product page, prices and campaign.")
