#!/usr/bin/env python3
import json,os,time
from pathlib import Path
from playwright.sync_api import sync_playwright

sites={
 'original':'https://ever-home.ru/',
 'belarus':'https://orkesterro-collab.github.io/eversense-by/'
}
Path('screenshots').mkdir(exist_ok=True)
checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 for site,url in sites.items():
  for device,width,height in [('desktop',1440,900),('mobile',390,844)]:
   page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1,ignore_https_errors=True)
   errors=[];failed=[]
   page.on('pageerror',lambda e:errors.append(str(e)[:200]))
   page.on('requestfailed',lambda r:failed.append(str(r.url)[:200]))
   response=None;gerror=None
   try:
    response=page.goto(url,wait_until='domcontentloaded',timeout=55000)
    page.wait_for_timeout(3500)
    page.screenshot(path=f'screenshots/{site}-{device}.png',full_page=False,animations='disabled',timeout=45000)
    d=page.evaluate('''() => ({title:document.title, bodyWidth:document.body.scrollWidth,windowWidth:innerWidth, viewportHeight:innerHeight, h1:document.querySelector('h1')?.innerText.slice(0,100), images:document.images.length,imagesLoaded:[...document.images].filter(x=>x.complete && x.naturalWidth>0).length, blockCount:document.querySelectorAll('.t-rec').length, resourceCount:performance.getEntriesByType('resource').length, videoCount:document.querySelectorAll('video').length, styleCount:document.styleSheets.length})''')
   except Exception as e:gerror=str(e);d={}
   row=dict(site=site,device=device,url=url,http_status=response.status if response else None,metrics=d,page_errors=errors[:30],failed_requests=failed[:30],error=gerror)
   checks.append(row)
   print(json.dumps(row,ensure_ascii=False),flush=True)
   page.close()
 browser.close()
Path('screenshots/qa.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')