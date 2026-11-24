#!/usr/bin/env python3
"""Check the published directory against the current public partner sheet."""
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright
from check_partners_feed import active_partners, has_pin

URL = "https://eversense.by/where-to-buy.html"
OUT = Path("partners-browser-qa")
OUT.mkdir(exist_ok=True)
dealers = active_partners()
ids = {row["partner_id"].strip() for row in dealers}
cities = {row["city"].strip() for row in dealers}
minsk = [row for row in dealers if row["city"].strip() == "Минск"]
located_cities = {row["city"].strip() for row in dealers if has_pin(row)}
located_cities.update(cities & {"Слуцк", "Берёза"})
results, errors = [], []


def card(page, row):
    return page.locator(f'.partner-card[data-partner-id="{row["partner_id"]}"]')


def check_directory(page, label):
    response = page.goto(URL, wait_until="domcontentloaded", timeout=55000)
    assert response and response.status == 200
    page.wait_for_function("() => window.EversensePartners?.isLoaded()", timeout=35000)
    panel = page.locator("#partners-map-panel")
    directory = page.locator("#partners-list")
    pins = panel.locator(".map-city")
    groups = page.locator("#partners-groups > .city-group")
    region = next(row for row in dealers if row["city"] != "Минск" and has_pin(row))
    city = region["city"].strip()
    city_select = page.locator("#partners-city")
    search = page.locator("#partners-search")
    reset = page.locator("#partners-reset")

    assert panel.is_visible() and directory.is_visible()
    assert panel.bounding_box()["y"] + panel.bounding_box()["height"] <= directory.bounding_box()["y"] + 1
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert pins.count() == len(located_cities) > 0
    assert set(pins.evaluate_all("els => els.map(el => el.dataset.city)")) == located_cities
    assert not panel.locator("iframe, .leaflet-container").count()
    assert page.locator("#map-hint").is_visible()
    # Check actual labels in screen pixels after the Cyrillic font has loaded.
    page.evaluate("document.fonts.ready")
    page.wait_for_function("""() => {
        const frame = document.querySelector('#partners-map').getBoundingClientRect();
        const labels = [...document.querySelectorAll('.map-city__label')].map(el => el.getBoundingClientRect());
        return labels.every((a, i) => a.left >= frame.left - 1 && a.right <= frame.right + 1
          && labels.slice(i + 1).every(b => a.right <= b.left + 1 || b.right <= a.left + 1
            || a.bottom <= b.top + 1 || b.bottom <= a.top + 1));
    }""")
    assert panel.locator("path.country-outline").is_visible()
    assert not reset.is_visible()
    assert page.locator("#partners-demo,.district-group,.city-group__right,#partners-count,.view-switch").count() == 0
    names = groups.evaluate_all("els => els.map(el => el.dataset.city)")
    assert len(names) == len(cities) and set(names) == cities and names[0] == "Минск"
    assert page.evaluate("s => s.slice(1).every((x,i) => !i || s[i].localeCompare(x,'ru')<=0)", names)
    assert groups.first.evaluate("el => el.tagName") == "SECTION"
    assert groups.first.locator(".partner-card:visible").count() == len(minsk)
    assert set(page.locator(".partner-card:visible").evaluate_all("a=>a.map(el=>el.dataset.partnerId)")) == ids
    assert page.locator(".demo-tag").count() == sum(r["demo"].upper() == "TRUE" for r in dealers)
    assert not page.locator('a[href="https://example.com"]').count()
    assert groups.nth(1).evaluate("el => getComputedStyle(el).borderTopWidth") == "1px"
    assert search.evaluate("el => getComputedStyle(el).borderTopWidth") == "0px"

    first = card(page, minsk[0])
    assert first.locator("summary").inner_text().strip().startswith(minsk[0]["name"].strip())
    assert minsk[0]["address"].strip() in first.locator("summary").inner_text()
    closed = first.evaluate("el => getComputedStyle(el).backgroundColor")
    first.locator("summary").click()
    assert first.locator(".partner-card__row").count() == 3
    assert first.evaluate("el => getComputedStyle(el).borderTopWidth") == "0px"
    assert first.evaluate("el => getComputedStyle(el).backgroundColor") != closed
    if minsk[0]["phone"]:
        assert first.locator('a[href^="tel:"]').count() == 1
    site = minsk[0]["website"] or minsk[0]["Сайт дилера"]
    if site:
        assert first.locator('dd a[href^="http"]').get_attribute("href").rstrip("/") == site.rstrip("/")
    for row in dealers:
        link = card(page, row).locator("a.partner-card__route")
        has_location = has_pin(row) or bool(row["address"].strip())
        if row["demo"].upper() == "TRUE" or not has_location:
            assert link.count() == 0
            continue
        url = urlparse(link.get_attribute("href"))
        params = parse_qs(url.query)
        assert url.scheme == "https" and url.netloc == "yandex.by"
        if has_pin(row):
            assert params.get("rtt") == ["auto"]
            destination = params["rtext"][0].removeprefix("~")
            assert list(map(float, destination.split(","))) == [
                float(row[key].replace(",", ".")) for key in ("latitude", "longitude")]
        else:
            assert params.get("text") == [", ".join(["Беларусь", row["city"].strip(), row["address"].strip()])]
            assert "rtext" not in params

    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(OUT / f"{label}-overview.png"), animations="disabled", timeout=40000)
    page.locator(".directory-link").click()
    assert page.evaluate("location.hash") == "#partners-list"

    city_select.select_option(city)
    assert reset.is_visible() and pins.count() == len(located_cities)
    assert page.locator(".partner-card:visible").count() == sum(r["city"].strip() == city for r in dealers)

    # A map link reveals the whole city even after a different city or an empty search.
    city_select.select_option("Минск")
    search.fill("no-such-store-987654")
    pin = panel.get_by_role("link", name=city + " — показать магазины", exact=True)
    pin.locator(".map-city__label").click()
    group = groups.filter(has=card(page, region))
    assert group.get_attribute("open") is not None
    assert city_select.input_value() == "" and search.input_value() == ""
    assert group.locator(".partner-card:visible").count() == sum(r["city"].strip() == city for r in dealers)
    assert group.locator(":scope > summary").evaluate("el => el === document.activeElement")
    assert page.evaluate("decodeURIComponent(location.hash)") == "#city-" + city.replace(" ", "-")
    group.locator(":scope > summary").click()
    assert group.get_attribute("open") is None
    pin.focus()
    pin.press("Enter")
    assert group.get_attribute("open") is not None
    assert group.locator(":scope > summary").evaluate("el => el === document.activeElement")
    if minsk:
        panel.get_by_role("link", name="Минск — показать магазины").click()
        assert groups.first.locator(".partner-card:visible").count() == len(minsk)
        assert groups.first.locator("h3").evaluate("el => el === document.activeElement")

    if minsk[0]["district"]:
        search.fill(minsk[0]["district"])
        assert card(page, minsk[0]).is_visible()
    search.fill("no-such-store-987654")
    assert page.locator("#partners-empty").is_visible() and page.locator(".partner-card").count() == 0
    assert pins.count() == len(located_cities)
    reset.click()
    assert page.locator(".partner-card").count() == len(ids) and not reset.is_visible()

    # A change in sheet sort_order must also work without a district grouping.
    if len(minsk) > 1:
        promoted = minsk[-1]["partner_id"]
        page.evaluate("""id => {
            const records = window.EversensePartners.all();
            const rows = records.map(r => ({c: [r.id,r.id===id?-100000:r.order,r.city,r.district,
                r.name,r.website,r.phone,r.address,r.hours,r.lat,r.lng,r.active,r.demo].map(v=>({v}))}));
            window.EversensePartnersFeed({status:"ok",table:{rows}});
        }""", promoted)
        assert page.locator(".partner-card").first.get_attribute("data-partner-id") == promoted
    directory.scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / f"{label}-directory.png"), full_page=True, animations="disabled", timeout=40000)
    return {"device": label, "shops": len(ids), "minsk": len(minsk), "cities": len(cities), "city_links": pins.count()}


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    for label, width, height in [("desktop", 1440, 920), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height}, has_touch=label == "mobile",
                                is_mobile=label == "mobile", reduced_motion="reduce", device_scale_factor=1)
        page.set_default_timeout(12000)
        js_errors = []
        page.on("pageerror", lambda error: js_errors.append(str(error)))
        try:
            result = check_directory(page, label)
            assert not js_errors, js_errors
            results.append(result)
            print("PARTNER_BROWSER_QA", json.dumps(result), flush=True)
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {exc}")
            page.screenshot(path=str(OUT / f"{label}-error.png"), animations="disabled")
            import traceback
            traceback.print_exc()
        finally:
            page.close()
    home = browser.new_page()
    try:
        response = home.goto("https://eversense.by/", wait_until="domcontentloaded", timeout=50000)
        assert response and response.ok
        assert home.locator('a[href="/where-to-buy.html"],a[href="https://eversense.by/where-to-buy.html"]').count()
    except Exception as exc:
        errors.append(f"Homepage navigation: {exc}")
    finally:
        browser.close()

(OUT / "results.json").write_text(json.dumps({"results": results, "errors": errors}, indent=2))
if errors:
    raise SystemExit("\n".join(errors))
