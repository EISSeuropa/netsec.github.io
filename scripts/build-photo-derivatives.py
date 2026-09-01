#!/usr/bin/env python3
"""Write a display-sized .webp beside every editorial photograph (#1615).

The conference gallery on /essc-2026.html served four 1400px JPEGs, 1.35 MB
between them, into a grid that renders each at most 327x240 CSS px. It was the
last page over the `resource-summary:image:size` budget in lighthouserc.json,
and a budget that warns on every run stops being read.

Same reading as the Network Map's faces (#1480): generate a derivative sized
to how the image actually renders, and prefer it where it exists. 1000px wide
covers the widest case, a 327px slot on a 3x phone, with room to spare.

These are hand-added editorial photographs rather than form submissions, so
they do not belong in sync-bios.py. This runs on demand, and in CI as a drift
gate, the same way build-calendar.py and build-network-map.py do.

Usage:
  python3 scripts/build-photo-derivatives.py           # write missing/stale derivatives
  python3 scripts/build-photo-derivatives.py --check    # exit 1 if any is missing or stale

Needs Pillow. Without it the script says so and exits 0 rather than failing a
run that never asked for images.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories of editorial photography. Member headshots are not here: they
# arrive through the bios form and sync-bios.py already derives their variants.
PHOTO_DIRS = [REPO / "assets" / "images" / "essc-2026"]

MAX_WIDTH = 1000
QUALITY = 80
SOURCE_SUFFIXES = (".jpg", ".jpeg", ".png")


def sources() -> list[Path]:
    out: list[Path] = []
    for directory in PHOTO_DIRS:
        if not directory.exists():
            continue
        out += [p for p in sorted(directory.iterdir())
                if p.suffix.lower() in SOURCE_SUFFIXES]
    return out


def render(src: Path) -> bytes:
    """Encode `src` to the derivative's bytes without touching the disk."""
    from PIL import Image
    buf = io.BytesIO()
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > MAX_WIDTH:
            height = round(im.height * MAX_WIDTH / im.width)
            im = im.resize((MAX_WIDTH, height), Image.LANCZOS)
        im.save(buf, "WEBP", quality=QUALITY, method=6)
    return buf.getvalue()


def is_stale(src: Path, derivative: Path) -> bool:
    """A derivative is stale when it is missing, or when re-encoding its
    source gives different bytes.

    This used to compare mtimes, which is the rule sync-bios.py used until
    #1761. Git does not store mtimes, so actions/checkout stamps every file
    with the checkout time in index order, and a source written after its
    derivative looks newer on every run. It was correct here only because
    `.webp` sorts after `.jpg`, `.jpeg` and `.png`, so the derivative always
    happened to be written last. Adding a subdirectory to PHOTO_DIRS whose
    name sorts before the filenames in it would have broken that, and here
    the failure mode is a drift gate that fails on every pull request.
    Comparing bytes does not depend on where a path sorts. The encode is
    deterministic for a given source and Pillow build, so it is also the
    honest test of whether the derivative is current.
    """
    return not derivative.exists() or derivative.read_bytes() != render(src)


def build(src: Path, derivative: Path) -> None:
    derivative.write_bytes(render(src))


def main(argv: list) -> int:
    check = "--check" in argv
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("  Pillow is not installed, so no derivatives were written.",
              file=sys.stderr)
        return 0

    stale = []
    for src in sources():
        derivative = src.with_suffix(".webp")
        if not is_stale(src, derivative):
            continue
        if check:
            stale.append(derivative.relative_to(REPO).as_posix())
        else:
            build(src, derivative)
            print(f"✓ wrote {derivative.relative_to(REPO).as_posix()} "
                  f"({derivative.stat().st_size // 1024} KB from "
                  f"{src.stat().st_size // 1024} KB)")

    if check:
        if stale:
            for name in stale:
                print(f"✗ {name} is missing or older than its source",
                      file=sys.stderr)
            print("  Run: python3 scripts/build-photo-derivatives.py",
                  file=sys.stderr)
            return 1
        print("✓ every editorial photograph has a current .webp")
        return 0

    print(f"✓ {len(sources())} photograph(s) checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
