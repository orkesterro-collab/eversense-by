#!/usr/bin/env python3
"""Optimize generated HTML without reserializing Tilda's scripts or layout.

Run after page generators. Deployment preparation also runs this pass so a
regenerated page retains local dependencies, responsive images and lazy video.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape, unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HOMES = {'index.html', 'ru/index.html', 'en/index.html'}
PNG_NAMES = ('1-overlay-corundum-v2', '1-overlay-corundum-v3',
             '2-decor-brown-casella-v2', '3-hdf-core-v2')
CARD_SIZES = '(max-width: 640px) calc(100vw - 40px), (max-width: 1050px) calc((100vw - 64px) / 2), 400px'


def relative_url(target, page):
    return posixpath.relpath(target.lstrip('/'), posixpath.dirname(page) or '.')


def local_path(url, page):
    parsed = urlsplit(unescape(url))
    if parsed.netloc and parsed.netloc not in {'eversense.by', 'www.eversense.by', 'orkesterro-collab.github.io'}:
        return None
    if parsed.scheme not in {'', 'https', 'http'}:
        return None
    path = unquote(parsed.path)
    if path.startswith('/eversense-by/'):
        path = path[len('/eversense-by'):]
    if path.startswith('/'):
        return path
    return '/' + posixpath.normpath(posixpath.join(posixpath.dirname(page), path))


def tag_html(tag, attrs):
    return '<' + tag + ''.join(' ' + key if value is None else
        ' ' + key + '="' + escape(value, quote=True) + '"' for key, value in attrs.items()) + '>'


def optimize_html(source, page, runtime, responsive, video_manifest):
    counts = Counter()
    # These four layer photographs used lossless PNG for photographic content.
    for name in PNG_NAMES:
        source = source.replace(name + '.png', name + '.webp')
    video_edits = 0

    def video(match):
        nonlocal video_edits
        block = match.group(0)
        if 'data-ev-lazy-video' in block:
            return block
        src = re.search(r'<source\b[^>]*\bsrc=(["\'])(.*?)\1', block, re.I | re.S)
        if not src:
            return block
        key = (local_path(src[2], page) or '').lstrip('/')
        delivery = video_manifest.get(key)
        if not delivery:
            return block
        attrs = {}
        class VideoTag(HTMLParser):
            def handle_starttag(self, tag, pairs):
                if tag == 'video':
                    attrs.update(pairs)
        VideoTag().feed(block[:block.index('>') + 1])
        attrs.pop('autoplay', None)
        if attrs.get('id') == 'vid':
            attrs.pop('id')  # The original duplicated this ID on both videos.
        attrs.update({'preload': 'none', 'data-ev-lazy-video': '',
                      'poster': relative_url(delivery['poster'], page)})
        block = tag_html('video', attrs) + block[block.index('>') + 1:]
        block = re.sub(r'(<source\b[^>]*?)\bsrc=(["\'])(.*?)\2',
            lambda m: m[1] + 'data-ev-src="' + escape(relative_url(delivery['video'], page), quote=True) + '"',
            block, count=1, flags=re.I | re.S)
        fallback = relative_url(delivery['video'], page)
        block += '<noscript><a href="' + escape(fallback, quote=True) + '">Смотреть видео</a></noscript>'
        video_edits += 1
        return block

    source = re.sub(r'<video\b[^>]*>.*?</video>', video, source, flags=re.I | re.S)
    counts['lazy_videos'] = video_edits
    offsets, position = [], 0
    for line in source.splitlines(keepends=True):
        offsets.append(position)
        position += len(line)
    edits = []
    noscript_backgrounds = []

    class Optimizer(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.scripts = set()
            self.styles = set()
            self.pending_script = None
            self.record = None
            self.records = []
            self.has_media_runtime = False

        def at(self):
            line, column = self.getpos()
            return offsets[line - 1] + column

        def handle_starttag(self, tag, pairs):
            raw = self.get_starttag_text()
            attrs = dict(pairs)
            original = attrs.copy()
            start = self.at()
            recid = attrs.get('id', '')
            if re.fullmatch(r'rec\d+', recid):
                self.record = recid
                self.records.append(recid)
            eager = self.record in self.records[:10]
            # Preserve synchronous jQuery/polyfill ordering: old inline code
            # calls these functions during HTML parsing.
            for key in ('src', 'href'):
                url = attrs.get(key, '')
                if url in runtime:
                    attrs[key] = relative_url(runtime[url], page)
                    counts['local_dependencies'] += 1
            if tag == 'script' and attrs.get('src'):
                url = attrs['src']
                if 'tilda-fallback-1.0.min.js' in url or url in self.scripts:
                    self.pending_script = start
                    counts['removed_scripts'] += 1
                    return
                self.scripts.add(url)
                if 'assets/performance.js' in url:
                    self.has_media_runtime = True
            if tag == 'link':
                rel = attrs.get('rel', '').lower()
                url = attrs.get('href', '')
                if rel == 'stylesheet':
                    if url in self.styles:
                        edits.append((start, start + len(raw), ''))
                        counts['removed_styles'] += 1
                        return
                    self.styles.add(url)
                if rel in {'dns-prefetch', 'preconnect'} and any(host in url for host in
                        ('tildacdn.com', 'fonts.googleapis.com', 'fonts.gstatic.com')):
                    edits.append((start, start + len(raw), ''))
                    return
            if tag == 'img':
                src = attrs.get('src', '')
                path = local_path(src, page)
                item = responsive.get(path)
                if item:
                    candidates = [(row['width'], relative_url(row['path'], page)) for row in item['variants']]
                    candidates.append((item['source_width'], src))
                    attrs['srcset'] = ', '.join(f'{url} {width}w' for width, url in candidates)
                    # Gallery details keep their full-size source. Catalog
                    # cards choose an appropriately small file on each screen.
                    if 'ev-gallery-image' in attrs.get('class', '').split():
                        attrs['sizes'] = '100vw'
                    attrs.setdefault('sizes', CARD_SIZES if 'ev-card' in attrs.get('class', '') or attrs.get('width') == '640'
                                     else '(max-width: 960px) 100vw, 900px')
                    counts['responsive_images'] += 1
                if page in HOMES and not eager:
                    attrs.setdefault('loading', 'lazy')
                attrs.setdefault('decoding', 'async')
            if page in HOMES and not eager and tag in {'div', 'a'}:
                classes = attrs.get('class', '').split()
                url = None
                if 't-bgimg' in classes and attrs.get('data-original'):
                    url = attrs['data-original']
                style = attrs.get('style', '')
                background = re.search(r'background-image\s*:\s*url\((.*?)\)\s*;?', style, re.I)
                if background:
                    url = background[1].strip('"\' ')
                if url and local_path(url, page):
                    attrs.pop('data-original', None)
                    attrs['class'] = ' '.join(x for x in classes if x != 't-bgimg')
                    if background:
                        attrs['style'] = style[:background.start()] + style[background.end():]
                    attrs['data-ev-background'] = url
                    # No-JavaScript visitors still see the original media.
                    selector = '[data-ev-background="' + url.replace('"', '\\"') + '"]'
                    noscript_backgrounds.append(selector + '{background-image:url(' + json.dumps(url) + ')!important}')
                    counts['lazy_backgrounds'] += 1
            if attrs != original:
                edits.append((start, start + len(raw), tag_html(tag, attrs)))

        def handle_endtag(self, tag):
            if tag == 'script' and self.pending_script is not None:
                end = source.find('>', self.at()) + 1
                edits.append((self.pending_script, end, ''))
                self.pending_script = None

    parser = Optimizer()
    parser.feed(source)
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    if (video_edits or noscript_backgrounds or 'data-ev-lazy-video' in source) and not parser.has_media_runtime:
        url = relative_url('/assets/performance.js', page)
        source = source.replace('</head>', '<script defer src="' + url + '"></script></head>', 1)
    if noscript_backgrounds:
        source = source.replace('</body>', '<noscript><style>' + ''.join(noscript_backgrounds) + '</style></noscript></body>', 1)
    return source, counts


def optimize_site(site):
    runtime = json.loads((ROOT / 'content/runtime-assets.json').read_text())
    responsive = json.loads((ROOT / 'content/image-optimization.json').read_text())['responsive']
    video_manifest = json.loads((ROOT / 'assets/video/manifest.json').read_text())['videos']
    total = Counter()
    buyer = site / 'assets/buyer.js'
    if buyer.exists():
        old = buyer.read_text(encoding='utf-8')
        widths = {path: item['source_width'] for path, item in responsive.items()}
        new = re.sub(r'/\* EV_RESPONSIVE_START \*/.*?/\* EV_RESPONSIVE_END \*/',
            lambda m: '/* EV_RESPONSIVE_START */\n  var responsiveImages=' +
                json.dumps(widths, ensure_ascii=False, separators=(',', ':')) +
                ';\n  /* EV_RESPONSIVE_END */', old, flags=re.S)
        if new != old:
            buyer.write_text(new, encoding='utf-8')
    for path in sorted(site.rglob('*.html')):
        page = path.relative_to(site).as_posix()
        if any(part.startswith('.') or part in {'reference', '_deploy', '_pages', 'buyer-qa'} for part in path.relative_to(site).parts):
            continue
        old = path.read_text(encoding='utf-8')
        new, counts = optimize_html(old, page, runtime, responsive, video_manifest)
        if new != old:
            path.write_text(new, encoding='utf-8')
            total['pages_changed'] += 1
        total.update(counts)
    print('DELIVERY:', json.dumps(dict(total), ensure_ascii=False))
    return total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', type=Path, default=ROOT)
    optimize_site(parser.parse_args().site_dir.resolve())
