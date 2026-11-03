#!/usr/bin/env python3
"""Verify sale-price rendering without inserting any fictional prices into Google Sheets."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT="https://orkesterro-collab.github.io/eversense-by"
PRODUCT=ROOT+"/catalog-ru/quiet-luxury-ru/natural-victoria-oak-ru/"
CATALOG=ROOT+"/catalog-ru/"
Path("price-qa").mkdir(exist_ok=True)
fixture=lambda end, start=None:{"status":"ok","table":{"rows":[{"c":[{"v":"EL1052"},{"v":120},{"v":95},{"v":end},{"v":start}]}]}}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
    for label,width in [("desktop",1440),("mobile",390)]:
        page=browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
        # The real asynchronous Google request must not overwrite deterministic QA fixtures.
        page.route("**/gviz/tq?**",lambda route: route.abort())
        page.goto(PRODUCT,wait_until="domcontentloaded",timeout=60000)
        page.wait_for_function("typeof EversensePriceFeed==='function' && !!document.querySelector('h2.tn-atom')",timeout=30000)
        page.evaluate("(value)=>EversensePriceFeed(value)",fixture("Date(2027,7,1)"))
        page.wait_for_selector("#ev-product-price .ev-price-sale",timeout=10000)
        data=page.locator("#ev-product-price").evaluate("""el=>({
            text:el.innerText,del:!!el.querySelector('del'),struck:el.querySelector('del')?getComputedStyle(el.querySelector('del')).textDecorationLine:'',width:el.getBoundingClientRect().width
        })""")
        assert "120,00" in data["text"] and "95,00" in data["text"] and "до 1.08" in data["text"], data
        assert data["del"] and "line-through" in data["struck"], data
        page.screenshot(path=f"price-qa/product-sale-{label}.png",animations="disabled",full_page=False)
        # After an expired promotion, only the regular price remains.
        page.evaluate("(value)=>EversensePriceFeed(value)",fixture("Date(2025,7,1)"))
        expired=page.locator("#ev-product-price").inner_text()
        assert "120,00" in expired and "95,00" not in expired and "до " not in expired, expired
        # A future promotion must not appear before its start date.
        page.evaluate("(value)=>EversensePriceFeed(value)",fixture("Date(2999,7,1)","Date(2999,0,1)"))
        upcoming=page.locator("#ev-product-price").inner_text()
        assert "120,00" in upcoming and "95,00" not in upcoming and "до " not in upcoming, upcoming
        print(label,"PRODUCT OK",json.dumps(data,ensure_ascii=False),"expired=",expired,"upcoming=",upcoming)
        page.close()
    page=browser.new_page(viewport={"width":1440,"height":900})
    page.route("**/gviz/tq?**",lambda route: route.abort())
    page.goto(CATALOG,wait_until="domcontentloaded",timeout=60000)
    page.wait_for_function("typeof EversensePriceFeed==='function' && [...document.querySelectorAll('.tn-atom')].some(n=>n.textContent.trim()==='EL1052')",timeout=30000)
    page.evaluate("(value)=>EversensePriceFeed(value)",fixture("Date(2027,7,1)"))
    page.wait_for_function("document.querySelectorAll('.ev-price-box--tile .ev-price-sale').length>0",timeout=10000)
    count=page.locator(".ev-price-box--tile .ev-price-sale").count()
    print("CATALOG OK",count,"price badge(s) for EL1052")
    page.screenshot(path="price-qa/catalog-sale-desktop.png",animations="disabled",full_page=False)
    page.close()
    browser.close()
print("PASS all pricing UI assertions")
