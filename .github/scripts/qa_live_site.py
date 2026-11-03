#!/usr/bin/env python3
"""Audit deployed Eversense pages and static assets at verified hoster.by IP."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path("_deploy")
HOST = "eversense.by"
IP = "87.232.64.108"
pages = sorted(ROOT.rglob("*.html"))
resources = [
    "assets/prices.js", "assets/prices.css", "assets/eversense.js",
    "assets/eversense.css", "assets/black-friday.js",
    "assets/black-friday-home.js", "assets/black-friday-home.css",
    "assets/img/forest-light.webp",
]
targets = []
for p in pages:
    rel = p.relative_to(ROOT).as_posix()
    if rel == "index.html":
        rel = ""
    elif rel.endswith("/index.html"):
        rel = rel[:-10]
    targets.append(("/" + rel, "page"))
for asset in resources:
    if (ROOT / asset).exists():
        targets.append(("/" + asset, "asset"))
def check(entry):
    path, typ = entry
    for attempt in range(2):
        proc = subprocess.run(
            ["curl", "-ksS", "-L", "--max-time", "22", "--resolve",
             f"{HOST}:443:{IP}", "-o", "/dev/null", "-w", "%{http_code}",
             "https://" + HOST + path],
            capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout.strip() == "200":
            return path, typ, "200"
        if attempt == 0:
            time.sleep(2)
    return path, typ, f"curl={proc.returncode}, http={proc.stdout.strip()}, err={proc.stderr[:100]}"
results = []
with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(check, t) for t in targets]
    for future in as_completed(futures):
        results.append(future.result())
bad = [r for r in results if r[2] != "200"]
print(f"LIVE_QA {HOST}: {len(pages)} HTML pages, {len(targets)-len(pages)} static assets, {len(bad)} errors", flush=True)
for path, typ, status in sorted(bad)[:80]:
    print(f"LIVE_QA BROKEN {typ} {path} => {status}", flush=True)
if bad:
    raise SystemExit(f"Live site has {len(bad)} failing paths")
print("PASS: every deployed HTML page and sampled CSS/JS/image URLs returned HTTP 200", flush=True)
