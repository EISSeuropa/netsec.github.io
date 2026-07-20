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
classify_diff = sync_bios.classify_diff
render_pr_title = sync_bios.render_pr_title
render_pr_body_overview = sync_bios.render_pr_body_overview
load_keyword_aliases = sync_bios.load_keyword_aliases
normalise_keyword = sync_bios.normalise_keyword
normalise_affiliation = sync_bios.normalise_affiliation
normalise_url = sync_bios.normalise_url
normalise_bluesky = sync_bios.normalise_bluesky
parse_mentorship = sync_bios.parse_mentorship
parse_stsm_hosting = sync_bios.parse_stsm_hosting
parse_regions = sync_bios.parse_regions
load_region_vocab = sync_bios.load_region_vocab
ensure_people_webp = sync_bios.ensure_people_webp
load_keyword_themes = sync_bios.load_keyword_themes
resolve_prior_entry = sync_bios.resolve_prior_entry
load_founding_slugs = sync_bios.load_founding_slugs
apply_founding_flag = sync_bios.apply_founding_flag


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
    # Title glued to the name by a dot with no space (the Yanina Shved-Dogrul
    # duplicate): must strip so it collapses onto the "Ms Yanina" twin.
    expect("dotted title, no space", name_key("Mrs.Yanina Shved-Dogrul"), ("yanina", "dogrul"))
    expect("…matches the spaced-title twin", name_key("Ms Yanina Shved-Dogrul"), ("yanina", "dogrul"))
    expect("real name starting Dr- preserved", name_key("Drew Barry"), ("drew", "barry"))
    expect("gender-neutral Mx dropped", name_key("Mx Sam Smith"), ("sam", "smith"))
    expect("diacritics stripped", name_key("Andreas Müller"), ("andreas", "muller"))
    expect("apostrophe stripped", name_key("Silvia D'Amato"), ("silvia", "damato"))
    expect("post-nominal stripped", name_key("Jane Doe PhD"), ("jane", "doe"))
    expect("suffix Jr stripped", name_key("John Smith Jr"), ("john", "smith"))
    expect("single-token returns None", name_key("Madonna"), None)
    expect("empty string returns None", name_key(""), None)
    expect("title only returns None", name_key("Dr"), None)


def test_slugify_titles() -> None:
    """A title glued to the name by a dot with no space ("Mrs.Yanina") must
    strip to the same slug as the spaced-title spelling, so a member who
    submits both ways collapses to one card rather than two."""
    print("\nslugify() title handling:")
    expect("spaced title", slugify("Ms Yanina Shved-Dogrul"), "yanina-shved-dogrul")
    expect("dotted title, no space", slugify("Mrs.Yanina Shved-Dogrul"), "yanina-shved-dogrul")
    expect("dotted title with space", slugify("Dr. John Smith"), "john-smith")
    expect("real name starting Dr- preserved", slugify("Drew Barry"), "drew-barry")


def test_normalise_title() -> None:
    """House style: Mr/Mrs/Ms/Mx/Dr carry no full stop; Prof carries one."""
    print("\nnormalise_title():")
    nt = sync_bios.normalise_title
    expect("Dr. -> Dr",            nt("Dr. John Smith"), "Dr John Smith")
    expect("Mr. -> Mr",            nt("Mr. Jane Doe"), "Mr Jane Doe")
    expect("Prof -> Prof.",        nt("Prof Filip Ejdus"), "Prof. Filip Ejdus")
    expect("Prof. stays Prof.",    nt("Prof. Filip Ejdus"), "Prof. Filip Ejdus")
    expect("Professor -> Prof.",   nt("Professor Mark Rhinard"), "Prof. Mark Rhinard")
    expect("Doctor -> Dr",         nt("Doctor Jane Roe"), "Dr Jane Roe")
    expect("glued dotted title",   nt("Mrs.Yanina Shved-Dogrul"), "Mrs Yanina Shved-Dogrul")
    expect("stacked titles",       nt("Prof. Dr. Hans Müller"), "Prof. Dr Hans Müller")
    expect("real name preserved",  nt("Drew Barry"), "Drew Barry")
    expect("no title untouched",   nt("Sara Russo"), "Sara Russo")
    expect("empty safe",           nt(""), "")
    # The written-out title must not leak into the slug or the match key,
    # which is what split "Professor Mark Rhinard" onto its own card with a
    # "professor-..." id before the full-word forms were recognised.
    expect("Professor not in slug", sync_bios.slugify("Professor Mark Rhinard"),
           "mark-rhinard")
    expect("Professor not in key",  sync_bios.name_key("Professor Mark Rhinard"),
           ("mark", "rhinard"))


def test_build_name() -> None:
    """The Title dropdown and Full name combine into a house-styled name,
    with a fallback to the legacy single-field header."""
    print("\nbuild_name():")
    cols = {"title": "Title", "name": "Full name",
            "name_legacy": "Full name (with title — Dr / Prof / Mr / Ms / Mx)"}
    bn = lambda row: sync_bios.build_name(row, cols)
    expect("title + name",
           bn({"Title": "Prof.", "Full name": "Mark Rhinard"}), "Prof. Mark Rhinard")
    expect("Dr keeps no dot",
           bn({"Title": "Dr", "Full name": "Jane Roe"}), "Dr Jane Roe")
    expect("None please -> no title",
           bn({"Title": "None please", "Full name": "Mark Rhinard"}), "Mark Rhinard")
    expect("blank title -> no title",
           bn({"Title": "", "Full name": "Mark Rhinard"}), "Mark Rhinard")
    expect("typed title not duplicated",
           bn({"Title": "Prof.", "Full name": "Prof. Mark Rhinard"}), "Prof. Mark Rhinard")
    expect("dropdown overrides typed title",
           bn({"Title": "Dr", "Full name": "Prof. Mark"}), "Dr Mark")
    expect("legacy single-field fallback",
           bn({"Full name (with title — Dr / Prof / Mr / Ms / Mx)": "Dr Silvia D'Amato"}),
           "Dr Silvia D'Amato")
    expect("legacy written-out title folds",
           bn({"Full name (with title — Dr / Prof / Mr / Ms / Mx)": "Professor Mark Rhinard"}),
           "Prof. Mark Rhinard")


def test_parse_keywords() -> None:
    """Resilient to whatever separator a submitter reaches for, while never
    splitting an intra-keyword hyphen."""
    print("\nparse_keywords():")
    pk = sync_bios.parse_keywords
    expect("commas",          pk("a, b, c"), ["a", "b", "c"])
    expect("semicolons",      pk("a; b"), ["a", "b"])
    expect("spaced dash",     pk("cyber - AI - defence"), ["cyber", "AI", "defence"])
    expect("slash separator", pk("Foreign policy / Security"), ["Foreign policy", "Security"])
    expect("newline bullets", pk("- cyber\n- AI"), ["cyber", "AI"])
    expect("intra-word hyphen kept", pk("Civil-military relations, Deterrence"),
           ["Civil-military relations", "Deterrence"])
    expect("acronym hyphen kept", pk("EU-NATO relations"), ["EU-NATO relations"])
    expect("empty", pk(""), [])


def test_suggest_theme() -> None:
    """Suggests the theme of the nearest already-mapped keyword, or None."""
    print("\nsuggest_theme():")
    theme_of = {
        "cyber security": "Cyber and emerging technology",
        "maritime security": "Transnational and human security",
        "national security": "Security and defence",
    }
    st = sync_bios.suggest_theme
    expect("shared word -> theme", (st("Cyber resilience", theme_of) or [None])[0],
           "Cyber and emerging technology")
    expect("nothing close -> None", st("Banana bread", theme_of), None)
    expect("empty -> None", st("", theme_of), None)


