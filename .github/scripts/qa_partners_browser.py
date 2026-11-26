#!/usr/bin/env python3
"""Check the published directory against the current public partner sheet."""
import json
from collections import Counter
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


def check_shop_contact(page, basemap, dealers, device):
    def location(row):
        return (row["city"].strip(), float(row["longitude"].replace(",", ".")),
                float(row["latitude"].replace(",", ".")))

    located = [r for r in dealers if has_pin(r)]
    if not located:
        return None
    counts = Counter(location(r) for r in located)
    singles = {r["partner_id"].strip() for r in located if counts[location(r)] == 1}
    target = next((r for r in located if r["city"].strip() == "Борисов" and "musson" in r["name"].lower()), None)
    if target is None:
        target = next((r for r in located if r["phone"].strip()), located[0])
    city, name, shop_id = (target[k].strip() for k in ("city", "name", "partner_id"))

    # Centre the chosen city before zooming, as a visitor would.
    basemap.evaluate("el => el.scrollIntoView({block:'center', behavior:'instant'})")
    city_pin = basemap.get_by_role("link", name=city + " — показать магазины", exact=True)
    frame, pin = basemap.bounding_box(), city_pin.bounding_box()
    dx = frame["x"] + frame["width"] / 2 - pin["x"] - pin["width"] / 2
    dy = frame["y"] + frame["height"] / 2 - pin["y"] - pin["height"] / 2
    x, y = frame["x"] + frame["width"] * 0.38, frame["y"] + frame["height"] * 0.32
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx, y + dy, steps=12)
    page.wait_for_timeout(180)
    page.mouse.up()
    shop_pins = basemap.locator("button.dealer-pin--shop")
    for _ in range(7):
        if shop_pins.count():
            break
        basemap.get_by_role("button", name="Приблизить").click()
        page.wait_for_timeout(350)
    assert shop_pins.count() == len(counts)
    assert set(basemap.locator("button.dealer-pin--shop[data-partner-id]").evaluate_all("els=>els.map(el=>el.dataset.partnerId)")) == singles
    marker = (shop_pins.filter(has_text=name) if shop_id not in singles
              else basemap.locator(f'button.dealer-pin[data-partner-id="{shop_id}"]'))
    caption = marker.locator(".dealer-pin__caption")
    assert name in caption.inner_text() and caption.evaluate("el => getComputedStyle(el).opacity === '1' && getComputedStyle(el).pointerEvents !== 'none'")
    initial_hash = page.evaluate("location.hash")
    (caption.tap if device == "mobile" else caption.click)()
    dialog = basemap.get_by_role("dialog")
    contact = dialog.locator(f'.dealer-contact[data-partner-id="{shop_id}"]')
    assert contact.is_visible() and contact.locator("h3").inner_text() == name
    assert page.evaluate("location.hash") == initial_hash
    phone = contact.locator(".dealer-contact__phone")
    has_phone = bool(phone.count())
    assert has_phone == any(c.isdigit() for c in target["phone"])
    if has_phone:
        assert phone.first.inner_text() in target["phone"]
        copy = contact.get_by_role("button", name="Скопировать номер").first
        (copy.tap if device == "mobile" else copy.click)()
        contact.get_by_text("Скопировано", exact=True).first.wait_for()
        assert page.evaluate("navigator.clipboard.readText()") == phone.first.inner_text()
    else:
        assert contact.locator(".dealer-contact__unlisted").is_visible() and not contact.locator(".dealer-contact__copy").count()
    page.screenshot(path=str(OUT / f"{device}-shop-contact.png"), animations="disabled")
    find = contact.get_by_role("link", name="Найти в списке")
    (find.tap if device == "mobile" else find.click)()
    dialog.wait_for(state="hidden")
    assert card(page, target).evaluate("el => el.open && el.firstElementChild === document.activeElement")
    assert page.evaluate("decodeURIComponent(location.hash)") == "#shop-" + shop_id
    basemap.get_by_role("button", name="Вся Беларусь").click()
    return {"store": name, "city": city, "copied": has_phone}


def check_directory(page, label):
    response = page.goto(URL, wait_until="domcontentloaded", timeout=55000)
    assert response and response.status == 200
    page.wait_for_function("() => window.EversensePartners?.isLoaded()", timeout=35000)
    panel = page.locator("#partners-map-panel")
    directory = page.locator("#partners-list")
    basemap = panel.locator("#partners-basemap")
    basemap.wait_for(state="visible", timeout=55000)
    pins = basemap.locator(".dealer-pin")
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
    canvas = basemap.locator("canvas.maplibregl-canvas")
    assert canvas.is_visible() and not panel.locator("#partners-map").is_visible()
    assert canvas.evaluate("el => getComputedStyle(el).filter") == "grayscale(1) sepia(0.25)"
    assert basemap.locator('a[href*="openstreetmap.org/copyright"]').count()
    assert basemap.get_by_role("button", name="Приблизить").is_visible()
    assert basemap.get_by_role("button", name="Вся Беларусь").is_visible()
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
    pin = basemap.get_by_role("link", name=city + " — показать магазины", exact=True)
    pin.click()
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
        basemap.get_by_role("link", name="Минск — показать магазины").click()
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

    contact_result = check_shop_contact(page, basemap, dealers, label)
    assert set(pins.evaluate_all("els => els.map(el => el.dataset.city)")) == located_cities

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
    return {"device": label, "shops": len(ids), "minsk": len(minsk), "cities": len(cities), "city_links": pins.count(), "contact": contact_result}


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
    for label, width, height in [("desktop", 1440, 920), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height}, has_touch=label == "mobile",
                                is_mobile=label == "mobile", reduced_motion="reduce", device_scale_factor=1)
        page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://eversense.by")
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
