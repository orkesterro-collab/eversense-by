#!/usr/bin/env python3
"""Read-only verification of public EVERSENSE price feed, as used by site JS."""
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json
import re
from pathlib import Path

SHEET = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY"
url = "https://docs.google.com/spreadsheets/d/" + SHEET + "/gviz/tq?" + urlencode({
    "tqx": "out:json;responseHandler:EversensePriceFeed",
    "sheet": "price", "headers": "1", "tq": "select A,C,D,E,F,G",
})
req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
with urlopen(req, timeout=35) as response:
    body = response.read(250000).decode("utf-8", "replace")
    print("PRICES public Google gviz HTTP:", response.status)
    print("PRICES content length:", len(body))
start = body.find("EversensePriceFeed(")
if start < 0:
    print("PRICES response prefix:", body[:250])
    raise RuntimeError("Public gviz callback missing: Google Sheet may not allow anonymous access")
payload = body[start + len("EversensePriceFeed("):].strip()
if payload.endswith(";"):
    payload = payload[:-1]
if not payload.endswith(")"):
    raise RuntimeError("Invalid gviz JSONP envelope")
data = json.loads(payload[:-1])
if data.get("status") != "ok":
    raise RuntimeError("Google gviz status: " + str(data.get("errors")))
table = data.get("table", {})
rows = table.get("rows", [])
price_rows = {}
sales = 0
for row in rows:
    cells = row.get("c") or []
    values = [(x or {}).get("v") for x in cells]
    sku = str(values[0] or "").strip().upper() if values else ""
    if re.fullmatch(r"EL\d{3,4}", sku):
        raw = values[1] if len(values) > 1 else None
        try:
            price = float(str(raw).replace(",", ".").strip())
        except (ValueError, TypeError):
            raise RuntimeError(f"Non-numeric regular price for {sku}: {raw!r}")
        if price <= 0:
            raise RuntimeError(f"Invalid regular price for {sku}")
        price_rows[sku] = price
        if len(values) > 2 and values[2] is not None:
            sales += 1
print(f"PRICES valid SKUs={len(price_rows)} sales_rows={sales}, sample EL1052={price_rows.get('EL1052')}")
if len(price_rows) != 30 or len(rows) < 30:
    raise RuntimeError(f"Expected 30 product prices, got {len(price_rows)}")
site_skus = {p.stem.upper() for p in Path("products").glob("EL*.html")}
if site_skus != set(price_rows):
    raise RuntimeError(f"SKU mismatch: absent in Google={sorted(site_skus-set(price_rows))}, absent on site={sorted(set(price_rows)-site_skus)}")
print("PRICES every one of the", len(site_skus), "individual product cards has a matching price row")
print("PASS: Public Google price feed is accessible to anonymous visitors with all 30 prices.")
