#!/usr/bin/env python3
"""Keep product details on native scrolling while preserving their layout."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import posixpath
import re


def is_product_page(page):
    parts = PurePosixPath(page).parts
    return len(parts) == 4 and parts[0] in {'catalog-ru', 'catalog-en'} and parts[-1] == 'index.html'


def make_static_product(source, page):
    if not is_product_page(page):
        return source
    offsets, offset = [], 0
    for line in source.splitlines(keepends=True):
        offsets.append(offset)
        offset += len(line)
    edits = []

    class Product(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.script = None
            self.style = None
            self.stylesheet = False

        def at(self):
            line, column = self.getpos()
            return offsets[line - 1] + column

        def handle_starttag(self, tag, pairs):
            raw = self.get_starttag_text()
            attrs = dict(pairs)
            previous = attrs.copy()
            start = self.at()
            if tag == 'script':
                url = attrs.get('src', '') or ''
                remove = bool(re.search(r'(?:SmoothScroll|tilda-zero-fixed-)', url, re.I))
                self.script = (start, remove, [])
            if tag == 'style':
                self.style = start + len(raw)
            if tag == 'link' and 'product-scroll.css' in attrs.get('href', ''):
                self.stylesheet = True
            if tag == 'html':
                classes = attrs.get('class', '').split()
                if 'ev-product-static' not in classes:
                    attrs['class'] = ' '.join(classes + ['ev-product-static'])
            # Hover/click controls are separate from scrolling. Only reveal
            # and scroll timelines lose their animation attributes.
            reveal = attrs.get('data-animate-sbs-event') in {'scroll', 'intoview'} or 'data-animate-style' in attrs
            if reveal:
                attrs = {key: value for key, value in attrs.items() if not key.startswith('data-animate-')}
                attrs['class'] = ' '.join(name for name in attrs.get('class', '').split()
                    if name not in {'t396__elem--anim-hidden', 't-animate', 't-animate_started'})
            # These obsolete headers are hidden by the shared navigation.
            if attrs.get('data-artboard-pos') == 'fixed':
                attrs = {key: value for key, value in attrs.items()
                         if key != 'data-artboard-pos' and not key.startswith('data-artboard-fixed-')}
            if 'style' in attrs:
                attrs['style'] = re.sub(r'background-attachment\s*:\s*fixed',
                                         'background-attachment:scroll', attrs['style'], flags=re.I)
            if attrs != previous:
                updated = '<' + tag + ''.join(' ' + key if value is None else
                    ' ' + key + '="' + escape(value, quote=True) + '"' for key, value in attrs.items()) + '>'
                edits.append((start, start + len(raw), updated))

        def handle_data(self, data):
            if self.script is not None:
                self.script[2].append(data)

        def handle_endtag(self, tag):
            if tag == 'style' and self.style is not None:
                text = source[self.style:self.at()]
                updated = re.sub(r'background-attachment\s*:\s*fixed',
                                 'background-attachment:scroll', text, flags=re.I)
                if updated != text:
                    edits.append((self.style, self.at(), updated))
                self.style = None
            if tag == 'script' and self.script is not None:
                start, remove, data = self.script
                # The initializer is standalone; preserve mixed scripts with
                # unrelated controls if a future template changes that.
                initializer = re.fullmatch(r'\s*SmoothScroll\s*\(\s*\{.*?\}\s*\)\s*;?\s*', ''.join(data), re.S)
                if remove or initializer:
                    edits.append((start, source.find('>', self.at()) + 1, ''))
                self.script = None

    parser = Product()
    parser.feed(source)
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    if not parser.stylesheet:
        stylesheet = posixpath.relpath('assets/product-scroll.css', posixpath.dirname(page))
        source = source.replace('</head>', '<link rel="stylesheet" href="' + stylesheet + '"></head>', 1)
    return source


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    changed = 0
    for language in ('catalog-ru', 'catalog-en'):
        for path in sorted((root / language).glob('*/*/index.html')):
            old = path.read_text(encoding='utf-8')
            new = make_static_product(old, path.relative_to(root).as_posix())
            if new != old:
                path.write_text(new, encoding='utf-8')
                changed += 1
    print(f'Native product scrolling: {changed} pages updated')
