#!/usr/bin/env python3
"""Verify public Google Sheets partner feed without editing the workbook."""
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json
import re

SHEET = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY"
params = urlencode({
    "sheet": "partners",
    "headers": "1",
    "tq": "select A,B,C,D,E,F,G,H,I,J,K,L,M",
    "tqx": "out:json;responseHandler:EversensePartnersFeed",
})
url = "https://docs.google.com/spreadsheets/d/" + SHEET + "/gviz/tq?" + params
with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=35) as response:
    body = response.read(300000).decode("utf-8", "replace")
    print("Partners gviz HTTP:", response.status, flush=True)
start = body.find("EversensePartnersFeed(")
if start < 0:
    raise SystemExit("Public Google Sheets partners JSONP callback unavailable: " + body[:150])
data = body[start + len("EversensePartnersFeed("):].strip()
if data.endswith(";"):
    data = data[:-1]
if not data.endswith(")"):
    raise SystemExit("Malformed JSONP response")
payload = json.loads(data[:-1])
if payload.get("status") != "ok":
    raise SystemExit("Google Sheets gviz status: " + str(payload.get("errors")))
rows = payload.get("table", {}).get("rows", [])
def val(row, i):
    cell = (row.get("c") or [])[i]
    return cell.get("v") if cell else None
partners = []
for row in rows:
    cells = row.get("c") or []
    if len(cells) < 13:
        continue
    if not str(val(row, 0) or "").strip():
        continue
    partners.append([val(row, i) for i in range(13)])
minsk = [p for p in partners if p[2] == "Минск"]
other = [p for p in partners if p[2] != "Минск"]
cities = sorted({p[2] for p in other})
from collections import Counter
counts = Counter(p[2] for p in other)
assert len(partners) == 40, "Expected 40 demo partners"
assert len(minsk) == 10 and len(other) == 30, "Expected 10 Minsk + 30 regional partners"
assert len(cities) == 15 and all(n == 2 for n in counts.values()), "Expected 15 cities with two demo partners each"
assert len(set(p[0] for p in partners)) == len(partners), "Partner IDs are not unique"
assert all(isinstance(p[1], (int, float)) for p in partners), "sort_order must be numeric"
assert all(p[11] is True and p[12] is True for p in partners), "Expected active demo flags"
assert all(isinstance(p[9], (int,float)) and isinstance(p[10], (int,float)) for p in partners), "Invalid coordinates"
print("PASS public partners feed:", len(partners), "records;", len(minsk), "Minsk;",
      len(other), "other cities;", len(cities), "regional cities", flush=True)
