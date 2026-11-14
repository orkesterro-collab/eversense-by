#!/usr/bin/env python3
"""Prepare and audit the static Eversense site for its own hosting domain.

The original site snapshot was generated under a GitHub Pages project prefix
(/eversense-by/). Strip that prefix from copied HTML/media link references
before uploading to the standalone https://eversense.by domain.
"""
from collections import Counter
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, unquote, unquote_plus
import json
import os
import posixpath
import re

ROOT = Path("_deploy")
PREFIX = "/eversense-by/"
PAGES_HOST = "https://orkesterro-collab.github.io/eversense-by/"
DOMAINS = {"eversense.by", "www.eversense.by", "orkesterro-collab.github.io"}
TRANSFORM_EXTS = {".html", ".css", ".js", ".json", ".txt", ".xml"}
release_revision = os.environ.get("GITHUB_SHA", "20261110b")[:12]
RELEASE_ASSETS = {
    "/assets/prices.js", "/assets/prices.css", "/assets/unified-header.js", "/assets/unified-header.css",
    "/assets/buyer.js", "/assets/buyer.css", "/assets/buyer-core.js", "/assets/products-data.js",
    "/assets/explore-guides.css", "/assets/explore-product.css", "/assets/explore-product.js",
    "/assets/explore-interiors.css", "/assets/explore-interiors.js",
    "/assets/home-senses.css", "/assets/home-senses.js",
    "/assets/home-footer.css",
    "/assets/installation-guides.css",
}


class Resources(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value and key in {"href", "src", "action", "poster", "data-original", "data-src"}:
                self.links.append((key, value))


def resolve(source, url):
    url = url.strip()
    if not url or url[0] in "#?" or url.lower().startswith(("mailto:", "tel:", "data:", "javascript:", "blob:", "//")):
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in {"", "http", "https"}:
        return None
    if parsed.netloc and parsed.netloc not in DOMAINS:
        return None
    if parsed.netloc == "orkesterro-collab.github.io":
        # Any old project links should have been rewritten before analysis.
        return "__old_github_pages_origin__"
    path = unquote(parsed.path)
    if not path:
        return None
    if path.startswith("/"):
        route = posixpath.normpath(path).lstrip("/")
    else:
        rel = source.parent.relative_to(ROOT).as_posix()
        route = posixpath.normpath(posixpath.join(rel, path))
    if route == ".":
        route = ""
    if route.startswith("../"):
        return route
    candidate = ROOT / route
    if (candidate.is_file() or (candidate / "index.html").is_file()):
        return None
    # Some routes are dynamically rendered by the original Tilda frontend.
    return route


def normalize_directory_link(raw, source, route_paths):
    parsed = urlsplit(raw)
    host = parsed.netloc.lower()
    if host and host not in {"eversense.by", "www.eversense.by"}:
        return raw
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return raw
    route = parsed.path
    if not route:
        return raw
    if route.startswith("/"):
        normalized = posixpath.normpath(route)
    else:
        base = "/" + source.parent.relative_to(ROOT).as_posix().lstrip("./")
        normalized = posixpath.normpath(posixpath.join(base, route))
    if normalized not in route_paths or route.endswith("/"):
        return raw
    route = route + "/"
    scheme = "https" if host else parsed.scheme
    return urlunsplit((scheme, parsed.netloc, route, parsed.query, parsed.fragment))


def rewrite_directory_hrefs(html, source, route_paths):
    href = re.compile(r"""(?P<head>\b(?:href|action)\s*=\s*)(?P<quote>["'])(?P<value>[^"']+)(?P=quote)""", re.I)
    count = 0
    def change(match):
        nonlocal count
        old = match.group("value")
        new = normalize_directory_link(old, source, route_paths)
        if new != old:
            count += 1
        return match.group("head") + match.group("quote") + new + match.group("quote")
    return href.sub(change, html), count


def version_asset_url(raw, source):
    """Only version the named local assets, preserving URL paths and fragments."""
    parsed = urlsplit(unescape(raw))
    if parsed.scheme not in {"", "http", "https"}:
        return raw
    if parsed.netloc and parsed.netloc.lower() not in {"eversense.by", "www.eversense.by"}:
        return raw
    if not parsed.path:
        return raw
    path = unquote(parsed.path)
    if path.startswith("/"):
        normalized = posixpath.normpath(path)
    else:
        base = "/" + source.parent.relative_to(ROOT).as_posix().lstrip("./")
        normalized = posixpath.normpath(posixpath.join(base, path))
    if normalized not in RELEASE_ASSETS:
        return raw
    # Keep unrelated query parameters byte-for-byte; replace any existing v.
    query = [part for part in parsed.query.split("&")
             if part and unquote_plus(part.split("=", 1)[0]) != "v"]
    query.append("v=" + release_revision)
    updated = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "&".join(query), parsed.fragment))
    return escape(updated, quote=True)


