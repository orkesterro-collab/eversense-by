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
                    onscreen = """a => {
                        const r=a.getBoundingClientRect(), x=r.left+r.width/2,y=r.top+r.height/2;
                        return r.width>0 && r.height>0 && x>0 && x<innerWidth && y>0 && y<innerHeight;
                    }"""
                    hit_test = """a => {
                        const r=a.getBoundingClientRect(), x=r.left+r.width/2,y=r.top+r.height/2;
                        const hit=document.elementFromPoint(x,y);
                        return hit===a || a.contains(hit);
                    }"""
                    if device == "mobile":
                        toggles = page.locator('a[href="#menuopen-ru"]')
                        usable = [a for a in toggles.all() if a.is_visible() and a.evaluate(onscreen)]
                        row["visible_mobile_menu_toggles"] = len(usable)
                        if usable:
                            try:
                                usable[0].click(timeout=8500)
                                page.wait_for_timeout(900)
                                row["mobile_menu_opened"] = True
                            except Exception as exc:
                                row["mobile_menu_error"] = str(exc)[:400]
                                failures.append("Mobile hamburger menu could not be opened")
                        else:
                            failures.append("Mobile hamburger button is not onscreen")
                    anchors = page.locator('a[href="/catalog-ru"],a[href="/catalog-ru/"]')
                    candidates = [a for a in anchors.all() if a.is_visible() and
                                  a.evaluate(onscreen) and a.evaluate(hit_test)]
                    row["clickable_catalog_links"] = len(candidates)
                    if candidates:
                        first = candidates[0]
                        row["clicked_catalog_link_html"] = first.evaluate("a => a.outerHTML.slice(0,380)")
                        try:
                            first.click(timeout=8000)
                            page.wait_for_timeout(1800)
                            row["url_after_catalog_click"] = page.url
                            row["open_page_urls"] = [p.url for p in context.pages]
                            print("HOME_CATALOG_CLICK_STATE", device,
                                  json.dumps({"clicked":row["clicked_catalog_link_html"],
                                              "current":page.url,
                                              "pages":row["open_page_urls"]},ensure_ascii=False),flush=True)
                            if "/catalog-ru" not in page.url and not any(
                                "/catalog-ru" in p.url for p in context.pages):
                                failures.append(f"{device} click did not open catalog in any browser tab")
                        except Exception as exc:
                            print("HOME_CATALOG_CLICK_ERROR", device, str(exc)[:1500], flush=True)
                            failures.append(f"{device} real catalog navigation failed: {str(exc)[:180]}")
                    else:
                        failures.append(f"{device} no onscreen and unobstructed catalog navigation link")
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
