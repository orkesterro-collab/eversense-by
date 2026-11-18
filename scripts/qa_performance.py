#!/usr/bin/env python3
"""Check homepage media loading, Tilda controls and responsive catalog images.

Uses only staged local assets. Price and analytics requests are deterministic
fixtures; the checks never write to the published website or Google Sheets.
"""
from __future__ import annotations

import argparse
import functools
import json
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
CDN_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
RETAINED_ANALYTICS = {"https://static.tildacdn.com/js/tilda-stat-1.0.min.js"}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_deploy")
    parser.add_argument("--output", type=Path, default=ROOT / "buyer-qa/performance")
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--browser-executable", help="Optional system Chromium path for local checks")
    args = parser.parse_args()
    site_dir, output = args.site_dir.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    summary = {"site_dir": str(site_dir), "checks": [], "fatal_error": None}
    server = None

    def save():
        summary["passed"] = sum(row["status"] == "passed" for row in summary["checks"])
        summary["failed"] = sum(row["status"] == "failed" for row in summary["checks"])
        summary["duration_seconds"] = round(time.monotonic() - started, 2)
        summary["ok"] = not summary["failed"] and summary["fatal_error"] is None
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    try:
        require((site_dir / "index.html").is_file(), "Staged homepage missing")
        products = json.loads((site_dir / "assets/products-data.json").read_text())
        rows = [{"c": [{"v": product["sku"]}, {"v": 65.66}, {"v": None},
                       {"v": None}, {"v": None}, {"v": 100}]} for product in products]
        feed = "window.EversensePriceFeed(" + json.dumps({"status": "ok", "table": {"rows": rows}}) + ");"
        server = ThreadingHTTPServer(("127.0.0.1", args.port),
            functools.partial(QuietHandler, directory=str(site_dir)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{args.port}"
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            browser = playwright.chromium.launch(**launch)
            for device, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
                context = browser.new_context(viewport={"width": width, "height": height},
                    device_scale_factor=1, is_mobile=width < 500, has_touch=width < 500,
                    user_agent=playwright.devices["Pixel 7"]["user_agent"] if device == "mobile" else None,
                    locale="ru-RU", reduced_motion="no-preference")
                if device == "mobile":
                    context.add_init_script("""if (navigator.connection) {
                        Object.defineProperty(navigator.connection, 'saveData', {get: () => true});
                    }""")
                context.set_default_timeout(15000)
                context.route("https://docs.google.com/spreadsheets/**/gviz/**",
                    lambda route: route.fulfill(status=200, content_type="application/javascript", body=feed))
                for host in ("mc.yandex.ru", "mc.yandex.com"):
                    context.route("https://" + host + "/**", lambda route:
                        route.fulfill(status=200, content_type="application/javascript", body=""))
                page = context.new_page()
                errors, failed, media, cdn = [], [], [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: failed.append({"url": response.url, "status": response.status})
                    if response.url.startswith(base + "/") and response.status >= 400 else None)

                def request(request):
                    host = urlsplit(request.url).hostname or ""
                    if request.resource_type == "media":
                        media.append(request.url)
                    if (host in CDN_HOSTS or host.endswith(".tildacdn.com")) and request.url not in RETAINED_ANALYTICS:
                        cdn.append(request.url)
                page.on("request", request)

                def case(name, callback):
                    row = {"name": device + ": " + name}
                    try:
                        row["details"] = callback()
                        row["status"] = "passed"
                    except Exception as error:
                        row.update(status="failed", error=str(error), traceback=traceback.format_exc(limit=4))
                        try:
                            page.screenshot(path=str(output / (device + "-failure.png")))
                        except Exception:
                            pass
                    summary["checks"].append(row)
                    save()

                response = page.goto(base + "/", wait_until="load")
                require(response and response.ok, "Homepage did not load")
                # Dwell past the observer's layout debounce without user input.
                page.wait_for_timeout(1000)

                cdp = context.new_cdp_session(page)

                def without_gesture(expression):
                    # Playwright's normal evaluation can grant user activation
                    # even if the test never taps or clicks.
                    result = cdp.send("Runtime.evaluate", {
                        "expression": expression, "returnByValue": True,
                        "awaitPromise": True, "userGesture": False,
                    })
                    require("exceptionDetails" not in result, str(result.get("exceptionDetails")))
                    return result["result"]["value"]

                def initial_media():
                    state = without_gesture("""Array.from(document.querySelectorAll('video[data-ev-lazy-video]'),
                        v => ({src: v.currentSrc, preload: v.preload, poster: v.poster}))""")
                    require(len(state) == 2 and not media and all(not video["src"] for video in state),
                            f"Video started loading before scrolling: {media}; {state}")
                    return state
                case("videos stay unloaded before scrolling", initial_media)

                def videos():
                    details = []
                    for index in range(2):
                        state = without_gesture(f"""(async () => {{
                            const video = document.querySelectorAll('video[data-ev-lazy-video]')[{index}];
                            const waitFor = async condition => {{
                                const deadline = performance.now() + 10000;
                                while (!condition() && performance.now() < deadline)
                                    await new Promise(resolve => setTimeout(resolve, 100));
                            }};
                            video.scrollIntoView({{block: 'center', behavior: 'instant'}});
                            await waitFor(() => video.currentTime > .1 || video.error || video.controls);
                            const state = {{src: video.currentSrc, time: video.currentTime,
                                muted: video.muted, playing: !video.paused, controls: video.controls,
                                activated: navigator.userActivation.hasBeenActive}};
                            window.scrollTo({{top: 0, behavior: 'instant'}});
                            await waitFor(() => video.paused);
                            state.pausedOffscreen = video.paused;
                            return state;
                        }})()""")
                        resolution = "-540p.mp4" if device == "mobile" else "-1080p.mp4"
                        require(state["src"].endswith(resolution) and state["time"] > .1 and
                                state["muted"] and state["playing"] and not state["controls"] and
                                not state["activated"] and state["pausedOffscreen"],
                                f"Video {index + 1} did not autoplay without a gesture and pause offscreen: {state}")
                        details.append(state)
                    return details
                case("videos autoplay without a gesture and pause offscreen", videos)

                page.wait_for_function("window.nlm087obj && window.nlm087obj.isSlidersLoaded['413064765']")

                def menu():
                    toggle = page.locator(".ev-header-toggle")
                    toggle.click()
                    require(toggle.get_attribute("aria-expanded") == "true" and
                            page.locator("#ev-global-menu").is_visible(), "Menu did not open")
                    count = page.locator("#ev-global-menu a").count()
                    require(count >= 10, "Menu links missing")
                    page.keyboard.press("Escape")
                    require(toggle.get_attribute("aria-expanded") == "false" and
                            not page.locator("#ev-global-menu").is_visible(), "Menu did not close")
                    return {"links": count}
                case("navigation menu opens and closes", menu)

                def slider():
                    page.evaluate("scrollTo(0,0)")
                    wrapper = page.locator("#rec413064765nlm .t-slds__items-wrapper")
                    before = wrapper.get_attribute("data-slider-pos")
                    require(before is not None, "Hero slider not initialized")
                    controls = page.locator("#rec413064765nlm .nextButton")
                    candidates = controls.evaluate_all("""els=>els.map((e,i)=>{const r=e.getBoundingClientRect();
                        return {i,left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height,
                            visible:e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})}})
                        .filter(r=>r.visible&&r.width>0&&r.height>0&&r.left<innerWidth&&r.right>0&&r.top<innerHeight&&r.bottom>70)""")
                    require(candidates, "No on-screen next control")
                    button = controls.nth(candidates[0]["i"])
                    button.click(force=True)
                    page.wait_for_function("before=>document.querySelector('#rec413064765nlm .t-slds__items-wrapper').dataset.sliderPos!==before", arg=before)
                    return {"before": before, "after": wrapper.get_attribute("data-slider-pos")}
                case("hero next slide works", slider)

                def scroll_images():
                    total = page.evaluate("document.documentElement.scrollHeight")
                    broken = []
                    # Sweep each viewport so deferred backgrounds get a real
                    # intersection, including sections shorter than the screen.
                    for y in range(0, min(total, 35000), max(400, height // 2)):
                        page.evaluate("y=>scrollTo(0,y)", y)
                        page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                        broken.extend(page.locator("img").evaluate_all("""els=>els.filter(e=>e.complete&&e.currentSrc&&!e.naturalWidth
                            &&e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})).map(e=>e.currentSrc)"""))
                    pending = page.locator("[data-ev-background]").evaluate_all("""els=>els.filter(e=>{
                        const r=e.getBoundingClientRect();const slide=e.closest('.t-slds__item');
                        return e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})&&r.width>0&&r.height>0
                            &&r.right>0&&r.left<innerWidth&&r.bottom>0&&r.top<innerHeight
                            &&(!slide||slide.classList.contains('t-slds__item_active'));
                        }).map(e=>e.dataset.evBackground)""")
                    require(not pending, "Visible backgrounds did not load: " + str(pending))
                    require(not broken, "Broken visible images: " + str(sorted(set(broken))))
                    return {"height": total, "visible_backgrounds_pending": len(pending)}
                case("deferred backgrounds and images load on scroll", scroll_images)

                def responsive():
                    response = page.goto(base + "/catalog-ru/", wait_until="load")
                    require(response and response.ok, "Catalog did not load")
                    image = page.locator(".ev-card-image img[srcset]").first
                    image.scroll_into_view_if_needed()
                    page.wait_for_function("()=>{const i=document.querySelector('.ev-card-image img[srcset]');return i&&i.complete&&i.naturalWidth>0}")
                    state = image.evaluate("e=>({chosen:e.currentSrc,fallback:e.src,width:e.naturalWidth,slot:e.getBoundingClientRect().width})")
                    require("/assets/responsive/" in state["chosen"] and state["width"] <= 960,
                            "Catalog loaded oversized original: " + str(state))
                    require(state["chosen"] != state["fallback"], "Responsive candidate was not selected")
                    page.screenshot(path=str(output / (device + "-catalog.png")))
                    return state
                case("catalog selects a smaller responsive image", responsive)

                def gallery_resolution():
                    response = page.goto(base + "/catalog-ru/nature-aesthetic-ru/light-virdia-oak-ru/", wait_until="load")
                    require(response and response.ok, "Product gallery did not load")
                    image = page.locator('img.ev-gallery-image[fetchpriority="high"][srcset]')
                    page.wait_for_function("()=>{const i=document.querySelector('img.ev-gallery-image[fetchpriority=high][srcset]');return i&&i.complete&&i.naturalWidth>0}")
                    state = image.evaluate("e=>({chosen:e.currentSrc,width:e.naturalWidth,slot:e.getBoundingClientRect().width,sizes:e.sizes})")
                    require(state["width"] + 1 >= state["slot"],
                            "Full-width product texture would be enlarged from an undersized candidate: " + str(state))
                    page.screenshot(path=str(output / (device + "-product.png")))
                    return state
                case("full-width product texture retains its resolution", gallery_resolution)

                def clean():
                    require(not errors, "JavaScript errors: " + str(errors))
                    require(not failed, "Failed local resources: " + str(failed))
                    require(not cdn, "Startup still depends on Tilda or Google Font CDN: " + str(cdn))
                    return {"javascript_errors": errors, "failed_resources": failed, "cdn_requests": cdn,
                            "retained_analytics": sorted(RETAINED_ANALYTICS)}
                case("local assets and scripts load without errors", clean)
                context.close()
            browser.close()
    except Exception as error:
        summary["fatal_error"] = str(error)
        summary["traceback"] = traceback.format_exc(limit=6)
    finally:
        if server:
            server.shutdown()
        save()
    print(json.dumps({key: summary[key] for key in ("ok", "passed", "failed", "fatal_error", "duration_seconds")}, ensure_ascii=False))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
