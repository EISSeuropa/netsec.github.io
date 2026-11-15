"""The two ledger steps in .github/workflows/spotlight-rotate.yml, exercised
as shell: `Fold in ledgers that have not reached main yet` before the post,
and `Limit the ledger change to this run's keys` before the auto-PR (#2130).

The fold-in unions the keys on `social/ledger` and `spotlight/auto` into the
checkout, so a re-run while the week's PR is still open sees the week's key
and posts nothing. The limit step then restores main's ledger and adds only
the keys the post step wrote, so the PR never carries another branch's keys
and cannot conflict with that branch's PR.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/spotlight-rotate.yml"
FOLD = "Fold in ledgers that have not reached main yet"
LIMIT = "Limit the ledger change to this run's keys"


def step_body(name):
    """The shell body of the named step, dedented. Reads the block scalar
    directly, as test-social-ledger-fold.py does, since CI has no PyYAML."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip() != f"- name: {name}":
            continue
        j = i + 1
        while lines[j].strip().startswith("#"):
            j += 1
        assert lines[j].strip() == "run: |", f"{name} must use a `run: |` block"
        indent = len(lines[j]) - len(lines[j].lstrip()) + 2
        body = []
        for nxt in lines[j + 1:]:
            if nxt.strip() and not nxt.startswith(" " * indent):
                break
            body.append(nxt[indent:])
        return "\n".join(body).rstrip("\n") + "\n"
    raise AssertionError(f"step not found: {name}")


def make_repo(main_keys, branches):
    """A fake checkout. `branches` maps a branch name to its ledger keys; a
    branch not in the map does not exist, so `git fetch` fails for it."""
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "tmp").mkdir()
    (d / "data/social-posted.json").write_text(json.dumps({"posted": main_keys}, indent=2) + "\n")
    for name, keys in branches.items():
        (d / f"{name.replace('/', '_')}.json").write_text(json.dumps({"posted": keys}))
    # fetch records the branch it was asked for, show prints that branch's ledger.
    (d / "git").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = fetch ]; then\n'
        '  f="' + str(d) + '/$(echo "$4" | tr / _).json"\n'
        '  [ -f "$f" ] || exit 1\n'
        '  echo "$f" > ' + str(d) + "/fetched\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = show ]; then cat "$(cat ' + str(d) + '/fetched)"; exit 0; fi\n'
        "exit 1\n"
    )
    (d / "git").chmod(0o755)
    return d


def run(d, name):
    proc = subprocess.run(
        ["bash", "-e", "-c", step_body(name)],
        cwd=d,
        env={**os.environ, "PATH": f"{d}:{os.environ['PATH']}", "RUNNER_TEMP": str(d / "tmp")},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def ledger(d):
    return json.loads((d / "data/social-posted.json").read_text())["posted"]


def post(d, *keys):
    """Stand-in for social-post.py appending what it published."""
    led = d / "data/social-posted.json"
    data = json.loads(led.read_text())
    data["posted"] += list(keys)
    led.write_text(json.dumps(data, indent=2) + "\n")


def test_fold_reads_both_branches():
    d = make_repo(["a"], {"social/ledger": ["a", "news::n1"], "spotlight/auto": ["a", "spotlight::x::2026-W46"]})
    out = run(d, FOLD)
    assert ledger(d) == ["a", "news::n1", "spotlight::x::2026-W46"]
    assert "social/ledger" in out and "spotlight/auto" in out


def test_missing_branches_leave_the_ledger_alone():
    d = make_repo(["a"], {})
    run(d, FOLD)
    assert ledger(d) == ["a"]


def test_stale_branch_removes_nothing():
    d = make_repo(["a", "b"], {"spotlight/auto": ["a"]})
    run(d, FOLD)
    assert ledger(d) == ["a", "b"]


def test_pr_carries_only_this_runs_keys():
    d = make_repo(["a"], {"social/ledger": ["a", "news::n1"], "spotlight/auto": ["a", "spotlight::x::2026-W45"]})
    run(d, FOLD)
    post(d, "spotlight::y::2026-W46")
    out = run(d, LIMIT)
    assert ledger(d) == ["a", "spotlight::y::2026-W46"]
    assert "carries 1 new key" in out


def test_rerun_with_open_pr_posts_nothing_and_changes_nothing():
    """The week's key is on spotlight/auto only. After the fold-in the post
    step sees it and skips, so the PR leaves main's ledger as it was."""
    d = make_repo(["a"], {"spotlight/auto": ["a", "spotlight::x::2026-W46"]})
    run(d, FOLD)
    assert "spotlight::x::2026-W46" in ledger(d)
    run(d, LIMIT)
    assert ledger(d) == ["a"]


def test_no_scratch_file_is_left_behind():
    d = make_repo(["a"], {"social/ledger": ["b"]})
    run(d, FOLD)
    assert not (d / "branch-ledger.json").exists()


def test_written_ledger_matches_the_composer_format():
    d = make_repo(["a"], {})
    run(d, FOLD)
    post(d, "b")
    run(d, LIMIT)
    text = (d / "data/social-posted.json").read_text()
    assert text == json.dumps({"posted": ["a", "b"]}, indent=2, ensure_ascii=False) + "\n"
