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


def test_joint_item_for_linkedin_needs_eiss_as_collaborator():
    with pytest.raises(SystemExit, match="pick EISS under Collaborator page"):
        nfi.parse_form("news: x", nfi.form_sections(
            form(Site="Joint (EISS and NetSec)", **{"Collaborator page": "No collaborator"})), TODAY)
    item = nfi.parse_form("news: x", nfi.form_sections(form(**{
        "Site": "Joint (EISS and NetSec)", "Collaborator page": "No collaborator",
        "Post on": "- [ ] LinkedIn\n- [X] Bluesky"})), TODAY)
    assert item["site"] == "joint" and item["networks"] == ["bluesky"] and "collaborator" not in item


def test_form_offers_post_on_and_no_eiss_site():
    text = (HERE.parent / ".github" / "ISSUE_TEMPLATE" / "news.yml").read_text(encoding="utf-8")
    site = text.split("    id: site\n", 1)[1].split("  - type:", 1)[0]
    assert "- EISS" not in site
    nets = text.split("    id: networks\n", 1)[1].split("  - type:", 1)[0]
    assert "label: Post on" in nets and "- label: LinkedIn" in nets and "- label: Bluesky" in nets


def test_eiss_item_stops(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="The Site is EISS"):
        run(monkeypatch, tmp_path, form(Site="EISS"))


def test_free_text_is_refused(monkeypatch, tmp_path):
    with pytest.raises(SystemExit, match="does not use the News item form"):
        run(monkeypatch, tmp_path, "Just some text.")


def test_headline_and_summary_limits(monkeypatch, tmp_path):
    # At the limit the text passes whole.
    _, data = run(monkeypatch, tmp_path, form(Headline="h" * 100, Summary="s" * 300))
    it = data["items"][0]
    assert it["title"]["en"] == "h" * 100 and it["summary"]["en"] == "s" * 300
    # Over it the run stops and says by how much, from the field or the title.
    with pytest.raises(SystemExit, match="Headline is 101 characters long, and the limit is 100"):
        run(monkeypatch, tmp_path, form(Headline="h" * 101))
    with pytest.raises(SystemExit, match="Headline is 101 characters"):
        run(monkeypatch, tmp_path, form(Headline="_No response_"), title="news: " + "h" * 101)
    with pytest.raises(SystemExit, match="Summary is 382 characters long.*at least 82 characters"):
        run(monkeypatch, tmp_path, form(Summary="s" * 382))


def test_empty_headline_and_default_title_stop(monkeypatch, tmp_path):
    # EISSeuropa/EISSeuropa.github.io#2189: no headline and the form's "news: " title.
    with pytest.raises(SystemExit, match="The Headline is empty"):
        run(monkeypatch, tmp_path, form(Headline="_No response_"), title="news: ")
    with pytest.raises(SystemExit, match="The Summary is empty"):
        run(monkeypatch, tmp_path, form(Summary="_No response_"))


def test_form_requires_the_headline_and_describes_every_field():
    text = (HERE.parent / ".github" / "ISSUE_TEMPLATE" / "news.yml").read_text(encoding="utf-8")
    blocks = re.split(r"^  - type: ", text, flags=re.M)[1:]
    fields = {re.search(r"^    id: (\S+)", b, re.M).group(1): b
              for b in blocks if not b.startswith("markdown")}
    assert len(fields) == 16, sorted(fields)
    for fid, b in fields.items():
        assert re.search(r"^      description: \S", b, re.M), f"{fid} has no description"
    assert "required: true" in fields["headline"]


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
              if not m.startswith(("Include", "Do not")) and m not in ("LinkedIn", "Bluesky")}
    read = {"site", "headline", "website summary", "post on", "body", "linkedin post", "bluesky post",
            "type", "working group", "link",
            "image", "image description", "publication date", "on the home page until", "collaborator page", "options"}
    assert labels == read


# The photo (EISSeuropa/EISSeuropa.github.io#2193). Pillow is in
# requirements.txt, which python-tests.yml installs.
UUID = "https://github.com/user-attachments/assets/0b1c2d3e-0000-4000-8000-000000000000"