def test_region_names_dropped_from_keywords() -> None:
    """A region name typed into the keyword box is excluded from keywords:
    geography belongs to the regions facet. The sync drops any normalised
    keyword whose lowercase form is in the regions vocabulary."""
    print("\nregion-name keyword drop:")
    vocab = load_region_vocab()
    # The predicate the keyword loop uses: `canon.lower() in region_vocab`.
    expect("region name is in vocab (would drop)", "The Americas".lower() in vocab, True)
    expect("real keyword not in vocab (kept)", "Maritime security".lower() in vocab, False)


def test_country_key() -> None:
    print("\ncountry_key():")
    expect("lowercased", country_key("United Kingdom"), "united kingdom")
    expect("trimmed", country_key("  France  "), "france")
    expect("empty stays empty", country_key(""), "")
    expect("None safely empty", country_key(None), "")  # type: ignore[arg-type]


def test_title_only_name_skipped() -> None:
    """A form row whose name is only a title ("Mr") with nothing after it is
    an incomplete submission. row_to_member must drop it: slugify/name_key
    strip the title to nothing, so it can never collapse onto the real entry
    and would otherwise surface as a duplicate "Mr" card."""
    print("\nrow_to_member() title-only name:")
    cols = {"name": "name", "consent": "consent"}
    for n in ("Mr", "Dr.", "Ms", "Prof", "Mx", "  Mrs  "):
        expect(f"{n!r} dropped",
               sync_bios.row_to_member({"name": n, "consent": "yes"}, cols), None)
    kept = sync_bios.row_to_member(
        {"name": "Mr Archishman Goswami", "consent": "yes"}, cols)
    expect("real name after title kept", kept is not None and kept.get("name"),
           "Mr Archishman Goswami")


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


def test_merge_mentorship_propagates() -> None:
    """A form submission carrying a mentorship facet must overwrite the
    matched prior entry's mentorship, the same way keywords do. Regression
    for the merge field allow-list omitting `mentorship`, which silently
    dropped the facet for any member who already had a directory entry."""
    print("\nmerge() — mentorship propagates onto a prior entry:")
    prior = [
        {"id": "arthur-laudrain", "name": "Dr Arthur Laudrain", "country": "Switzerland",
         "roles": ["Science Communication Coordinator"], "wgs": [], "source": "seed"},
    ]
    form_entries = [
        {
            "id": "arthur-laudrain", "name": "Dr Arthur Laudrain", "country": "Switzerland",
            "country_code": "", "mentorship": ["mentor"], "wgs": [],
            "source": "form", "_email_key": "", "_timestamp": "2026-06-04 09:00:00",
        },
    ]
    merged = merge(prior, form_entries)
    expect("one entry", len(merged), 1)
    expect("mentorship carried from form", merged[0].get("mentorship"), ["mentor"])
    expect("role preserved", merged[0]["roles"], ["Science Communication Coordinator"])


def test_merge_stsm_propagates() -> None:
    """A form submission carrying an STSM-hosting answer must overwrite the
    matched prior entry's `stsm_hosting`, the same way mentorship does.
    Regression for the merge field allow-list omitting `stsm_hosting` (added
    by #760 but never added to the overwrite loop), which silently dropped a
    member's changed answer for anyone who already had a directory entry."""
    print("\nmerge() — STSM hosting propagates onto a prior entry:")
    prior = [
        {"id": "arthur-laudrain", "name": "Dr Arthur Laudrain", "country": "Switzerland",
         "roles": ["Science Communication Coordinator"], "wgs": [], "source": "seed"},
    ]
    form_entries = [
        {
            "id": "arthur-laudrain", "name": "Dr Arthur Laudrain", "country": "Switzerland",
            "country_code": "", "stsm_hosting": "yes", "wgs": [],
            "source": "form", "_email_key": "", "_timestamp": "2026-06-13 09:00:00",
        },
    ]
    merged = merge(prior, form_entries)
    expect("one entry", len(merged), 1)
    expect("stsm_hosting carried from form", merged[0].get("stsm_hosting"), "yes")
    expect("role preserved", merged[0]["roles"], ["Science Communication Coordinator"])


def test_merge_allowlist_covers_every_form_field() -> None:
    """Structural guard against the whole class of bug behind #874: every
    field row_to_member emits from a form row must be either overwritten by
    merge() (sync_bios._FORM_OVERWRITE_FIELDS) or deliberately excluded
    (sync_bios._MERGE_EXCLUDED_FIELDS). When a new Form question is parsed
    into a new field but added to neither, this fails — so it can never
    again be silently dropped the way `mentorship` and `stsm_hosting` were
    when a returning member resubmitted. The fix when it fails is named in
    the assertion: add the new field to one of the two sets in sync-bios.py."""
    print("\nmerge() — overwrite allow-list covers every form-sourced field:")
    # A minimal row that clears the consent gate; every other column is
    # absent, so there is no photo download and the entry carries empty
    # values — but all the keys row_to_member emits are present, which is
    # what we check.
    entry = sync_bios.row_to_member(
        {"name": "Test Person", "consent": "yes"},
        {"name": "name", "consent": "consent"},
    )
    expect("row_to_member returns an entry", entry is not None, True)
    content = {k for k in entry if not k.startswith("_")}
    covered = set(sync_bios._FORM_OVERWRITE_FIELDS) | set(sync_bios._MERGE_EXCLUDED_FIELDS)
    expect("every form field is overwritten or explicitly excluded by merge()",
           sorted(content - covered), [])


