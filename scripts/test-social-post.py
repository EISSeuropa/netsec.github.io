#!/usr/bin/env python3
"""Test suite for scripts/social-post.py (pure logic; no network, no posting).

Run standalone:  /usr/bin/python3 scripts/test-social-post.py
Or under pytest: python3 -m pytest scripts/test-social-post.py -q
"""
from __future__ import annotations

import importlib.util
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


def test_spotlight_uses_lamp_prefix():
    post = sp.Post(kind="spotlight", key="k", title="Member spotlight",
                   summary="Meet X.", link="https://netsec-cost.eu/people/x.html")
    assert post.render("bluesky").startswith("🔦")


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


def test_read_thread_parses_link_card():
    spec = _MOD.parent.parent / "data" / "social-threads" / "directory-early-access.json"
    if not spec.exists():
        return
    thread = sp.read_thread(spec)
    assert thread.key == "thread::directory-early-access"
    post = thread.posts[0]
    assert sp.graphemes(post.text) <= sp.BLUESKY_LIMIT
    assert post.card and post.card["uri"] == "https://netsec-cost.eu/people.html"
    # thumb resolves to a real file in the repo
    assert post.card["thumb"].exists()
    # the card carries the link, so the post text should NOT repeat the URL
    assert "http" not in post.text


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
    assert sp._status_sentence(m) == "Looking for a mentor and hosting STSMs."
    # WG leadership wins over plain membership; three phrases use one "and".
    m2 = {"wgs": [3], "wg_leadership": {"lead": [2]}, "mentorship": ["mentor"],
          "stsm_hosting": "ask"}
    assert sp._status_sentence(m2) == "Leading WG2, offering mentorship and open to hosting STSMs."
    # nothing set → empty string (sentence is omitted)
    assert sp._status_sentence({}) == ""


def test_spotlight_uses_directory_not_network():
    post = sp.read_spotlight()
    if post is not None:
        assert "NetSec Directory" in post.summary
        assert "member of the NetSec network" not in post.summary


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
