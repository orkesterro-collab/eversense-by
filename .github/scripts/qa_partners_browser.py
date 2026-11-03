#!/usr/bin/env python3
"""Real-browser QA for new Eversense partners directory on hoster.by."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://eversense.by/where-to-buy.html"
OUT = Path("partners-browser-qa")
OUT.mkdir(exist_ok=True)
results = []
errors = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    for label, width, height in [("desktop", 1440, 920), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height},
                                ignore_https_errors=False, device_scale_factor=1)
        row = {"device": label}
        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)[:220]))
        try:
            response = page.goto(URL, wait_until="domcontentloaded", timeout=55000)
            row["http"] = response.status if response else None
            assert response is not None and response.status == 200, f"HTTP {row['http']}"
            page.wait_for_function(
                "() => !!(window.EversensePartners && window.EversensePartners.isLoaded())",
                timeout=35000)
            page.wait_for_timeout(700)
            row["data_count"] = page.evaluate("window.EversensePartners.all().length")
            row["city_count"] = page.locator(".city-group").count()
            row["minsk_count"] = page.locator('.city-group[data-city="Минск"] .partner-card').count()
            row["map_markers"] = page.locator(".leaflet-marker-icon").count()
            row["districts"] = page.locator('.city-group[data-city="Минск"] .district-group').count()
            row["demo_banner_visible"] = page.locator("#partners-demo").is_visible()
            assert row["data_count"] == 40, row
            assert row["city_count"] == 16 and row["minsk_count"] == 10, row
            assert row["districts"] == 9, row
            assert row["map_markers"] == 40, "All 40 markers should appear on map: " + str(row)
            assert row["demo_banner_visible"], "Demo data must be clearly labeled"
            assert page.locator('a[href="https://example.com"]').count() == 0, "Demo websites must not be promoted as real links"

            # Expanding partner shows all requested contact fields.
            minsk = page.locator('.city-group[data-city="Минск"]')
            minsk.locator(".district-group > summary").first.click()
            partner = minsk.locator(".partner-card").first
            partner.locator("summary").click()
            assert partner.get_attribute("open") is not None, "Contact accordion did not open"
            row["contact_rows"] = partner.locator(".partner-card__row").count()
            assert row["contact_rows"] == 4, "Expected address, telephone, website, hours"

            # City filter: 2 sites in Brest, with two corresponding pins.
            page.select_option("#partners-city", "Брест")
            page.wait_for_timeout(300)
            row["brest_visible"] = page.locator(".partner-card").count()
            row["brest_pins"] = page.locator(".leaflet-marker-icon").count()
            assert row["brest_visible"] == 2 and row["brest_pins"] == 2, row

            # Rank changes are driven by sort_order, not the Sheet row's physical position.
            # Inject a temporary, in-browser-only response: no Google Sheet writes.
            page.evaluate("""() => {
                const records = window.EversensePartners.all();
                const cells = r => [r.id,r.order,r.city,r.district,r.name,r.website,r.phone,
                                    r.address,r.hours,r.lat,r.lng,r.active,r.demo]
                                 .map(v=>({v:v}));
                const second = records.find(r=>r.id==="DEMO-BY-02");
                if (!second) throw Error("Brest sample #2 not found");
                second.order = -100;
                window.EversensePartnersFeed({status:"ok",table:{rows:records.map(r=>({c:cells(r)}))}});
            }""")
            page.wait_for_timeout(200)
            row["rank_first"] = page.locator(".partner-card").first.get_attribute("data-partner-id")
            assert row["rank_first"] == "DEMO-BY-02", "sort_order did not promote dealer above peer"

            page.select_option("#partners-city", "")
            page.fill("#partners-search", "Фрунзенский")
            page.wait_for_timeout(200)
            row["district_search_count"] = page.locator(".partner-card").count()
            assert row["district_search_count"] == 2, row

            page.fill("#partners-search", "")
            page.screenshot(path=str(OUT / (label + "-directory.png")),
                            full_page=True, animations="disabled", timeout=40000)
            row["js_errors"] = js_errors
            assert not js_errors, "JS errors: " + str(js_errors)
        except Exception as exc:
            row["error"] = str(exc)[:400]
            errors.append(label + ": " + str(exc)[:400])
        print("PARTNER_BROWSER_QA", json.dumps(row, ensure_ascii=False), flush=True)
        results.append(row)
        page.close()
    home = browser.new_page(ignore_https_errors=False)
    try:
        response = home.goto("https://eversense.by/", wait_until="domcontentloaded", timeout=50000)
        assert response and response.status == 200
        home_links = home.evaluate("""() => [...document.querySelectorAll('a[href]')]
            .filter(a => /где купить/i.test(a.textContent || '') ||
                (a.getAttribute('href') || '').includes('where-to-buy'))
            .map(a => ({label:(a.textContent||'').trim().slice(0,40),
                         href:a.getAttribute('href')||''}))""")
        print("PARTNERS_HOMEPAGE_LINKS",json.dumps(home_links[:30],ensure_ascii=False),flush=True)
        assert any(x["href"] in ("/where-to-buy.html","https://eversense.by/where-to-buy.html")
                   for x in home_links), "Homepage is missing link to new live dealer directory"
    except Exception as exc:
        errors.append("Homepage partner navigation: " + str(exc)[:400])
    finally:
        home.close()
    browser.close()

(OUT / "results.json").write_text(
    json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
for err in errors:
    print("PARTNER_BROWSER_QA FAIL:", err, flush=True)
if errors:
    raise SystemExit("Partner browser QA failed")
print("PASS: 40 partners, Minsk districts, city filter, marker sync, demo notice,",
      "contact accordion and numerical ranking in desktop/mobile browser.", flush=True)