def test_resolve_prior_entry() -> None:
    """The photo-churn fix: a name-collapse submission must resolve to
    its canonical prior entry (by name+country) so the photo writes to
    that slug, not the form slug. Mirrors merge()'s signal order."""
    print("\nresolve_prior_entry():")
    prior = [
        {"id": "john-helferich", "name": "Dr John Helferich",
         "country": "United Kingdom", "email": "",
         "photo_source_sha256": "abc123"},
        {"id": "maria-garcia", "name": "Dr Maria Garcia", "country": "Spain",
         "email": "maria@uni.es", "photo_source_sha256": "def456"},
    ]
    by_id = {m["id"]: m for m in prior}
    by_email = {m["email"].lower(): m for m in prior if m.get("email")}
    by_namekey = {}
    for m in prior:
        nk = name_key(m["name"])
        if nk:
            by_namekey[(nk[0], nk[1], country_key(m["country"]))] = m

    # Name-collapse: form slug differs, bridged by name+country.
    hit = resolve_prior_entry("john-n-t-helferich", "", "Dr John N.T. Helferich",
                              "United Kingdom", by_id, by_email, by_namekey)
    expect("name-collapse resolves to canonical slug", (hit or {}).get("id"), "john-helferich")
    expect("…carrying the stored hash", (hit or {}).get("photo_source_sha256"), "abc123")
    # Email match wins first.
    hit = resolve_prior_entry("someone-else", "maria@uni.es", "Maria Garcia",
                              "Spain", by_id, by_email, by_namekey)
    expect("email match resolves", (hit or {}).get("id"), "maria-garcia")
    # Plain slug match.
    hit = resolve_prior_entry("maria-garcia", "", "Maria Garcia", "Spain",
                              by_id, by_email, by_namekey)
    expect("slug match resolves", (hit or {}).get("id"), "maria-garcia")
    # Genuinely new member → None.
    hit = resolve_prior_entry("nora-newcomer", "nora@x.org", "Nora Newcomer",
                              "Finland", by_id, by_email, by_namekey)
    expect("new member resolves to None", hit, None)


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

    # Reset the module-level PHOTOS_CHANGED tracker so assertions
    # below see a clean slate. This list is shared state across tests
    # in the same process, so explicit reset keeps test ordering safe.
    sync_bios.PHOTOS_CHANGED.clear()

    try:
        # First call: no prior hash → re-encode + write.
        path1, hash1 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash=None,
        )
        expect("first call returns path",        path1 is not None, True)
        expect("first call returns hash",        bool(hash1), True)
        expect("first call wrote file",          dest_jpg.exists(), True)
        expect("first call recorded write in PHOTOS_CHANGED",
               len(sync_bios.PHOTOS_CHANGED), 1)
        expect("PHOTOS_CHANGED entry points at the written file",
               sync_bios.PHOTOS_CHANGED[0], path1)

        jpeg_after_first = dest_jpg.read_bytes()
        mtime_after_first = dest_jpg.stat().st_mtime_ns

        # Second call: prior hash matches → must NOT write, must NOT
        # append to PHOTOS_CHANGED.
        path2, hash2 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash=hash1,
        )
        expect("second call returns same path",  path2, path1)
        expect("second call returns same hash",  hash2, hash1)
        expect("second call did not touch file (bytes)",
               dest_jpg.read_bytes(), jpeg_after_first)
        expect("second call did not touch file (mtime)",
               dest_jpg.stat().st_mtime_ns, mtime_after_first)
        expect("second call did not append to PHOTOS_CHANGED",
               len(sync_bios.PHOTOS_CHANGED), 1)

        # Third call with a wrong prior_hash → falls through and
        # re-encodes; the byte-equality guard then catches the
        # write (PIL is deterministic for THIS process, even if
        # not across PIL minor-version updates). Bytes on disk
        # already match the freshly-encoded output, so no write
        # happens → PHOTOS_CHANGED stays at one entry.
        path3, hash3 = download_photo(
            "https://fake/photo.jpg", dest_no_ext, prior_hash="deadbeef",
        )
        expect("wrong prior_hash → returns same path", path3, path1)
        expect("wrong prior_hash → returns the upstream hash, not the bogus prior",
               hash3, hash1)
        expect("byte-equality fast path also avoided PHOTOS_CHANGED append",
               len(sync_bios.PHOTOS_CHANGED), 1)
    finally:
        sync_bios.requests.get = saved_get
        sync_bios.drive_file_id = saved_drive_id
        sync_bios.PHOTOS_CHANGED.clear()
        if dest_jpg.exists():
            dest_jpg.unlink()


def test_row_to_member_resolves_photo_to_canonical_slug() -> None:
    """Regression for the photo re-encode churn: main() must pass all
    three prior indexes into row_to_member so a name-collapse submission
    (form slug != canonical slug) downloads its photo to the canonical
    slug and compares against the stored hash. With only old_by_id wired
    in (the bug), resolve_prior_entry returned None, the photo wrote under
    the form slug, re-encoded every run, and merge then churned the
    canonical .webp. Captures the dest path download_photo is called with
    rather than touching the network."""
    print("\nrow_to_member() resolves photo to canonical slug:")
    prior = [
        {"id": "john-helferich", "name": "Dr John Helferich",
         "country": "United Kingdom", "email": "",
         "photo_source_sha256": "abc123"},
    ]
    by_id = {m["id"]: m for m in prior}
    by_email = {m["email"].lower(): m for m in prior if m.get("email")}
    by_namekey = {}
    for m in prior:
        nk = name_key(m["name"])
        if nk:
            by_namekey[(nk[0], nk[1], country_key(m["country"]))] = m

    captured: dict = {}

    def fake_download(url, dest_no_ext, *, prior_hash=None):
        captured["dest"] = str(dest_no_ext)
        captured["prior_hash"] = prior_hash
        return ("assets/images/people/john-helferich.jpg", "abc123")

    cols = {"name": "name", "consent": "consent", "email": "email",
            "country": "country", "photo": "photo"}
    row = {"name": "Dr John N.T. Helferich", "consent": "yes",
           "email": "", "country": "United Kingdom",
           "photo": "https://drive.example/abc"}
    saved_dl = sync_bios.download_photo
    sync_bios.download_photo = fake_download
    try:
        entry = sync_bios.row_to_member(row, cols, by_id, by_email, by_namekey)
    finally:
        sync_bios.download_photo = saved_dl
    expect("entry built", entry is not None, True)
    expect("photo writes to canonical slug",
           captured.get("dest", "").endswith("john-helferich"), True)
    expect("…not under the form slug",
           captured.get("dest", "").endswith("n-t-helferich"), False)
    expect("…comparing against the stored hash",
           captured.get("prior_hash"), "abc123")


def test_merge_keeps_webp_when_photo_already_canonical() -> None:
    """Regression: when row_to_member has already resolved a name-collapse
    photo to its canonical slug, merge()'s rebase is a no-op (src == dest)
    and must NOT delete the canonical .webp derivative. The old code
    globbed `<slug>.*` and unlinked everything but the .jpg dest, nuking
    the .webp every sync for ensure_people_webp to regenerate, churning a
    lone binary diff."""
    print("\nmerge() keeps .webp on canonical-slug collapse:")
    slug = "zztest-webp-canon"
    jpg = sync_bios.PHOTO_DIR / f"{slug}.jpg"
    webp = sync_bios.PHOTO_DIR / f"{slug}.webp"
    jpg.write_bytes(b"jpgbytes")
    webp.write_bytes(b"webpbytes")
    try:
        prior = [{
            "id": slug, "name": "Dr Test Canon", "country": "Sweden",
            "country_code": "se", "roles": [], "wgs": [], "wg_leadership": {},
            "email": "", "photo": f"assets/images/people/{slug}.jpg",
            "photo_source_sha256": "h1", "source": "seed",
        }]
        # Form entry: different slug, but photo already at canonical slug
        # (the path row_to_member now produces pre-download).
        form = [{
            "id": "test-c-canon", "name": "Dr Test C. Canon",
            "country": "Sweden", "country_code": "", "affiliation": "Lund",
            "position": "", "roles": [], "wgs": [], "wg_leadership": {},
            "bio": "", "keywords": [], "email": "", "website": "",
            "orcid": "", "linkedin": "", "twitter": "", "bluesky": "",
            "mastodon": "", "photo": f"assets/images/people/{slug}.jpg",
            "photo_source_sha256": "h1", "source": "form",
            "_email_key": "", "_timestamp": "2026-06-01 09:00:00",
        }]
        merged = sync_bios.merge(prior, form)
        expect("collapsed to one entry", len(merged), 1)
        expect("canonical .jpg preserved", jpg.exists(), True)
        expect("canonical .webp NOT deleted", webp.exists(), True)
        expect("…and its bytes untouched", webp.read_bytes(), b"webpbytes")
    finally:
        for f in (jpg, webp):
            if f.exists():
                f.unlink()


