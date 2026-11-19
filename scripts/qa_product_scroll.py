#!/usr/bin/env python3
"""Check native scrolling on every product template without masking animation.

Static checks cover all RU/EN detail documents. Browser checks cover every RU
product and three EN representatives at desktop/mobile widths. --quick checks
three representatives per language; --all-languages opens every EN page too.
Prices and analytics are read-only fixtures; no published data is changed.
"""
from __future__ import annotations

import argparse
import functools
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import threading
import time
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPRESENTATIVE_SKUS = ("EL1036", "EL1052", "EL153")
PROBE = """(() => {
 window.__productScrollProbe={prevented:[]};
 const prevent=Event.prototype.preventDefault;
 Event.prototype.preventDefault=function(){
  if(['wheel','mousewheel','DOMMouseScroll','touchmove'].includes(this.type))
   window.__productScrollProbe.prevented.push(this.type);
  return prevent.call(this);
 };
})()"""
MEASURE = """() => {
 const texture=document.querySelector('img.ev-gallery-image[fetchpriority=high]') ||
  document.querySelector('[data-elem-id="1747407968428"] .tn-atom');
 const title=document.querySelector('h1');
 const header=document.getElementById('ev-global-header');
 const coordinate=e=>e?e.getBoundingClientRect().top+scrollY:null;
 return {y:scrollY,max:document.documentElement.scrollHeight-innerHeight,
  textureY:coordinate(texture),titleY:coordinate(title),
  header:header?{top:header.getBoundingClientRect().top,height:header.getBoundingClientRect().height,
   hidden:header.classList.contains('ev-header-hidden'),transform:getComputedStyle(header).transform}:null,
  behavior:getComputedStyle(document.documentElement).scrollBehavior,
  snap:getComputedStyle(document.documentElement).scrollSnapType,
  smoothScroll:typeof window.SmoothScroll,
  prevented:window.__productScrollProbe.prevented};
}"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def static_product(path):
    source = path.read_text(encoding="utf-8")
    problems = []
    class Tags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag == "html" and "ev-product-static" not in values.get("class", "").split():
                problems.append("missing ev-product-static class")
            if tag == "script" and re.search(r"SmoothScroll|tilda-zero-fixed", values.get("src") or "", re.I):
                problems.append("scroll/fixed runtime: " + values["src"])
            if values.get("data-animate-sbs-event") in {"scroll", "intoview"} or "data-animate-style" in values:
                problems.append("scroll/reveal animation attributes")
            if values.get("data-artboard-pos") == "fixed" or any(key.startswith("data-artboard-fixed") for key in values):
                problems.append("fixed artboard attributes")
            if "t-animate" in values.get("class", "").split():
                problems.append("reveal class remains")
    Tags().feed(source)
    if re.search(r"\bSmoothScroll\s*\(", source):
        problems.append("SmoothScroll initializer")
    if re.search(r"background-attachment\s*:\s*fixed", source, re.I):
        problems.append("fixed background CSS")
    return sorted(set(problems))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_deploy")
    parser.add_argument("--output", type=Path, default=ROOT / "buyer-qa/product-scroll")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--browser-executable")
    parser.add_argument("--url", help="Optional published origin for read-only browser checks")
    parser.add_argument("--expected-release", help="Optional deployed price-client revision")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--all-languages", action="store_true")
    args = parser.parse_args()
    site_dir, output = args.site_dir.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    summary = {"site_dir": str(site_dir), "checks": [], "fatal_error": None,
               "reduced_motion": "no-preference", "price_source": "deterministic fixture"}
    server = None

    def save():
        summary["passed"] = sum(row["status"] == "passed" for row in summary["checks"])
        summary["failed"] = sum(row["status"] == "failed" for row in summary["checks"])
        summary["duration_seconds"] = round(time.monotonic() - started, 2)
        summary["ok"] = not summary["failed"] and summary["fatal_error"] is None
        (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    def case(name, callback):
        row = {"name": name}
        try:
            row["details"] = callback()
            row["status"] = "passed"
        except Exception as error:
            row.update(status="failed", error=str(error), traceback=traceback.format_exc(limit=5))
        summary["checks"].append(row)
        save()

    try:
        details = sorted(site_dir.glob("catalog-*/*/*/index.html"))
        require(len(details) == 60, f"Expected 60 RU/EN product documents; found {len(details)}")
        products = json.loads((site_dir / "assets/products-data.json").read_text())
        by_sku = {product["sku"]: product for product in products}
        for path in details:
            route = path.relative_to(site_dir).as_posix()
            def check_static(path=path, route=route):
                problems = static_product(path)
                require(not problems, str(problems))
                return {"path": route}
            case("static: " + route, check_static)
        summary["static_product_documents"] = len(details)

        if args.url:
            base = args.url.rstrip("/")
        else:
            server = ThreadingHTTPServer(("127.0.0.1", args.port),
                functools.partial(QuietHandler, directory=str(site_dir)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{args.port}"
        summary["base_url"] = base
        rows = [{"c": [{"v": p["sku"]}, {"v": 65.66}, {"v": None}, {"v": None},
                        {"v": None}, {"v": 100}]} for p in products]
        feed = "window.EversensePriceFeed(" + json.dumps({"status": "ok", "table": {"rows": rows}}) + ");"
        ru_paths = [p["canonicalPath"] for p in products]
        if args.quick:
            ru_paths = [by_sku[sku]["canonicalPath"] for sku in REPRESENTATIVE_SKUS]
        en_paths = ["/" + path.parent.relative_to(site_dir).as_posix() + "/" for path in details
                    if path.relative_to(site_dir).parts[0] == "catalog-en"]
        if not args.all_languages:
            # Source pages declare their SKU in the same Tilda text element.
            en_paths = ["/" + path.parent.relative_to(site_dir).as_posix() + "/" for path in details
                if path.relative_to(site_dir).parts[0] == "catalog-en"
                and any(re.search(r">\s*" + sku + r"\s*<", path.read_text()) for sku in REPRESENTATIVE_SKUS)]
        paths = ru_paths + en_paths
        summary["browser_product_paths"] = paths

        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            launch = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            if args.url and os.environ.get("HTTPS_PROXY"):
                launch["proxy"] = {"server": os.environ["HTTPS_PROXY"], "bypass": "127.0.0.1,localhost"}
            browser = playwright.chromium.launch(**launch)
            for device, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844)]:
                options = {"viewport": {"width": width, "height": height}, "device_scale_factor": 1,
                           "locale": "ru-RU", "reduced_motion": "no-preference",
                           "is_mobile": device == "mobile", "has_touch": device == "mobile"}
                if device == "mobile":
                    options["user_agent"] = playwright.devices["Pixel 7"]["user_agent"]
                context = browser.new_context(**options)
                context.set_default_timeout(10000)
                context.add_init_script(PROBE)
                context.route("https://docs.google.com/spreadsheets/**/gviz/**", lambda route:
                    route.fulfill(status=200, content_type="application/javascript", body=feed))
                for pattern in ("https://mc.yandex.ru/**", "https://mc.yandex.com/**",
                                "https://static.tildacdn.com/js/tilda-stat-*.js"):
                    context.route(pattern, lambda route:
                        route.fulfill(status=200, content_type="application/javascript", body=""))
                page = context.new_page()
                errors, failures = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: failures.append({"url": response.url, "status": response.status})
                    if response.url.startswith(base + "/") and response.status >= 400
                    and not response.url.endswith("/favicon.ico") else None)
                for route in paths:
                    errors.clear()
                    failures.clear()
                    def check_browser(route=route):
                        response = page.goto(base + route, wait_until="domcontentloaded")
                        require(response and response.ok, "Product did not load")
                        page.wait_for_selector("#ev-global-header")
                        if args.expected_release:
                            src = page.locator('script[src*="assets/prices.js"]').first.get_attribute("src")
                            require(args.expected_release in src, "Unexpected deployed release: " + src)
                        page.wait_for_function("""() => {
                          const e=document.querySelector('img.ev-gallery-image[fetchpriority=high]')||document.querySelector('[data-elem-id="1747407968428"] .tn-atom');
                          if(!e)return false;const board=e.closest('.t396__artboard');
                          return e.getBoundingClientRect().width>0&&(!board||board.classList.contains('rendered'));
                        }""")
                        page.evaluate("""async()=>{await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,400))]);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}""")
                        if route in ru_paths[:1] + en_paths[:1]:
                            page.screenshot(path=str(output / (device + "-" + ("en" if "/catalog-en/" in route else "ru") + "-intro.png")))
                        page.evaluate("scrollTo(0,400)")
                        page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                        before = page.evaluate(MEASURE)
                        require(before["behavior"] == "auto" and before["snap"] == "none", "Non-native CSS scrolling: " + str(before))
                        require(before["smoothScroll"] == "undefined", "SmoothScroll runtime still present")
                        page.evaluate("window.__productScrollProbe.prevented=[]")
                        page.mouse.move(width - 20, height // 2)
                        page.mouse.wheel(0, 600)
                        page.wait_for_timeout(250)
                        settled = page.evaluate(MEASURE)
                        page.wait_for_timeout(100)
                        after = page.evaluate(MEASURE)
                        expected = min(before["max"], before["y"] + 600)
                        require(not after["prevented"], "Native scroll input was canceled: " + str(after["prevented"]))
                        require(abs(settled["y"] - expected) <= 2, f"Wheel did not scroll natively: start={before['y']}, expected={expected}, at250ms={settled['y']}")
                        require(abs(after["y"] - settled["y"]) <= 2, "Scroll keeps drifting after wheel input: " + str([settled["y"], after["y"]]))
                        for key in ("textureY", "titleY"):
                            require(before[key] is not None and abs(after[key] - before[key]) <= 2,
                                    "Content moves relative to document: " + key + " " + str([before[key], after[key]]))
                        header = after["header"]
                        require(header and header["height"] > 40, "Missing product header")
                        if device == "mobile":
                            require(header["hidden"] and header["top"] + header["height"] <= 0,
                                    "Mobile product header stayed onscreen: " + str(header))
                            page.mouse.wheel(0, -10)
                            page.wait_for_function("document.querySelector('#ev-global-header').getBoundingClientRect().top >= -1")
                        else:
                            require(abs(header["top"]) <= 2 and not header["hidden"],
                                    "Desktop product header moved: " + str(header))
                        pinned = page.locator("body *").evaluate_all("""els=>els.filter(e=>getComputedStyle(e).backgroundAttachment==='fixed').map(e=>e.outerHTML.slice(0,200))""")
                        require(not pinned, "Fixed/parallax background remains: " + str(pinned))
                        if route in ru_paths[:1] + en_paths[:1]:
                            page.evaluate("scrollTo(0,document.documentElement.scrollHeight)")
                            page.evaluate("()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
                            page.screenshot(path=str(output / (device + "-" + ("en" if "/catalog-en/" in route else "ru") + "-footer.png")))
                        require(not errors, "JavaScript errors: " + str(errors))
                        require(not failures, "Failed resources: " + str(failures))
                        return {"route": route, "wheel_from": before["y"], "wheel_at250ms": settled["y"],
                                "wheel_at350ms": after["y"], "prevented": after["prevented"],
                                "texture_document_y": [before["textureY"], after["textureY"]],
                                "header": header}
                    case(device + ": " + route, check_browser)
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
