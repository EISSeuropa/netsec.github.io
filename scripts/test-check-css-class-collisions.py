"""Tests for scripts/check-css-class-collisions.py.

The module name contains hyphens, so it cannot be imported by name; it is
loaded via importlib from its relative path. Tests exercise the
logic-bearing functions: the selector-subject extractor (`styled_class`),
the CSS tokenising state machine (`iter_selectors`), declaration
collection with suppression / media / multi-subject filtering
(`collect_declarations`), clustering (`cluster`), collision detection for
both rules (`find_collisions`), and human-readable formatting
(`format_problem`). `main` is covered for both the missing-file and the
found-collisions paths via monkeypatching the module globals (no real
network, no mutation of tracked repo files).
"""

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the hyphenated module from its relative path.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_MODULE_PATH = _HERE / "check-css-class-collisions.py"

_spec = importlib.util.spec_from_file_location("check_css_class_collisions", _MODULE_PATH)
ccc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccc)


# ---------------------------------------------------------------------------
# styled_class
# ---------------------------------------------------------------------------
class TestStyledClass:
    def test_plain_class(self):
        assert ccc.styled_class(".foo") == "foo"

    def test_pseudo_class_attached(self):
        assert ccc.styled_class(".foo:hover") == "foo"

    def test_descendant_returns_last_compound(self):
        assert ccc.styled_class(".foo .bar") == "bar"

    def test_child_combinator(self):
        assert ccc.styled_class(".foo > .bar:hover") == "bar"

    def test_pseudo_element(self):
        assert ccc.styled_class(".foo .bar::after") == "bar"

    def test_last_compound_no_class_returns_none(self):
        assert ccc.styled_class(".foo a::after") is None

    def test_empty_selector_returns_none(self):
        assert ccc.styled_class("") is None
        assert ccc.styled_class("   ") is None

    def test_no_class_at_all_returns_none(self):
        assert ccc.styled_class("div > span") is None

    def test_compound_multiple_classes_picks_last_in_source(self):
        # `.foo.bar` is a single compound; last class token wins.
        assert ccc.styled_class(".foo.bar") == "bar"

    def test_not_pseudo_last_in_source_wins(self):
        # `:not(.bar)` class comes after `.foo` in source order.
        assert ccc.styled_class(".foo:not(.bar)") == "bar"

    def test_hyphenated_class_name(self):
        assert ccc.styled_class(".member-card") == "member-card"

    def test_leading_whitespace_stripped(self):
        assert ccc.styled_class("   .foo   ") == "foo"

    def test_tilde_and_plus_combinators(self):
        assert ccc.styled_class(".a + .b") == "b"
        assert ccc.styled_class(".a ~ .b") == "b"

    def test_numeric_after_dot_not_a_class(self):
        # CLASS_RE requires a leading letter; ".5em"-style tokens ignored.
        assert ccc.styled_class("0.5em") is None


