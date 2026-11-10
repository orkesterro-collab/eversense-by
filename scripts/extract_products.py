#!/usr/bin/env python3
"""Build the Eversense catalogue from the 30 mirrored Russian product pages.

Uses only the Python standard library. Run from any directory:
    python3 scripts/extract_products.py
    python3 scripts/extract_products.py --check

Technical values are taken from the mirrored Tilda product fields, never from
the old simplified catalogue. The checked element IDs identify values in that
specific source template; unexpected source changes fail rather than silently
inventing a value. The JSON retains source evidence. The browser payload omits
the evidence so implementation metadata is not part of the customer interface.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = {
    "nature-aesthetic-ru": ("nature", "Природная эстетика"),
    "quiet-luxury-ru": ("luxury", "Тихая роскошь"),
    "new-minimalism-ru": ("minimal", "Новый минимализм"),
}
FIELD_IDS = {
    "sku": "1750765893201",
    "family": "1750102435070",
    "shade": "1751030332684",
    "packCount": "1747661627970",
    "thicknessMM": "1747661626846",
    "format": "1747661625679",
    "lock": "1747661463573",
    "bevel": "1747661630185",
    "packArea": "1747661629031",
    "dimensions": "1750097974649",
    "collectionName": "1750943995919",
}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


def compact(value: str) -> str:
    return " ".join(value.split())


class ProductHTML(HTMLParser):
    """Collect Tilda atoms and their source coordinates without dependencies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.atoms: list[dict] = []
        self.images: list[dict] = []
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        parent = next((node["attrs"] for node in reversed(self.stack)
                       if "data-elem-id" in node["attrs"]), {})
        artboard = next((node["attrs"].get("data-artboard-recid")
                         for node in reversed(self.stack)
                         if "data-artboard-recid" in node["attrs"]), None)
        if tag == "meta" and attributes.get("property"):
            self.meta[attributes["property"]] = attributes.get("content", "")
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical = attributes.get("href")
        is_atom = "tn-atom" in attributes.get("class", "").split()
        node = {"tag": tag, "attrs": attributes,
                "text": [] if is_atom else None,
                "elementID": parent.get("data-elem-id"),
                "line": self.getpos()[0]}
        if is_atom:
            self.atoms.append(node)
        if attributes.get("role") == "img":
            raw = attributes.get("data-original", "")
            source_attribute = "data-original"
            if not raw:
                match = re.search(r"background-image\s*:\s*url\(['\"]?([^)'\"]+)",
                                  attributes.get("style", ""))
                if match:
                    raw = match.group(1)
                    source_attribute = "style/background-image"
            if re.search(r"\.(webp|jpe?g|png)(?:[?#]|$)", raw, re.I):
                self.images.append({"raw": raw, "elementID": parent.get("data-elem-id"),
                                    "artboard": artboard,
                                    "top": parent.get("data-field-top-value"),
                                    "width": parent.get("data-field-width-value"),
                                    "attribute": source_attribute,
                                    "line": self.getpos()[0]})
        if tag == "br":
            self.handle_data(" ")
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        # Recover only to a matching open tag; unmatched void/end tags are ignored.
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, value: str) -> None:
        for node in self.stack:
            if node["text"] is not None:
                node["text"].append(value)

    def field(self, key: str, optional: bool = False) -> tuple[str | None, dict | None]:
        element_id = FIELD_IDS[key]
        found = [node for node in self.atoms if node["elementID"] == element_id
                 and compact("".join(node["text"]))]
        values = {compact("".join(node["text"])) for node in found}
        if not values and optional:
            return None, None
        if len(values) != 1:
            raise ValueError(f"Expected one {key} value at element {element_id}: {values}")
        value = values.pop()
        return value, {"selector": f'[data-elem-id="{element_id}"] .tn-atom',
                       "text": value, "line": found[0]["line"]}


