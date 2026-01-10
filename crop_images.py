"""Crop all images in a folder using a provided bounding box.

Usage examples:
  python crop_images.py --src images --dest crops 10 20 200 220
  python crop_images.py --src images --dest crops --recursive --relative 0.1 0.1 0.9 0.9

This script accepts xmin, ymin, xmax, ymax (either absolute pixels or relative [0..1] if
--relative is used or if all coords are <= 1). It clamps the crop to image bounds and
saves cropped images preserving filenames with an optional suffix.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


def iter_images(src: Path, exts: Iterable[str], recursive: bool = False):
    if recursive:
        for p in src.rglob("*"):
            if p.suffix.lower().lstrip(".") in exts:
                yield p
    else:
        for p in src.iterdir():
            if p.is_file() and p.suffix.lower().lstrip(".") in exts:
                yield p


def clamp_box(box: Tuple[int, int, int, int], w: int, h: int) -> Tuple[int, int, int, int]:
    left, top, right, bottom = box
    left = max(0, min(left, w))
    top = max(0, min(top, h))
    right = max(0, min(right, w))
    bottom = max(0, min(bottom, h))
    return left, top, right, bottom


def crop_and_save(img_path: Path, dest_dir: Path, box: Tuple[float, float, float, float],
                  relative: bool, suffix: str = "_crop") -> bool:
    try:
        with Image.open(img_path) as im:
            w, h = im.size
            xmin, ymin, xmax, ymax = box

            if relative:
                xmin_px = xmin * w
                ymin_px = ymin * h
                xmax_px = xmax * w
                ymax_px = ymax * h
            else:
                xmin_px = xmin
                ymin_px = ymin
                xmax_px = xmax
                ymax_px = ymax

            # Round to ints for pixel indices
            left = int(round(xmin_px))
            top = int(round(ymin_px))
            right = int(round(xmax_px))
            bottom = int(round(ymax_px))

            left, top, right, bottom = clamp_box((left, top, right, bottom), w, h)

            if right <= left or bottom <= top:
                # invalid or empty box
                return False

            cropped = im.crop((left, top, right, bottom))

            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_name = f"{img_path.stem}{suffix}{img_path.suffix}"
            dest_path = dest_dir / dest_name
            # Preserve quality/format by saving with same format when possible
            save_kwargs = {}
            if im.format:
                save_kwargs["format"] = im.format

            cropped.save(dest_path, **save_kwargs)
            return True
    except Exception:
        return False


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crop all images in a folder to a given box")
    p.add_argument("--src", required=True, type=Path, help="Source images folder")
    p.add_argument("--dest", required=True, type=Path, help="Destination folder for cropped images")
    p.add_argument("--recursive", action="store_true", help="Recursively traverse subfolders")
    p.add_argument("--exts", nargs="*", default=["jpg", "jpeg", "png", "bmp", "tif", "tiff"],
                   help="Image file extensions to include (default: jpg jpeg png bmp tif tiff)")
    p.add_argument("--suffix", default="_crop", help="Suffix to append to cropped filenames")
    p.add_argument("--relative", action="store_true", help="Treat bbox coords as relative (0..1)")

    # bbox args
    p.add_argument("xmin", type=float, help="xmin (left) - pixel or relative value")
    p.add_argument("ymin", type=float, help="ymin (top) - pixel or relative value")
    p.add_argument("xmax", type=float, help="xmax (right) - pixel or relative value")
    p.add_argument("ymax", type=float, help="ymax (bottom) - pixel or relative value")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    src: Path = args.src
    dest: Path = args.dest
    exts = [e.lower().lstrip(".") for e in args.exts]

    if not src.exists() or not src.is_dir():
        raise SystemExit(f"Source folder does not exist or is not a directory: {src}")

    # determine whether coords should be treated as relative
    coords = (args.xmin, args.ymin, args.xmax, args.ymax)
    if args.relative:
        relative = True
    else:
        # If all coords are between 0 and 1 inclusive, treat as relative
        if all(0.0 <= c <= 1.0 for c in coords):
            relative = True
        else:
            relative = False

    total = 0
    success = 0
    for img_path in iter_images(src, exts, recursive=args.recursive):
        total += 1
        ok = crop_and_save(img_path, dest, coords, relative, suffix=args.suffix)
        if ok:
            success += 1

    print(f"Processed {total} images. Saved {success} cropped images to {dest}")


if __name__ == "__main__":
    main()