def test_substance_check_catches_photo_only_change() -> None:
    """Regression: the "no substantive changes" guard in main()
    compares `merged != old_members`. A respondent submitting a fresh
    form to update only their photo (the documented workaround for
    the Google Forms file-upload-edit bug, see #183) leaves every
    text field identical to the prior submission. The ONLY thing
    distinguishing the new state from the old is the photo bytes,
    captured as `photo_source_sha256` on the member dict.

    This test pins down the contract: when sha256 changes, the
    merge output differs from the prior, so the guard correctly
    triggers a PR. When sha256 is unchanged (respondent re-uploaded
    the same bytes), the merge output equals the prior and the
    guard correctly no-ops. A legacy bio without a stored sha256
    still triggers a PR on the next form submission, because the
    sha256 field appears for the first time.
    """
    print("\nmerge(): substance guard, photo-only resubmissions:")

    def _strip_internal(members: list[dict]) -> list[dict]:
        """Mirror what main() does before comparing. Internal `_`
        prefixed fields are stripped from `merged` by the post-loop
        in merge() but not from `prior` (the prior comes straight off
        bios.json which never carried them). For an apples-to-apples
        comparison the test must compare against the prior in the
        same shape."""
        return [{k: v for k, v in m.items() if not k.startswith("_")} for m in members]

    base_prior = {
        "id": "alex-petrova",
        "name": "Dr Alexandra Petrova",
        "country": "Germany",
        "country_code": "de",
        "roles": ["WG1 Co-Leader"],
        "wgs": [1],
        "wg_leadership": {"co_lead": [1]},
        "affiliation": "TU Berlin",
        "position": "Postdoc",
        "bio": "Researches X.",
        "keywords": ["cybersecurity"],
        "email": "alex@tu-berlin.de",
        "website": "",
        "orcid": "0000-0001-2345-6789",
        "linkedin": "https://linkedin.com/in/alex",
        "twitter": "",
        "bluesky": "",
        "mastodon": "",
        "photo": "data/photos/alex-petrova.jpg",
        "source": "form",
    }

    # Scenario 1: sparse resubmission, new photo bytes (new sha256),
    # all text fields identical to prior. Guard MUST trigger.
    prior1 = [{**base_prior, "photo_source_sha256": "OLDhash" + "0" * 57}]
    form_sparse_new_photo = [{
        "id": "alex-petrova",
        "name": "Dr Alexandra Petrova",
        "country": "Germany",
        "country_code": "",
        "affiliation": "TU Berlin",
        "position": "Postdoc",
        "roles": [],
        "wgs": [],
        "wg_leadership": {},
        "bio": "Researches X.",
        "keywords": [],
        "email": "",
        "website": "",
        "orcid": "",
        "linkedin": "",
        "twitter": "",
        "bluesky": "",
        "mastodon": "",
        "photo": "data/photos/alex-petrova.jpg",
        "photo_source_sha256": "NEWhash" + "1" * 57,
        "source": "form",
        "_email_key": "alex@tu-berlin.de",
        "_timestamp": "2026-05-25 10:00:00",
    }]
    merged1 = merge(prior1, form_sparse_new_photo)
    expect("photo-only change → merged differs from prior",
           merged1 != _strip_internal(prior1), True)
    expect("photo-only change → new sha replaces old",
           merged1[0]["photo_source_sha256"], "NEWhash" + "1" * 57)
    # Sparse resubmission must NOT wipe optional fields the respondent
    # left blank in the new form. (Already covered by truthy-merge logic
    # in merge() but worth pinning here since the photo workaround makes
    # this guarantee user-visible.)
    expect("sparse: LinkedIn survives",
           merged1[0]["linkedin"], "https://linkedin.com/in/alex")
    expect("sparse: ORCID survives",
           merged1[0]["orcid"], "0000-0001-2345-6789")
    expect("sparse: keywords survive",
           merged1[0]["keywords"], ["cybersecurity"])
    expect("sparse: role survives",
           merged1[0]["roles"], ["WG1 Co-Leader"])

    # Scenario 2: respondent re-uploaded byte-identical photo (same
    # sha256). Nothing genuinely changed. Guard MUST no-op.
    prior2 = [{**base_prior, "photo_source_sha256": "SAMEhash" + "0" * 56}]
    form_same_photo = [{**form_sparse_new_photo[0],
                        "photo_source_sha256": "SAMEhash" + "0" * 56}]
    merged2 = merge(prior2, form_same_photo)
    expect("identical photo → merged equals prior",
           merged2 == _strip_internal(prior2), True)

    # Scenario 3: legacy bio without a stored sha256 (e.g. a member
    # that pre-dates the photo_source_sha256 field). The first new
    # submission populates the field, which itself is a substance
    # change that triggers a one-time migration PR. Acceptable.
    prior3_legacy = {k: v for k, v in base_prior.items()}
    # explicitly no photo_source_sha256 on the prior
    prior3 = [prior3_legacy]
    merged3 = merge(prior3, form_sparse_new_photo)
    expect("legacy bio + new sha → merged differs from prior",
           merged3 != _strip_internal(prior3), True)
    expect("legacy bio + new sha → sha now stored",
           "photo_source_sha256" in merged3[0], True)


