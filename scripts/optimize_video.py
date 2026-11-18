#!/usr/bin/env python3
"""Build web delivery copies of the mirrored home videos without altering sources.

Requires ffmpeg with libx264 and libwebp. Run from any directory; outputs and
checksums live under assets/video/. Matching builds are skipped on rerun.
"""
from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets/video"
MANIFEST = OUTPUT / "manifest.json"
SOURCES = ("7633391bb438-1", "fa4db5586248-2")
RECIPE = "h264-1920-crf23-medium-yuv420p-faststart-muted-v1;poster-1280-webp80-t1"
MOBILE_RECIPE = "h264-960-baseline-crf26-maxrate760k-faststart-muted-v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atoms(path: Path) -> list[str]:
    result = []
    with path.open("rb") as stream:
        while header := stream.read(8):
            size, kind = struct.unpack(">I4s", header)
            length = 8
            if size == 1:
                size = struct.unpack(">Q", stream.read(8))[0]
                length += 8
            result.append(kind.decode("ascii"))
            if size == 0:
                break
            if size < length:
                raise ValueError("Invalid MP4 atom size")
            stream.seek(size - length, 1)
    return result


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height",
        "-of", "json", str(path)], text=True))


def verify_delivery(path: Path, original: dict, max_width: int) -> dict:
    encoded = probe(path)
    assert abs(float(original["format"]["duration"]) - float(encoded["format"]["duration"])) < 0.05
    assert len(encoded["streams"]) == 1, "Delivery copy should contain only video"
    assert encoded["streams"][0]["width"] <= max_width
    order = atoms(path)
    assert order.index("moov") < order.index("mdat"), "Video must support progressive playback"
    return encoded


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    records = {}
    for stem in SOURCES:
        source = ROOT / "assets/original-tilda" / (stem + ".mp4")
        video, poster = OUTPUT / (stem + "-1080p.mp4"), OUTPUT / (stem + "-poster.webp")
        mobile = OUTPUT / (stem + "-540p.mp4")
        fingerprint = sha(source)
        old = previous.get("videos", {}).get(str(source.relative_to(ROOT)), {})
        if not (old.get("source_sha256") == fingerprint and previous.get("recipe") == RECIPE
                and video.exists() and poster.exists()
                and old.get("video_sha256") == sha(video) and old.get("poster_sha256") == sha(poster)):
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(source),
                "-map", "0:v:0", "-an", "-vf", "scale='min(1920,iw)':-2:flags=lanczos",
                "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-threads", "4",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], check=True)
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(source),
                "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2:flags=lanczos",
                "-c:v", "libwebp", "-quality", "80", "-threads", "2", str(poster)], check=True)
        if not (old.get("source_sha256") == fingerprint and previous.get("mobile_recipe") == MOBILE_RECIPE
                and mobile.exists() and old.get("mobile_sha256") == sha(mobile)):
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(source),
                "-map", "0:v:0", "-an", "-vf", "scale='min(960,iw)':-2:flags=lanczos",
                "-c:v", "libx264", "-profile:v", "baseline", "-level:v", "3.1",
                "-crf", "26", "-maxrate", "760k", "-bufsize", "950k", "-g", "50",
                "-preset", "medium", "-threads", "4",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mobile)], check=True)
        original = probe(source)
        encoded = verify_delivery(video, original, 1920)
        verify_delivery(mobile, original, 960)
        records[str(source.relative_to(ROOT))] = {
            "video": str(video.relative_to(ROOT)), "mobile": str(mobile.relative_to(ROOT)),
            "poster": str(poster.relative_to(ROOT)),
            "source_sha256": fingerprint, "video_sha256": sha(video), "poster_sha256": sha(poster),
            "mobile_sha256": sha(mobile),
            "source_bytes": source.stat().st_size, "video_bytes": video.stat().st_size,
            "mobile_bytes": mobile.stat().st_size,
            "poster_bytes": poster.stat().st_size,
            "duration_seconds": float(encoded["format"]["duration"]),
            "width": encoded["streams"][0]["width"], "height": encoded["streams"][0]["height"],
            "faststart": True,
        }
        print(f"{source.name}: {video.stat().st_size:,} bytes at 1080p, {mobile.stat().st_size:,} at 540p")
    MANIFEST.write_text(json.dumps({"recipe": RECIPE, "mobile_recipe": MOBILE_RECIPE, "videos": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
