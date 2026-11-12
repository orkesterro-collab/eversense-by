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
    ("/where-to-buy.html", "partners"),
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
                row["internal_catalog_anchors"] = page.evaluate("() => [...document.querySelectorAll('a[href]')].filter(a => a.origin === location.origin && /^\\/catalog-ru\\/?$/.test(a.pathname)).length")
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
                # The static homepage keeps its header visible; other pages hide it on scroll.
                header = page.locator("#ev-global-header")
                header.wait_for(state="visible", timeout=12000)
                row["shared_header_visible"] = True
                row["official_logo_loaded"] = header.locator("img").first.evaluate(
                    "img => img.complete && img.naturalWidth > 0")
                if not row["official_logo_loaded"]:
                    failures.append(f"{device} {path}: official header logo missing")
                toggle = header.locator(".ev-header-toggle")
                toggle.click(timeout=8000)
                row["menu_opens"] = page.locator("#ev-global-menu").is_visible()
                if not row["menu_opens"]:
                    failures.append(f"{device} {path}: shared menu failed to open")
                page.keyboard.press("Escape")
                row["escape_closes_menu"] = not page.locator("#ev-global-menu").is_visible()
                if not row["escape_closes_menu"]:
                    failures.append(f"{device} {path}: Escape did not close shared menu")
                page.evaluate("window.scrollTo({top: 500, behavior: 'instant'})")
                page.wait_for_timeout(450)
                row["header_hides_down"] = "ev-header-hidden" in (header.get_attribute("class") or "")
                if row["header_hides_down"] != (label != "home"):
                    failures.append(f"{device} {path}: unexpected header behavior on downward scroll")
                page.evaluate("window.scrollTo({top: 180, behavior: 'instant'})")
                page.wait_for_timeout(450)
                row["header_returns_up"] = "ev-header-hidden" not in (header.get_attribute("class") or "")
                if not row["header_returns_up"]:
                    failures.append(f"{device} {path}: header did not reappear on upward scroll")
                page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                page.wait_for_timeout(150)
                if label == "home":
                    toggle.click(timeout=8000)
                    catalog_link = page.locator('#ev-global-menu a[href$="/catalog-ru/"]').first
                    catalog_link.click(timeout=8000)
                    page.wait_for_timeout(1000)
                    row["url_after_catalog_click"] = page.url
                    if not page.url.startswith("https://eversense.by/catalog-ru/"):
                        failures.append(f"{device}: shared menu catalog navigation failed: {page.url}")
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
