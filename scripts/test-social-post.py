#!/usr/bin/env python3
"""Test suite for scripts/social-post.py (pure logic; no network, no posting).

Run standalone:  /usr/bin/python3 scripts/test-social-post.py
Or under pytest: python3 -m pytest scripts/test-social-post.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path

_MOD = Path(__file__).resolve().parent / "social-post.py"
_spec = importlib.util.spec_from_file_location("social_post", _MOD)
sp = importlib.util.module_from_spec(_spec)
# Register before exec so @dataclass can resolve its module via sys.modules.
sys.modules["social_post"] = sp
_spec.loader.exec_module(sp)


def test_truncate_keeps_short_and_ellipsises_long():
    assert sp._truncate("hello", 20) == "hello"
    out = sp._truncate("one two three four five", 12)
    assert out.endswith("…") and len(out) <= 12


def test_bluesky_render_within_limit():
    post = sp.Post(kind="news", key="k", title="A reasonably long headline here",
                   summary="x " * 400, link="https://netsec-cost.eu/x.html")
    text = post.render("bluesky")
    assert len(text) <= sp.BLUESKY_LIMIT
    assert "https://netsec-cost.eu/x.html" in text  # link is never trimmed


def test_linkedin_render_has_summary_and_hashtags():
    post = sp.Post(kind="news", key="k", title="Headline",
                   summary="The full summary stays.", link="https://netsec-cost.eu/x.html")
    text = post.render("linkedin")
    assert "The full summary stays." in text
    assert sp.HASHTAGS in text
    assert "https://netsec-cost.eu/x.html" in text


def test_spotlight_uses_star_prefix():
    post = sp.Post(kind="spotlight", key="k", title="Member spotlight",
                   summary="Meet X.", link="https://netsec-cost.eu/people/x.html")
    assert post.render("bluesky").startswith("⭐")


def test_news_feed_parses_real_xml():
    posts = sp.read_news_feed()
    assert posts, "expected items from news.xml"
    for p in posts:
        assert p.kind == "news"
        assert p.key.startswith("news::")
        assert p.title and p.link.startswith("http")


def test_pending_respects_ledger():
    posts = sp.read_news_feed()
    assert posts
    first = posts[0]
    ledger = {"posted": [first.key]}
    pend_keys = {p.key for p in sp.pending({"news"}, ledger)}
    assert first.key not in pend_keys  # already posted -> excluded


def test_spotlight_post_shape_or_none():
    post = sp.read_spotlight()
    # Either dormant (None) or a well-formed spotlight post keyed by week.
    if post is not None:
        assert post.kind == "spotlight"
        assert post.key.startswith("spotlight::") and post.key.count("::") == 2
        assert post.link.startswith(sp.SITE + "/people/")


def test_strip_tags_and_unescape_in_feed():
    # The composer must not leak raw HTML tags into post text.
    for p in sp.read_news_feed():
        assert "<" not in p.title and "<" not in p.summary


def test_link_facets_byte_offsets():
    # Bluesky facet offsets are over UTF-8 bytes; a multibyte char before the
    # URL must shift the start. "café " is 6 bytes (é = 2).
    text = "café https://netsec-cost.eu/x.html"
    facets = sp.link_facets(text, "https://netsec-cost.eu/x.html")
    assert len(facets) == 1
    idx = facets[0]["index"]
    assert idx["byteStart"] == len("café ".encode("utf-8"))
    assert text.encode("utf-8")[idx["byteStart"]:idx["byteEnd"]].decode() == "https://netsec-cost.eu/x.html"
    assert facets[0]["features"][0]["$type"] == "app.bsky.richtext.facet#link"


def test_link_facets_empty_when_url_absent():
    assert sp.link_facets("no link here", "https://x.org") == []


def test_bluesky_handle_strips_at(monkeypatch=None):
    import os
    os.environ["BSKY_HANDLE"] = "@netsec-cost.eu"
    try:
        assert sp.BlueskyChannel("bluesky")._handle() == "netsec-cost.eu"
    finally:
        del os.environ["BSKY_HANDLE"]


def test_graphemes_folds_emoji_and_combining():
    # 🏆 and 🧵 are one grapheme each; ▫️ is base + VS16 (still one).
    assert sp.graphemes("abc") == 3
    assert sp.graphemes("🏆 hi 🧵") == 6  # trophy, space, h, i, space, thread
    assert sp.graphemes("▫️x") == 2


def test_find_mentions_byte_offsets_with_multibyte_prefix():
    text = "café @eissnetwork.bsky.social!"
    ms = sp.find_mentions(text)
    assert len(ms) == 1
    handle, bs, be = ms[0]
    assert handle == "eissnetwork.bsky.social"
    # "café " is 6 bytes (é = 2), so the @ starts at byte 6.
    assert text.encode("utf-8")[bs:be].decode() == "@eissnetwork.bsky.social"
    assert bs == 6


def test_find_mentions_handles_punctuation_and_two_in_one_post():
    text = "by @eissnetwork.bsky.social, NetSec, and @stockholm-uni.bsky.social"
    handles = [h for h, _, _ in sp.find_mentions(text)]
    assert handles == ["eissnetwork.bsky.social", "stockholm-uni.bsky.social"]


def test_find_links_byte_offsets():
    text = "see https://netsec-cost.eu/x.html for more"
    links = sp.find_links(text)
    assert links and links[0][0] == "https://netsec-cost.eu/x.html"
    u, bs, be = links[0]
    assert text.encode("utf-8")[bs:be].decode() == u


def test_img_mime_by_extension():
    assert sp._img_mime(Path("a.jpeg")) == "image/jpeg"
    assert sp._img_mime(Path("a.JPG")) == "image/jpeg"
    assert sp._img_mime(Path("a.png")) == "image/png"


def test_read_thread_real_spec_under_limit():
    spec = _MOD.parent.parent / "data" / "social-threads" / "best-paper-prize-2026.json"
    if not spec.exists():
        return
    thread = sp.read_thread(spec)
    assert thread.key == "thread::best-paper-prize-2026"
    assert len(thread.posts) == 3
    assert all(sp.graphemes(tp.text) <= sp.BLUESKY_LIMIT for tp in thread.posts)
    # the image rides the first post and exists in the repo
    assert thread.posts[0].image and thread.posts[0].image.exists()
    # the spec's @handles are detectable as mentions
    assert any(sp.find_mentions(tp.text) for tp in thread.posts)


def test_image_size_reads_jpeg_and_png():
    jpeg = _MOD.parent.parent / "assets" / "img" / "social" / "best-paper-prize-2026.jpeg"
    if jpeg.exists():
        assert sp.image_size(jpeg) == (1214, 732)
    # a 1x1 PNG (IHDR width/height = 1,1)
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
           b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89")
    tmp = _MOD.parent.parent / "data" / "_tmp_test.png"
    tmp.write_bytes(png)
    try:
        assert sp.image_size(tmp) == (1, 1)
    finally:
        tmp.unlink()


def test_directory_early_access_is_an_image_post():
    spec = _MOD.parent.parent / "data" / "social-threads" / "directory-early-access.json"
    if not spec.exists():
        return
    thread = sp.read_thread(spec)
    assert thread.key == "thread::directory-early-access"
    post = thread.posts[0]
    assert sp.graphemes(post.text) <= sp.BLUESKY_LIMIT
    # The announcement leads with the directory poster as the image.
    assert post.image and post.image.exists()
    assert post.image_alt, "the poster image needs alt text"
    assert not post.card, "an image embed and a link card are mutually exclusive"
    # With no link card, the directory URL lives in the text as a clickable facet.
    assert "https://netsec-cost.eu/people.html" in post.text
    assert sp.find_links(post.text), "the directory URL should resolve to a link facet"


def test_read_thread_parses_a_link_card(tmp_path):
    # Coverage for the card-parsing branch of read_thread, which no shipped
    # thread currently uses (the directory post is now image-led).
    spec = tmp_path / "card-thread.json"
    spec.write_text(json.dumps({
        "key": "thread::_card_test",
        "channel": "bluesky",
        "posts": [{
            "text": "A card post.",
            "card": {"uri": "https://example.org", "title": "T",
                     "description": "D", "thumb": "assets/images/og-image.png"},
        }],
    }), encoding="utf-8")
    post = sp.read_thread(spec).posts[0]
    assert post.card and post.card["uri"] == "https://example.org"
    assert post.card["thumb"].exists()


def test_news_feed_keys_on_id_not_link():
    # The <guid> carries an attribute (isPermaLink="false"); the key must be
    # the item id, not the link, so same-page items don't collide.
    posts = sp.read_news_feed()
    assert posts, "expected the real news.xml to yield items"
    for p in posts:
        assert p.key.startswith("news::")
        assert "http" not in p.key  # id-keyed, not link-keyed


def test_news_directives_and_thread_skip():
    directives = sp.news_directives()
    # the prize item opts out via a thread directive
    assert directives.get("essc-2026-best-paper-prize") == "thread:best-paper-prize-2026"
    # ...so it is absent from the auto-post feed
    keys = {p.key for p in sp.read_news_feed()}
    assert "news::essc-2026-best-paper-prize" not in keys


def test_titlecase_theme_preserves_acronyms_and_proper_nouns():
    assert sp.titlecase_theme("black sea security") == "Black Sea Security"
    assert sp.titlecase_theme("EU foreign policy") == "EU Foreign Policy"
    assert sp.titlecase_theme("Eastern Europe") == "Eastern Europe"
    # small connector words stay lowercase mid-phrase, but capitalise if first
    assert sp.titlecase_theme("rule of law") == "Rule of Law"
    assert sp.titlecase_theme("of mice") == "Of Mice"


def test_status_sentence_from_wg_mentorship_stsm():
    # mentee + STSM host, no WG → British join, capitalised, full stop.
    m = {"mentorship": ["mentee"], "stsm_hosting": "yes"}
    assert sp._status_sentence(m) == "Looking for a mentor and willing to host Short Term Scientific Missions."
    # WG leadership wins over plain membership; three phrases use one "and".
    m2 = {"wgs": [3], "wg_leadership": {"lead": [2]}, "mentorship": ["mentor"],
          "stsm_hosting": "ask"}
    assert sp._status_sentence(m2) == "Leading WG2, offering mentorship and open to hosting Short Term Scientific Missions."
    # nothing set → empty string (sentence is omitted)
    assert sp._status_sentence({}) == ""


def test_spotlight_uses_directory_not_network():
    post = sp.read_spotlight()
    if post is not None:
        assert "NetSec Directory" in post.summary
        assert post.title == "NetSec Directory Spotlight"
        assert "member of the NetSec network" not in post.summary


def test_spotlight_bluesky_render_fits_without_truncation():
    # The composer trims whole pieces to fit, so the live post never ends in a
    # hard-truncated "…" mid-word.
    post = sp.read_spotlight()
    if post is not None:
        text = post.render("bluesky")
        assert len(text) <= sp.BLUESKY_LIMIT
        assert "…" not in text


def test_bluesky_handle_from_profile_url_or_bare():
    assert sp.bluesky_handle("https://bsky.app/profile/apb-ldn.org") == "apb-ldn.org"
    assert sp.bluesky_handle("https://bsky.app/profile/foo.bsky.social") == "foo.bsky.social"
    assert sp.bluesky_handle("foo.bsky.social") == "foo.bsky.social"   # bare handle
    assert sp.bluesky_handle("@bar.example.com") == "bar.example.com"  # bare, @-prefixed
    assert sp.bluesky_handle("https://www.linkedin.com/in/x") is None  # wrong platform
    assert sp.bluesky_handle("") is None
    assert sp.bluesky_handle(None) is None


def test_spotlight_render_tags_bluesky_only():
    # A member with a Bluesky handle gets an @-mention on Bluesky (an actual
    # detectable mention token, within the limit), and the LinkedIn body stays
    # link-free (its profile link rides along as a comment instead).
    post = sp.Post(
        kind="spotlight", key="k", title="NetSec Directory Spotlight",
        summary="Meet Dr X in the NetSec Directory, Researcher at Y. Working on Cyber.",
        link="https://netsec-cost.eu/people/x.html",
        bsky_handle="foo.bsky.social",
        profile_url="https://www.linkedin.com/in/foo",
    )
    bt = post.render("bluesky")
    assert len(bt) <= sp.BLUESKY_LIMIT
    assert "@foo.bsky.social" in bt
    assert [h for h, _, _ in sp.find_mentions(bt)] == ["foo.bsky.social"]
    lt = post.render("linkedin")
    assert "@foo.bsky.social" not in lt      # the handle is Bluesky-only
    assert "linkedin.com/in/foo" not in lt    # profile link is a comment, not body


def test_spotlight_render_without_handle_is_unchanged():
    post = sp.Post(kind="spotlight", key="k", title="T", summary="S",
                   link="https://x/")
    assert "On Bluesky:" not in post.render("bluesky")


def _standalone() -> int:
    failures = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and isinstance(f, types.FunctionType)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ok  {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append((name, exc))
            print(f"FAIL  {name}: {exc}")
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys

    sys.exit(_standalone())


# ── LinkedIn adapter (mocked HTTP; no network, no posting) ─────────────────

def _li_recorder(responses):
    """(fake_request, calls). Each item in `responses` is popped per call and is
    either an (status, headers, body) tuple to return or an Exception to raise."""
    calls = []

    def fake(url, method="GET", headers=None, json_body=None, data=None, content_type=None):
        calls.append({"url": url, "method": method, "headers": headers or {},
                      "json": json_body, "data": data, "content_type": content_type})
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    return fake, calls


def test_pinned_api_version_reads_the_data_file():
    # The committed pin file drives the LinkedIn-Version header.
    assert re.fullmatch(r"\d{6}", sp._pinned_api_version())
    assert sp._pinned_api_version() == sp.LinkedInChannel.VERSION


def test_pinned_api_version_falls_back_when_file_unreadable(monkeypatch, tmp_path):
    monkeypatch.setattr(sp, "LINKEDIN_VERSION_FILE", tmp_path / "gone.json")
    assert sp._pinned_api_version() == sp._LINKEDIN_VERSION_FALLBACK


def test_pinned_api_version_falls_back_on_malformed_pin(monkeypatch, tmp_path):
    bad = tmp_path / "pin.json"
    bad.write_text('{"version": "not-a-version"}', encoding="utf-8")
    monkeypatch.setattr(sp, "LINKEDIN_VERSION_FILE", bad)
    assert sp._pinned_api_version() == sp._LINKEDIN_VERSION_FALLBACK


def test_gha_warning_only_emits_under_actions(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    sp._gha_warning("nope")
    assert capsys.readouterr().out == ""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    sp._gha_warning("boom")
    assert "::warning" in capsys.readouterr().out


def test_linkedin_configured_requires_org_and_token(monkeypatch):
    monkeypatch.delenv("LINKEDIN_ORG_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)
    assert sp.LinkedInChannel("linkedin").configured() is False
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    assert sp.LinkedInChannel("linkedin").configured() is True


def test_linkedin_text_post_shape_and_headers(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    fake, calls = _li_recorder([(201, {"x-restli-id": "urn:li:share:99"}, {})])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="news", key="k", title="T", summary="S", link="https://x/")
    url = sp.LinkedInChannel("linkedin").publish(post)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:99/"
    assert len(calls) == 1                      # text-only → no image upload
    c = calls[0]
    assert c["url"].endswith("/rest/posts") and c["method"] == "POST"
    assert c["json"]["author"] == "urn:li:organization:12345"
    assert c["json"]["lifecycleState"] == "PUBLISHED"
    assert "content" not in c["json"]
    assert c["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
    assert c["headers"]["LinkedIn-Version"]
    assert c["headers"]["Authorization"] == "Bearer tok-abc"


def test_linkedin_image_post_uploads_then_posts(monkeypatch, tmp_path):
    img = tmp_path / "card.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    fake, calls = _li_recorder([
        (200, {}, {"value": {"uploadUrl": "https://dms/upload/1", "image": "urn:li:image:7"}}),
        (201, {}, ""),                                   # binary upload
        (201, {"x-restli-id": "urn:li:share:5"}, {}),    # create post
    ])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="spotlight", key="k", title="T", summary="S",
                   link="https://x/", image=img, image_alt="alt text")
    url = sp.LinkedInChannel("linkedin").publish(post)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:5/"
    assert calls[0]["url"].endswith("/rest/images?action=initializeUpload")
    assert calls[0]["json"]["initializeUploadRequest"]["owner"] == "urn:li:organization:12345"
    assert calls[1]["url"] == "https://dms/upload/1" and calls[1]["method"] == "PUT"
    assert calls[1]["data"] == img.read_bytes()
    assert calls[2]["json"]["content"]["media"]["id"] == "urn:li:image:7"
    assert calls[2]["json"]["content"]["media"]["altText"] == "alt text"


def test_linkedin_posts_profile_link_as_first_comment(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    fake, calls = _li_recorder([
        (201, {"x-restli-id": "urn:li:share:99"}, {}),   # create post
        (201, {}, {}),                                    # comment
    ])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="spotlight", key="k", title="T", summary="S",
                   link="https://x/", profile_url="https://www.linkedin.com/in/foo")
    url = sp.LinkedInChannel("linkedin").publish(post)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:99/"
    assert len(calls) == 2
    comment = calls[1]
    # URN is path-encoded (colons escaped) on the socialActions comments route.
    assert comment["url"].endswith("/rest/socialActions/urn%3Ali%3Ashare%3A99/comments")
    assert comment["method"] == "POST"
    assert comment["json"]["actor"] == "urn:li:organization:12345"
    assert comment["json"]["message"]["text"] == "https://www.linkedin.com/in/foo"


def test_linkedin_comment_failure_does_not_fail_the_post(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    # The comment call errors (SystemExit, as _li_request raises on HTTP fail);
    # the share already went out, so publish must still return its URL.
    fake, calls = _li_recorder([
        (201, {"x-restli-id": "urn:li:share:99"}, {}),
        SystemExit("HTTP 500 from comments"),
    ])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="spotlight", key="k", title="T", summary="S",
                   link="https://x/", profile_url="https://www.linkedin.com/in/foo")
    url = sp.LinkedInChannel("linkedin").publish(post)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:99/"
    assert len(calls) == 2   # attempted, then swallowed


def test_linkedin_no_comment_when_no_profile_url(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok-abc")
    fake, calls = _li_recorder([(201, {"x-restli-id": "urn:li:share:1"}, {})])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="spotlight", key="k", title="T", summary="S", link="https://x/")
    sp.LinkedInChannel("linkedin").publish(post)
    assert len(calls) == 1   # no profile link → no comment call


def test_linkedin_refreshes_token_on_401_and_retries(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "stale")
    monkeypatch.setenv("LINKEDIN_REFRESH_TOKEN", "refresh-xyz")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "cid")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "csecret")
    fake, calls = _li_recorder([
        sp._Unauthorized("expired"),                     # first create-post 401
        (200, {}, {"access_token": "fresh"}),            # token refresh
        (201, {"x-restli-id": "urn:li:share:8"}, {}),    # retry create-post
    ])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="news", key="k", title="T", summary="S", link="https://x/")
    url = sp.LinkedInChannel("linkedin").publish(post)
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:8/"
    assert "oauth/v2/accessToken" in calls[1]["url"]     # the refresh call
    import os
    assert os.environ["LINKEDIN_ACCESS_TOKEN"] == "fresh"  # env updated for the run


def test_linkedin_401_without_refresh_creds_raises(monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "12345")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "stale")
    monkeypatch.delenv("LINKEDIN_REFRESH_TOKEN", raising=False)
    fake, _ = _li_recorder([sp._Unauthorized("expired")])
    monkeypatch.setattr(sp, "_li_request", fake)
    post = sp.Post(kind="news", key="k", title="T", summary="S", link="https://x/")
    import pytest
    with pytest.raises(SystemExit):
        sp.LinkedInChannel("linkedin").publish(post)