# ---------------------------------------------------------------------------
# iter_selectors
# ---------------------------------------------------------------------------
class TestIterSelectors:
    def test_single_rule(self):
        css = ".foo { color: red; }"
        out = list(ccc.iter_selectors(css))
        assert out == [(1, ".foo", 0)]

    def test_line_numbers_tracked(self):
        css = "\n\n.foo {\n  color: red;\n}\n.bar { color: blue; }"
        out = list(ccc.iter_selectors(css))
        # .foo selector starts on line 3, .bar on line 6.
        assert out[0][0] == 3 and out[0][1] == ".foo"
        assert out[1][0] == 6 and out[1][1] == ".bar"

    def test_media_depth_marks_nested_rules(self):
        css = "@media (min-width: 600px) {\n  .foo { color: red; }\n}\n.bar { color: blue; }"
        out = list(ccc.iter_selectors(css))
        sel_map = {s: (ln, md) for (ln, s, md) in out}
        assert sel_map[".foo"][1] == 1   # inside @media
        assert sel_map[".bar"][1] == 0   # back to top level after closing

    def test_supports_and_container_also_increase_depth(self):
        css = "@supports (display:grid) {\n  .a { x: 1; }\n}\n@container (min-width: 1px) {\n  .b { y: 2; }\n}"
        out = {s: md for (_, s, md) in ccc.iter_selectors(css)}
        assert out[".a"] == 1
        assert out[".b"] == 1

    def test_keyframes_block_skipped_entirely(self):
        css = "@keyframes spin {\n  from { opacity: 0; }\n  to { opacity: 1; }\n}\n.real { color: red; }"
        out = list(ccc.iter_selectors(css))
        # The from/to keyframe selectors must not be yielded.
        sels = [s for (_, s, _) in out]
        assert sels == [".real"]

    def test_brace_inside_string_does_not_break_state(self):
        css = '.foo { content: "{"; }\n.bar { color: red; }'
        out = [s for (_, s, _) in ccc.iter_selectors(css)]
        assert out == [".foo", ".bar"]

    def test_brace_inside_comment_does_not_break_state(self):
        css = ".foo { color: red; }\n/* a { rogue brace */\n.bar { color: blue; }"
        out = [s for (_, s, _) in ccc.iter_selectors(css)]
        assert out == [".foo", ".bar"]

    def test_unterminated_comment_stops_cleanly(self):
        css = ".foo { color: red; }\n/* never closed"
        out = [s for (_, s, _) in ccc.iter_selectors(css)]
        assert out == [".foo"]

    def test_comment_line_count_within_keyframes_skip(self):
        # Comment with newlines inside a skipped @-block must keep line
        # numbers accurate for a following rule.
        css = "@font-face {\n  /* multi\nline\ncomment */\n  src: url(x);\n}\n.after { color: red; }"
        out = list(ccc.iter_selectors(css))
        assert out[0][1] == ".after"
        # ".after" is on line 7.
        assert out[0][0] == 7

    def test_string_with_escaped_quote(self):
        css = '.foo { content: "a\\"b"; }\n.bar { x: 1; }'
        out = [s for (_, s, _) in ccc.iter_selectors(css)]
        assert out == [".foo", ".bar"]

    def test_selector_list_yielded_as_one(self):
        css = ".a, .b, .c { color: red; }"
        out = list(ccc.iter_selectors(css))
        assert len(out) == 1
        assert out[0][1] == ".a, .b, .c"


# ---------------------------------------------------------------------------
# collect_declarations
# ---------------------------------------------------------------------------
class TestCollectDeclarations:
    def test_basic_collection(self):
        css = ".foo { color: red; }\n.bar { color: blue; }"
        decls = ccc.collect_declarations(css)
        assert decls == {"foo": [1], "bar": [2]}

    def test_media_rules_excluded(self):
        css = "@media (min-width: 1px) {\n  .foo { color: red; }\n}\n.bar { color: blue; }"
        decls = ccc.collect_declarations(css)
        assert "foo" not in decls
        # line 1 @media, line 2 .foo, line 3 closing brace, line 4 .bar
        assert decls["bar"] == [4]

    def test_descendant_selectors_skipped(self):
        css = ".dark .foo { color: red; }\n.foo { color: blue; }"
        decls = ccc.collect_declarations(css)
        # Only the sole-compound `.foo` (line 2) is recorded.
        assert decls == {"foo": [2]}

    def test_multi_subject_selector_list_over_three_skipped(self):
        css = ".a, .b, .c, .d { color: red; }\n.keep { x: 1; }"
        decls = ccc.collect_declarations(css)
        for cls in ("a", "b", "c", "d"):
            assert cls not in decls
        assert decls["keep"] == [2]

    def test_three_subject_list_kept(self):
        css = ".a, .b, .c { color: red; }"
        decls = ccc.collect_declarations(css)
        assert set(decls) == {"a", "b", "c"}

    def test_suppression_on_preceding_line(self):
        css = "/* css-collision-allow: .foo */\n.foo { color: red; }"
        decls = ccc.collect_declarations(css)
        assert "foo" not in decls

    def test_suppression_only_targets_named_class(self):
        css = "/* css-collision-allow: .foo */\n.bar { color: red; }"
        decls = ccc.collect_declarations(css)
        # Marker names .foo but the rule is .bar, so .bar is NOT suppressed.
        assert decls == {"bar": [2]}

    def test_duplicate_lines_deduplicated_and_sorted(self):
        # Same class on two separate lines -> sorted unique list.
        css = ".foo { a: 1; }\n.foo { b: 2; }"
        decls = ccc.collect_declarations(css)
        assert decls == {"foo": [1, 2]}

    def test_selector_with_no_class_ignored(self):
        css = "div { color: red; }\n.foo { x: 1; }"
        decls = ccc.collect_declarations(css)
        assert decls == {"foo": [2]}


