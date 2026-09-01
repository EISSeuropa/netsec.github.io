"""Tests for build-photo-derivatives.py (#1615).

Covers the freshness rule and the resize, which are the two places a
mistake would ship either a stale derivative or a needlessly large one.
The freshness rule compares bytes rather than mtimes since #1761.
Pillow is a hard requirement here, unlike in the script itself, where its
absence is a no-op rather than a failure.
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "build_photo_derivatives", REPO / "scripts" / "build-photo-derivatives.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

Image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")


def _jpeg(path: Path, size=(1400, 1050)) -> Path:
    Image.new("RGB", size, (120, 90, 60)).save(path, "JPEG")
    return path


def test_missing_derivative_is_stale(tmp_path):
    src = _jpeg(tmp_path / "a.jpg")
    assert mod.is_stale(src, tmp_path / "a.webp")


def test_changed_source_makes_the_derivative_stale(tmp_path):
    src = _jpeg(tmp_path / "a.jpg")
    out = tmp_path / "a.webp"
    mod.build(src, out)
    # Replace the photograph behind the same filename, the case the gate
    # exists to catch.
    Image.new("RGB", (1400, 1050), (10, 200, 30)).save(src, "JPEG")
    assert mod.is_stale(src, out)


def test_a_newer_source_mtime_alone_is_not_staleness(tmp_path):
    """The regression guard for #1761. is_stale compared mtimes until then,
    and actions/checkout stamps every file with the checkout time in index
    order, so a source that sorts after its derivative looks newer on every
    run. Same bytes means current, whatever the timestamps say."""
    src = _jpeg(tmp_path / "a.jpg")
    out = tmp_path / "a.webp"
    mod.build(src, out)
    import os
    os.utime(src, (out.stat().st_mtime + 10, out.stat().st_mtime + 10))
    assert not mod.is_stale(src, out)


def test_fresh_derivative_is_left_alone(tmp_path):
    src = _jpeg(tmp_path / "a.jpg")
    out = tmp_path / "a.webp"
    mod.build(src, out)
    assert not mod.is_stale(src, out)


def test_wide_source_is_resized_to_the_cap(tmp_path):
    src = _jpeg(tmp_path / "a.jpg", (1400, 1050))
    out = tmp_path / "a.webp"
    mod.build(src, out)
    with Image.open(out) as im:
        assert im.width == mod.MAX_WIDTH
        # Aspect preserved, so the grid's object-fit crop stays the same.
        assert im.height == round(1050 * mod.MAX_WIDTH / 1400)


def test_narrow_source_is_not_upscaled(tmp_path):
    src = _jpeg(tmp_path / "a.jpg", (600, 400))
    out = tmp_path / "a.webp"
    mod.build(src, out)
    with Image.open(out) as im:
        assert im.size == (600, 400)


def test_derivative_is_smaller_than_its_source(tmp_path):
    src = _jpeg(tmp_path / "a.jpg")
    out = tmp_path / "a.webp"
    mod.build(src, out)
    assert out.stat().st_size < src.stat().st_size
