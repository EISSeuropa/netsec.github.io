#!/usr/bin/env python3
"""pytest suite for scripts/news-from-issue.py.

No network: the translation is a stub passed to main(), and every write goes
to tmp_path. Also checks the News item form itself, since GitHub hides a form
from the issue chooser when a dropdown with a default lists "None" or "n/a".

Run: python3 -m pytest scripts/test-news-from-issue.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("news_from_issue", HERE / "news-from-issue.py")
nfi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nfi)

TODAY = "2026-12-01"


def form(**over) -> str:
    fields = {
        "Site": "NetSec",
        "Headline": "Training School 2027: call open",
        "Summary": "Applications are open for the NetSec Training School in Belgrade.",
        "Body": "Applications are open.\n\nThe school runs in June.",
        "Type": "call",
        "Working Group": "WG3",
        "Link": "essc-2026.html",
        "Publication date": "2026-12-01",
        "On the home page until": "2027-01-31",
        "Collaborator page": "EISS",
        "Options": "- [X] Include in the newsletter\n- [ ] Do not post to LinkedIn and Bluesky",
    }
    fields.update(over)
    return "\n\n".join(f"### {k}\n\n{v}" for k, v in fields.items() if v is not None)


def stub(english):
    return {loc: {k: f"[{loc}] {v}" for k, v in english.items()} for loc in ("fr", "de")}


def news_file(tmp_path: Path) -> Path:
    p = tmp_path / "news.json"
    p.write_text(json.dumps({
        "_documentation": "x",
        "lastBuildDate": "2026-10-07T12:00:00+02:00",
        "items": [{"id": "old", "pubDate": "2026-10-07T12:00:00+02:00",
                   "title": {"en": "Grüße"}}],
    }, indent=2) + "\n", encoding="utf-8")
    return p


def run(monkeypatch, tmp_path, body, translator=stub, title="news: x"):
    monkeypatch.setenv("ISSUE_TITLE", title)
    monkeypatch.setenv("ISSUE_BODY", body)
    monkeypatch.setenv("TODAY", TODAY)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    path = news_file(tmp_path)
    nfi.main(translator=translator, news_path=path, root=HERE.parent)
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_full_form_maps_every_field(monkeypatch, tmp_path):
    _, data = run(monkeypatch, tmp_path, form())
    it = data["items"][0]
    assert it["id"] == "training-school-2027-call-open-2026-12"
    assert it["type"] == "call" and it["wg"] == 3
    assert it["pubDate"] == "2026-12-01T12:00:00+01:00"
    assert it["homeUntil"] == "2027-01-31T23:59:00+01:00"
    assert it["displayDate"] == {"en": "1 December 2026", "fr": "1er décembre 2026",
                                 "de": "1. Dezember 2026"}
    assert it["body"]["en"] == "Applications are open. The school runs in June."
    assert it["title"]["fr"] == "[fr] Training School 2027: call open"
    assert it["summary"]["de"].startswith("[de] ")
    assert it["cta"]["href"] == {"en": "essc-2026.html", "fr": "essc-2026.fr.html",
                                 "de": "essc-2026.de.html"}
    assert it["cta"]["external"] is False and set(it["cta"]["i18n"]) == {"en", "fr", "de"}
    assert it["collaborator"] == "eiss" and it["newsletter"] is True
    assert "social" not in it and "site" not in it
    assert data["lastBuildDate"] == it["pubDate"]


def test_minimal_form_and_summer_time(monkeypatch, tmp_path):
    body = form(Headline="", Body="", Type="announcement", **{
        "Working Group": "No Working Group", "Link": "", "Publication date": "2027-06-15",
        "On the home page until": "", "Collaborator page": "No collaborator",
        "Options": "- [ ] Include in the newsletter\n- [X] Do not post to LinkedIn and Bluesky"})
    _, data = run(monkeypatch, tmp_path, body, title="news: Plain headline")
    it = data["items"][0]
    assert it["title"]["en"] == "Plain headline"
    assert it["body"]["en"] == it["summary"]["en"]
    assert it["pubDate"] == "2027-06-15T12:00:00+02:00"
    assert it["social"] == "skip"
    for key in ("wg", "cta", "homeUntil", "collaborator", "newsletter"):
        assert key not in it


def test_blank_date_uses_today(monkeypatch, tmp_path):
    _, data = run(monkeypatch, tmp_path, form(**{"Publication date": "_No response_"}))
    assert data["items"][0]["pubDate"].startswith(TODAY)


def test_external_link_and_missing_locale_pages():
    ext = nfi.make_cta("https://example.org/call")
    assert ext["href"] == "https://example.org/call" and ext["external"] is True
    assert nfi.make_cta("no-such-page.html")["href"] == "no-such-page.html"
    assert nfi.make_cta("not a link") is None


def test_joint_item(monkeypatch, tmp_path):
    _, data = run(monkeypatch, tmp_path, form(Site="Joint (EISS and NetSec)"))
    assert data["items"][0]["site"] == "joint"


def test_eiss_item_stops(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="belongs in EISSeuropa/EISSeuropa.github.io"):
        run(monkeypatch, tmp_path, form(Site="EISS"))


def test_free_text_is_refused(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="does not use the News item form"):
        run(monkeypatch, tmp_path, "Just some text.")


def test_failed_translation_keeps_english(monkeypatch, tmp_path, capsys):
    def broken(_):
        raise RuntimeError("boom")
    _, data = run(monkeypatch, tmp_path, form(), translator=broken)
    it = data["items"][0]
    assert set(it["title"]) == {"en"}
    assert "TRANSLATED=false" in capsys.readouterr().out


def test_no_api_key_skips_translation(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    item = {k: {"en": "x"} for k in ("title", "summary", "body")}
    assert nfi.add_translations(item) is False
    assert item["title"] == {"en": "x"}


def test_rerun_changes_nothing_and_keeps_bytes(monkeypatch, tmp_path):
    path, _ = run(monkeypatch, tmp_path, form())
    first = path.read_text(encoding="utf-8")
    assert "\\u00fc" in first  # the old item's escapes survive the splice
    nfi.main(translator=stub, news_path=path, root=HERE.parent)
    assert path.read_text(encoding="utf-8") == first


def test_github_output(monkeypatch, tmp_path):
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("ISSUE_TITLE", "news: x")
    monkeypatch.setenv("ISSUE_BODY", form())
    monkeypatch.setenv("TODAY", TODAY)
    nfi.main(translator=stub, news_path=news_file(tmp_path), root=HERE.parent)
    assert "translated=true" in out.read_text()


def test_form_has_no_reserved_dropdown_option():
    text = (HERE.parent / ".github" / "ISSUE_TEMPLATE" / "news.yml").read_text(encoding="utf-8")
    assert not re.findall(r"^\s+-\s*[\"']?(none|n/a)[\"']?\s*$", text, re.M | re.I)


def test_form_headings_match_the_script():
    text = (HERE.parent / ".github" / "ISSUE_TEMPLATE" / "news.yml").read_text(encoding="utf-8")
    labels = {m.lower() for m in re.findall(r"^\s+label: (.+?)\s*$", text, re.M)
              if not m.startswith(("Include", "Do not"))}
    read = {"site", "headline", "summary", "body", "type", "working group", "link",
            "publication date", "on the home page until", "collaborator page", "options"}
    assert labels == read