# ---------------------------------------------------------------------------
# cluster
# ---------------------------------------------------------------------------
class TestCluster:
    def test_empty(self):
        assert ccc.cluster([], 200) == []

    def test_single(self):
        assert ccc.cluster([5], 200) == [[5]]

    def test_within_gap_merges(self):
        assert ccc.cluster([10, 50, 100], 200) == [[10, 50, 100]]

    def test_beyond_gap_splits(self):
        assert ccc.cluster([10, 300], 200) == [[10], [300]]

    def test_exactly_gap_is_same_cluster(self):
        # spacing == gap is <= gap, so same cluster.
        assert ccc.cluster([10, 210], 200) == [[10, 210]]

    def test_one_past_gap_splits(self):
        assert ccc.cluster([10, 211], 200) == [[10], [211]]

    def test_mixed(self):
        assert ccc.cluster([1, 2, 500, 501, 1000], 200) == [[1, 2], [500, 501], [1000]]


# ---------------------------------------------------------------------------
# find_collisions
# ---------------------------------------------------------------------------
class TestFindCollisions:
    def test_collision_two_far_clusters(self):
        decls = {"foo": [10, 400]}
        problems = list(ccc.find_collisions(decls))
        assert len(problems) == 1
        p = problems[0]
        assert p["kind"] == "collision"
        assert p["name"] == "foo"
        assert p["clusters"] == [[10], [400]]

    def test_no_collision_when_close(self):
        decls = {"foo": [10, 50]}
        assert list(ccc.find_collisions(decls)) == []

    def test_orphan_bem_detected(self):
        # child `.foo-bar` is far from its parent `.foo`.
        decls = {"foo": [10], "foo-bar": [500]}
        problems = list(ccc.find_collisions(decls))
        assert len(problems) == 1
        p = problems[0]
        assert p["kind"] == "orphan_bem"
        assert p["name"] == "foo-bar"
        assert p["parent"] == "foo"
        assert p["distance"] == 490
        assert p["child_lines"] == [500]
        assert p["parent_lines"] == [10]

    def test_bem_child_close_to_parent_ok(self):
        decls = {"foo": [10], "foo-bar": [50]}
        assert list(ccc.find_collisions(decls)) == []

    def test_bem_child_with_no_known_parent_ignored(self):
        decls = {"foo-bar": [500]}  # no ".foo" anywhere
        assert list(ccc.find_collisions(decls)) == []

    def test_collision_takes_precedence_over_orphan_bem(self):
        # `.foo-bar` is itself a collision (rule 1) AND an orphan (rule 2);
        # it must be reported only once, as a collision.
        decls = {"foo": [10], "foo-bar": [20, 600]}
        problems = list(ccc.find_collisions(decls))
        kinds = [(p["kind"], p["name"]) for p in problems]
        assert ("collision", "foo-bar") in kinds
        assert ("orphan_bem", "foo-bar") not in kinds

    def test_orphan_bem_uses_nearest_parent_declaration(self):
        # Parent declared in two spots, both far from the child; distance
        # is to the nearer of the two (1000 -> |1000-300|=700 beats
        # |1000-10|=990).
        decls = {"foo": [10, 300], "foo-bar": [1000]}
        problems = list(ccc.find_collisions(decls))
        orphan = [p for p in problems if p["kind"] == "orphan_bem"]
        assert len(orphan) == 1
        assert orphan[0]["distance"] == 700  # |1000 - 300|

    def test_no_problems_empty(self):
        assert list(ccc.find_collisions({})) == []


# ---------------------------------------------------------------------------
# format_problem
# ---------------------------------------------------------------------------
class TestFormatProblem:
    def test_collision_format(self):
        p = {"kind": "collision", "name": "member-card", "clusters": [[10], [400, 420]]}
        out = ccc.format_problem(p)
        assert "COLLISION  .member-card" in out
        assert "L10" in out
        assert "L400–L420" in out
        assert "(1 rule)" in out      # singular for single-line cluster
        assert "(2 rules)" in out     # plural for two-line cluster
        assert str(ccc.GAP_THRESHOLD_LINES) in out

    def test_orphan_bem_format(self):
        p = {
            "kind": "orphan_bem",
            "name": "foo-bar",
            "child_lines": [500],
            "parent": "foo",
            "parent_lines": [10],
            "distance": 490,
        }
        out = ccc.format_problem(p)
        assert "ORPHAN BEM CHILD  .foo-bar" in out
        assert "L500" in out
        assert "490 lines away" in out
        assert "`.foo`" in out

    def test_unknown_kind(self):
        p = {"kind": "weird", "name": "x"}
        out = ccc.format_problem(p)
        assert out.startswith("  UNKNOWN")


