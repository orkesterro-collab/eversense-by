"""Render the approved Russian phone layout alongside the original wide artboards."""
from functools import lru_cache
from html import escape, unescape
from pathlib import Path
import re

from history_banner import BANNER

CONTENT = Path(__file__).resolve().parents[1] / 'content'
RECORDS = {
    'intro': '1002599921', 'solution': '1002600036', 'layers': '1002600136',
    'collections': '1002600151', 'eco': '1016194446', 'textures': '2341420221',
}
GENERATED = re.compile(r'<!-- ev-mobile:start -->.*?<!-- ev-mobile:end -->', re.S)


@lru_cache(maxsize=1)
def blocks():
    template = (CONTENT / 'home-mobile.html.in').read_text(encoding='utf-8')
    return dict(re.findall(r'<template id="([a-z]+)">\s*(.*?)\s*</template>', template, re.S))


def marked(markup):
    return '<!-- ev-mobile:start -->' + markup + '<!-- ev-mobile:end -->'


def campaign_banner(target='/black-friday/'):
    return (CONTENT / 'home-campaign.html.in').read_text(encoding='utf-8').strip().replace('{{target}}', target)


def record_open(source, record):
    marker = f'<div id="rec{record}"'
    start = source.index(marker)
    return source[start:source.index('>', start) + 1]


def make_mobile_home(source, page):
    if page not in ('index.html', 'ru/index.html'):
        return source
    alias = page == 'ru/index.html'
    base = '../' if alias else ''
    source = GENERATED.sub('', source)
    source = re.sub(r'(<a\b(?![^>]*\baria-label=)[^>]*\bhref="#bullet([1-5])")>',
                    r'\1 aria-label="Слайд \2">', source)
    files = [f'<link rel="stylesheet" href="{base}assets/home-mobile.css?v=1">']
    first_filter = '<div class="t396__filter" data-artboard-recid="1028545506"></div>'
    campaign_controls = ('<p class="ev-m-only ev-bf-home__date">4–29 ноября 2026</p>'
                         '<a class="ev-m-collections-link" href="#rec1002600151">Смотреть коллекции</a>')
    if alias and 'class="ev-bf-home__wrap"' not in source:
        banner = campaign_banner(base + 'black-friday/').replace('class="ev-bf-home"', 'class="ev-bf-home ev-m-alias-campaign"')
        banner = banner.replace('<a class="ev-bf-home__button"', campaign_controls + '<a class="ev-bf-home__button"', 1)
        source = source.replace(first_filter, first_filter + marked(banner), 1)
        files[:0] = [f'<link rel="stylesheet" media="(max-width: 959px)" href="{base}assets/black-friday-home.css?v=3">',
                     f'<script defer src="{base}assets/black-friday-home.js?v=1"></script>']
    else:
        source = source.replace('<a class="ev-bf-home__button"', marked(campaign_controls) + '<a class="ev-bf-home__button"', 1)

    download = re.search(r'href=["\']([^"\']*EVERSENSE\.zip[^"\']*)["\']', source)
    if download is None:
        raise ValueError('Missing source download for designer textures')
    for name, record in RECORDS.items():
        start = record_open(source, record)
        section = blocks()[name].replace('{{base}}', base).replace('{{textures}}', escape(unescape(download[1]), quote=True))
        source = source.replace(start, start + marked(section), 1)

    help_block = blocks()['help'].replace('{{base}}', base)
    help_root = re.search(r'<section\b[^>]*\bid="ev-buyer-path"[^>]*>', source)
    if help_root:
        source = source[:help_root.end()] + marked(help_block) + source[help_root.end():]
    else:
        before = record_open(source, RECORDS['eco'])
        source = source.replace(before, marked('<section class="ev-m-only" id="ev-buyer-path">' + help_block + '</section>') + before, 1)

    if 'id="ev-history-banner"' not in source:
        banner = BANNER.replace('src="assets/', f'src="{base}assets/').replace('href="history.html"', f'href="{base}history.html"')
        if alias:
            banner = banner.replace('id="ev-history-banner"', 'id="ev-history-banner" class="ev-m-alias-history"', 1)
        footer = '<div id="ev-home-footer"'
        source = source.replace(footer, marked(banner) + footer, 1)
        files.insert(0, f'<link rel="stylesheet" href="{base}assets/history-banner.css">')
    return source.replace('</head>', marked(''.join(files)) + '</head>', 1)