def _photo(w, h, fmt="JPEG", mode="RGB", exif=None, noise=True) -> bytes:
    """Random noise compresses badly, like a detailed phone photo."""
    import io
    import random
    from PIL import Image
    random.seed(1)
    if noise:
        img = Image.frombytes("RGB", (w, h), random.randbytes(w * h * 3))
    else:
        img = Image.new("RGB", (w, h), (40, 90, 160))
    if mode == "RGBA":
        img = img.convert("RGBA")
        img.putalpha(0)
    buf = io.BytesIO()
    kw = {"quality": 95} if fmt == "JPEG" else {}
    if exif is not None:
        kw["exif"] = exif
    img.save(buf, format=fmt, **kw)
    return buf.getvalue()


@pytest.mark.parametrize("text", [
    f'<img width="1024" height="768" alt="IMG_1234" src="{UUID}" />',
    f"![IMG_1234]({UUID})",
    UUID,
    f"  {UUID}  ",
])
def test_image_source_reads_what_github_writes(text):
    assert nfi.image_source(text) == UUID


def test_image_source_site_path_and_upload_in_progress():
    assert nfi.image_source("") == ""
    assert nfi.image_source("/assets/images/x.jpg") == "assets/images/x.jpg"
    with pytest.raises(SystemExit, match="no photo in it"):
        nfi.image_source("Uploading IMG_1234.jpg…")


def test_photo_needs_a_description_up_to_300():
    f = nfi.form_sections(form(Image=f"![p]({UUID})", **{"Image description": "_No response_"}))
    with pytest.raises(SystemExit, match="Image description is empty"):
        nfi.parse_form("news: x", f, TODAY)
    f = nfi.form_sections(form(Image=f"![p]({UUID})", **{"Image description": "d" * 301}))
    with pytest.raises(SystemExit, match="Image description is 301 characters"):
        nfi.parse_form("news: x", f, TODAY)
    f = nfi.form_sections(form(Image="_No response_", **{"Image description": "Ignored."}))
    item = nfi.parse_form("news: x", f, TODAY)
    assert "image" not in item and "imageAlt" not in item


def test_shrink_fits_bluesky_and_keeps_small_photos():
    import io
    from PIL import Image
    big = _photo(4032, 3024)
    assert len(big) > 5_000_000
    out = nfi.shrink(big)
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and len(out) <= nfi.IMAGE_MAX_BYTES
    assert max(img.size) <= nfi.IMAGE_MAX_SIDE and img.size[0] > img.size[1]
    assert Image.open(io.BytesIO(nfi.shrink(_photo(800, 600, noise=False)))).size == (800, 600)


def test_shrink_turns_upright_and_drops_the_camera_data():
    import io
    from PIL import Image
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° clockwise to display
    exif[0x8825] = {1: "N", 2: (48.0, 51.0, 24.0)}  # GPS
    img = Image.open(io.BytesIO(nfi.shrink(_photo(1200, 900, exif=exif, noise=False))))
    assert img.size == (900, 1200)
    assert not img.getexif() and "exif" not in img.info


def test_shrink_flattens_transparency_and_refuses_non_images():
    import io
    from PIL import Image
    img = Image.open(io.BytesIO(nfi.shrink(_photo(600, 400, fmt="PNG", mode="RGBA", noise=False))))
    assert img.mode == "RGB" and img.getpixel((10, 10)) == (255, 255, 255)
    with pytest.raises(SystemExit, match="not a photo that can be read"):
        nfi.shrink(b"<html>Not found</html>")


def test_photo_end_to_end(monkeypatch, tmp_path):
    body = form(Image=f'<img alt="IMG_1" src="{UUID}" />',
                **{"Image description": "The Faculty of Political Science building in Belgrade."})
    monkeypatch.setenv("ISSUE_TITLE", "news: x")
    monkeypatch.setenv("ISSUE_BODY", body)
    monkeypatch.setenv("TODAY", TODAY)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    path = news_file(tmp_path)
    fetched = []
    big = _photo(3000, 2000)

    def fetcher(url):
        fetched.append(url)
        return big

    for _ in range(2):  # the re-run finds the item and fetches nothing
        nfi.main(translator=stub, news_path=path, root=tmp_path, fetcher=fetcher)
    assert fetched == [UUID]
    it = json.loads(path.read_text(encoding="utf-8"))["items"][0]
    assert it["image"] == f"assets/images/news/{it['id']}.jpg"
    assert it["imageAlt"] == "The Faculty of Political Science building in Belgrade."
    assert "_image_url" not in it
    assert list(it).index("image") < list(it).index("imageAlt")
    assert (tmp_path / it["image"]).stat().st_size <= nfi.IMAGE_MAX_BYTES


