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
