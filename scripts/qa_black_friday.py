#!/usr/bin/env python3
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT="https://orkesterro-collab.github.io/eversense-by/"
out=Path("black-friday-qa");out.mkdir(exist_ok=True)
checks=[]
with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,args=["--no-sandbox","--disable-dev-shm-usage"])
  for label,width,height in [("desktop",1440,900),("mobile",390,844)]:
    page=browser.new_page(viewport={"width":width,"height":height},ignore_https_errors=True)
    home=page.goto(ROOT,wait_until="domcontentloaded",timeout=60000)
    page.wait_for_selector("#rec1028545506 .ev-bf-home",timeout=25000)
    hero=page.locator("#rec1028545506 .ev-bf-home")
    assert hero.count()==1,"Missing replacement banner"
    assert hero.is_visible(),"First slide is not visible"
    button=hero.get_by_role("link",name="Смотреть акцию")
    assert button.count()==1 and button.get_attribute("href")=="/eversense-by/black-friday/"
    page.screenshot(path=str(out/f"homepage-{label}.png"),animations="disabled",timeout=30000)
    response=page.goto(ROOT+"black-friday/",wait_until="domcontentloaded",timeout=60000)
    page.wait_for_selector(".bf-card",timeout=20000)
    assert response.status==200,response.status
    assert page.locator(".bf-card").count()==10
    for c in page.locator(".bf-card").all():
      assert (c.get_attribute("data-promo-sku") or "").startswith("EL")
      href=c.locator(".bf-card__link").get_attribute("href")
      assert href.startswith("../catalog-ru/") and href.endswith("-ru/"),href
    cta=page.get_by_role("link",name="Посмотреть вживую")
    assert cta.count()==1 and cta.get_attribute("href")=="../where-to-buy.html"
    assert not page.get_by_role("link",name="Связаться").count()
    page.screenshot(path=str(out/f"landing-{label}.png"),animations="disabled",timeout=30000)
    checks.append({"device":label,"width":width,"home_status":home.status,"landing_status":response.status,"cards":10,"cta_href":cta.get_attribute("href"),"images_loaded":page.evaluate("([...document.querySelectorAll('.bf-card img')]).filter(i=>i.complete&&i.naturalWidth>0).length")})
    print(json.dumps(checks[-1],ensure_ascii=False),flush=True)
    page.close()
  browser.close()
(out/"results.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS branded Black Friday slider and retail page")
