"""The `Fold in a ledger that has not reached main yet` step in
.github/workflows/social-bluesky.yml, exercised as shell.

The step exists because a published post only reaches the ledger on `main`
once its auto-merging PR lands. A news.xml push arriving in that window used
to re-queue an already-published item for approval (run 30129049311, 24 July
2026). The step unions in the keys sitting on the `social/ledger` branch.

Union, not replace: `social/ledger` outlives its merged PR and is usually
behind main, so replacing the file would resurrect items main had already
ruled out. These tests pin that distinction, and pin that both jobs run the
same shell.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/social-bluesky.yml"
STEP = "Fold in a ledger that has not reached main yet"


def fold_steps():
    """The shell body of every `STEP` step, dedented. No PyYAML in CI, so this
    reads the block scalars directly: everything indented past the `run: |`
    line, up to the first non-blank line that is not."""
    out = []
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip() != f"- name: {STEP}":
            continue
        assert lines[i + 1].strip() == "run: |", f"{STEP} must use a `run: |` block"
        indent = len(lines[i + 1]) - len(lines[i + 1].lstrip()) + 2
        body = []
        for nxt in lines[i + 2:]:
            if nxt.strip() and not nxt.startswith(" " * indent):
                break
            body.append(nxt[indent:])
        out.append("\n".join(body).rstrip("\n") + "\n")
    return out


def run_fold(main_keys, branch_keys):
    """Run the step against a fake repo. `branch_keys=None` means no such branch."""
    script = fold_steps()[0]
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "data/social-posted.json").write_text(json.dumps({"posted": main_keys}, indent=2) + "\n")

    # Stub `git`: no branch means fetch fails, otherwise show prints its ledger.
    if branch_keys is None:
        (d / "git").write_text("#!/bin/sh\nexit 1\n")
    else:
        (d / "branch.json").write_text(json.dumps({"posted": branch_keys}))
        (d / "git").write_text(f'#!/bin/sh\n[ "$1" = show ] && cat {d}/branch.json\nexit 0\n')
    (d / "git").chmod(0o755)

    proc = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=d,
        env={**os.environ, "PATH": f"{d}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads((d / "data/social-posted.json").read_text())["posted"], proc.stdout


def test_both_jobs_run_the_same_fold():
    steps = fold_steps()
    assert len(steps) == 2, "preview and publish must both fold the ledger"
    assert steps[0] == steps[1], "the two copies of the fold step have drifted apart"


def test_key_published_but_not_yet_merged_is_folded_in():
    posted, out = run_fold(["a"], ["a", "b"])
    assert posted == ["a", "b"]
    assert "Folded 1 key" in out


def test_stale_branch_behind_main_removes_nothing():
    posted, out = run_fold(["a", "b", "c"], ["a"])
    assert posted == ["a", "b", "c"]
    assert "Folded 0 key" in out


def test_identical_ledgers_are_a_no_op():
    posted, _ = run_fold(["a", "b"], ["a", "b"])
    assert posted == ["a", "b"]


def test_absent_branch_leaves_the_ledger_alone():
    posted, _ = run_fold(["a"], None)
    assert posted == ["a"]


def test_written_ledger_matches_the_composer_format():
    """save_ledger() in social-post.py writes indent=2 plus a trailing newline."""
    script = fold_steps()[0]
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "data/social-posted.json").write_text('{\n  "posted": [\n    "a"\n  ]\n}\n')
    (d / "branch.json").write_text(json.dumps({"posted": ["b"]}))
    (d / "git").write_text(f'#!/bin/sh\n[ "$1" = show ] && cat {d}/branch.json\nexit 0\n')
    (d / "git").chmod(0o755)
    subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=d,
        env={**os.environ, "PATH": f"{d}:{os.environ['PATH']}"},
        check=True,
        capture_output=True,
    )
    text = (d / "data/social-posted.json").read_text()
    assert text.endswith("\n")
    assert text == json.dumps({"posted": ["a", "b"]}, indent=2, ensure_ascii=False) + "\n"


def test_no_scratch_file_is_left_behind():
    script = fold_steps()[0]
    d = Path(tempfile.mkdtemp())
    (d / "data").mkdir()
    (d / "data/social-posted.json").write_text('{"posted": ["a"]}\n')
    (d / "branch.json").write_text(json.dumps({"posted": ["b"]}))
    (d / "git").write_text(f'#!/bin/sh\n[ "$1" = show ] && cat {d}/branch.json\nexit 0\n')
    (d / "git").chmod(0o755)
    subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=d,
        env={**os.environ, "PATH": f"{d}:{os.environ['PATH']}"},
        check=True,
        capture_output=True,
    )
    # The ledger PR uses add-paths, but a stray file would still dirty the tree.
    assert not (d / "branch-ledger.json").exists()
