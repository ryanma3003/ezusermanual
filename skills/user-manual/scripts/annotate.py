#!/usr/bin/env python3
"""Annotate screenshots: red highlight boxes with numbered markers, and blurred regions.

Coordinates are image pixels: x,y = top-left corner, w,h = size.

  annotate.py draw in.png out.png --box 120,80,200,40:1 --box 400,300,90,36:2 --blur 600,20,180,30
  annotate.py grid in.png grid.png [--step 100]     # overlay a labeled pixel grid to read coordinates

--box X,Y,W,H[:LABEL]   red box; optional LABEL (e.g. 1, 2, A) is drawn in a red circle
--blur X,Y,W,H          blur the region (private data)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RED = (220, 38, 38)
WHITE = (255, 255, 255)


def font(size: int):
    for name in ("Arial Bold.ttf", "Arial-BoldMT.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    for path in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "C:/Windows/Fonts/arialbd.ttf"):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def clamp_box(img: Image.Image, x: float, y: float, w: float, h: float):
    x0, y0 = max(0, int(x)), max(0, int(y))
    x1, y1 = min(img.width, int(x + w)), min(img.height, int(y + h))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def blur(img: Image.Image, regions, scale: float = 1.0):
    """regions: iterable of (x, y, w, h)."""
    for x, y, w, h in regions:
        box = clamp_box(img, x, y, w, h)
        if not box:
            continue
        crop = img.crop(box)
        small = crop.resize((max(1, crop.width // 12), max(1, crop.height // 12)), Image.BILINEAR)
        img.paste(small.resize(crop.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(3 * scale)), box)


def highlight(img: Image.Image, boxes, scale: float = 1.0):
    """boxes: iterable of (x, y, w, h, label_or_None). scale = device pixel ratio (line/marker size)."""
    draw = ImageDraw.Draw(img)
    pad, line = 4 * scale, max(2, round(3 * scale))
    radius = 13 * scale
    f = font(int(15 * scale))
    for x, y, w, h, label in boxes:
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(img.width - 1, x + w + pad), min(img.height - 1, y + h + pad)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=4 * scale, outline=RED, width=line)
        if label:
            # marker sits left of the box (so it never covers labels above it); right of it if no room; else on the corner
            gap = radius + 3 * scale
            cy = min(max((y0 + y1) / 2, radius + 1), img.height - radius - 1)
            if x0 - gap - radius >= 0:
                cx = x0 - gap
            elif x1 + gap + radius <= img.width:
                cx = x1 + gap
            else:
                cx, cy = x0 + radius, max(y0, radius + 1)
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=RED, outline=WHITE, width=max(1, round(2 * scale)))
            draw.text((cx, cy), str(label), fill=WHITE, font=f, anchor="mm")


def grid(img: Image.Image, step: int) -> Image.Image:
    out = img.convert("RGB")
    draw = ImageDraw.Draw(out, "RGBA")
    f = font(max(10, step // 7))
    for x in range(0, out.width, step):
        draw.line((x, 0, x, out.height), fill=(255, 0, 255, 110), width=1)
        draw.text((x + 2, 2), str(x), fill=(255, 0, 255, 255), font=f)
    for y in range(0, out.height, step):
        draw.line((0, y, out.width, y), fill=(255, 0, 255, 110), width=1)
        draw.text((2, y + 2), str(y), fill=(255, 0, 255, 255), font=f)
    return out


def parse_box(value: str, with_label: bool):
    coords, _, label = value.partition(":") if with_label else (value, "", "")
    try:
        x, y, w, h = (float(v) for v in coords.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected X,Y,W,H{'[:LABEL]' if with_label else ''}, got {value!r}")
    return (x, y, w, h, label or None) if with_label else (x, y, w, h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw", help="draw boxes/markers and blur regions")
    d.add_argument("src", type=Path)
    d.add_argument("dest", type=Path)
    d.add_argument("--box", action="append", default=[], type=lambda v: parse_box(v, True))
    d.add_argument("--blur", action="append", default=[], type=lambda v: parse_box(v, False))
    d.add_argument("--scale", type=float, default=None, help="marker size factor (default: from image width)")
    g = sub.add_parser("grid", help="overlay a coordinate grid")
    g.add_argument("src", type=Path)
    g.add_argument("dest", type=Path)
    g.add_argument("--step", type=int, default=100)
    args = ap.parse_args()

    if not args.src.is_file():
        sys.exit(f"error: {args.src} not found")
    img = Image.open(args.src).convert("RGB")
    if args.cmd == "grid":
        grid(img, args.step).save(args.dest)
    else:
        scale = args.scale or max(1.0, img.width / 1000)  # images print at full text width, so size follows width
        blur(img, args.blur, scale)
        highlight(img, args.box, scale)
        args.dest.parent.mkdir(parents=True, exist_ok=True)
        img.save(args.dest)
    print(f"wrote {args.dest} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
