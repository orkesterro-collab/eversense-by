#!/usr/bin/env python3
"""Generate collection galleries from the catalog's interior photographs.

Run this file with ImageMagick installed to regenerate the mobile WebP files.
The delivery optimizer embeds the gallery markup using the committed images.
"""
from html import escape
import json
from pathlib import Path
import posixpath
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
HOME_PAGES = {'index.html', 'ru/index.html'}
RECORDS = {'nature': '1002600156', 'luxury': '1002600161', 'minimal': '1002600166'}
ASSET_DIR = 'assets/collection-interiors'
STYLE = 'home-collection-interiors.css'
SCRIPT = 'home-collection-interiors.js'
VERSION = '5'
HEART_ICON = '<svg class="ev-heart-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20.8 4.6c-2.1-2.1-5.5-2.1-7.6 0L12 5.8l-1.2-1.2c-2.1-2.1-5.5-2.1-7.6 0s-2.1 5.5 0 7.6L12 21l8.8-8.8c2.1-2.1 2.1-5.5 0-7.6Z"/></svg>'
MARKUP = re.compile(r'\n<!-- ev-collection-interiors -->.*?<!-- /ev-collection-interiors -->', re.S)
ASSETS = re.compile(r'<link\b[^>]*\bid="ev-collection-interiors-css"[^>]*>|'
                    r'<script\b[^>]*\bid="ev-collection-interiors-js"[^>]*>\s*</script>')


def collection_data():
    products = json.loads((ROOT / 'assets/products-data.json').read_text(encoding='utf-8'))
    settings = json.loads((ROOT / 'content/home-collection-interiors.json').read_text(encoding='utf-8'))
    for key, record in RECORDS.items():
        config = settings[key]
        first = config['first']
        centers = config['cropCenterX']
        items = [p for p in products if p['collectionID'] == key]
        if {p['sku'] for p in items} != centers.keys() or first not in centers:
            raise ValueError(f'Crop settings do not match the catalog for {key}')
        items.sort(key=lambda p: (p['sku'] != first, int(p['sku'][2:])))
        yield key, record, items, centers


def picture_markup(product, asset_url, responsive, navigation):
    source = product['interiorImage']
    image = responsive[source]
    candidates = [(variant['path'], variant['width']) for variant in image['variants']]
    candidates.append((source, image['source_width']))
    srcset = ', '.join(f'{asset_url(path)} {width}w' for path, width in candidates)
    sku = product['sku']
    name = escape(product['name'])
    return f'''    <figure class="ev-interiors__slide" data-sku="{escape(sku)}" aria-hidden="true" inert>
      <picture>
        <source media="(max-width: 639px)" data-srcset="{asset_url(f'{ASSET_DIR}/mobile/{sku}.webp')}">
        <img alt="" decoding="async" loading="eager" sizes="min(100vw, 100vh)" data-srcset="{srcset}" data-src="{asset_url(source)}">
      </picture>{navigation}
      <button class="ev-card-favorite ev-interiors__favorite" type="button" data-ev-favorite="{escape(sku)}" aria-pressed="false" aria-label="Избранное — {name}">{HEART_ICON}</button>
      <figcaption>{name}</figcaption>
    </figure>'''


