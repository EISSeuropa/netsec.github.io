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
parse_mentorship = sync_bios.parse_mentorship
ensure_people_webp = sync_bios.ensure_people_webp
load_keyword_themes = sync_bios.load_keyword_themes
resolve_prior_entry = sync_bios.resolve_prior_entry


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
    # Directory badge labels (what a maintainer might type into the Sheet
    # by hand) are recognised too, not only the Form-option wording.
    expect("badge 'Available to mentor' -> mentor",
           parse_mentorship("Available to mentor"), ["mentor"])
    expect("badge 'Seeking mentorship' -> mentee",
           parse_mentorship("Seeking mentorship"), ["mentee"])
    expect("both badge labels",
           parse_mentorship("Available to mentor, Seeking mentorship"),
           ["mentor", "mentee"])


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
    expect("disinformation → Information and influence",
           theme_of.get("disinformation"), "Information and influence")
    expect("eu foreign policy → Foreign and security policy",
           theme_of.get("eu foreign policy"), "Foreign and security policy")
    expect("policy evaluation → Research methods and behaviour",
           theme_of.get("policy evaluation"), "Research methods and behaviour")
    expect("economic statecraft → Economic security and statecraft",
           theme_of.get("economic statecraft"), "Economic security and statecraft")
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


def main() -> None:
    test_name_key()
    test_normalise_keyword()
    test_load_keyword_themes()
    test_normalise_affiliation()
    test_parse_mentorship()
    test_country_key()
    test_merge_helferich()
    test_merge_country_guards_false_positive()
    test_merge_name_match_different_country_does_not_collapse()
    test_merge_name_match_same_country_collapses()
    test_merge_mentorship_propagates()
    test_resolve_prior_entry()
    test_download_photo_idempotent_on_unchanged_upstream()
    test_ensure_people_webp()
    test_substance_check_catches_photo_only_change()
    test_pr_title_and_overview()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