def test_pr_title_and_overview() -> None:
    """The auto-PR title + structured overview must reflect what
    actually changed so a maintainer scanning the notifications list
    can tell at a glance whether this is a new joiner, a self-update,
    or a bulk batch. classify_diff + render_pr_title +
    render_pr_body_overview drive this; they're pure functions over
    the (old, new, photos_changed) tuple, easy to test exhaustively.

    Cases covered:
      - single new member
      - single photo-only update
      - single data-only update
      - single combined (data + photo) update
      - mixed multi-actor batch (counts in title)
      - photo-only alarm (no member-level diff)
      - empty diff (fallback)
      - removed member (mentioned in body, suppressed from title)
    """
    print("\nPR title + overview rendering:")

    def _bio(mid: str, name: str, **extra: object) -> dict:
        out = {
            "id": mid,
            "name": name,
            "country": "Germany",
            "country_code": "de",
            "affiliation": "TU Berlin",
            "position": "Postdoc",
            "roles": [],
            "wgs": [],
            "wg_leadership": {},
            "bio": "Bio text.",
            "keywords": [],
            "email": "",
            "website": "",
            "orcid": "",
            "linkedin": "",
            "twitter": "",
            "bluesky": "",
            "mastodon": "",
            "photo": "",
            "source": "form",
        }
        out.update(extra)
        return out

    # Case 1: a single brand-new member.
    old = []
    new = [_bio("alex", "Dr Alexandra Petrova")]
    diff = classify_diff(old, new, [])
    expect("case-new: title names the joiner",
           render_pr_title(diff),
           "data: Dr Alexandra Petrova joined the network")
    overview = render_pr_body_overview(diff)
    expect("case-new: overview has the 'New members' header",
           "### New members (1)" in overview, True)
    expect("case-new: overview lists the bio with country + affiliation",
           "Dr Alexandra Petrova" in overview and "Germany" in overview,
           True)

    # Case 2: a single photo-only update (the workaround case for the
    # Google Forms file-upload-edit bug).
    prior = _bio("alex", "Dr Alexandra Petrova",
                 photo="data/photos/alex.jpg",
                 photo_source_sha256="OLD" + "0" * 61)
    updated = dict(prior, photo_source_sha256="NEW" + "1" * 61)
    diff = classify_diff([prior], [updated],
                         ["data/photos/alex.jpg"])
    expect("case-photo-only: title mentions headshot",
           render_pr_title(diff),
           "data: Dr Alexandra Petrova updated their headshot")
    overview = render_pr_body_overview(diff)
    expect("case-photo-only: overview lists 'headshot replaced'",
           "headshot replaced" in overview, True)
    expect("case-photo-only: overview lists the file under Headshot files",
           "data/photos/alex.jpg" in overview, True)

    # Case 3: a single data-only update.
    prior = _bio("alex", "Dr Alexandra Petrova",
                 bio="Old bio.", linkedin="")
    updated = _bio("alex", "Dr Alexandra Petrova",
                   bio="New bio.", linkedin="https://linkedin.com/in/alex")
    diff = classify_diff([prior], [updated], [])
    expect("case-data: title mentions bio update",
           render_pr_title(diff),
           "data: Dr Alexandra Petrova updated their bio")
    overview = render_pr_body_overview(diff)
    expect("case-data: overview enumerates the changed fields",
           "bio" in overview and "LinkedIn" in overview, True)
    expect("case-data: overview does NOT mention headshot",
           "headshot" in overview, False)

    # Case 4: combined data + photo update.
    prior = _bio("alex", "Dr Alexandra Petrova",
                 bio="Old.", photo="data/photos/alex.jpg",
                 photo_source_sha256="OLD" + "0" * 61)
    updated = _bio("alex", "Dr Alexandra Petrova",
                   bio="New.", photo="data/photos/alex.jpg",
                   photo_source_sha256="NEW" + "1" * 61)
    diff = classify_diff([prior], [updated],
                         ["data/photos/alex.jpg"])
    expect("case-both: title mentions both bio + headshot",
           render_pr_title(diff),
           "data: Dr Alexandra Petrova updated their bio + headshot")
    overview = render_pr_body_overview(diff)
    expect("case-both: overview line mentions '+ headshot'",
           "+ headshot" in overview, True)

    # Case 5: mixed multi-actor batch (2 new bios + 1 update).
    old5 = [_bio("alex", "Alex")]
    new5 = [
        dict(_bio("alex", "Alex"), bio="updated bio"),
        _bio("bob", "Bob"),
        _bio("carol", "Carol"),
    ]
    diff = classify_diff(old5, new5, [])
    expect("case-batch: title uses counts not names",
           render_pr_title(diff),
           "data: 2 new bios + 1 update")
    overview = render_pr_body_overview(diff)
    expect("case-batch: overview has both headers",
           "### New members (2)" in overview
           and "### Updated members (1)" in overview,
           True)

    # Case 6: photo-only alarm (substance guard didn't see a
    # member-level diff but PHOTOS_CHANGED is non-empty). render_pr_title
    # should route to the 'investigate' phrasing.
    diff = classify_diff([_bio("alex", "Alex")],
                         [_bio("alex", "Alex")],
                         ["data/photos/alex.jpg"])
    title = render_pr_title(diff)
    expect("case-alarm: title flags the situation",
           "investigate" in title.lower(), True)

    # Case 7: empty diff (the workflow should fall back to the
    # workflow-level generic title, but render_pr_title still has to
    # return something coherent rather than raise).
    diff = classify_diff([], [], [])
    expect("case-empty: title is the generic fallback",
           render_pr_title(diff), "data: weekly bios sync")
    expect("case-empty: overview is empty so the workflow can skip it",
           render_pr_body_overview(diff), "")

    # Case 8: a removed member alongside a new joiner. Removals stay
    # out of the title (they're maintainer-side admin actions, not
    # respondent events) but appear in the body.
    old8 = [_bio("departed", "Departed Person")]
    new8 = [_bio("alex", "Alex")]
    diff = classify_diff(old8, new8, [])
    title = render_pr_title(diff)
    expect("case-removed: title omits the removal",
           "joined the network" in title or "new bio" in title, True)
    expect("case-removed: title doesn't say 'removed'",
           "removed" in title.lower(), False)
    overview = render_pr_body_overview(diff)
    expect("case-removed: overview surfaces the removal",
           "### Removed members (1)" in overview, True)
    expect("case-removed: overview names the removed person",
           "Departed Person" in overview, True)


def test_normalise_keyword() -> None:
    """Keyword normalisation against the live data/keyword-aliases.json:
    American-to-British spelling, acronym preservation, whole-keyword
    aliases, and the sentence-case fallback."""
    print("\nnormalise_keyword():")
    acronyms, alias_map, spelling_map = load_keyword_aliases()

    def norm(s: str) -> str:
        return normalise_keyword(s, acronyms, alias_map, spelling_map)

    # American → British spelling, applied per word so compounds work.
    expect("defense → Defence", norm("Defense"), "Defence")
    expect("cyber defense → Cyber defence", norm("Cyber defense"), "Cyber defence")
    expect("behavioral → Behavioural", norm("Behavioral economics"), "Behavioural economics")
    expect("organization → Organisation", norm("International organization"), "International organisation")
    # Existing behaviour still holds.
    expect("acronym first word", norm("eu foreign policy"), "EU foreign policy")
    expect("acronym mid-phrase", norm("nato enlargement"), "NATO enlargement")
    expect("whole-keyword alias", norm("european union"), "EU")
    # "Cyber security" (two words) folds onto the one-word canonical, while
    # the distinct "Cyber defence" is left alone.
    expect("cyber security → Cybersecurity", norm("Cyber security"), "Cybersecurity")
    expect("cyber defence stays distinct", norm("Cyber defence"), "Cyber defence")
    expect("sentence-case fallback", norm("Grand Strategy"), "Grand strategy")
    # British spelling already correct is left untouched.
    expect("british spelling unchanged", norm("Defence policy"), "Defence policy")
    # Proper nouns (countries / regions) keep their capital mid-phrase,
    # not just as the first word (regression for #505). Examples chosen
    # to avoid the curated aliases tested below.
    expect("proper noun mid-phrase parens", norm("Counterinsurgency (Afghanistan)"),
           "Counterinsurgency (Afghanistan)")
    expect("proper noun mid-phrase", norm("Russia-Ukraine war"), "Russia-Ukraine war")
    expect("region mid-phrase", norm("NATO enlargement in Europe"), "NATO enlargement in Europe")
    expect("proper noun first word still capitalised", norm("Ukraine reconstruction"),
           "Ukraine reconstruction")
    # A standalone "&" reads as the conjunction "and"; &-bearing acronyms
    # (R&D) are matched whole and stay intact (Layer A hygiene).
    expect("ampersand → and", norm("Security & defence"), "Security and defence")
    expect("R&D acronym kept intact", norm("R&D policy"), "R&D policy")
    # Curated aliases for the current outliers (Layer A hygiene pass).
    expect("germany → german adjective alias", norm("Germany Security Policy"),
           "German security policy")
    expect("long parenthetical phrase aliased to a tag",
           norm("Policy Evaluation & Lessons Learned (Afghanistan)"), "Policy evaluation")
    expect("and-spelling of that phrase aliased too",
           norm("Policy evaluation and lessons learned (Afghanistan)"), "Policy evaluation")


