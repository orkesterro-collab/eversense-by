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


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    previous = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    records = {}
    for stem in SOURCES:
        source = ROOT / "assets/original-tilda" / (stem + ".mp4")
        video, poster = OUTPUT / (stem + "-1080p.mp4"), OUTPUT / (stem + "-poster.webp")
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
        original, encoded = probe(source), probe(video)
        assert abs(float(original["format"]["duration"]) - float(encoded["format"]["duration"])) < 0.05
        assert encoded["streams"][0]["width"] <= 1920
        order = atoms(video)
        assert order.index("moov") < order.index("mdat"), "Video must support progressive playback"
        assert len(encoded["streams"]) == 1, "Delivery copy should contain only video"
        records[str(source.relative_to(ROOT))] = {
            "video": str(video.relative_to(ROOT)), "poster": str(poster.relative_to(ROOT)),
            "source_sha256": fingerprint, "video_sha256": sha(video), "poster_sha256": sha(poster),
            "source_bytes": source.stat().st_size, "video_bytes": video.stat().st_size,
            "poster_bytes": poster.stat().st_size,
            "duration_seconds": float(encoded["format"]["duration"]),
            "width": encoded["streams"][0]["width"], "height": encoded["streams"][0]["height"],
            "faststart": True,
        }
        print(f"{source.name}: {source.stat().st_size:,} → {video.stat().st_size:,} bytes; poster {poster.stat().st_size:,}")
    MANIFEST.write_text(json.dumps({"recipe": RECIPE, "videos": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
