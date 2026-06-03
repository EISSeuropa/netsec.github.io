#!/usr/bin/env python3
"""
One-shot brand-asset processor for the designer's logo deliverable.

Takes the designer's raw PNGs (mark only, primary lockup, white-on-
dark, monochrome) and produces the deployment set the site needs:
cleaned lockups (cropped to content bbox, no transparent padding),
a favicon family at standard sizes, and the manifest icons.

The OG / social cards are hand-designed marketing graphics, kept as
design assets (assets/images/og-image.png and og-image-people.png)
rather than generated here, so this script never overwrites them.

The designer sent PNG only. SVG masters would be better for favicon
and high-DPI rendering; tracked as a follow-up. Until then,
rasterising from the 595×599 mark PNG gives an acceptable result
at the standard favicon sizes.

Usage:
    python3 scripts/build-brand-assets.py \\
        --source ~/path/to/LOGO_RASTER

    # Or accept the default path from the designer hand-off:
    python3 scripts/build-brand-assets.py

Idempotent: re-running just overwrites the output. Safe to commit
output PNGs because they're small (mark = ~10 KB, lockups ~30 KB,
OG card ~100 KB) and we want them tracked in git so the deploy
doesn't depend on this script being re-run.

Tracked in #220 (logo deployment).
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Install: pip install -r scripts/requirements.txt")


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "images" / "brand"

DEFAULT_SOURCE = Path(
    "/Users/NewArthur/Documents/Emploi/Op_2025-2026/EISS/COST/Website/"
    "NetSec/LOGO_RASTER (Web e Office)"
)

# Map each designer-source filename to the cleaned output filename.
# The lockups (primary, White, black) ship with a lot of transparent
# padding in the designer's 1920×1080 canvas; we crop to content bbox
# before saving. `imageonly.png` is already tight.
LOCKUPS = {
    "primary.png":    "netsec-lockup-primary.png",   # light bg
    "White.png":      "netsec-lockup-white.png",     # dark bg
    "black.png":      "netsec-lockup-mono.png",      # print / monochrome
    "imageonly.png":  "netsec-mark.png",             # icon only, square
}

# Favicon family. Rasterised from imageonly.png because that's the
# square, no-text variant — only thing that reads at small sizes.
FAVICON_SIZES = {
    "favicon-16.png":          16,
    "favicon-32.png":          32,
    "favicon-48.png":          48,
    "apple-touch-icon.png":   180,    # iOS home-screen
    "android-chrome-192.png": 192,    # PWA manifest
    "android-chrome-512.png": 512,    # PWA manifest, splash screens
}



# ──────────────────────────── helpers ────────────────────────────

def crop_to_content(im: Image.Image) -> Image.Image:
    """Crop an RGBA image to the bounding box of its non-transparent
    pixels. The designer's lockup PNGs are 1920×1080 with the logo
    centred in a smaller area; cropping makes them deploy-ready
    without a percentage of empty alpha around the content."""
    bbox = im.getbbox()
    if bbox is None:
        return im
    return im.crop(bbox)


def save_png(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "PNG", optimize=True)
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes, {im.size[0]}×{im.size[1]})")


# ──────────────────────────── steps ────────────────────────────

def process_lockups(source: Path) -> None:
    """Copy + crop the four core lockups into assets/images/brand/."""
    print("\n── 1. Lockups (cropped to content bbox) ──")
    for src_name, dst_name in LOCKUPS.items():
        src = source / src_name
        if not src.exists():
            sys.exit(f"Source not found: {src}")
        im = Image.open(src).convert("RGBA")
        if dst_name != "netsec-mark.png":
            im = crop_to_content(im)
        save_png(im, OUT / dst_name)


def build_favicons(source: Path) -> None:
    """Rasterise the mark to standard favicon sizes. Bicubic resample
    via Lanczos for the cleanest small-size output we can manage from
    a 595px source (still worse than SVG would give us)."""
    print("\n── 2. Favicon family (resampled from imageonly.png) ──")
    mark = Image.open(source / "imageonly.png").convert("RGBA")
    for name, size in FAVICON_SIZES.items():
        resized = mark.resize((size, size), Image.Resampling.LANCZOS)
        save_png(resized, OUT / name)

    # Multi-resolution .ico for legacy browsers + Windows OS shortcuts.
    # Modern browsers prefer the per-size PNG `<link rel="icon">` chain;
    # this is here so Internet Explorer 11 era still gets a sharp icon.
    print("\n── 3. Multi-resolution favicon.ico ──")
    ico_sizes = [(16, 16), (32, 32), (48, 48)]
    ico_path = OUT / "favicon.ico"
    mark.save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
    )
    print(f"  wrote {ico_path.relative_to(ROOT)} ({ico_path.stat().st_size:,} bytes, sizes={ico_sizes})")


# build_og_card() was removed. The OG / social cards are now
# hand-designed marketing graphics, not auto-generated from the lockup:
# assets/images/og-image.png (the general card, used on every page) and
# assets/images/og-image-people.png (the directory card, used on
# /people.html). They are maintained as design assets, so this script no
# longer touches them and a brand rebuild cannot clobber them.
# scripts/inject-seo.py selects which card each page advertises.


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the designer's LOGO_RASTER folder.",
    )
    args = p.parse_args()

    if not args.source.exists():
        sys.exit(f"Source folder not found: {args.source}")

    print(f"Brand-asset build")
    print(f"  source: {args.source}")
    print(f"  output: {OUT.relative_to(ROOT)}")

    process_lockups(args.source)
    build_favicons(args.source)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