def test_strip_bio_chrome() -> None:
    """Leading website-nav chrome pasted ahead of a bio is dropped, but
    real prose is never trimmed (regression for Alexandra Brankova's first
    sync, where Uppsala's "Till startsidan" / "Search" header came along)."""
    print("\nstrip_bio_chrome():")
    strip = sync_bios.strip_bio_chrome
    expect("uppsala header dropped, body kept",
           strip("Till startsidan\nSearch\n\nAlexandra is a postdoctoral fellow."),
           "Alexandra is a postdoctoral fellow.")
    expect("case-insensitive label match",
           strip("MENU\nSearch\nReal bio starts here."),
           "Real bio starts here.")
    expect("clean bio untouched",
           strip("A normal bio with no chrome at all."),
           "A normal bio with no chrome at all.")
    expect("a real sentence is never treated as chrome",
           strip("Search and rescue is my research focus."),
           "Search and rescue is my research focus.")
    expect("empty stays empty", strip(""), "")
    expect("only a chrome label collapses to empty", strip("Search"), "")


def test_normalise_affiliation() -> None:
    """Affiliation punctuation is standardised: spaced hyphen/dash -> comma
    (institution + sub-unit), semicolon -> slash (two affiliations).
    Regression for #506."""
    print("\nnormalise_affiliation():")
    expect("empty stays empty", normalise_affiliation(""), "")
    expect("None safe", normalise_affiliation(None), "")  # type: ignore[arg-type]
    expect("spaced hyphen -> comma",
           normalise_affiliation("ETH Zurich - Center for Security Studies"),
           "ETH Zurich, Center for Security Studies")
    expect("en-dash -> comma",
           normalise_affiliation("ETH Zurich – Center for Security Studies"),
           "ETH Zurich, Center for Security Studies")
    expect("semicolon -> slash",
           normalise_affiliation("Ghent University; Egmont Institute"),
           "Ghent University / Egmont Institute")
    expect("already-comma unchanged",
           normalise_affiliation("Sciences Po, Center for International Studies (CERI)"),
           "Sciences Po, Center for International Studies (CERI)")
    expect("plain name unchanged", normalise_affiliation("Sciences Po Paris"), "Sciences Po Paris")
    expect("hyphenated name with no spaces untouched",
           normalise_affiliation("Aix-Marseille University"), "Aix-Marseille University")
    expect("idempotent",
           normalise_affiliation(normalise_affiliation("ETH Zurich - Center for Security Studies")),
           "ETH Zurich, Center for Security Studies")
    # The hand-curated affiliation_aliases map folds a differently-worded
    # spelling of one institution onto its canonical name (punctuation
    # normalisation alone cannot do this). Seeded with the ETH CSS case.
    expect("alias variant folds to canonical",
           normalise_affiliation("ETH Center for Security Studies"),
           "ETH Zurich, Center for Security Studies")
    expect("canonical name is idempotent under the alias map",
           normalise_affiliation("ETH Zurich, Center for Security Studies"),
           "ETH Zurich, Center for Security Studies")


def test_normalise_url() -> None:
    """Website / profile fields become absolute URLs so the card's link
    icon never resolves to a broken relative path."""
    print("\nnormalise_url():")
    expect("empty stays empty", normalise_url(""), "")
    expect("None safe", normalise_url(None), "")  # type: ignore[arg-type]
    expect("bare domain gets https",
           normalise_url("itsallcyber.baby"), "https://itsallcyber.baby")
    expect("www prefix gets https",
           normalise_url("www.example.org/path"), "https://www.example.org/path")
    expect("https passes through",
           normalise_url("https://example.org"), "https://example.org")
    expect("http passes through",
           normalise_url("http://example.org"), "http://example.org")
    expect("leading slashes stripped before scheme",
           normalise_url("//example.org"), "https://example.org")
    expect("explicit non-web scheme left alone",
           normalise_url("mailto:a@b.eu"), "mailto:a@b.eu")
    expect("whitespace trimmed",
           normalise_url("  example.org  "), "https://example.org")
    expect("idempotent",
           normalise_url(normalise_url("itsallcyber.baby")), "https://itsallcyber.baby")


def test_normalise_bluesky() -> None:
    """A Bluesky handle in any of its three submitted forms becomes a
    profile URL the card can link to."""
    print("\nnormalise_bluesky():")
    expect("empty stays empty", normalise_bluesky(""), "")
    expect("None safe", normalise_bluesky(None), "")  # type: ignore[arg-type]
    expect("@handle -> profile URL",
           normalise_bluesky("@annapagnacco.com"),
           "https://bsky.app/profile/annapagnacco.com")
    expect("bare handle -> profile URL",
           normalise_bluesky("annapagnacco.com"),
           "https://bsky.app/profile/annapagnacco.com")
    expect("scheme-less bsky.app path -> profile URL",
           normalise_bluesky("bsky.app/profile/annapagnacco.com"),
           "https://bsky.app/profile/annapagnacco.com")
    expect("full profile URL passes through",
           normalise_bluesky("https://bsky.app/profile/annapagnacco.com"),
           "https://bsky.app/profile/annapagnacco.com")
    expect("idempotent",
           normalise_bluesky(normalise_bluesky("@annapagnacco.com")),
           "https://bsky.app/profile/annapagnacco.com")


def test_parse_mentorship() -> None:
    """Mentorship checkbox cell -> {mentor, mentee} role tags."""
    print("\nparse_mentorship():")
    expect("empty -> []", parse_mentorship(""), [])
    expect("none -> []", parse_mentorship(None), [])
    expect("offering only",
           parse_mentorship("Open to mentoring early-career researchers"),
           ["mentor"])
    expect("seeking only",
           parse_mentorship("Looking for a mentor"),
           ["mentee"])
    expect("both ticked (order: mentor, mentee)",
           parse_mentorship("Open to mentoring early-career researchers, Looking for a mentor"),
           ["mentor", "mentee"])
    expect("order-independent in cell",
           parse_mentorship("Looking for a mentor, Open to mentoring early-career researchers"),
           ["mentor", "mentee"])
    expect("unrelated text -> []",
           parse_mentorship("Maybe later"), [])
    # The two off-switches (#1416). Each retires the standing flag it
    # replaces, including when the member leaves the old box ticked, so the
    # re-parsed cell can actually take a member out of the matching pool.
    expect("at capacity -> mentor-full",
           parse_mentorship("I am currently mentoring at full capacity"),
           ["mentor-full"])
    expect("at capacity suppresses a still-ticked offer",
           parse_mentorship("Open to mentoring early-career researchers, "
                            "I am currently mentoring at full capacity"),
           ["mentor-full"])
    expect("found a mentor -> matched",
           parse_mentorship("I found a mentor through this directory"),
           ["matched"])
    expect("found a mentor suppresses a still-ticked request",
           parse_mentorship("Looking for a mentor, "
                            "I found a mentor through this directory"),
           ["matched"])
    expect("offering while matched keeps the offer",
           parse_mentorship("Open to mentoring early-career researchers, "
                            "I found a mentor through this directory"),
           ["mentor", "matched"])
    expect("badge 'Mentoring, at capacity' -> mentor-full",
           parse_mentorship("Mentoring, at capacity"), ["mentor-full"])
    # Directory badge labels (what a maintainer might type into the Sheet
    # by hand) are recognised too, not only the Form-option wording.
    expect("badge 'Available to mentor' -> mentor",
           parse_mentorship("Available to mentor"), ["mentor"])
    expect("badge 'Seeking mentorship' -> mentee",
           parse_mentorship("Seeking mentorship"), ["mentee"])
    expect("both badge labels",
           parse_mentorship("Available to mentor, Seeking mentorship"),
           ["mentor", "mentee"])


