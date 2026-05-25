#!/usr/bin/env python3
"""
One-shot brand-asset processor for the designer's logo deliverable.

Takes the designer's raw PNGs (mark only, primary lockup, white-on-
dark, monochrome) and produces the deployment set the site needs:
cleaned lockups (cropped to content bbox, no transparent padding),
a favicon family at standard sizes, the manifest icons, and an OG
social card composed from the primary lockup over a brand-coloured
background.

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

# OG card: 1200×630 is the canonical Twitter/OG size; 2× for retina.
# Card design: primary lockup centred on a soft brand-tinted canvas
# (very light blue, the lightest swatch from the palette). Matches
# the existing og-image.png 2400×1260 dimensions so HTML references
# don't need to change.
OG_SIZE = (2400, 1260)
OG_BACKGROUND = (240, 247, 255, 255)   # near-white with a hint of brand blue


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


def build_og_card(source: Path) -> None:
    """Compose a 2400×1260 OG card: primary lockup centred over a
    light-brand-tinted background. The size matches the existing
    og-image.png so the HTML meta tags don't need updating."""
    print("\n── 4. OG social card ──")
    lockup = Image.open(source / "primary.png").convert("RGBA")
    lockup = crop_to_content(lockup)

    # Scale the lockup to ~55% of the canvas width. Leaves clearance
    # on all sides (brand guidelines: 1 petal width = ~10% of mark
    # width, so 22% padding either side is well above the minimum).
    target_w = int(OG_SIZE[0] * 0.55)
    scale = target_w / lockup.size[0]
    target_h = int(lockup.size[1] * scale)
    lockup_scaled = lockup.resize((target_w, target_h), Image.Resampling.LANCZOS)

    card = Image.new("RGBA", OG_SIZE, OG_BACKGROUND)
    x = (OG_SIZE[0] - target_w) // 2
    y = (OG_SIZE[1] - target_h) // 2
    card.paste(lockup_scaled, (x, y), lockup_scaled)

    # OG image goes at /assets/images/og-image.png — same path as
    # before so no HTML change. PIL saves PNG-32 by default; RGB is
    # smaller and lossless enough for this content. Flatten alpha
    # against the background.
    card_rgb = Image.new("RGB", OG_SIZE, OG_BACKGROUND[:3])
    card_rgb.paste(card, mask=card)
    out_path = ROOT / "assets" / "images" / "og-image.png"
    card_rgb.save(out_path, "PNG", optimize=True)
    print(f"  wrote {out_path.relative_to(ROOT)} ({out_path.stat().st_size:,} bytes, 2400×1260)")


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
    build_og_card(args.source)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