# One box per surface (EISSeuropa/EISSeuropa.github.io#2195).
def boxes(**over) -> str:
    fields = {"Website summary": "Applications are open for the NetSec Training School in Belgrade.",
              "LinkedIn post": "📣 Applications are open!   \n\nWith @EISS and @cost.\n\n\n\n#NetSec",
              "Bluesky post": "Applications are open, with @EISS. #NetSec"}
    fields.update(over)
    return form(Summary=None, **fields)


def test_boxes_map_with_paragraphs():
    item = nfi.parse_form("news: x", nfi.form_sections(boxes()), TODAY)
    assert item["summary"]["en"] == "Applications are open for the NetSec Training School in Belgrade."
    assert item["posts"] == {"linkedin": "📣 Applications are open!\n\nWith @EISS and @cost.\n\n#NetSec",
                             "bluesky": "Applications are open, with @EISS. #NetSec"}
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{"Bluesky post": "_No response_"})), TODAY)
    assert set(item["posts"]) == {"linkedin"}


@pytest.mark.parametrize("over, message", [
    ({"Website summary": "_No response_"}, "Website summary is empty"),
    ({"Website summary": "w" * 301}, "Website summary is 301 characters"),
    ({"Body": "b" * 2001}, "Body is 2001 characters"),
    ({"LinkedIn post": "With @Nope"}, "LinkedIn post tags @Nope"),
    ({"Bluesky post": "With @Nobody"}, "Bluesky post tags @Nobody"),
    ({"Link": "the event page"}, "The Link is not a web address"),
    ({"Publication date": "next week"}, 'Publication date "next week"'),
    ({"On the home page until": "end of January"}, "On the home page until date"),
])
def test_every_box_is_checked(over, message):
    with pytest.raises(SystemExit, match=re.escape(message)):
        nfi.parse_form("news: x", nfi.form_sections(boxes(**over)), TODAY)


def test_post_limits_count_the_link_and_the_handles():
    sp = nfi._module("social-post.py")
    link = nfi._module("build-news-rss.py").item_link(
        nfi.parse_form("news: x", nfi.form_sections(boxes()), TODAY))
    room = 300 - len("\n\n" + link) - len(" @eissnetwork.bsky.social")
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{"Bluesky post": "b" * room + " @EISS"})), TODAY)
    shown, _ = sp.tagged(sp.with_link(item["posts"]["bluesky"], link), "bluesky", sp.load_accounts())
    assert len(shown) == 300
    with pytest.raises(SystemExit, match="Bluesky post is 301 characters long with the link"):
        nfi.parse_form("news: x", nfi.form_sections(boxes(**{"Bluesky post": "b" * (room + 1) + " @EISS"})), TODAY)
    room = 3000 - len("\n\n" + link)
    nfi.parse_form("news: x", nfi.form_sections(boxes(**{"LinkedIn post": "l" * room})), TODAY)
    with pytest.raises(SystemExit, match="LinkedIn post is 3001 characters long"):
        nfi.parse_form("news: x", nfi.form_sections(boxes(**{"LinkedIn post": "l" * (room + 1)})), TODAY)


def test_emails_and_urls_are_not_tags():
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{
        "LinkedIn post": "Write to info@netsec-cost.eu or see https://x.com/@a, with @NetSec"})), TODAY)
    assert "info@netsec-cost.eu" in item["posts"]["linkedin"]


def test_post_boxes_render_as_code_blocks():
    # The issue shows the post boxes as code blocks, so an @tag notifies no
    # GitHub user. The fence is dropped, the text kept.
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{
        "Bluesky post": "```text\nApplications are open, with @EISS. #NetSec\n```"})), TODAY)
    assert item["posts"]["bluesky"] == "Applications are open, with @EISS. #NetSec"
    assert nfi.post_text("```text\nA\n\n\n\nB\n```") == "A\n\nB"
    assert nfi.post_text("```\nA\n```") == "A" and nfi.post_text("Use ``` here") == "Use ``` here"
    text = (HERE.parent / ".github" / "ISSUE_TEMPLATE" / "news.yml").read_text(encoding="utf-8")
    for fid in ("linkedin-post", "bluesky-post"):
        block = text.split(f"    id: {fid}\n", 1)[1].split("  - type:", 1)[0]
        assert "render: text" in block, fid


