"""Unit tests for scripts/inject-seo.py.

The module name has hyphens, so it can't be imported by name; we load it
via importlib from the relative path. Every filesystem touch goes through
tmp_path and the module-level ROOT is monkeypatched so nothing reads or
writes a tracked file. No network is involved anywhere in the module.

Focus areas (per the brief): the ?v= cache-bust stripping/rewriting in
stamp_assets, and the content-hash computation in compute_asset_versions.
The SEO/JSON-LD builders, probe(), canonical_url(), base_of() and the
inject() idempotency path are also covered.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

# ── Load the hyphenated module from its relative path ────────────────
_MOD_PATH = Path(__file__).resolve().parent / "inject-seo.py"
_spec = importlib.util.spec_from_file_location("inject_seo", _MOD_PATH)
seo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seo)


# ── canonical_url ────────────────────────────────────────────────────

def test_canonical_index_en_is_root():
    assert seo.canonical_url("index", "en") == "https://netsec-cost.eu/"


def test_canonical_index_fr_is_full_path():
    # index is only special-cased for EN; FR/DE get the .lang.html form.
    assert seo.canonical_url("index", "fr") == "https://netsec-cost.eu/index.fr.html"


def test_canonical_en_non_index():
    assert seo.canonical_url("people", "en") == "https://netsec-cost.eu/people.html"


def test_canonical_de_non_index():
    assert seo.canonical_url("grants", "de") == "https://netsec-cost.eu/grants.de.html"


# ── probe ────────────────────────────────────────────────────────────

def test_probe_extracts_lang_title_desc():
    html = (
        '<html lang="fr"><head><title>Titre ici</title>'
        '<meta name="description" content="Une description."></head></html>'
    )
    lang, title, desc = seo.probe(html)
    assert lang == "fr"
    assert title == "Titre ici"
    assert desc == "Une description."


def test_probe_defaults_lang_en_when_missing():
    lang, title, desc = seo.probe("<html><head></head></html>")
    assert lang == "en"
    assert title == ""
    assert desc == ""


def test_probe_strips_whitespace_in_title():
    lang, title, _ = seo.probe("<html lang='en'><title>   Spaced   </title>")
    assert title == "Spaced"


def test_probe_lang_uppercase_normalised_to_lower():
    lang, _, _ = seo.probe('<html lang="DE"><title>x</title>')
    assert lang == "de"


def test_probe_title_with_attributes():
    lang, title, _ = seo.probe('<html lang="en"><title data-x="y">Hi</title>')
    assert title == "Hi"


# ── _attr_escape ─────────────────────────────────────────────────────

def test_attr_escape_quotes():
    assert seo._attr_escape('say "hi"') == "say &quot;hi&quot;"


def test_attr_escape_noop_when_clean():
    assert seo._attr_escape("plain text & stuff") == "plain text & stuff"


# ── base_of / is_seo_managed ─────────────────────────────────────────

def test_base_of_strips_fr_suffix():
    assert seo.base_of(Path("people.fr.html")) == "people"


def test_base_of_strips_de_suffix():
    assert seo.base_of(Path("grants.de.html")) == "grants"


def test_base_of_plain_en_page():
    assert seo.base_of(Path("index.html")) == "index"


def test_base_of_does_not_strip_other_dotted_names():
    # only .fr / .de are stripped, not arbitrary dotted stems
    assert seo.base_of(Path("foo.bar.html")) == "foo.bar"


def test_is_seo_managed_true_for_known_page():
    assert seo.is_seo_managed(Path("people.fr.html")) is True


def test_is_seo_managed_true_for_404():
    assert seo.is_seo_managed(Path("404.html")) is True


def test_is_seo_managed_false_for_unmanaged():
    assert seo.is_seo_managed(Path("random-page.html")) is False


# ── compute_asset_versions (hashing) ─────────────────────────────────

def _make_assets(root: Path, css: dict, js: dict):
    (root / "assets" / "css").mkdir(parents=True)
    (root / "assets" / "js").mkdir(parents=True)
    for name, content in css.items():
        (root / "assets" / "css" / name).write_bytes(content)
    for name, content in js.items():
        (root / "assets" / "js" / name).write_bytes(content)


def test_compute_asset_versions_hashes(tmp_path, monkeypatch):
    body = b"body { color: red; }"
    _make_assets(tmp_path, {"site.css": body}, {"site.js": b"console.log(1)"})
    monkeypatch.setattr(seo, "ROOT", tmp_path)

    versions = seo.compute_asset_versions()
    expected = hashlib.sha256(body).hexdigest()[:8]
    assert versions["assets/css/site.css"] == expected
    assert versions["assets/js/site.js"] == hashlib.sha256(b"console.log(1)").hexdigest()[:8]


def test_compute_asset_versions_hash_is_8_hex_chars(tmp_path, monkeypatch):
    _make_assets(tmp_path, {"a.css": b"x"}, {})
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    h = seo.compute_asset_versions()["assets/css/a.css"]
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_asset_versions_changes_when_bytes_change(tmp_path, monkeypatch):
    _make_assets(tmp_path, {"a.css": b"one"}, {})
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    first = seo.compute_asset_versions()["assets/css/a.css"]
    (tmp_path / "assets" / "css" / "a.css").write_bytes(b"two")
    second = seo.compute_asset_versions()["assets/css/a.css"]
    assert first != second


def test_compute_asset_versions_empty_when_no_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    assert seo.compute_asset_versions() == {}


def test_compute_asset_versions_ignores_non_matching_extensions(tmp_path, monkeypatch):
    _make_assets(tmp_path, {"a.css": b"x"}, {})
    # a stray font in the css dir must not be versioned
    (tmp_path / "assets" / "css" / "font.woff2").write_bytes(b"f")
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    versions = seo.compute_asset_versions()
    assert "assets/css/a.css" in versions
    assert "assets/css/font.woff2" not in versions


# ── stamp_assets (the cache-bust ?v= rewriting) ──────────────────────

VERSIONS = {
    "assets/css/site.css": "ab12cd34",
    "assets/js/site.js": "deadbeef",
}


def test_stamp_assets_adds_version():
    html = '<link rel="stylesheet" href="assets/css/site.css">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == '<link rel="stylesheet" href="assets/css/site.css?v=ab12cd34">'
    assert changed is True


def test_stamp_assets_stamps_script_src():
    html = '<script src="assets/js/site.js"></script>'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert 'assets/js/site.js?v=deadbeef' in new
    assert changed is True


def test_stamp_assets_replaces_existing_version_not_stack():
    # The crux of issue #416: an old ?v= must be replaced, never stacked.
    html = '<link href="assets/css/site.css?v=00000000">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == '<link href="assets/css/site.css?v=ab12cd34">'
    assert "?v=00000000" not in new
    assert new.count("?v=") == 1
    assert changed is True


def test_stamp_assets_idempotent_when_hash_current():
    html = '<link href="assets/css/site.css?v=ab12cd34">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == html
    assert changed is False


def test_stamp_assets_leaves_unknown_asset_untouched():
    # File not on disk => not in versions => reference left as-is so the
    # drift surfaces elsewhere.
    html = '<link href="assets/css/missing.css">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == html
    assert changed is False


def test_stamp_assets_strips_stale_version_on_unknown_asset_is_noop():
    # An asset not in the versions map keeps whatever ?v= it already has.
    html = '<link href="assets/css/missing.css?v=12345678">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == html
    assert changed is False


def test_stamp_assets_does_not_touch_fonts_or_images():
    html = (
        '<link href="assets/fonts/x.woff2">'
        '<img src="assets/images/og-image.png">'
    )
    new, changed = seo.stamp_assets(html, {"assets/fonts/x.woff2": "zzzzzzzz"})
    assert new == html
    assert changed is False


def test_stamp_assets_handles_multiple_refs():
    html = (
        '<link href="assets/css/site.css">'
        '<script src="assets/js/site.js"></script>'
    )
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert "assets/css/site.css?v=ab12cd34" in new
    assert "assets/js/site.js?v=deadbeef" in new
    assert changed is True


def test_stamp_assets_only_matches_href_and_src_attrs():
    # data-foo="assets/css/site.css" must not be rewritten.
    html = '<div data-foo="assets/css/site.css"></div>'
    new, changed = seo.stamp_assets(html, VERSIONS)
    assert new == html
    assert changed is False


def test_stamp_assets_ignores_external_urls():
    html = '<link href="https://cdn.example/assets/css/site.css">'
    new, changed = seo.stamp_assets(html, VERSIONS)
    # The regex requires the path to start right after href="/src=", so a
    # host-prefixed absolute URL is never a local ref and is left as-is.
    assert new == html
    assert changed is False


# ── build_seo_block ──────────────────────────────────────────────────

def test_seo_block_wrapped_in_sentinels():
    block = seo.build_seo_block("people", "en", "T", "D")
    assert block.startswith(seo.SENTINEL_BEGIN)
    assert block.rstrip().endswith(seo.SENTINEL_END)


def test_seo_block_canonical_and_url_match():
    block = seo.build_seo_block("grants", "fr", "Titre", "Desc")
    assert '<link rel="canonical" href="https://netsec-cost.eu/grants.fr.html">' in block
    assert 'og:url" content="https://netsec-cost.eu/grants.fr.html"' in block


def test_seo_block_locale_and_alternates():
    block = seo.build_seo_block("people", "fr", "T", "D")
    assert 'og:locale" content="fr_FR"' in block
    # alternates are EN + DE, in that order, excluding the page's own locale
    assert 'og:locale:alternate" content="en_GB"' in block
    assert 'og:locale:alternate" content="de_DE"' in block
    assert 'og:locale:alternate" content="fr_FR"' not in block


def test_seo_block_og_type_article_for_prose_page():
    block = seo.build_seo_block("privacy", "en", "T", "D")
    assert 'og:type" content="article"' in block


def test_seo_block_og_type_defaults_website():
    block = seo.build_seo_block("people", "en", "T", "D")
    assert 'og:type" content="website"' in block


def test_seo_block_escapes_quotes_in_title():
    block = seo.build_seo_block("people", "en", 'A "quoted" title', "D")
    assert 'A &quot;quoted&quot; title' in block
    # raw unescaped form must not leak into an attribute
    assert 'content="A "quoted" title"' not in block


# ── build_jsonld_block ───────────────────────────────────────────────

def test_jsonld_index_has_website_and_webpage():
    block = seo.build_jsonld_block("index", "en", "Home", "Desc")
    inner = block.split("<script type=\"application/ld+json\">\n", 1)[1]
    inner = inner.rsplit("\n</script>", 1)[0]
    data = json.loads(inner)
    types = [n["@type"] for n in data]
    assert "Organization" in types
    assert "WebSite" in types
    assert "WebPage" in types


def test_jsonld_non_index_no_website():
    block = seo.build_jsonld_block("people", "en", "People", "Desc")
    inner = block.split("<script type=\"application/ld+json\">\n", 1)[1]
    inner = inner.rsplit("\n</script>", 1)[0]
    data = json.loads(inner)
    types = [n["@type"] for n in data]
    assert "WebSite" not in types
    assert "Organization" in types
    assert "WebPage" in types


def test_jsonld_inlanguage_maps_locale_to_dashed():
    block = seo.build_jsonld_block("people", "de", "x", "y")
    inner = block.split("<script type=\"application/ld+json\">\n", 1)[1]
    inner = inner.rsplit("\n</script>", 1)[0]
    data = json.loads(inner)
    webpage = [n for n in data if n["@type"] == "WebPage"][0]
    assert webpage["inLanguage"] == "de-DE"


def test_jsonld_is_valid_json_and_wrapped():
    block = seo.build_jsonld_block("about", "en", "About", "Desc")
    assert block.startswith(seo.JSONLD_BEGIN)
    assert block.rstrip().endswith(seo.JSONLD_END)


# ── inject (in-place rewrite + idempotency) ──────────────────────────

MINIMAL_PAGE = (
    '<!DOCTYPE html><html lang="en"><head>'
    '<title>People</title>'
    '<meta name="description" content="The team.">'
    '<link rel="icon" href="/favicon.ico">'
    '</head><body></body></html>'
)


def test_inject_adds_blocks_when_absent():
    new, changed = seo.inject(MINIMAL_PAGE, "people")
    assert changed is True
    assert seo.SENTINEL_BEGIN in new
    assert seo.JSONLD_BEGIN in new
    # SEO block inserted before the icon link
    assert new.index(seo.SENTINEL_BEGIN) < new.index('<link rel="icon"')
    # JSON-LD inserted before </head>
    assert new.index(seo.JSONLD_BEGIN) < new.index("</head>")


def test_inject_idempotent_on_second_run():
    once, _ = seo.inject(MINIMAL_PAGE, "people")
    twice, changed = seo.inject(once, "people")
    assert twice == once
    assert changed is False


def test_inject_rewrites_block_in_place_when_content_changes():
    once, _ = seo.inject(MINIMAL_PAGE, "people")
    # change the title; re-injecting must update the existing block, not
    # duplicate it.
    edited = once.replace("<title>People</title>", "<title>Our People</title>")
    twice, changed = seo.inject(edited, "people")
    assert changed is True
    assert twice.count(seo.SENTINEL_BEGIN) == 1
    assert "Our People" in twice


def test_inject_warns_and_skips_without_icon_anchor(capsys):
    html = '<html lang="en"><head><title>x</title></head></html>'
    new, changed = seo.inject(html, "people")
    # No icon anchor => SEO block skipped, but JSON-LD still goes in
    # before </head>.
    assert seo.SENTINEL_BEGIN not in new
    assert seo.JSONLD_BEGIN in new
    assert changed is True
    out = capsys.readouterr().out
    assert "no <link" in out


# ── main (end-to-end via monkeypatched ROOT) ─────────────────────────

def _write_page(root: Path, name: str, body: str):
    (root / name).write_text(body, encoding="utf-8")


def test_main_check_returns_1_on_drift(tmp_path, monkeypatch, capsys):
    _make_assets(tmp_path, {"site.css": b"x"}, {})
    _write_page(
        tmp_path, "people.html",
        '<html lang="en"><head><title>P</title>'
        '<meta name="description" content="d">'
        '<link rel="icon" href="/f.ico">'
        '<link rel="stylesheet" href="assets/css/site.css">'
        '</head><body></body></html>',
    )
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    monkeypatch.setattr(seo.sys, "argv", ["inject-seo.py", "--check"])
    rc = seo.main()
    assert rc == 1
    assert "would update" in capsys.readouterr().out
    # --check must not write
    assert seo.SENTINEL_BEGIN not in (tmp_path / "people.html").read_text()


def test_main_writes_and_is_then_idempotent(tmp_path, monkeypatch):
    _make_assets(tmp_path, {"site.css": b"x"}, {})
    page = (
        '<html lang="en"><head><title>P</title>'
        '<meta name="description" content="d">'
        '<link rel="icon" href="/f.ico">'
        '<link rel="stylesheet" href="assets/css/site.css">'
        '</head><body></body></html>'
    )
    _write_page(tmp_path, "people.html", page)
    monkeypatch.setattr(seo, "ROOT", tmp_path)

    monkeypatch.setattr(seo.sys, "argv", ["inject-seo.py"])
    assert seo.main() == 0
    written = (tmp_path / "people.html").read_text()
    assert seo.SENTINEL_BEGIN in written
    assert "assets/css/site.css?v=" in written

    # second run: nothing changed, --check should pass with rc 0
    monkeypatch.setattr(seo.sys, "argv", ["inject-seo.py", "--check"])
    assert seo.main() == 0


def test_main_returns_1_when_no_html(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    monkeypatch.setattr(seo.sys, "argv", ["inject-seo.py"])
    rc = seo.main()
    assert rc == 1
    assert "No HTML files" in capsys.readouterr().out


def test_main_stamps_unmanaged_page_assets_only(tmp_path, monkeypatch):
    # An unmanaged page gets asset stamps but no SEO/JSON-LD block.
    _make_assets(tmp_path, {"site.css": b"x"}, {})
    _write_page(
        tmp_path, "random.html",
        '<html lang="en"><head><title>R</title>'
        '<link rel="stylesheet" href="assets/css/site.css">'
        '</head><body></body></html>',
    )
    monkeypatch.setattr(seo, "ROOT", tmp_path)
    monkeypatch.setattr(seo.sys, "argv", ["inject-seo.py"])
    assert seo.main() == 0
    written = (tmp_path / "random.html").read_text()
    assert "assets/css/site.css?v=" in written
    assert seo.SENTINEL_BEGIN not in written
    assert seo.JSONLD_BEGIN not in written


# ── plain-text helpers ───────────────────────────────────────────────

def test_plain_text_strips_tags_and_collapses_whitespace():
    frag = 'A\n  <strong>bold</strong>   answer with a <a href="x">link</a>.'
    assert seo._plain_text(frag) == "A bold answer with a link."


def test_plain_text_unescapes_entities():
    assert seo._plain_text("Grants &amp; funding &mdash; here") == "Grants & funding — here"


def test_truncate_leaves_short_text_untouched():
    assert seo._truncate("short", cap=50) == "short"


def test_truncate_cuts_on_word_boundary_with_ellipsis():
    text = "alpha beta gamma delta epsilon"
    out = seo._truncate(text, cap=14)
    assert out.endswith("…")
    assert "  " not in out
    # cut on a space, never mid-word
    assert out[:-1] in {"alpha beta", "alpha beta gamma"} or out[:-1].count(" ") >= 1
    assert not out[:-1].endswith(" ")


# ── FAQ / glossary parsing ───────────────────────────────────────────

_FAQ_HTML = (
    '<section class="faq-section">'
    '<h2 id="about">About</h2>'
    '<h3 class="faq-q" id="what-is">What is it?</h3>'
    '<p class="faq-a">It is a <a href="x">thing</a> &amp; more.</p>'
    '<h3 class="faq-q" id="who">Who runs it?</h3>'
    '<p class="faq-a">The team.</p>'
    '</section>'
)

_GLOSSARY_HTML = (
    '<dl class="glossary-dl">'
    '<dt id="action">Action</dt>'
    '<dd>A four-year network. See the <a href="y">MoU</a>.</dd>'
    '<dt id="cost">COST</dt>'
    '<dd>European Cooperation in Science and Technology.</dd>'
    '</dl>'
)


def test_parse_faq_items_extracts_anchor_question_answer():
    items = seo.parse_faq_items(_FAQ_HTML)
    assert items == [
        ("what-is", "What is it?", "It is a thing & more."),
        ("who", "Who runs it?", "The team."),
    ]


def test_parse_faq_items_empty_when_no_markup():
    assert seo.parse_faq_items("<p>nothing here</p>") == []


def test_parse_glossary_items_extracts_anchor_term_definition():
    items = seo.parse_glossary_items(_GLOSSARY_HTML)
    assert items == [
        ("action", "Action", "A four-year network. See the MoU."),
        ("cost", "COST", "European Cooperation in Science and Technology."),
    ]


def test_parse_glossary_items_empty_when_no_markup():
    assert seo.parse_glossary_items("<p>nothing</p>") == []


# ── FAQPage / DefinedTermSet JSON-LD nodes ───────────────────────────

def _ld_nodes(block: str):
    inner = block.split('<script type="application/ld+json">\n', 1)[1]
    inner = inner.rsplit("\n</script>", 1)[0]
    data = json.loads(inner)
    return data if isinstance(data, list) else [data]


def test_faqpage_node_built_from_markup():
    node = seo.build_faqpage_node("faq", "en", _FAQ_HTML)
    assert node["@type"] == "FAQPage"
    assert node["url"] == "https://netsec-cost.eu/faq.html"
    qs = node["mainEntity"]
    assert [q["name"] for q in qs] == ["What is it?", "Who runs it?"]
    assert qs[0]["@type"] == "Question"
    assert qs[0]["url"] == "https://netsec-cost.eu/faq.html#what-is"
    assert qs[0]["acceptedAnswer"] == {"@type": "Answer", "text": "It is a thing & more."}


def test_faqpage_node_none_when_no_questions():
    assert seo.build_faqpage_node("faq", "en", "<p>no faq markup</p>") is None


def test_definedtermset_node_built_from_markup():
    node = seo.build_definedtermset_node("glossary", "en", "Glossary", _GLOSSARY_HTML)
    assert node["@type"] == "DefinedTermSet"
    assert node["name"] == "Glossary"
    terms = node["hasDefinedTerm"]
    assert [t["name"] for t in terms] == ["Action", "COST"]
    assert terms[0]["@type"] == "DefinedTerm"
    assert terms[0]["url"] == "https://netsec-cost.eu/glossary.html#action"
    assert terms[0]["description"] == "A four-year network. See the MoU."
    assert terms[0]["inDefinedTermSet"] == "https://netsec-cost.eu/glossary.html"


def test_definedtermset_node_none_when_no_terms():
    assert seo.build_definedtermset_node("glossary", "en", "G", "<p>nope</p>") is None


def test_jsonld_faq_appends_faqpage_node():
    block = seo.build_jsonld_block("faq", "en", "FAQ", "Desc", _FAQ_HTML)
    types = [n["@type"] for n in _ld_nodes(block)]
    assert "FAQPage" in types
    assert "WebPage" in types
    assert "Organization" in types


def test_jsonld_faq_locale_carries_to_faqpage():
    block = seo.build_jsonld_block("faq", "fr", "FAQ", "Desc", _FAQ_HTML)
    faq = [n for n in _ld_nodes(block) if n["@type"] == "FAQPage"][0]
    assert faq["inLanguage"] == "fr-FR"
    assert faq["url"] == "https://netsec-cost.eu/faq.fr.html"
    assert faq["mainEntity"][0]["url"].startswith("https://netsec-cost.eu/faq.fr.html#")


def test_jsonld_glossary_appends_definedtermset_node():
    block = seo.build_jsonld_block("glossary", "en", "Glossary", "Desc", _GLOSSARY_HTML)
    types = [n["@type"] for n in _ld_nodes(block)]
    assert "DefinedTermSet" in types
    assert "WebPage" in types


def test_jsonld_other_pages_get_no_page_type_schema():
    block = seo.build_jsonld_block("people", "en", "People", "Desc", _FAQ_HTML)
    types = [n["@type"] for n in _ld_nodes(block)]
    assert "FAQPage" not in types
    assert "DefinedTermSet" not in types


def test_jsonld_faq_without_markup_omits_faqpage_but_keeps_webpage():
    # A faq page whose body has no faq-q markup still gets the base nodes.
    block = seo.build_jsonld_block("faq", "en", "FAQ", "Desc", html="<body></body>")
    types = [n["@type"] for n in _ld_nodes(block)]
    assert "FAQPage" not in types
    assert "WebPage" in types


def test_inject_faq_is_idempotent_with_structured_data():
    page = (
        '<html lang="en"><head><title>FAQ</title>'
        '<meta name="description" content="Questions.">'
        '<link rel="icon" href="/f.ico"></head><body>'
        + _FAQ_HTML +
        '</body></html>'
    )
    once, changed1 = seo.inject(page, "faq")
    assert changed1 is True
    assert "FAQPage" in once
    twice, changed2 = seo.inject(once, "faq")
    assert changed2 is False
    assert twice == once
    # the injected JSON-LD must not feed back as new questions on re-run
    assert once.count('"@type": "FAQPage"') == 1