def make_home_collection_interiors(source, page, responsive):
    if page not in HOME_PAGES:
        return source

    def asset_url(path):
        return escape(posixpath.relpath(path.lstrip('/'), posixpath.dirname(page) or '.'), quote=True)

    source = MARKUP.sub('', source)
    for key, record, items, _ in collection_data():
        name = items[0]['collectionName']
        collection = escape(name)
        collection_path = items[0]['canonicalPath'].rsplit('/', 2)[0]
        button = re.compile(
            r'(<a\b[^>]*\bhref=["\'][^"\']*' + re.escape(collection_path) +
            r'/?["\'][^>]*>\s*<div\b[^>]*>\s*<span class="tn-atom__button-text">)[^<]*(</span>)'
        )
        source, count = button.subn(lambda match: match[1] + collection + match[2], source)
        if count != 2:
            raise ValueError(f'Expected the two catalog buttons for {name} in {page}, found {count}')

        filter_tag = f'<div class="t396__filter" data-artboard-recid="{record}"></div>'
        if source.count(filter_tag) != 1:
            raise ValueError(f'Collection artboard {record} missing from {page}')
        gallery_id = f'ev-interiors-{key}'
        next_button = f'\n      <button class="ev-interiors__next" type="button" aria-label="Следующий интерьер" aria-controls="{gallery_id}"></button>'
        panels = '\n'.join(
            picture_markup(product, asset_url, responsive,
                           next_button if index < len(items) - 1 else '')
            for index, product in enumerate(items)
        )
        block = f'''
<!-- ev-collection-interiors -->
<div class="ev-interiors" hidden>
  <div class="ev-interiors__sheet" inert>
    <img class="ev-interiors__preview" alt="" decoding="async" loading="eager" data-src="{asset_url(f'{ASSET_DIR}/{key}-preview.webp')}">
    <div class="ev-interiors__track" id="{gallery_id}" role="region" aria-label="Интерьеры коллекции «{collection}»" tabindex="0">
{panels}
    </div>
    <div class="ev-interiors__controls">
      <button class="ev-interiors__previous" type="button" aria-label="Предыдущий интерьер" aria-controls="{gallery_id}" disabled></button>
    </div>
    <button class="ev-interiors__close" type="button" aria-label="Закрыть интерьеры коллекции «{collection}»" aria-controls="{gallery_id}"></button>
  </div>
  <button class="ev-interiors__opener" type="button" aria-label="Посмотреть интерьеры коллекции «{collection}»" aria-controls="{gallery_id}" aria-expanded="false">
    <span class="ev-interiors__hint" aria-hidden="true"></span>
  </button>
  <span class="ev-interiors__announcement" role="status"></span>
</div>
<!-- /ev-collection-interiors -->'''
        source = source.replace(filter_tag, filter_tag + block, 1)

    assets = (f'<link id="ev-collection-interiors-css" rel="stylesheet" href="{asset_url(f"assets/{STYLE}")}?v={VERSION}">'
              f'<script id="ev-collection-interiors-js" src="{asset_url(f"assets/{SCRIPT}")}?v={VERSION}" defer></script>')
    return ASSETS.sub('', source).replace('</head>', assets + '</head>', 1)


def make_mobile_images():
    destination = ROOT / ASSET_DIR
    mobile = destination / 'mobile'
    mobile.mkdir(parents=True, exist_ok=True)
    for key, _, items, centers in collection_data():
        for product in items:
            sku = product['sku']
            original = ROOT / product['interiorImage'].lstrip('/')
            dimensions = subprocess.check_output(
                ['magick', 'identify', '-ping', '-format', '%w %h', str(original)], text=True
            )
            width, height = map(int, dimensions.split())
            # Keep the floor at the bottom and use the chosen furniture as the horizontal focal point.
            crop_height = min(height * 94 // 100, width * 3 // 2) // 3 * 3
            crop_width = crop_height * 2 // 3
            left = max(0, min(round(width * centers[sku] - crop_width / 2), width - crop_width))
            top = height - crop_height
            output = mobile / f'{sku}.webp'
            subprocess.run([
                'magick', str(original), '-crop', f'{crop_width}x{crop_height}+{left}+{top}', '+repage',
                '-resize', '720x1080', '-strip', '-quality', '79', '-define', 'webp:method=6', str(output),
            ], check=True)
        subprocess.run([
            'magick', str(mobile / f'{items[0]["sku"]}.webp'), '-resize', '112x168', '-strip',
            '-quality', '64', str(destination / f'{key}-preview.webp'),
        ], check=True)


if __name__ == '__main__':
    make_mobile_images()