# ---------------------------------------------------------------------------
# main (via monkeypatched module globals; no real file mutation / network)
# ---------------------------------------------------------------------------
class TestMain:
    @staticmethod
    def _css_dir(tmp_path):
        d = tmp_path / "assets" / "css"
        d.mkdir(parents=True)
        return d

    def test_missing_file_returns_2(self, tmp_path, monkeypatch, capsys):
        # An empty (or absent) css directory is a setup error.
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", tmp_path / "nope")
        rc = ccc.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "no CSS files" in err

    def test_clean_file_returns_0(self, tmp_path, monkeypatch, capsys):
        d = self._css_dir(tmp_path)
        (d / "site.css").write_text(".foo { color: red; }\n.bar { color: blue; }", encoding="utf-8")
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", d)
        rc = ccc.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "no class-name collisions" in out

    def test_collision_file_returns_1(self, tmp_path, monkeypatch, capsys):
        # `.foo` declared ~400 lines apart -> a collision.
        d = self._css_dir(tmp_path)
        body = ".foo { color: red; }\n" + ("/* pad */\n" * 400) + ".foo { color: blue; }\n"
        (d / "site.css").write_text(body, encoding="utf-8")
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", d)
        rc = ccc.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "collision" in out.lower()
        assert "css-collision-allow" in out

    def test_suppression_round_trip(self, tmp_path, monkeypatch, capsys):
        # Same collision as above but the second rule is suppressed.
        d = self._css_dir(tmp_path)
        body = (
            ".foo { color: red; }\n"
            + ("/* pad */\n" * 400)
            + "/* css-collision-allow: .foo */\n"
            + ".foo { color: blue; }\n"
        )
        (d / "site.css").write_text(body, encoding="utf-8")
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", d)
        rc = ccc.main()
        assert rc == 0

    def test_cross_file_duplicate_returns_1(self, tmp_path, monkeypatch, capsys):
        # The same keyed class in two stylesheets is the split-bundle
        # variant of the collision: the second file silently overrides
        # the first on any page loading both.
        d = self._css_dir(tmp_path)
        (d / "site.css").write_text(".foo { color: red; }", encoding="utf-8")
        (d / "bundle.css").write_text(".foo { color: blue; }", encoding="utf-8")
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", d)
        rc = ccc.main()
        assert rc == 1
        out = capsys.readouterr().out
        assert "cross-file" in out
        assert ".foo" in out

    def test_cross_file_suppression(self, tmp_path, monkeypatch, capsys):
        # An allow-comment on either declaration excuses the pair.
        d = self._css_dir(tmp_path)
        (d / "site.css").write_text(".foo { color: red; }", encoding="utf-8")
        (d / "bundle.css").write_text(
            "/* css-collision-allow: .foo */\n.foo { color: blue; }", encoding="utf-8")
        monkeypatch.setattr(ccc, "ROOT", tmp_path)
        monkeypatch.setattr(ccc, "CSS_DIR", d)
        rc = ccc.main()
        assert rc == 0


# ---------------------------------------------------------------------------
# End-to-end on the real repo CSS (read-only smoke; never mutates).
# ---------------------------------------------------------------------------
def test_real_css_parses_if_present():
    """If the repo's site.css exists, collect_declarations must run without
    raising and return a dict. This is read-only; it never writes."""
    css_files = sorted(ccc.CSS_DIR.glob("*.css"))
    if not css_files:
        pytest.skip("no stylesheets present in this checkout")
    for css_file in css_files:
        text = css_file.read_text(encoding="utf-8")
        decls = ccc.collect_declarations(text)
        assert isinstance(decls, dict)
    # find_collisions must also be iterable without error.
    problems = list(ccc.find_collisions(decls))
    assert isinstance(problems, list)