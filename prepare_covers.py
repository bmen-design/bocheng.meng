"""Rebuild the homepage crops from each project's original media."""

import argparse
import json
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms

ROOT = Path(__file__).resolve().parent
WIDTHS = (320, 480, 640, 960, 1280)
# The largest print spread in the catalogue is 16667 × 11092.
Image.MAX_IMAGE_PIXELS = 200_000_000


def open_source(path, crop, ffmpeg):
    if path.suffix.lower() == ".mp4":
        frame = subprocess.check_output([
            ffmpeg, "-v", "error", "-i", str(path), "-ss", str(crop["seconds"]),
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ])
        return Image.open(BytesIO(frame))
    return Image.open(path)


def build_cover(project, ffmpeg):
    crop = project["coverCrop"]
    allowed = {figure["src"] for figure in project["gallery"]}
    allowed.add(f'/media/cases/{project["slug"]}/cover-source.png')
    if crop["source"] not in allowed:
        raise ValueError(f"Unexpected cover source for {project['slug']}")
    source = ROOT / crop["source"].lstrip("/")
    target = ROOT / project["cover"].lstrip("/")
    left, top, width, height = crop["rect"]
    with open_source(source, crop, ffmpeg) as original:
        if width * 5 != height * 4 or not (
            0 <= left < left + width <= original.width
            and 0 <= top < top + height <= original.height
        ):
            raise ValueError(f"Invalid 4:5 crop for {source.name}: {crop['rect']}")
        image = original.crop((left, top, left + width, top + height))
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        profile = original.info.get("icc_profile")
        if profile:
            image = ImageCms.profileToProfile(
                image, ImageCms.ImageCmsProfile(BytesIO(profile)),
                ImageCms.createProfile("sRGB"), outputMode="RGB",
            )
    image = image.convert("RGB")
    if alpha is not None and alpha.getextrema()[0] < 255:
        image.putalpha(alpha)
    fallback_width = min(640, width)
    sizes = {w for w in WIDTHS if w <= width} | {fallback_width}
    for size in sorted(sizes):
        resized = image.resize((size, size * 5 // 4), Image.Resampling.LANCZOS)
        variant = target.with_name(f"{target.stem}-{size}.webp")
        resized.save(variant, "WEBP", quality=89, method=6)
        if size == fallback_width:
            target.write_bytes(variant.read_bytes())
    prefix = target.stem + "-"
    for previous in target.parent.glob(f"{prefix}[0-9]*.webp"):
        suffix = previous.stem[len(prefix):]
        if suffix.isdecimal() and int(suffix) not in sizes:
            previous.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable for video stills")
    args = parser.parse_args()
    for item in json.loads((ROOT / "content/projects.json").read_text())["projects"]:
        build_cover(item, args.ffmpeg)