def test_parse_stsm_hosting() -> None:
    """STSM-hosting cell -> tri-state scalar 'yes' / 'ask' / '' (#760)."""
    print("\nparse_stsm_hosting():")
    expect("empty -> ''", parse_stsm_hosting(""), "")
    expect("none -> ''", parse_stsm_hosting(None), "")
    expect("whitespace -> ''", parse_stsm_hosting("   "), "")
    expect("Yes -> yes", parse_stsm_hosting("Yes"), "yes")
    expect("No -> ''", parse_stsm_hosting("No"), "")
    expect("Ask me -> ask", parse_stsm_hosting("Ask me"), "ask")
    expect("case-insensitive yes", parse_stsm_hosting("YES"), "yes")
    expect("phrase 'We can host visitors' -> yes",
           parse_stsm_hosting("We can host visitors"), "yes")
    expect("'maybe, depends on the year' -> ask",
           parse_stsm_hosting("Maybe, depends on the year"), "ask")
    # The 'ask' signal wins over a co-occurring 'yes' so a conditional
    # answer is never overstated as a firm yes.
    expect("'yes, but ask me first' -> ask",
           parse_stsm_hosting("Yes, but ask me first"), "ask")
    expect("unrelated text -> ''", parse_stsm_hosting("Not sure what this is"), "")


def test_load_region_vocab() -> None:
    """The `regions` section of data/keyword-aliases.json yields a
    lowercased → canonical-display map, the controlled vocabulary the
    directory's research-region filter draws on."""
    print("\nload_region_vocab():")
    vocab = load_region_vocab()
    expect("europe → Europe", vocab.get("europe"), "Europe")
    expect("eastern neighbours / russia (lowercased key)",
           vocab.get("europe - eastern neighbours / russia"),
           "Europe - Eastern neighbours / Russia")
    expect("the americas → The Americas", vocab.get("the americas"), "The Americas")
    expect("unknown region absent", vocab.get("atlantis"), None)


def test_parse_regions() -> None:
    """Research-regions form cell -> sorted list of canonical region names.
    Case-insensitive match against the controlled vocabulary; comma- or
    semicolon-separated; unknown values dropped; deduplicated."""
    print("\nparse_regions():")
    expect("empty -> []", parse_regions(""), [])
    expect("none -> []", parse_regions(None), [])
    expect("single canonical",
           parse_regions("Europe"), ["Europe"])
    expect("case-insensitive match",
           parse_regions("europe"), ["Europe"])
    expect("comma-separated, sorted",
           parse_regions("Europe, Africa"), ["Africa", "Europe"])
    expect("semicolon separator too",
           parse_regions("Asia; Africa"), ["Africa", "Asia"])
    expect("multi-word region with mixed case",
           parse_regions("middle east and north africa"),
           ["Middle East and North Africa"])
    expect("unknown value dropped, known kept",
           parse_regions("Europe, Narnia"), ["Europe"])
    expect("all-unknown -> []",
           parse_regions("Narnia; Atlantis"), [])
    expect("duplicates collapsed (case-insensitive)",
           parse_regions("Europe, europe, EUROPE"), ["Europe"])


def test_ensure_people_webp() -> None:
    """ensure_people_webp() writes a sibling .webp per .jpg/.jpeg/.png
    headshot, is idempotent, and ignores sources that are already .webp."""
    print("\nensure_people_webp():")
    if not sync_bios.HAS_PIL:
        print("  ok  skipped (Pillow not installed)")
        return
    import shutil
    import tempfile
    from PIL import Image

    # The dir lives under ROOT because ensure_people_webp() records each
    # write as a path relative to ROOT (the real folder always is).
    photo_dir = Path(tempfile.mkdtemp(dir=sync_bios.ROOT, prefix=".webp-test-"))
    try:
        # Three source headshots in the mixed extensions the real folder
        # carries, plus one that is already webp (must be left alone).
        Image.new("RGB", (120, 120), (90, 110, 160)).save(photo_dir / "alpha-one.jpg")
        Image.new("RGBA", (120, 120), (90, 110, 160, 255)).save(photo_dir / "beta-two.png")
        Image.new("RGB", (120, 120), (90, 110, 160)).save(photo_dir / "gamma-three.webp", format="WEBP")

        orig_dir, orig_changed = sync_bios.PHOTO_DIR, sync_bios.PHOTOS_CHANGED
        sync_bios.PHOTO_DIR = photo_dir
        sync_bios.PHOTOS_CHANGED = []
        try:
            first = ensure_people_webp()
            expect("first pass writes one webp per non-webp source", first, 2)
            expect("alpha-one.webp created", (photo_dir / "alpha-one.webp").exists(), True)
            expect("beta-two.webp created (RGBA flattened)", (photo_dir / "beta-two.webp").exists(), True)
            expect("PHOTOS_CHANGED recorded both", len(sync_bios.PHOTOS_CHANGED), 2)

            # Second pass: nothing newer, so no re-encode.
            sync_bios.PHOTOS_CHANGED = []
            second = ensure_people_webp()
            expect("idempotent second pass writes nothing", second, 0)
            expect("the already-webp source spawned no gamma-three.webp.webp",
                   (photo_dir / "gamma-three.webp.webp").exists(), False)
        finally:
            sync_bios.PHOTO_DIR = orig_dir
            sync_bios.PHOTOS_CHANGED = orig_changed
    finally:
        shutil.rmtree(photo_dir, ignore_errors=True)


def test_load_keyword_themes() -> None:
    """The `themes` section of data/keyword-aliases.json resolves each
    canonical keyword (lowercased) to exactly one broad research theme,
    which drives the directory's cluster filter."""
    print("\nload_keyword_themes():")
    theme_of = load_keyword_themes()
    expect("disinformation → Intelligence, information and influence",
           theme_of.get("disinformation"), "Intelligence, information and influence")
    expect("eu foreign policy → Foreign policy and diplomacy",
           theme_of.get("eu foreign policy"), "Foreign policy and diplomacy")
    expect("policy evaluation → Theory and methods",
           theme_of.get("policy evaluation"), "Theory and methods")
    expect("economic statecraft → Economic security and geoeconomics",
           theme_of.get("economic statecraft"), "Economic security and geoeconomics")
    # Every keyword maps to at most one theme (the loader keeps the last
    # write, but the curated file must not list a keyword under two themes).
    from collections import Counter
    import json as _json
    from pathlib import Path as _Path
    doc = _json.loads((_Path(sync_bios.__file__).resolve().parent.parent
                       / "data" / "keyword-aliases.json").read_text(encoding="utf-8"))
    counts = Counter()
    for kws in (doc.get("themes") or {}).values():
        for kw in kws:
            counts[kw.lower()] += 1
    dupes = [k for k, n in counts.items() if n > 1]
    expect("no keyword listed under two themes", dupes, [])


