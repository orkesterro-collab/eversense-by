#!/usr/bin/env python3
"""Add the approved designer-card section without rebuilding the product page.

The selected products and their furniture palette are in content/designer-cards.json.
Run this script after intentionally rebuilding original Tilda product pages.
Only the stylesheet link and the marked section are added or replaced.
"""
from html import escape
import json
from pathlib import Path
import posixpath
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/designer-cards.json"
START = "<!-- EVERSENSE DESIGNER CARD START -->"
END = "<!-- EVERSENSE DESIGNER CARD END -->"
STYLE_ID = "ev-designer-card-css"


def relative(asset, page):
    return posixpath.relpath(asset.lstrip("/"), posixpath.dirname(page))


def e(value):
    return escape(str(value), quote=True)


def image_attrs(image, page, alt, css_class):
    return (
        f'class="{css_class}" src="{e(relative(image["src"], page))}" '
        f'width="{image["width"]}" height="{image["height"]}" '
        f'loading="lazy" decoding="async" alt="{e(alt)}"'
    )


def render(product):
    sku, name, page = product["sku"], product["name"], product["page"]
    materials = []
    for material in product["materials"]:
        alt = f'{material["code"]} — {material["name"]}, образец мебельного декора'
        attrs = image_attrs(material["image"], page, alt, "ev-designer-card__swatch")
        role = material.get("role", "")
        role_html = f'\n            <p class="ev-designer-card__role">{e(role)}</p>' if role else ""
        materials.append(f'''      <li class="ev-designer-card__material">
        <figure>
          <img {attrs}>
          <figcaption>
            <span class="ev-designer-card__code">{e(material["code"])}</span>
            <h4>{e(material["name"])}</h4>{role_html}
          </figcaption>
        </figure>
      </li>''')
    interior_alt = f'Визуализация кухни с полом EVERSENSE {name} {sku} и мебельными декорами из подборки'
    interior = image_attrs(product["interior"], page, interior_alt, "ev-designer-card__interior-image")
    palette = "\n".join(materials)
    block = f'''{START}
<section id="ev-designer-card" class="ev-designer-card" aria-labelledby="ev-designer-card-title" data-floor-sku="{e(sku)}">
  <div class="ev-designer-card__inner">
    <header class="ev-designer-card__header">
      <div class="ev-designer-card__heading">
        <p class="ev-designer-card__eyebrow">Пол и мебель в одном интерьере</p>
        <h2 id="ev-designer-card-title">Дизайнерская карта</h2>
        <p class="ev-designer-card__floor">{e(name)} <span>{e(sku)}</span></p>
      </div>
      <p class="ev-designer-card__intro">Цвета и фактуры мебели, подобранные к этому полу.</p>
    </header>
    <div class="ev-designer-card__materials-heading">
      <h3 id="ev-designer-card-materials-title">Мебельные декоры EGGER</h3>
    </div>
    <ul class="ev-designer-card__materials" aria-labelledby="ev-designer-card-materials-title">
{palette}
    </ul>
    <figure class="ev-designer-card__interior">
      <img {interior}>
      <figcaption>
        <span class="ev-designer-card__caption-title">Пол и палитра в интерьере</span>
        <span>Пол — EVERSENSE {e(sku)}. Мебель — в декорах из подборки выше.</span>
      </figcaption>
    </figure>
    <p class="ev-designer-card__note">Интерьер — визуализация сочетания. Оттенки уточняйте по реальным образцам при вашем освещении.</p>
  </div>
</section>
{END}'''
    # Keep original source line numbers stable for extract_products.py provenance.
    return re.sub(r"\n[ \t]*", "", block)


def strip_addition(html):
    html = re.sub(re.escape(START) + r".*?" + re.escape(END), "", html, flags=re.S)
    return re.sub(r'<link\b[^>]*\bid="' + STYLE_ID + r'"[^>]*>', "", html)


def navigation_position(html):
    records = list(re.finditer(r'<div\b[^>]*\bid=["\']rec\d+["\'][^>]*>', html))
    candidates = []
    for index, match in enumerate(records):
        end = records[index + 1].start() if index + 1 < len(records) else len(html)
        record = html[match.start():end]
        if "Вернуться назад" in record and "В каталог" in record:
            candidates.append(match.start())
    if len(candidates) != 1:
        raise ValueError(f"Expected one existing catalog navigation record, found {len(candidates)}")
    return candidates[0]


def validate(product):
    if len(product["materials"]) != 4:
        raise ValueError(f'{product["sku"]}: expected four furniture materials')
    for image in [product["interior"]] + [m["image"] for m in product["materials"]]:
        path = (ROOT / image["src"].lstrip("/")).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Missing or invalid image: {image['src']}")
        if image["width"] <= 0 or image["height"] <= 0:
            raise ValueError("Images need their intrinsic dimensions")
    page_path = (ROOT / product["page"]).resolve()
    if not page_path.is_relative_to(ROOT) or not page_path.is_file():
        raise ValueError("Product page must already exist")


def main():
    products = json.loads(DATA.read_text(encoding="utf-8"))["products"]
    if len({p["sku"] for p in products}) != len(products):
        raise ValueError("Duplicate product SKU")
    updates = []
    for product in products:
        validate(product)
        path = ROOT / product["page"]
        original = path.read_text(encoding="utf-8")
        base = strip_addition(original)
        if 'id="ev-designer-card"' in base:
            raise ValueError(f"Unmarked designer card already exists: {path}")
        position = navigation_position(base)
        updated = base[:position] + render(product) + base[position:]
        if updated.count("</head>") != 1:
            raise ValueError("Expected one page head")
        css = e(relative("assets/designer-cards.css", product["page"]))
        link = f'<link id="{STYLE_ID}" rel="stylesheet" href="{css}?v=20261114">'
        updated = updated.replace("</head>", link + "</head>", 1)
        if strip_addition(updated) != base:
            raise ValueError("Existing page content was changed")
        updates.append((path, original, updated))
    changed = 0
    for path, original, updated in updates:
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Designer cards: {len(products)} verified, {changed} updated.")


if __name__ == "__main__":
    main()
