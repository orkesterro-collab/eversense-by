#!/usr/bin/env python3
"""Fix legacy root navigation only in the staged GitHub Pages project mirror."""
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

PREFIX = '/eversense-by'
HOST = 'orkesterro-collab.github.io'
ATTRIBUTE = re.compile(r'''(?P<head>(?P<name>[^\s"'<>/=]+)\s*=\s*)(?:(?P<quote>["'])(?P<quoted>.*?)(?P=quote)|(?P<unquoted>[^\s>]+))''', re.S)


def navigation_url(value, root):
    parsed = urlsplit(unescape(value))
    if parsed.scheme not in {'', 'http', 'https'} or (parsed.netloc and parsed.netloc != HOST):
        return value
    path = parsed.path
    if not path.startswith('/') or path == PREFIX or path.startswith(PREFIX + '/'):
        return value
    # Rewrite actual site routes only; leave unknown routes visible to audits.
    target = root / path.lstrip('/')
    if not target.is_file() and not (target / 'index.html').is_file():
        return value
    if target.is_dir() and not path.endswith('/'):
        path += '/'
    return escape(urlunsplit((parsed.scheme, parsed.netloc, PREFIX + path, parsed.query, parsed.fragment)), quote=True)


def rewrite(html, root):
    offsets, offset = [], 0
    for line in html.splitlines(keepends=True):
        offsets.append(offset)
        offset += len(line)
    changes = []
    def attribute(match):
        if match.group('name').lower() != 'href':
            return match.group(0)
        raw = match.group('quoted') if match.group('quote') else match.group('unquoted')
        new = navigation_url(raw, root)
        if new == raw:
            return match.group(0)
        quote = match.group('quote') or '"'
        return match.group('head') + quote + new + quote
    class Tags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() not in {'a', 'area'}:
                return
            raw = self.get_starttag_text()
            updated = ATTRIBUTE.sub(attribute, raw)
            if raw != updated:
                line, col = self.getpos()
                start = offsets[line - 1] + col
                changes.append((start, start + len(raw), updated))
    Tags(convert_charrefs=False).feed(html)
    for start, end, updated in reversed(changes):
        html = html[:start] + updated + html[end:]
    return html, len(changes)


def main():
    root = Path('_pages')
    if not (root / 'index.html').is_file():
        raise SystemExit('Stage the website in _pages first')
    count = 0
    for path in root.rglob('*.html'):
        original = path.read_text(encoding='utf-8')
        updated, changed = rewrite(original, root)
        if changed:
            path.write_text(updated, encoding='utf-8')
        count += changed
    print(f'PAGES: repaired {count} legacy navigation links; source and standalone host unchanged')


if __name__ == '__main__':
    main()