def rewrite_asset_versions(html, source):
    # Parse real tags so data-src, inline script strings and attribute contents
    # resembling another attribute are never mistaken for href/src.
    attribute = re.compile(r"""(?P<head>(?P<name>[^\s"'<>/=]+)\s*=\s*)(?:(?P<quote>["'])(?P<quoted>.*?)(?P=quote)|(?P<unquoted>[^\s>]+))""", re.I | re.S)
    count = 0
    def change(match):
        nonlocal count
        if match.group("name").lower() not in {"href", "src"}:
            return match.group(0)
        old = match.group("quoted") if match.group("quote") else match.group("unquoted")
        new = version_asset_url(old, source)
        if new != old:
            count += 1
            quote = match.group("quote") or '"'
            return match.group("head") + quote + new + quote
        return match.group(0)
    offsets = []
    offset = 0
    for line in html.splitlines(keepends=True):
        offsets.append(offset)
        offset += len(line)
    replacements = []
    class AssetTags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if not any(key in {"href", "src"} for key, _ in attrs):
                return
            raw_tag = self.get_starttag_text()
            updated_tag = attribute.sub(change, raw_tag)
            if updated_tag != raw_tag:
                line, column = self.getpos()
                start = offsets[line - 1] + column
                replacements.append((start, start + len(raw_tag), updated_tag))
    parser = AssetTags(convert_charrefs=False)
    parser.feed(html)
    for start, end, tag in reversed(replacements):
        html = html[:start] + tag + html[end:]
    return html, count


def version_dynamic_loaders(script, path):
    if path == "assets/prices.js":
        return re.sub(r"(unified-header\.js\?v=)[^\"'#&\s]+",
                      lambda match: match.group(1) + release_revision, script)
    if path == "assets/unified-header.js":
        return re.sub(r"""(\bvar\s+version\s*=\s*)(["'])[^"']*\2""",
                      lambda match: match.group(1) + match.group(2) + release_revision + match.group(2),
                      script, count=1)
    return script


def main():
    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in TRANSFORM_EXTS]
    transformed = Counter()
    changed_html = []
    normalized_count = 0
    versioned_count = 0
    directories = {"/" + p.parent.relative_to(ROOT).as_posix() for p in ROOT.rglob("index.html")
                   if p.parent != ROOT}
    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        updated = raw.replace(PAGES_HOST, "/").replace(PREFIX, "/")
        # Correct a renamed collection that is linked in the original home page.
        updated = updated.replace("/catalog-ru/silent-luxury-ru", "/catalog-ru/quiet-luxury-ru")
        # Tilda source has two phone-number hrefs without the tel: URI scheme.
        updated = re.sub(r"""href=(["'])(\+\d{10,15})\1""",
                         lambda m: "href=" + m.group(1) + "tel:" + m.group(2) + m.group(1),
                         updated)
        if p.suffix.lower() == ".html":
            updated, changed_links = rewrite_directory_hrefs(updated, p, directories)
            normalized_count += changed_links
            updated, changed_versions = rewrite_asset_versions(updated, p)
            versioned_count += changed_versions
        elif p.suffix.lower() == ".js":
            updated = version_dynamic_loaders(updated, p.relative_to(ROOT).as_posix())
        if updated != raw:
            if p.suffix.lower() == ".html":
                changed_html.append(p.relative_to(ROOT).as_posix())
            transformed[p.suffix.lower()] += 1
            p.write_text(updated, encoding="utf-8")
        if PREFIX in updated:
            raise RuntimeError(f"Legacy /eversense-by/ route remains in {p}")
    page_paths = sorted(ROOT.rglob("*.html"))
    missing = Counter()
    sample = {}
    checked = 0
    for path in page_paths:
        parser = Resources()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        for key, url in parser.links:
            checked += 1
            problem = resolve(path, url)
            if problem:
                missing[problem] += 1
                sample.setdefault(problem, str(path.relative_to(ROOT)) + " -> " + url[:130])
    print("SITE_AUDIT page_count =", len(page_paths), flush=True)
    print("SITE_AUDIT attributes_checked =", checked, flush=True)
    print("SITE_AUDIT transformed_files =", dict(transformed), flush=True)
    print("SITE_AUDIT normalized_directory_links =", normalized_count, flush=True)
    print("SITE_AUDIT release_revision =", release_revision, flush=True)
    print("SITE_AUDIT versioned_asset_links =", versioned_count, flush=True)
    Path("site-changed-html.json").write_text(json.dumps(changed_html, ensure_ascii=False), encoding="utf-8")
    print("SITE_AUDIT unmatched_local_targets =", len(missing), flush=True)
    for path, count in missing.most_common(70):
        print(f"SITE_AUDIT unmatched ({count}): {path} | {sample[path]}", flush=True)
    result = {
        "pages": len(page_paths),
        "attributes_checked": checked,
        "rewritten_files_by_extension": dict(transformed),
        "release_revision": release_revision,
        "versioned_asset_links": versioned_count,
        "unmatched_local_targets": dict(missing),
        "examples": sample,
    }
    Path("site-audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if missing:
        raise RuntimeError(f"Broken local links remain: {len(missing)} distinct paths")
    if not (ROOT / "catalog-ru/index.html").is_file():
        raise RuntimeError("Russian catalog is missing")
    if not (ROOT / "catalog.html").is_file():
        raise RuntimeError("Local catalog fallback is missing")
    if not (ROOT / "assets/prices.js").is_file():
        raise RuntimeError("Google Sheets price client is missing")
    if not (ROOT / "products/EL1000.html").is_file():
        raise RuntimeError("Product page missing")
    print("SITE_AUDIT: required catalog, price script and product pages present", flush=True)


if __name__ == "__main__":
    main()