def local_image(raw: str, source: Path, media_by_url: dict) -> str:
    parsed = urlsplit(raw)
    if parsed.netloc:
        mapped = media_by_url.get(raw)
        if not mapped:
            raise ValueError(f"Image not in local media manifest: {raw}")
        path = ROOT / mapped
    elif parsed.path.startswith("/"):
        path = ROOT / unquote(parsed.path).removeprefix("/eversense-by/").lstrip("/")
    else:
        path = source.parent / unquote(parsed.path)
    path = path.resolve()
    relative = path.relative_to(ROOT)
    if not path.is_file() or not relative.as_posix().startswith("assets/"):
        raise ValueError(f"Missing/non-asset image: {source} -> {raw}")
    return "/" + relative.as_posix()


def number(text: str, pattern: str, field: str) -> float | int:
    matched = re.fullmatch(pattern, text, re.I)
    if not matched:
        raise ValueError(f"Unexpected {field}: {text!r}")
    result = float(matched.group(1).replace(",", "."))
    return int(result) if result.is_integer() else result


def derive_tags(family: str, shade: str | None) -> dict:
    # UI labels only: do not infer durability, water resistance or use classes.
    lower = family.casefold()
    if lower.startswith("дуб "):
        design = "wood"
    elif lower == "мрамор":
        design = "stone"
    elif lower == "однотонные":
        design = "plain"
    else:
        raise ValueError(f"Unknown design family: {family}")
    tone = None
    if shade and re.search(r"бел|светл", shade, re.I):
        tone = "light"
    elif shade and re.search(r"тёмн|темн", shade, re.I):
        tone = "dark"
    elif shade and re.search(r"средн", shade, re.I):
        tone = "medium"
    # "Натуральный", "серый" and "коричневый" do not state lightness.
    return {"tone": tone, "design": design}