def test_founding_contributor_flag() -> None:
    """A bio whose name matches a founding proposer is flagged
    `founding_contributor: true` at merge time; a non-matching bio is
    not. The match runs through slugify(), so a title-prefixed or
    diacritic-bearing proposer name still resolves against the bio slug.
    Reads the real data/founding-proposers.json so the test also guards
    against the file shape drifting away from a `proposers` list."""
    print("\nfounding-contributor flag:")
    founding_slugs = load_founding_slugs()
    expect("proposer list loaded (52 names)", len(founding_slugs), 52)
    # "Dr Hugo Meijer" → "hugo-meijer" is the proposer; a synthetic bio
    # under that name must pick up the flag.
    expect("Hugo Meijer slug present", "hugo-meijer" in founding_slugs, True)

    matching = {"id": "hugo-meijer", "name": "Dr Hugo Meijer", "country": "France"}
    apply_founding_flag(matching, founding_slugs)
    expect("matching bio flagged", matching.get("founding_contributor"), True)

    non_matching = {"id": "nora-newcomer", "name": "Dr Nora Newcomer", "country": "Finland"}
    apply_founding_flag(non_matching, founding_slugs)
    expect("non-matching bio not flagged", "founding_contributor" in non_matching, False)

    # Idempotent: a stale flag on a now-non-matching entry is cleared.
    stale = {"id": "nora-newcomer", "name": "Dr Nora Newcomer",
             "country": "Finland", "founding_contributor": True}
    apply_founding_flag(stale, founding_slugs)
    expect("stale flag cleared", "founding_contributor" in stale, False)

    # End-to-end through merge(): a seed entry matching a proposer name
    # comes out flagged, a non-matching one does not.
    prior = [
        {"id": "hugo-meijer", "name": "Dr Hugo Meijer", "country": "France",
         "roles": [], "wgs": [], "source": "seed"},
        {"id": "nora-newcomer", "name": "Dr Nora Newcomer", "country": "Finland",
         "roles": [], "wgs": [], "source": "seed"},
    ]
    merged = merge(prior, [])
    by_id = {m["id"]: m for m in merged}
    expect("merge flags the proposer", by_id["hugo-meijer"].get("founding_contributor"), True)
    expect("merge leaves the newcomer unflagged",
           "founding_contributor" in by_id["nora-newcomer"], False)


def test_pr_overview_review_flags() -> None:
    """#796: the two signals the sync used to bury in stderr (keywords
    with no theme, and link fields it rewrote) surface in the auto-PR
    body's 'Review flags' section, and only when non-empty."""
    print("\nPR overview review-flags section (#796):")

    def _bio(mid: str, name: str) -> dict:
        return {"id": mid, "name": name, "country": "Germany",
                "country_code": "de", "affiliation": "TU Berlin",
                "position": "Postdoc", "roles": [], "wgs": [],
                "wg_leadership": {}, "bio": "Bio text.", "keywords": [],
                "email": "", "website": "", "orcid": "", "linkedin": "",
                "twitter": "", "bluesky": "", "mastodon": "", "photo": "",
                "source": "form"}

    diff = classify_diff([], [_bio("alex", "Alex")], [])

    # Both signals empty: the section is absent entirely.
    clean = render_pr_body_overview(diff, set(), [])
    expect("clean sync omits the Review flags section",
           "## Review flags" in clean, False)

    # Both signals present.
    uncategorised = {"Cyber security", "Cyber defence"}
    rewrites = [
        {"name": "Anna Pagnacco", "field": "website",
         "before": "itsallcyber.baby", "after": "https://itsallcyber.baby"},
        {"name": "Anna Pagnacco", "field": "bluesky",
         "before": "@annapagnacco.com",
         "after": "https://bsky.app/profile/annapagnacco.com"},
    ]
    body = render_pr_body_overview(diff, uncategorised, rewrites)
    expect("flagged overview has the Review flags header",
           "## Review flags" in body, True)
    expect("uncategorised block counts the keywords",
           "### Keywords with no theme (won't cluster) (2)" in body, True)
    expect("uncategorised block lists a keyword (sorted)",
           "- Cyber defence" in body, True)
    expect("rewrite block counts the rewrites",
           "### Link fields rewritten (2)" in body, True)
    expect("rewrite block shows before → after with the field label",
           "**Anna Pagnacco** · website: `itsallcyber.baby` → "
           "`https://itsallcyber.baby`" in body, True)
    expect("rewrite block uses the Bluesky display label",
           "Bluesky: `@annapagnacco.com`" in body, True)

    # A duplicate rewrite (same submitter processed by two rows) collapses.
    deduped = render_pr_body_overview(diff, set(), rewrites + rewrites[:1])
    expect("duplicate rewrites are de-duplicated",
           "### Link fields rewritten (2)" in deduped, True)

    # Flags with no member-level change still render (the PR exists because
    # something opened it; the flags must not be silently dropped).
    empty_diff = classify_diff([], [], [])
    flags_only = render_pr_body_overview(empty_diff, {"Power"}, [])
    expect("flags render even with no member changes",
           "### Keywords with no theme (won't cluster) (1)" in flags_only, True)
    expect("flags-only overview omits the What changed header",
           "## What changed" in flags_only, False)
    # Truly nothing to say: still empty so the workflow can skip the block.
    expect("empty diff + empty flags stays empty",
           render_pr_body_overview(empty_diff, set(), []), "")


def test_link_rewrites_captured() -> None:
    """#796: row_to_member records every link field the normaliser
    rewrote into LINK_REWRITES (raw → normalised), and leaves an
    already-canonical value uncaptured."""
    print("\nLINK_REWRITES capture in row_to_member (#796):")
    cols = {"name": "name", "consent": "consent", "website": "website",
            "bluesky": "bluesky", "linkedin": "linkedin"}
    row = {"name": "Test Person", "consent": "yes",
           "website": "itsallcyber.baby",
           "bluesky": "@handle.bsky.social",
           "linkedin": "https://www.linkedin.com/in/x"}
    sync_bios.LINK_REWRITES.clear()
    try:
        member = sync_bios.row_to_member(row, cols)
        expect("website normalised on the member entry",
               member["website"], "https://itsallcyber.baby")
        by_field = {r["field"]: r for r in sync_bios.LINK_REWRITES}
        expect("website rewrite captured", "website" in by_field, True)
        expect("website before is the raw input",
               by_field["website"]["before"], "itsallcyber.baby")
        expect("website after is the normalised URL",
               by_field["website"]["after"], "https://itsallcyber.baby")
        expect("bluesky rewrite captured", "bluesky" in by_field, True)
        expect("already-absolute linkedin is NOT captured",
               "linkedin" in by_field, False)
        expect("capture carries the member name",
               by_field["website"]["name"], "Test Person")
    finally:
        sync_bios.LINK_REWRITES.clear()


def main() -> None:
    test_name_key()
    test_normalise_keyword()
    test_strip_bio_chrome()
    test_load_keyword_themes()
    test_normalise_affiliation()
    test_normalise_url()
    test_normalise_bluesky()
    test_parse_mentorship()
    test_parse_stsm_hosting()
    test_load_region_vocab()
    test_parse_regions()
    test_slugify_titles()
    test_normalise_title()
    test_build_name()
    test_parse_keywords()
    test_suggest_theme()
    test_region_names_dropped_from_keywords()
    test_country_key()
    test_title_only_name_skipped()
    test_merge_helferich()
    test_merge_country_guards_false_positive()
    test_merge_name_match_different_country_does_not_collapse()
    test_merge_name_match_same_country_collapses()
    test_merge_mentorship_propagates()
    test_merge_stsm_propagates()
    test_merge_allowlist_covers_every_form_field()
    test_resolve_prior_entry()
    test_row_to_member_resolves_photo_to_canonical_slug()
    test_merge_keeps_webp_when_photo_already_canonical()
    test_founding_contributor_flag()
    test_download_photo_idempotent_on_unchanged_upstream()
    test_ensure_people_webp()
    test_substance_check_catches_photo_only_change()
    test_pr_title_and_overview()
    test_pr_overview_review_flags()
    test_link_rewrites_captured()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
