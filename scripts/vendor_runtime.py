#!/usr/bin/env python3
"""Vendor the site's existing runtime without rebuilding or changing HTML.

Uses the captured originals where available, retaining Tilda's canonical
filenames for its optional dependency loader. Gzip-encoded captured responses
are decoded before serving as ordinary .js/.css files. Existing output is
reused; --refresh explicitly fetches current upstream versions.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content/runtime-assets.json"
VENDOR = ROOT / "assets/vendor"
FONT_URL = "https://fonts.googleapis.com/css2?family=Manrope:wght@300..800&display=swap"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
TILDA_HOSTS = {"static.tildacdn.com", "neo.tildacdn.com"}
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)
OPTIONAL_JS = {
    "tilda-errors-1.0.min.js", "tilda-forms-custommask-1.0.min.js",
    "tilda-undercut-1.0.min.js", "tilda-calc-1.0.min.js",
    "tilda-conditional-form-1.0.min.js", "tilda-date-picker-1.0.min.js",
    "tilda-img-select-1.0.min.js", "tilda-phone-mask-1.1.min.js",
    "tilda-range-1.0.min.js", "tilda-upwidget-1.1.min.js",
    "uploadcare-3.x.full.min.js", "uploadcare-3.x.min.js",
}
OPTIONAL_CSS = {
    "tilda-date-picker-1.0.min.css", "tilda-img-select-1.0.min.css",
    "tilda-range-1.0.min.css", "tilda-zero-form-errorbox.min.css",
    "tilda-zero-form-horizontal.min.css",
}


def fetch(url: str) -> bytes:
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location",
         "--compressed", "--retry", "2", "--max-time", "40",
         "--user-agent", UA, url],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout


def decoded(data: bytes) -> bytes:
    return gzip.decompress(data) if data.startswith(b"\x1f\x8b") else data


def local_path(url: str) -> Path:
    parsed = urlsplit(url)
    if parsed.hostname in TILDA_HOSTS:
        if Path(parsed.path).suffix.lower() in {".png", ".svg", ".ico"}:
            filename = hashlib.sha256(url.encode()).hexdigest()[:12] + "-" + Path(parsed.path).name
            return VENDOR / "icons" / filename
        # Preserve /js/ and /css/ alongside one another: zero-forms derives its
        # dependency root from the URL of its own script.
        return VENDOR / "tilda" / parsed.path.lstrip("/")
    if parsed.hostname == "fonts.gstatic.com":
        return VENDOR / "fonts" / Path(parsed.path).name
    if parsed.hostname == "fonts.googleapis.com":
        return VENDOR / "fonts/manrope.css"
    suffix = Path(parsed.path).suffix
    return VENDOR / (hashlib.sha256(url.encode()).hexdigest()[:12] + suffix)


def public_path(path: Path) -> str:
    return "/" + path.relative_to(ROOT).as_posix()


def discover() -> set[str]:
    urls = set()
    for page in ROOT.rglob("*.html"):
        rel = page.relative_to(ROOT)
        if rel.parts[0] in {".git", "reference", "_deploy", "_pages", "buyer-qa"}:
            continue
        source = page.read_text(encoding="utf-8")
        class IconLinks(HTMLParser):
            def handle_starttag(self, tag, pairs):
                attrs = dict(pairs)
                if tag != "link" or "icon" not in attrs.get("rel", "").lower():
                    return
                url = html.unescape(attrs.get("href", ""))
                if url.startswith("//"):
                    url = "https:" + url
                if urlsplit(url).hostname in TILDA_HOSTS:
                    urls.add(url)
        IconLinks().feed(source)
        for raw in re.findall(r"(?:src|href)\s*=\s*['\"]((?:https?:)?//[^'\"<>]+)", source):
            url = html.unescape(raw)
            if url.startswith("//"):
                url = "https:" + url
            host = urlsplit(url).hostname
            if (host in TILDA_HOSTS and urlsplit(url).path.endswith((".css", ".js"))
                    and "tilda-stat" not in url):
                urls.add(url)
            elif host == "fonts.googleapis.com" and "family=Manrope" in url:
                urls.add(url)
    # A later regeneration can start from pages already using local paths.
    if MANIFEST.exists():
        urls.update(json.loads(MANIFEST.read_text()))
    return urls


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    capture = json.loads((ROOT / "reference/original-media-manifest.json").read_text())
    originals = {row["url"]: ROOT / row["local"] for row in capture["files"] if row.get("local")}
    urls = discover()
    font_aliases = {url for url in urls if urlsplit(url).hostname == "fonts.googleapis.com"}
    urls.difference_update(font_aliases)
    urls.update("https://static.tildacdn.com/js/" + name for name in OPTIONAL_JS)
    urls.update("https://static.tildacdn.com/css/" + name for name in OPTIONAL_CSS)
    urls.add("https://neo.tildacdn.com/js/tilda-fallback-advanced-1.0.min.js")

    def save(url: str) -> tuple[str, str]:
        target = local_path(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not args.refresh:
            return url, public_path(target)
        original = originals.get(url)
        # Captured PNG photos were converted to WebP. Icons must keep their
        # original format, especially PNG apple-touch-icon links.
        if original and original.suffix.lower() != target.suffix.lower():
            original = None
        data = decoded(original.read_bytes()) if original and not args.refresh else fetch(url)
        target.write_bytes(data)
        return url, public_path(target)

    with ThreadPoolExecutor(max_workers=6) as pool:
        manifest = dict(pool.map(save, sorted(urls)))

    # One variable font serves every weight requested by both Tilda and buyer
    # pages. Keep Google's unicode ranges so the browser downloads only the
    # subsets actually used, with swap to make text visible immediately.
    font_target = local_path(FONT_URL)
    if args.refresh or not font_target.exists():
        css = fetch(FONT_URL).decode("utf-8")
        font_urls = sorted(set(m.group(2) for m in CSS_URL.finditer(css)))
        with ThreadPoolExecutor(max_workers=6) as pool:
            manifest.update(pool.map(save, font_urls))
        css = CSS_URL.sub(lambda m: 'url("' + os.path.relpath(local_path(m.group(2)), font_target.parent).replace(os.sep, "/") + '")', css)
        font_target.parent.mkdir(parents=True, exist_ok=True)
        font_target.write_text(css, encoding="utf-8")
    for url in font_aliases | {FONT_URL}:
        manifest[url] = public_path(font_target)

    # CSS image/font dependencies are resolved against the original upstream
    # URL, then referenced relative to the vendored CSS file.
    for url, local in sorted(manifest.copy().items()):
        target = ROOT / local.lstrip("/")
        if target.suffix != ".css" or target == font_target:
            continue
        source = target.read_text(encoding="utf-8")
        def localize(match: re.Match) -> str:
            reference = match.group(2)
            if reference.startswith(("data:", "#")):
                return match.group(0)
            if not urlsplit(reference).scheme and not reference.startswith("//") and (target.parent / reference).is_file():
                return match.group(0)
            absolute = urljoin(url, reference)
            if urlsplit(absolute).hostname not in TILDA_HOSTS | {"fonts.gstatic.com"}:
                return match.group(0)
            _, path = save(absolute)
            manifest[absolute] = path
            relative = os.path.relpath(ROOT / path.lstrip("/"), target.parent).replace(os.sep, "/")
            return 'url("' + relative + '")'
        result = CSS_URL.sub(localize, source)
        if result != source:
            target.write_text(result, encoding="utf-8")

    license_path = VENDOR / "fonts/OFL.txt"
    if not license_path.exists():
        license_path.write_bytes(fetch("https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/OFL.txt"))
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    files = {ROOT / local.lstrip("/") for local in manifest.values()}
    print(f"Vendored {len(files)} files ({sum(p.stat().st_size for p in files):,} bytes); {len(manifest)} URL mappings")


if __name__ == "__main__":
    main()