def extract(source: Path, media_by_url: dict, media_by_local: dict) -> dict:
    parsed = ProductHTML()
    parsed.feed(source.read_text(encoding="utf-8"))
    raw: dict[str, str | None] = {}
    evidence = {}
    for key in FIELD_IDS:
        raw[key], evidence[key] = parsed.field(key, optional=key == "shade")
    sku = raw["sku"]
    if not sku or not re.fullmatch(r"EL\d+", sku):
        raise ValueError(f"Unexpected SKU: {sku!r}")
    collection_id, collection_name = COLLECTIONS[source.parent.parent.name]
    if raw["collectionName"] != collection_name:
        raise ValueError(f"Collection name mismatch in {source}")
    expected_path = "/" + source.parent.relative_to(ROOT).as_posix() + "/"
    canonical = urlsplit(parsed.canonical or "").path
    canonical = canonical.removeprefix("/eversense-by")
    if canonical.rstrip("/") + "/" != expected_path:
        raise ValueError(f"Unexpected canonical in {source}: {parsed.canonical}")
    dimensions = re.fullmatch(r"(\d+)\s*[хx×]\s*(\d+)\s*мм", raw["dimensions"], re.I)
    if not dimensions:
        raise ValueError(f"Unexpected dimensions: {raw['dimensions']}")
    product_candidates = [item for item in parsed.images
                          if re.search(re.escape(sku), item["raw"], re.I)
                          and "top" in item["raw"].lower()
                          and item["top"] == "0" and item["width"] == "100"]
    if len(product_candidates) != 1:
        raise ValueError(f"Expected one SKU-labelled top image for {sku}")
    product_image = product_candidates[0]
    interiors = [item for item in parsed.images
                 if item["artboard"] == product_image["artboard"]
                 and item is not product_image and item["width"] == "50"]
    selected_images = {"productImage": product_image,
                       "interiorImage": interiors[0] if interiors else None}
    image_paths = {}
    for key, item in selected_images.items():
        image_paths[key] = local_image(item["raw"], source, media_by_url) if item else None
        if item:
            image_evidence = {name: value for name, value in item.items() if name != "raw"}
            image_evidence["htmlValue"] = item["raw"]
            image_evidence["originalURL"] = media_by_local.get(image_paths[key].lstrip("/"))
            evidence[key] = image_evidence
        else:
            evidence[key] = None
    family, shade = raw["family"], raw["shade"]
    name = shade if family == "Однотонные" and shade else family + (" " + shade.lower() if shade else "")
    evidence["name"] = {"derivedFrom": ["family", "shade"],
                        "originalPageTitle": parsed.meta.get("og:title")}
    evidence["canonicalPath"] = {"selector": 'link[rel="canonical"]',
                                "htmlValue": parsed.canonical,
                                "normalization": "root-relative path with trailing slash"}
    evidence["tags"] = {"derivedFrom": ["family", "shade"],
                        "purpose": "UI classification; null tone means name does not state lightness"}
    result = {
        "sku": sku, "name": name, "family": family, "shade": shade,
        "collectionID": collection_id, "collectionName": collection_name,
        "canonicalPath": expected_path,
        **image_paths,
        "widthMM": int(dimensions.group(2)), "lengthMM": int(dimensions.group(1)),
        "thicknessMM": number(raw["thicknessMM"], r"(\d+(?:[.,]\d+)?)\s*мм", "thickness"),
        "packCount": number(raw["packCount"], r"(\d+)\s*штук", "pack count"),
        "packArea": number(raw["packArea"], r"(\d+(?:[.,]\d+)?)\s*м[²2]", "pack area"),
        "format": raw["format"], "bevel": raw["bevel"], "lock": raw["lock"],
        "tags": derive_tags(family, shade),
        "sourcePath": source.relative_to(ROOT).as_posix(),
        "sourceEvidence": evidence,
    }
    calculated_area = result["widthMM"] * result["lengthMM"] * result["packCount"] / 1_000_000
    if abs(calculated_area - result["packArea"]) > 0.01:
        raise ValueError(f"Pack area inconsistent with panel dimensions/count: {sku}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing outputs without changing files")
    arguments = parser.parse_args()
    manifest = json.loads((ROOT / "reference/original-media-manifest.json").read_text(encoding="utf-8"))
    media_by_url = {entry["url"]: entry["local"] for entry in manifest["files"] if entry.get("local")}
    media_by_local = {local: url for url, local in media_by_url.items()}
    sources = sorted((ROOT / "catalog-ru").glob("*/*/index.html"))
    if len(sources) != 30:
        raise ValueError(f"Expected 30 product sources, found {len(sources)}")
    products = [extract(source, media_by_url, media_by_local) for source in sources]
    products.sort(key=lambda product: int(product["sku"][2:]))
    if len({product["sku"] for product in products}) != 30:
        raise ValueError("Duplicate product SKUs")
    if len({product["canonicalPath"] for product in products}) != 30:
        raise ValueError("Duplicate canonical paths")
    browser_products = [{key: value for key, value in product.items()
                         if key not in {"sourcePath", "sourceEvidence"}} for product in products]
    outputs = {
        ROOT / "assets/products-data.json": json.dumps(products, ensure_ascii=False, indent=2) + "\n",
        ROOT / "assets/products-data.js": (
            "/* Generated by scripts/extract_products.py; edit the mirrored source, then regenerate. */\n"
            "window.EversenseCatalogData = " + json.dumps(browser_products, ensure_ascii=False, indent=2) + ";\n"
        ),
    }
    for path, content in outputs.items():
        if arguments.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Generated output is out of date: {path.relative_to(ROOT)}")
        else:
            path.write_text(content, encoding="utf-8")
    print("Verified 30 unique SKUs, 30 existing canonical pages and 60 local images.")
    print("Collections:", dict(Counter(product["collectionID"] for product in products)))
    print("Pack formats:", dict(Counter((product["format"], product["packArea"]) for product in products)))
    print("Source provenance retained in products-data.json; browser payload contains customer data only.")


if __name__ == "__main__":
    main()
