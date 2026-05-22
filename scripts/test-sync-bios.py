#!/usr/bin/env python3
"""
Smoke tests for scripts/sync-bios.py.

Not a pytest test tree — the rest of the repo doesn't have one and the
sync script doesn't need that ceremony. Just a standalone runnable that
asserts on a handful of representative cases.

Usage:
    python3 scripts/test-sync-bios.py

Exits non-zero on the first failed assertion. No network calls — uses
in-memory fixtures, never fetches the live Google Sheet.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import the module under test as a sibling.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sync_bios = __import__("sync-bios")
name_key = sync_bios.name_key
country_key = sync_bios.country_key
slugify = sync_bios.slugify
merge = sync_bios.merge
download_photo = sync_bios.download_photo


def expect(label: str, got, want) -> None:
    if got != want:
        print(f"FAIL: {label}\n  got:  {got!r}\n  want: {want!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  ok  {label}")


def test_name_key() -> None:
    print("\nname_key():")
    expect("plain two-token", name_key("John Helferich"), ("john", "helferich"))
    expect("title prefix dropped", name_key("Dr John Helferich"), ("john", "helferich"))
    expect("middle initial dropped", name_key("Dr John N.T. Helferich"), ("john", "helferich"))
    expect("title with period", name_key("Dr. Moritz Weiss"), ("moritz", "weiss"))
    expect("diacritics stripped", name_key("Andreas Müller"), ("andreas", "muller"))
    expect("apostrophe stripped", name_key("Silvia D'Amato"), ("silvia", "damato"))
    expect("post-nominal stripped", name_key("Jane Doe PhD"), ("jane", "doe"))
    expect("suffix Jr stripped", name_key("John Smith Jr"), ("john", "smith"))
    expect("single-token returns None", name_key("Madonna"), None)
    expect("empty string returns None", name_key(""), None)
    expect("title only returns None", name_key("Dr"), None)


def test_country_key() -> None:
    print("\ncountry_key():")
    expect("lowercased", country_key("United Kingdom"), "united kingdom")
    expect("trimmed", country_key("  France  "), "france")
    expect("empty stays empty", country_key(""), "")
    expect("None safely empty", country_key(None), "")  # type: ignore[arg-type]


def test_merge_helferich() -> None:
    """The canonical regression: seed entry for Dr John Helferich +
    form submission as Dr John N.T. Helferich → ONE merged entry on
    the seed slug, with the form's name and content, the seed's role,
    and the union of WGs."""
    print("\nmerge() — Helferich regression:")
    prior = [
        {
            "id": "john-helferich",
            "name": "Dr John Helferich",
            "country": "United Kingdom",
            "country_code": "gb",
            "roles": ["WG2 Leader"],
            "wgs": [1],
            "wg_leadership": {"lead": [2]},
            "email": "",
            "photo": "assets/images/people/john-helferich.jpeg",
            "source": "seed",
        },
    ]
    form_entries = [
        {
            "id": "john-n-t-helferich",  # what slugify() gives the new name
            "name": "Dr John N.T. Helferich",
            "country": "United Kingdom",
            "country_code": "",
            "affiliation": "University of Oxford",
            "position": "Lecturer in Politics",
            "roles": [],
            "wgs": [2],
            "wg_leadership": {},
            "bio": "Lecturer at Hertford College.",
            "keywords": ["EU Defence"],
            "email": "john.helferich@hertford.ox.ac.uk",
            "website": "johnhelferich.com",
            "orcid": "",
            "linkedin": "",
            "twitter": "",
            "bluesky": "",
            "mastodon": "",
            # No photo in this fixture — keeps the test offline.
            "photo": "",
            "source": "form",
            "_email_key": "john.helferich@hertford.ox.ac.uk",
            "_timestamp": "2026-05-22 10:00:00",
        },
    ]
    merged = merge(prior, form_entries)
    expect("one entry, not two", len(merged), 1)
    m = merged[0]
    expect("id preserved", m["id"], "john-helferich")
    expect("name from form", m["name"], "Dr John N.T. Helferich")
    expect("role preserved", m["roles"], ["WG2 Leader"])
    expect("wg_leadership preserved", m["wg_leadership"], {"lead": [2]})
    expect("wgs union", sorted(m["wgs"]), [1, 2])
    expect("affiliation from form", m["affiliation"], "University of Oxford")
    expect("bio from form", m["bio"], "Lecturer at Hertford College.")


def test_merge_country_guards_false_positive() -> None:
    """Two genuinely different people who happen to share first + last
    names should NOT collapse. Distinct countries → two entries."""
    print("\nmerge() — country guard against false positives:")
    prior = [
        {"id": "maria-garcia", "name": "Dr Maria Garcia", "country": "Spain", "roles": [], "wgs": [1]},
    ]
    form_entries = [
        {
            "id": "maria-garcia",   # SAME slug — already covered by signal #2
            "name": "Maria Garcia",
            "country": "Portugal",  # different country
            "country_code": "",
            "_email_key": "",
            "_timestamp": "2026-05-22 10:00:00",
        },
    ]
    merged = merge(prior, form_entries)
    # Same slug — signal #2 collapses them regardless of country. This
    # test exists to document the boundary: signal #2 (slug equality)
    # is *not* country-guarded; signal #3 (name+country) is. A future
    # tightening could add country-mismatch warnings on signal-#2 hits.
    expect("slug match still collapses regardless of country (existing behaviour)", len(merged), 1)


def test_merge_name_match_different_country_does_not_collapse() -> None:
    """Different first-letter slug + different country → no collapse.
    Two distinct entries survive."""
    print("\nmerge() — name match with different countries leaves entries apart:")
    prior = [
        {"id": "maria-garcia", "name": "Dr Maria Garcia", "country": "Spain", "roles": [], "wgs": [1]},
    ]
    form_entries = [
        {
            "id": "maria-jose-garcia",   # different slug
            "name": "Maria José Garcia",
            "country": "Portugal",       # different country guards the merge
            "country_code": "",
            "_email_key": "",
            "_timestamp": "2026-05-22 10:00:00",
            "wgs": [],
        },
    ]
    merged = merge(prior, form_entries)
    expect("two entries (no collapse)", len(merged), 2)


def test_merge_name_match_same_country_collapses() -> None:
    """The Helferich case at the more general scale — names that
    slugify() splits apart but that share first + last + country are
    treated as the same person."""
    print("\nmerge() — name+country match without email collapses entries:")
    prior = [
        {"id": "maria-garcia", "name": "Dr Maria Garcia", "country": "Spain", "roles": ["WG3 Leader"], "wgs": [3]},
    ]
    form_entries = [
        {
            "id": "maria-elena-garcia",
            "name": "Maria Elena Garcia",
            "country": "Spain",
            "country_code": "",
            "_email_key": "",
            "_timestamp": "2026-05-22 10:00:00",
            "wgs": [],
        },
    ]
    merged = merge(prior, form_entries)
    expect("one entry after collapse", len(merged), 1)
    expect("seed id preserved", merged[0]["id"], "maria-garcia")
    expect("role preserved", merged[0]["roles"], ["WG3 Leader"])


def test_download_photo_idempotent_on_unchanged_upstream() -> None:
    """The fix for the empty-PR bug. download_photo computes a sha256
    of the raw upstream bytes; on a second call with the same
    `prior_hash` and an existing dest file, it must NOT re-encode and
    must NOT write — even though PIL/libjpeg-turbo would otherwise
    emit subtly different bytes on the second run, dirtying the
    working tree and triggering an auto-PR with a lone binary diff.
    """
    print("\ndownload_photo() — idempotent on unchanged upstream:")
    import io as _io
    try:
        from PIL import Image as _Image
    except ImportError:
        print("  skip — Pillow not available")
        return

    # Build a small in-memory JPEG fixture (different content than
    # whatever the real Drive URL would return — pure isolation).
    fixture = _Image.new("RGB", (320, 240), (180, 60, 90))
    buf = _io.BytesIO()
    fixture.save(buf, format="JPEG", quality=88)
    raw_jpeg_bytes = buf.getvalue()

    class _MockResponse:
        def __init__(self, data: bytes):
            self.content = data
        def raise_for_status(self) -> None:
            pass

    saved_get = sync_bios.requests.get
    saved_drive_id = sync_bios.drive_file_id
    sync_bios.requests.get = lambda *args, **kwargs: _MockResponse(raw_jpeg_bytes)
    # Skip the drive_file_id parsing — we're using a fake URL.
    sync_bios.drive_file_id = lambda url: None

    # download_photo computes its return path as `dest.relative_to(ROOT)`,
    # so the fixture has to live under ROOT. Use PHOTO_DIR with a
    # test-only slug that we clean up in `finally` regardless of how
    # the test exits.
    slug = "zztest-idempotent-fixture"
    dest_no_ext = sync_bios.PHOTO_DIR / slug
    dest_jpg = dest_no_ext.with_suffix(".jpg")
    if dest_jpg.exists():
        dest_jpg.unlink()

    try:
        # First call: no prior hash → re-encode + write.
        path1, hash1 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash=None,
        )
        expect("first call returns path",        path1 is not None, True)
        expect("first call returns hash",        bool(hash1), True)
        expect("first call wrote file",          dest_jpg.exists(), True)

        jpeg_after_first = dest_jpg.read_bytes()
        mtime_after_first = dest_jpg.stat().st_mtime_ns

        # Second call: prior hash matches → must NOT write.
        path2, hash2 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash=hash1,
        )
        expect("second call returns same path",  path2, path1)
        expect("second call returns same hash",  hash2, hash1)
        expect("second call did not touch file (bytes)",
               dest_jpg.read_bytes(), jpeg_after_first)
        expect("second call did not touch file (mtime)",
               dest_jpg.stat().st_mtime_ns, mtime_after_first)

        # Third call with a wrong prior_hash → falls through and
        # re-encodes; the byte-equality guard then catches the
        # write (PIL is deterministic for THIS process, even if
        # not across PIL minor-version updates).
        path3, hash3 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash="deadbeef",
        )
        expect("wrong prior_hash → returns same path", path3, path1)
        expect("wrong prior_hash → returns the upstream hash, not the bogus prior",
               hash3, hash1)
    finally:
        sync_bios.requests.get = saved_get
        sync_bios.drive_file_id = saved_drive_id
        if dest_jpg.exists():
            dest_jpg.unlink()


def main() -> None:
    test_name_key()
    test_country_key()
    test_merge_helferich()
    test_merge_country_guards_false_positive()
    test_merge_name_match_different_country_does_not_collapse()
    test_merge_name_match_same_country_collapses()
    test_download_photo_idempotent_on_unchanged_upstream()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
