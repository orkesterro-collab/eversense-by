#!/usr/bin/env python3
"""Focused browser checks for the EVERSENSE exploration experience.

Run in CI after staging the public site. Starts a loopback fixture server,
uses deterministic prices, and writes screenshots plus a machine-readable
summary under buyer-qa/exploration. It never alters the published website.
"""
from __future__ import annotations

import argparse
import functools
import json
import re
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEVICES = [("desktop", 1440, 1000), ("mobile360", 360, 800)]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_deploy")
    parser.add_argument("--output", type=Path, default=ROOT / "buyer-qa/exploration")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    site_dir = args.site_dir.resolve()
    base = f"http://127.0.0.1:{args.port}"
    started = time.monotonic()
    summary = {"checks": [], "screenshots": [], "fatal_error": None,
               "site_dir": str(site_dir), "price_source": "mocked 45.90 BYN/m²"}
    server = None

    def save():
        summary["passed"] = sum(c["status"] == "passed" for c in summary["checks"])
        summary["failed"] = sum(c["status"] == "failed" for c in summary["checks"])
        summary["ok"] = not summary["failed"] and summary["fatal_error"] is None
        summary["duration_seconds"] = round(time.monotonic() - started, 2)
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    try:
        products = json.loads((site_dir / "assets/products-data.json").read_text())
        by_sku = {p["sku"]: p for p in products}
        payload = {"status": "ok", "table": {"rows": [
            {"c": [{"v": p["sku"]}, {"v": 45.90}, {"v": None}, {"v": None}, {"v": None}]}
            for p in products]}}
        jsonp = "window.EversensePriceFeed(" + json.dumps(payload) + ");"
        server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                     functools.partial(QuietHandler, directory=str(site_dir)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

            def goto(page, path, js=True):
                response = page.goto(base + "/" + path.lstrip("/"), wait_until="domcontentloaded")
                require(response is not None and response.ok, "Could not open " + path)
                if js:
                    page.wait_for_function("window.__eversenseBuyerStarted")
                page.evaluate("async () => { await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,2000))]); }")

            def screenshot(page, name, selector=None):
                path = output / (re.sub(r"[^a-zA-Z0-9_.-]", "-", name) + ".png")
                if selector:
                    page.locator(selector).screenshot(path=str(path), animations="disabled", timeout=30000)
                else:
                    page.screenshot(path=str(path), full_page=True, animations="disabled", timeout=30000)
                summary["screenshots"].append(path.name)

            def layout(page):
                result = page.evaluate("""() => {
                    const visible = el => !!el.getClientRects().length;
                    return {width:innerWidth, document:document.documentElement.scrollWidth,
                      h1:[...document.querySelectorAll('h1')].filter(visible).map(el=>el.textContent.trim()),
                      duplicateIds:[...document.querySelectorAll('[id]')].map(el=>el.id)
                        .filter((id,i,all)=>all.indexOf(id)!==i)};
                }""")
                require(result["document"] <= result["width"] + 2,
                        f"Horizontal overflow: {result}")
                require(len(result["h1"]) == 1 and result["h1"][0], f"Invalid visible title: {result['h1']}")
                require(not result["duplicateIds"], f"Duplicate IDs: {result['duplicateIds']}")
                return result

            def images(page, selector="main img"):
                page.locator(selector).evaluate_all("els=>els.forEach(el=>{el.loading='eager';})")
                page.wait_for_function("selector=>[...document.querySelectorAll(selector)].every(el=>el.complete)",
                                       arg=selector, timeout=20000)
                broken = page.locator(selector).evaluate_all(
                    "els=>els.filter(el=>!el.naturalWidth).map(el=>el.currentSrc||el.src)")
                require(not broken, "Broken images: " + str(broken))
                return page.locator(selector).count()

            def case(name, fn, width=1440, height=1000, js=True):
                context = browser.new_context(viewport={"width": width, "height": height},
                    locale="ru-RU", reduced_motion="reduce", java_script_enabled=js,
                    ignore_https_errors=True, device_scale_factor=1)
                context.set_default_timeout(10000)
                context.set_default_navigation_timeout(30000)
                context.route("https://docs.google.com/spreadsheets/**/gviz/**",
                              lambda route: route.fulfill(status=200,
                                  content_type="application/javascript; charset=utf-8", body=jsonp))
                page = context.new_page()
                errors = []
                failures = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: failures.append({"url": response.url, "status": response.status})
                        if response.url.startswith(base + "/") and response.status >= 400
                        and not response.url.endswith("/favicon.ico") else None)
                row = {"name": name, "viewport": width, "javascript": js}
                try:
                    row["details"] = fn(page, context, name)
                    require(not errors, "JavaScript errors: " + str(errors))
                    require(not failures, "Failed local resources: " + str(failures))
                    row["status"] = "passed"
                except Exception as error:
                    row.update(status="failed", error=str(error), traceback=traceback.format_exc(limit=5))
                    try:
                        screenshot(page, name + "-failure")
                    except Exception:
                        pass
                finally:
                    row["page_errors"] = errors
                    row["local_failures"] = failures
                    summary["checks"].append(row)
                    save()
                    context.close()

            def layers(page, context, name):
                goto(page, "about.html")
                explorer = page.locator("[data-layer-explorer]")
                page.wait_for_selector('[data-layer-explorer][data-layer-ready="true"]')
                controls = explorer.locator("[data-layer-control]")
                require(controls.count() == 4, "Expected all four selectable construction layers")
                seen = []
                for control in controls.all():
                    layer = control.get_attribute("data-layer-control")
                    control.click()
                    require(control.get_attribute("aria-selected") == "true", "Layer not selected: " + layer)
                    panel = explorer.locator('[data-layer-panel="' + layer + '"]')
                    require(panel.is_visible() and len(panel.inner_text()) > 100, "Missing explanation for " + layer)
                    require(explorer.locator('[data-layer-panel]:visible').count() == 1,
                            "More than one layer explanation remains visible")
                    active = explorer.locator('[data-layer-image].is-active')
                    require(active.count() == 1 and active.get_attribute("data-layer-image") == layer,
                            "Layer illustration does not follow its explanation")
                    require(float(active.evaluate("el=>getComputedStyle(el).opacity")) > .9,
                            "Active layer is not emphasized")
                    seen.append(layer)
                controls.first.focus()
                page.keyboard.press("End")
                require(controls.last.evaluate("el=>el===document.activeElement"), "End did not focus last layer")
                page.keyboard.press("ArrowRight")
                require(controls.first.evaluate("el=>el===document.activeElement"), "Arrow navigation did not wrap")
                page.keyboard.press("ArrowRight")
                require(controls.nth(1).get_attribute("aria-selected") == "true", "Keyboard did not select second layer")
                require(explorer.locator('[data-layer-control][tabindex="0"]').count() == 1,
                        "Layer controls do not have a single keyboard entry point")
                image_count = images(page, "[data-layer-explorer] img")
                screenshot(page, name, "[data-layer-explorer]")
                metrics = layout(page)
                page.goto(base + "/about.html#ev-layer-panel-board", wait_until="domcontentloaded")
                page.wait_for_selector('[data-layer-control="board"][aria-selected="true"]')
                require(page.locator('[data-layer-panel="board"]').is_visible(), "Deep link hid its target explanation")
                response = page.reload(wait_until="domcontentloaded")
                require(response is not None and response.ok, "Could not reload construction deep link")
                page.wait_for_selector('[data-layer-control="board"][aria-selected="true"]')
                return {"layers": seen, "images": image_count, "keyboard": True, "deep_link": True, "layout": metrics}

            def layers_no_js(page, context, name):
                goto(page, "about.html", js=False)
                panels = page.locator("[data-layer-panel]")
                require(panels.count() == 4, "No-JS construction content missing")
                for panel in panels.all():
                    require(panel.is_visible() and len(panel.inner_text()) > 100, "No-JS layer explanation hidden")
                for control in page.locator("[data-layer-control]").all():
                    target = control.get_attribute("href")
                    require(target.startswith("#") and page.locator(target).count() == 1,
                            "No-JS layer control is not a working fragment link")
                return {"visible_explanations": 4, "images": images(page, "[data-layer-explorer] img"),
                        "layout": layout(page)}

            for device, width, height in DEVICES:
                case("construction-" + device, layers, width, height)
                case("construction-no-js-" + device, layers_no_js, width, height, js=False)

            def interiors(page, context, name):
                goto(page, "projects.html")
                page.wait_for_selector('[data-interior-stories][data-interior-ready="true"]')
                stories = page.locator("[data-interior-story]")
                require(stories.count() == 3, "Expected three curated interior comparisons")
                pairs = []
                initial_selections = []
                for story in stories.all():
                    initial_selections.append(story.locator('[data-story-scene]:visible').get_attribute("data-story-scene"))
                for index, story in enumerate(stories.all()):
                    choices = story.locator("[data-story-select]")
                    require(choices.count() == 2, "Story needs two exact decor choices")
                    pair = [choice.get_attribute("data-story-select") for choice in choices.all()]
                    require(all(sku in by_sku for sku in pair) and len(set(pair)) == 2,
                            "Story choices are not two distinct catalog SKUs")
                    for choice in choices.all():
                        sku = choice.get_attribute("data-story-select")
                        choice.click()
                        scene = story.locator('[data-story-scene="' + sku + '"]')
                        require(choice.get_attribute("aria-pressed") == "true" and scene.is_visible(),
                                "Selected decor does not reveal its scene: " + sku)
                        require(story.locator('[data-story-scene]:visible').count() == 1,
                                "Scene selection left another scene visible")
                        photo = scene.locator("[data-story-photo]")
                        for view, field in [("detail", "productImage"), ("room", "interiorImage")]:
                            toggle = story.locator('[data-story-view="' + view + '"]')
                            toggle.click()
                            require(toggle.get_attribute("aria-pressed") == "true", "Image view button lacks selected state")
                            actual_path = urlparse(photo.get_attribute("src")).path.lstrip("/")
                            require(actual_path == by_sku[sku][field].lstrip("/"),
                                    f"Wrong {view} photograph for {sku}: {actual_path}")
                            require(bool(photo.get_attribute("alt")), "Scene image has no alternative text")
                        product_link = scene.locator("[data-story-product]")
                        require(urlparse(product_link.get_attribute("href")).path.lstrip("/") ==
                                by_sku[sku]["canonicalPath"].lstrip("/"), "Scene links to another decor")
                    # A choice in one story must not silently recolor another.
                    for later in range(index + 1, stories.count()):
                        require(stories.nth(later).locator('[data-story-scene]:visible').get_attribute("data-story-scene") ==
                                initial_selections[later], "Scene choice changed another independent story")
                    selection_link = story.locator('a[href*="favorites.html?items="]')
                    require(selection_link.count() == 1, "Story is missing its saved-pair link")
                    pair_in_link = parse_qs(urlparse(selection_link.get_attribute("href")).query).get("items", [""])[0].split(",")
                    require(pair_in_link == pair, "Saved-pair link does not match the two depicted decors")
                    pairs.append(pair)
                first = stories.first
                selected = first.locator('[data-story-scene]:visible')
                sku = selected.get_attribute("data-story-scene")
                favorite = selected.locator("[data-ev-favorite]")
                favorite.focus()
                page.keyboard.press("Enter")
                require(favorite.get_attribute("aria-pressed") == "true", "Keyboard favorite action failed")
                require(sku in json.loads(page.evaluate("localStorage.getItem('eversense.favorites.v1')")),
                        "Selected story decor was not saved to favorites")
                image_count = images(page, "[data-interior-stories] img")
                metrics = layout(page)
                screenshot(page, name, "[data-interior-stories]")
                first.locator('a[href*="favorites.html?items="]').click()
                page.wait_for_selector("#ev-favorites .ev-card")
                displayed = page.locator("#ev-favorites .ev-card").evaluate_all("els=>els.map(el=>el.dataset.product)")
                require(displayed == pairs[0], f"Opening saved pair showed wrong products: {displayed}")
                return {"pairs": pairs, "favorite": sku, "images": image_count, "layout": metrics,
                        "saved_pair_opened": displayed}

            def interiors_no_js(page, context, name):
                goto(page, "projects.html", js=False)
                stories = page.locator("[data-interior-story]")
                require(stories.count() == 3, "No-JS stories missing")
                visible = page.locator("[data-story-scene]:visible")
                require(visible.count() == 6, "No-JS must keep both decor scenes available in all three stories")
                for scene in visible.all():
                    sku = scene.get_attribute("data-story-scene")
                    require(sku in by_sku, "No-JS story uses unknown product")
                    link = scene.locator("[data-story-product]")
                    require(link.is_visible() and link.get_attribute("href"), "No-JS product link missing")
                require(page.locator('[data-story-select]:visible').count() == 0,
                        "Nonfunctional story selection controls shown without JavaScript")
                return {"visible_scenes": visible.count(), "images": images(page, "[data-interior-stories] img"),
                        "layout": layout(page)}

            def choose(page, context, name):
                goto(page, "choose.html")
                require(page.locator("[data-design-route]").count() == 3, "Visual design entrances missing")
                expected = {design: sum(p["tags"]["design"] == design for p in products)
                            for design in ["wood", "stone", "plain"]}
                for design, count in expected.items():
                    tile = page.locator('[data-design-route="' + design + '"]')
                    require(tile.is_visible() and tile.locator("img").count() == 1,
                            "Design entrance needs its visible catalog image")
                    tile.click()
                    page.wait_for_selector("#ev-catalog-results .ev-card")
                    # Static fallback cards are visible before deferred catalog initialization.
                    expect(page.locator('#ev-catalog-filters [name="design"]')).to_have_value(
                        design, timeout=10000)
                    shown = page.locator("#ev-catalog-results .ev-card").count()
                    require(shown == count, f"Expected {count} {design} decors, found {shown}")
                    goto(page, "choose.html")
                checks = page.locator('#sample .ev-sample-step input[type="checkbox"]')
                require(checks.count() == 4, "Sample guide needs four observations")
                for check in checks.all():
                    require(check.evaluate("el=>el.labels.length>0"), "Sample checkbox is missing a label")
                    check.focus()
                    page.keyboard.press("Space")
                    require(check.is_checked(), "Sample observation cannot be checked with keyboard")
                page.locator('#sample .ev-sample-step').first.locator('strong').click()
                require(not checks.first.is_checked(), "Full sample label does not toggle its native checkbox")
                screenshot(page, name + "-sample", "#sample")
                metrics = layout(page)
                loaded = images(page)
                screenshot(page, name + "-designs", "#designs")
                return {"catalog_counts": expected, "keyboard_sample_checks": 4,
                        "images": loaded, "layout": metrics}

            def choose_no_js(page, context, name):
                goto(page, "choose.html", js=False)
                cards = page.locator("[data-design-route]")
                require(cards.count() == 3, "No-JS visual design routes missing")
                for card in cards.all():
                    require(card.is_visible() and "design=" in card.get_attribute("href"),
                            "No-JS visual design route does not expose catalog link")
                check = page.locator('#sample .ev-sample-step input[type="checkbox"]').first
                check.check()
                require(check.is_checked(), "Native sample checkbox stopped working without JavaScript")
                return {"visual_routes": 3, "native_checkbox": True, "images": images(page), "layout": layout(page)}

            def situations(page, context, name):
                visited = {}
                for path in ["care.html", "installation.html"]:
                    goto(page, path)
                    if path == "installation.html":
                        links = page.locator(".ev-install-navigation a")
                        require(links.count() == 3, "Expected separate installation and comparison pages")
                        targets = [link.get_attribute("href") for link in links.all()]
                        for target in targets:
                            goto(page, path)
                            page.locator('.ev-install-navigation a[href="' + target + '"]').click()
                            require(urlparse(page.url).path.endswith(target), "Installation route did not open: " + target)
                            require(page.locator(".ev-install-article").is_visible(), "Installation article is hidden")
                            require(page.locator('.ev-install-navigation [aria-current="page"]').count() == 1,
                                    "Installation navigation did not identify the current page")
                            layout(page)
                            article_name = name + '-' + target.removesuffix('.html')
                            screenshot(page, article_name + '-intro', '.ev-install-intro')
                            table = '#comparison .ev-install-table-wrap' if target == 'installation-methods.html' else '#moisture .ev-install-table-wrap'
                            require(page.locator(table).is_visible(), "Required comparison or moisture table is hidden")
                            screenshot(page, article_name + '-table', table)
                        visited[path] = {"targets": targets, "layout": layout(page)}
                        continue
                    links = page.locator(".ev-situations .ev-link-card")
                    require(links.count() == 3, "Expected three useful situation entry points on " + path)
                    targets = []
                    for link in links.all():
                        target = link.get_attribute("href")
                        require(target.startswith("#") and page.locator(target).count() == 1,
                                "Situation entry has missing content target: " + target)
                        link.click()
                        require(urlparse(page.url).fragment == target[1:], "Situation link did not open its section")
                        require(page.locator(target).is_visible(), "Situation target is hidden")
                        targets.append(target)
                    visited[path] = {"targets": targets, "layout": layout(page)}
                return visited

            for device, width, height in DEVICES:
                case("interiors-" + device, interiors, width, height)
                case("interiors-no-js-" + device, interiors_no_js, width, height, js=False)
                case("choose-" + device, choose, width, height)
                case("choose-no-js-" + device, choose_no_js, width, height, js=False)
                case("situations-" + device, situations, width, height)
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