def post_on(linkedin, bluesky, **over):
    box = lambda on: "X" if on else " "
    return nfi.form_sections(boxes(**{"Post on": f"- [{box(linkedin)}] LinkedIn\n- [{box(bluesky)}] Bluesky", **over}))


def test_post_on_picks_the_networks():
    item = nfi.parse_form("news: x", post_on(True, True), TODAY)
    assert "networks" not in item and set(item["posts"]) == {"linkedin", "bluesky"}
    item = nfi.parse_form("news: x", post_on(True, False), TODAY)
    assert item["networks"] == ["linkedin"] and set(item["posts"]) == {"linkedin"}
    assert item["collaborator"] == "eiss"
    # The unticked network's box is ignored, even when it would stop the run.
    item = nfi.parse_form("news: x", post_on(False, True, **{"LinkedIn post": "With @Nope"}), TODAY)
    assert item["networks"] == ["bluesky"] and set(item["posts"]) == {"bluesky"}
    assert "collaborator" not in item
    with pytest.raises(SystemExit, match="No box is ticked under Post on"):
        nfi.parse_form("news: x", post_on(False, False), TODAY)


def test_post_on_and_do_not_post():
    skip = "- [ ] Include in the newsletter\n- [X] Do not post to LinkedIn and Bluesky"
    item = nfi.parse_form("news: x", post_on(False, False, Options=skip), TODAY)
    assert item["social"] == "skip" and "posts" not in item and "networks" not in item
    assert "collaborator" not in item
    with pytest.raises(SystemExit, match="untick one of them"):
        nfi.parse_form("news: x", post_on(True, False, Options=skip), TODAY)


PASTE = ("[#ESSC2027](https://www.linkedin.com/search/results/all/?keywords=%23essc2027) with "
         "[Networking European Security Knowledge (NetSec)](https://www.linkedin.com/company/costnetsec/), "
         "[EISS](https://www.linkedin.com/company/eiss-europa/), "
         "[COST Association](https://www.linkedin.com/company/cost-office/), "
         "[FPN](https://www.linkedin.com/school/fakultet-politickih-nauka-univerzitet-u-beogradu/) "
         "and [Jane Doe](https://www.linkedin.com/in/jane-doe-123/). See https://netsec-cost.eu/")


def test_pasted_linkedin_text():
    assert nfi.untangle_linkedin(PASTE) == ("#ESSC2027 with @NetSec, @EISS, @COST, FPN and Jane Doe. "
                                            "See https://netsec-cost.eu/")
    assert nfi.untangle_linkedin(PASTE, tags=False).startswith(
        "#ESSC2027 with Networking European Security Knowledge (NetSec), EISS, COST Association, FPN")
    assert nfi.untangle_linkedin("[a](https://example.org/)") == "[a](https://example.org/)"
    # The organisation number in the page's address works too.
    assert nfi.untangle_linkedin("[x](https://www.linkedin.com/company/120343970/)") == "@NetSec"
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{"LinkedIn post": PASTE})), TODAY)
    assert "with @NetSec, @EISS, @COST, FPN" in item["posts"]["linkedin"]
    item = nfi.parse_form("news: x", nfi.form_sections(boxes(**{
        "Website summary": "Open, with [EISS](https://www.linkedin.com/company/eiss-europa/)."})), TODAY)
    assert item["summary"]["en"] == "Open, with EISS."


def test_github_output_names_the_headline(monkeypatch, tmp_path):
    out = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("ISSUE_TITLE", "news:")
    monkeypatch.setenv("ISSUE_BODY", form())
    monkeypatch.setenv("TODAY", TODAY)
    nfi.main(translator=stub, news_path=news_file(tmp_path), root=HERE.parent)
    assert "headline=Training School 2027: call open\n" in out.read_text()
