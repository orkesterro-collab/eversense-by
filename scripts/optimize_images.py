#!/usr/bin/env python3
"""Reduce photographic raster transfer sizes without resizing or repeat loss.

Run from any directory with Pillow installed. Existing optimized WebP files
are recognized by their checksum and never encoded again. Changed/new source
files are evaluated once; candidates that save less than 15% are discarded.
PNG sources are retained and get a .webp sibling for explicit URL migration.
Technical installation diagrams and SVG files are intentionally excluded.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content/image-optimization.json"
DIRECTORIES = ("assets/original-tilda", "assets/designer-cards/interiors",
               "assets/designer-cards/swatches", "assets/img")
MIN_BYTES = 160_000
MIN_SAVING = 0.15
RESPONSIVE_WIDTHS = (480, 960)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def optimize(path: Path, previous: dict) -> tuple[str, dict]:
    relative = path.relative_to(ROOT).as_posix()
    original = path.read_bytes()
    original_hash = digest(original)
    old = previous.get(relative, {})
    destination = path.with_suffix(".webp")
    if old:
        expected = old.get("output_sha256") if path == destination else old.get("source_sha256")
        if original_hash == expected and destination.is_file():
            if digest(destination.read_bytes()) == old.get("output_sha256"):
                return relative, old
        # An unchanged PNG with a missing/modified output is regenerated below.
    if len(original) < MIN_BYTES:
        return relative, {}
    quality = 88 if path.suffix.lower() == ".png" else 82
    with Image.open(BytesIO(original)) as image:
        if getattr(image, "n_frames", 1) != 1:
            return relative, {}
        dimensions = list(image.size)
        profile = image.info.get("icc_profile")
        options = {"format": "WEBP", "quality": quality, "method": 6}
        if profile:
            options["icc_profile"] = profile
        output = BytesIO()
        image.save(output, **options)
    candidate = output.getvalue()
    if len(candidate) > len(original) * (1 - MIN_SAVING):
        # Remember rejected encodes too, so a routine rerun does no extra work.
        return relative, {"source_sha256": original_hash, "output_sha256": original_hash,
                          "output": relative, "source_bytes": len(original),
                          "output_bytes": len(original), "dimensions": dimensions,
                          "status": "kept-original"}
    destination.write_bytes(candidate)
    return relative, {"source_sha256": original_hash, "output_sha256": digest(candidate),
                      "output": destination.relative_to(ROOT).as_posix(),
                      "source_bytes": len(original), "output_bytes": len(candidate),
                      "dimensions": dimensions, "quality": quality, "status": "optimized"}


def responsive(path: str, previous: dict, images: dict, source_dir: Path) -> tuple[str, dict]:
    relative = path.lstrip("/")
    source = source_dir / relative
    source_hash = digest(source.read_bytes())
    old = previous.get(path, {})
    image_record = images.get(relative, {})
    recognized_output = (image_record.get("source_sha256") == old.get("source_sha256")
                         and image_record.get("output_sha256") == source_hash)
    if old and (old.get("source_sha256") == source_hash or recognized_output):
        if all((ROOT / row["path"].lstrip("/")).is_file()
               and digest((ROOT / row["path"].lstrip("/")).read_bytes()) == row["sha256"]
               for row in old["variants"]):
            return path, old
    variants = []
    destination_dir = ROOT / "assets/responsive"
    destination_dir.mkdir(exist_ok=True)
    with Image.open(source) as image:
        width, height = image.size
        profile = image.info.get("icc_profile")
        options = {"format": "WEBP", "quality": 82, "method": 6}
        if profile:
            options["icc_profile"] = profile
        for target_width in RESPONSIVE_WIDTHS:
            if width <= target_width:
                continue
            target_height = round(height * target_width / width)
            scaled = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            destination = destination_dir / f"{source.stem}-{target_width}.webp"
            scaled.save(destination, **options)
            data = destination.read_bytes()
            variants.append({"width": target_width, "height": target_height,
                             "path": "/" + destination.relative_to(ROOT).as_posix(),
                             "bytes": len(data), "sha256": digest(data)})
    return path, {"source_sha256": source_hash, "source_width": width, "source_height": height,
                  "variants": variants}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--source-dir", type=Path, default=ROOT,
                        help="Optional pristine source checkout for responsive variants")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    previous = manifest.get("images", {})
    products = json.loads((ROOT / "assets/products-data.json").read_text())
    product_images = sorted({row[key] for row in products for key in ("productImage", "interiorImage")})
    responsive_images = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        work = lambda path: responsive(path, manifest.get("responsive", {}), previous, args.source_dir)
        for path, record in executor.map(work, product_images):
            responsive_images[path] = record
    sources = sorted(path for directory in DIRECTORIES for path in (ROOT / directory).iterdir()
                     if path.suffix.lower() in {".webp", ".png"})
    # Newly created PNG siblings are outputs, not new source images.
    png_siblings = {path.with_suffix(".webp") for path in sources if path.suffix.lower() == ".png"}
    sources = [path for path in sources if path not in png_siblings]
    images = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        for relative, record in executor.map(lambda path: optimize(path, previous), sources):
            if record:
                images[relative] = record
    optimized = [row for row in images.values() if row["status"] == "optimized"]
    totals = {"optimized_files": len(optimized),
              "source_bytes": sum(row["source_bytes"] for row in optimized),
              "output_bytes": sum(row["output_bytes"] for row in optimized)}
    result = {"description": "Same dimensions and ICC profiles; checksum guard prevents repeated lossy encoding.",
              "minimum_saving_percent": MIN_SAVING * 100, "totals": totals,
              "images": dict(sorted(images.items())), "responsive": responsive_images}
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(totals))


if __name__ == "__main__":
    main()
