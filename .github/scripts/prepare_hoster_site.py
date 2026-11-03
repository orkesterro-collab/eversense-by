#!/usr/bin/env python3
"""Prepare and audit the static Eversense site for its own hosting domain.

The original site snapshot was generated under a GitHub Pages project prefix
(/eversense-by/). Strip that prefix from copied HTML/media link references
before uploading to the standalone https://eversense.by domain.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, unquote
import json
import posixpath
import re

ROOT = Path("_deploy")
PREFIX = "/eversense-by/"
PAGES_HOST = "https://orkesterro-collab.github.io/eversense-by/"
DOMAINS = {"eversense.by", "www.eversense.by", "orkesterro-collab.github.io"}
TRANSFORM_EXTS = {".html", ".css", ".js", ".json", ".txt", ".xml"}


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


def main():
    files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() in TRANSFORM_EXTS]
    transformed = Counter()
    changed_html = []
    normalized_count = 0
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
    Path("site-changed-html.json").write_text(json.dumps(changed_html, ensure_ascii=False), encoding="utf-8")
    print("SITE_AUDIT unmatched_local_targets =", len(missing), flush=True)
    for path, count in missing.most_common(70):
        print(f"SITE_AUDIT unmatched ({count}): {path} | {sample[path]}", flush=True)
    result = {
        "pages": len(page_paths),
        "attributes_checked": checked,
        "rewritten_files_by_extension": dict(transformed),
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
