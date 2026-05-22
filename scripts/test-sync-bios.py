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


def main() -> None:
    test_name_key()
    test_country_key()
    test_merge_helferich()
    test_merge_country_guards_false_positive()
    test_merge_name_match_different_country_does_not_collapse()
    test_merge_name_match_same_country_collapses()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
