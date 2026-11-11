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
            row["demo_banner_removed"] = page.locator("#partners-demo").count() == 0
            row["demo_tags_count"] = page.locator(".demo-tag").count()
            assert row["data_count"] == 40, row
            assert row["city_count"] == 16 and row["minsk_count"] == 10, row
            assert row["districts"] == 9, row
            assert row["map_markers"] == 40, "All 40 markers should appear on map: " + str(row)
            assert row["demo_banner_removed"], "Large DEMO banner must be removed"
            assert row["demo_tags_count"] == 40, "Sample dealers must retain compact DEMO labels"
            assert not page.locator("#partners-reset").is_visible(), "Clear filter should be hidden initially"
            row["search_style"] = page.locator(".search-field input").evaluate("el => ({top:getComputedStyle(el).borderTopWidth, bottom:getComputedStyle(el).borderBottomWidth, bg:getComputedStyle(el).backgroundColor})")
            assert row["search_style"]["top"] == "0px" and row["search_style"]["bottom"] == "0px", "Search must be unboxed"
            assert page.locator(".district-group__count,.city-group__right,#partners-count,#cities-count,#partners-showing").count() == 0, "Visible partner counters must be removed"
            border = page.locator('.city-group[data-city="Минск"] .partner-card').first.evaluate(
                "el => ({width:getComputedStyle(el).borderTopWidth,shadow:getComputedStyle(el).boxShadow})")
            row["partner_card_style"] = border
            assert border["width"] == "0px" and border["shadow"] == "none", "Dealer rows must have no boxes or shadows"
            # A single fine border separates cities; no separators between salons.
            row["city_dividers"] = page.locator("#partners-groups > .city-group + .city-group").count()
            city_divider_width = page.locator("#partners-groups > .city-group + .city-group").first.evaluate(
                "el => getComputedStyle(el).borderTopWidth")
            row["city_divider_width"] = city_divider_width
            assert row["city_dividers"] == 15 and city_divider_width == "1px", "City separators are missing"
            closed_card_background = page.locator('.city-group[data-city="Минск"] .partner-card').nth(1).evaluate(
                "el => getComputedStyle(el).backgroundColor")
            row["closed_card_background"] = closed_card_background
            assert not page.locator(".partner-card__sub:visible").count(), "Duplicate district caption must be removed"
            assert page.locator('a[href="https://example.com"]').count() == 0, "Demo websites must not be promoted as real links"

            # Map is the default view; the directory remains available on demand.
            assert page.locator("#partners-map-panel").is_visible(), "Map must be the default view"
            assert not page.locator("#partners-list").is_visible(), "List must have its own view"
            assert page.locator("#partners-view-map").get_attribute("aria-pressed") == "true"
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Horizontal overflow"
            page.screenshot(path=str(OUT / (label + "-map.png")), full_page=True, animations="disabled")
            page.click("#partners-view-list")
            assert page.locator("#partners-list").is_visible(), "List switch did not reveal the directory"
            assert not page.locator("#partners-map-panel").is_visible()
            assert page.locator("#partners-view-list").get_attribute("aria-pressed") == "true"

            # Expanding partner shows all requested contact fields.
            minsk = page.locator('.city-group[data-city="Минск"]')
            row["minsk_static_section"] = minsk.evaluate("el => el.tagName === 'SECTION'")
            row["district_headers_visible"] = minsk.locator(".district-group__heading:visible").count()
            row["district_accordions"] = minsk.locator(".district-group > summary").count()
            assert row["minsk_static_section"], "Minsk must not be collapsible"
            assert row["district_headers_visible"] == 9, "All 9 districts must be visible immediately"
            assert row["district_accordions"] == 0, "Districts must not require a click"
            assert minsk.locator(".partner-card:visible").count() == 10, "All Minsk dealers must be visible"
            partner = minsk.locator(".partner-card").first
            partner.locator("summary").click()
            assert partner.get_attribute("open") is not None, "Contact accordion did not open"
            row["expanded_card_background"] = partner.evaluate("el => getComputedStyle(el).backgroundColor")
            assert row["expanded_card_background"] != closed_card_background, (
                "An expanded salon must have a different, slightly darker background")
            assert partner.evaluate("el => getComputedStyle(el).borderTopWidth") == "0px", (
                "Expanded salons must remain borderless")
            row["contact_rows"] = partner.locator(".partner-card__row").count()
            assert row["contact_rows"] == 4, "Expected address, telephone, website, hours"

            # City filter: 2 sites in Brest, with two corresponding pins.
            page.select_option("#partners-city", "Брест")
            page.wait_for_timeout(300)
            assert page.locator("#partners-reset").is_visible(), "Clear filter must appear when city is selected"
            row["brest_visible"] = page.locator(".partner-card").count()
            page.click("#partners-view-map")
            assert page.locator("#partners-city").input_value() == "Брест", "Switching views lost the city filter"
            row["brest_pins"] = page.locator(".leaflet-marker-icon").count()
            assert row["brest_visible"] == 2 and row["brest_pins"] == 2, row

            # A marker opens contacts in place; the explicit link opens the matching list card.
            page.locator(".leaflet-marker-icon").first.click()
            page.locator(".ev-popup__details").wait_for(state="visible")
            assert page.locator("#partners-map-panel").is_visible(), "Marker unexpectedly left the map"
            page.locator(".ev-popup__details").click()
            assert page.locator("#partners-list").is_visible()
            active = page.locator(".partner-card[open]").first
            assert active.locator(".partner-card__row").count() == 4
            active.locator("button[data-map-id]").click()
            assert page.locator("#partners-map-panel").is_visible(), "Show on map did not switch back"
            page.locator(".ev-popup__details").wait_for(state="visible")

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

            page.fill("#partners-search", "no-such-store-987654")
            assert page.locator("#partners-empty").is_visible(), "Empty search needs a visible message"
            assert page.locator(".leaflet-marker-icon").count() == 0
            assert page.locator(".leaflet-popup").count() == 0, "Empty search retained an old popup"
            page.click("#partners-map-reset")
            assert page.locator("#partners-search").input_value() == ""
            assert page.locator(".leaflet-marker-icon").count() == 40
            assert not page.locator("#partners-reset").is_visible(), "Clear filter must disappear when filters are empty"
            page.click("#partners-view-list")
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
print("PASS: 40 partners, map/list switching, Minsk districts, city filter, popup/list navigation,",
      "empty search, reset, demo labels, contacts and ranking on desktop/mobile.", flush=True)
