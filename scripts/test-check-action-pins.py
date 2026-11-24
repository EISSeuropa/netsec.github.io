"""scripts/check-action-pins.py (#2260): each SHA-pinned action's comment
names the major version of the tags at its SHA. No network: the tag lookup
is replaced with a fixed table.

Run: python3 -m pytest scripts/test-check-action-pins.py -q
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_action_pins", Path(__file__).resolve().parent / "check-action-pins.py")
pins = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pins)

A = "a" * 40   # tagged v7 and v7.0.2
B = "b" * 40   # tagged 12.6.2 and v12, no v prefix on the full version
C = "c" * 40   # an annotated tag: only the ^{} line names the commit
D = "d" * 40   # no tag at all

TAGS = {
    "actions/upload-artifact": [(A, "v7"), (A, "v7.0.2"), ("e" * 40, "v4.6.2")],
    "treosh/lighthouse-ci-action": [(B, "12.6.2"), (B, "v12")],
    "peter-evans/create-pull-request": [("f" * 40, "v8.1.3"), (C, "v8.1.3^{}"), (C, "latest")],
    "owner/untagged": [],
}
CALLS: list[str] = []


def resolve(repo):
    CALLS.append(repo)
    return [(sha, tag.removesuffix("^{}")) for sha, tag in TAGS[repo]]


def run(tmp_path, text, *argv):
    wf = tmp_path / "wf"
    wf.mkdir(exist_ok=True)
    (wf / "ci.yml").write_text(text, encoding="utf-8")
    CALLS.clear()
    code = pins.main(list(argv), resolve=resolve, workflows=wf)
    return code, (wf / "ci.yml").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(pins, "ROOT", tmp_path)


def test_matching_comments_pass(tmp_path, capsys):
    text = (f"      - uses: actions/upload-artifact@{A}  # v7 (sha-pinned)\n"
            f"        uses: treosh/lighthouse-ci-action@{B}  # v12 (sha-pinned)\n"
            f"        uses: peter-evans/create-pull-request@{C}  # v8 (sha-pinned)\n")
    code, after = run(tmp_path, text)
    assert code == 0 and after == text
    assert "Drifted comments: 0." in capsys.readouterr().out


def test_drifted_comment_fails_with_an_annotation(tmp_path, capsys):
    code, _ = run(tmp_path, f"        uses: actions/upload-artifact@{A}  # v4.6.2 (sha-pinned)\n")
    out = capsys.readouterr().out
    assert code == 1
    assert "::error file=wf/ci.yml,line=1::comment says v4.6.2, the SHA is v7" in out


def test_warn_reports_drift_and_exits_zero(tmp_path, capsys):
    code, _ = run(tmp_path, f"        uses: actions/upload-artifact@{A}  # v4 (sha-pinned)\n", "--warn")
    assert code == 0
    assert "::warning file=wf/ci.yml,line=1::" in capsys.readouterr().out


def test_fix_rewrites_drifted_and_missing_comments_only(tmp_path):
    text = ("jobs:\n"
            f"      - uses: actions/upload-artifact@{A}  # v4.6.2 (sha-pinned)\n"
            f"        uses: treosh/lighthouse-ci-action@{B}\n"
            f"        uses: peter-evans/create-pull-request@{C}  # v8 (sha-pinned)\n")
    code, after = run(tmp_path, text, "--fix")
    assert code == 0
    assert after == ("jobs:\n"
                     f"      - uses: actions/upload-artifact@{A}  # v7 (sha-pinned)\n"
                     f"        uses: treosh/lighthouse-ci-action@{B}  # v12 (sha-pinned)\n"
                     f"        uses: peter-evans/create-pull-request@{C}  # v8 (sha-pinned)\n")
    assert run(tmp_path, after)[0] == 0


def test_unresolvable_lines_fail_in_every_mode(tmp_path, capsys):
    text = (f"        uses: owner/untagged@{D}  # v1 (sha-pinned)\n"
            "        uses: actions/upload-artifact@v7\n")
    for argv in ([], ["--warn"], ["--fix"]):
        code, after = run(tmp_path, text, *argv)
        assert code == 1 and after == text
    out = capsys.readouterr().out
    assert "no version tag of owner/untagged points at this SHA" in out
    assert "not pinned to a 40-character SHA" in out


def test_local_reusable_workflows_are_skipped(tmp_path):
    code, _ = run(tmp_path, "    uses: ./.github/workflows/_pycheck.yml\n")
    assert code == 0 and CALLS == []


def test_one_tag_lookup_per_repository(tmp_path):
    line = f"        uses: actions/upload-artifact@{A}  # v7 (sha-pinned)\n"
    run(tmp_path, line * 3)
    assert CALLS == ["actions/upload-artifact"]


def test_sub_path_actions_resolve_against_their_repository(tmp_path):
    code, _ = run(tmp_path, f"        uses: actions/upload-artifact/merge@{A}  # v7 (sha-pinned)\n")
    assert code == 0 and CALLS == ["actions/upload-artifact"]
