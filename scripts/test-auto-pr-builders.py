"""Every auto-PR workflow reruns the gated builders its own writes invalidate.

Four times a workflow has committed a data file without rerunning a builder
that reads it, and the auto-PR arrived already failing: the Pagefind bio stubs
(#1428), the network map (#764), then the directory index and the sitemap on
the same workflow within a day (#1803, #1804). The shape is always the same,
so check it instead of finding it again.

The gate side is derived. what-to-rebuild.py already reads which builders run
with `--check`, and a builder's inputs are the repo paths it names, so adding
a gate or an input needs no edit here.

The write side is declared in WRITES below, because reading it back out of the
sync scripts is not reliable: sync-cost.py writes its HTML pages through a loop
variable, and a static read misses those. Declaring it is only safe because
test_every_auto_pr_workflow_is_accounted_for fails when a workflow is added
and left out, so the table cannot go stale in silence.
"""
import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("wtr", ROOT / "scripts/what-to-rebuild.py")
wtr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wtr)

# What each auto-PR workflow commits. Paths only, no globs: a directory entry
# ends in "/" and matches anything beneath it.
WRITES = {
    "sync-bios.yml": {"data/bios.json", "assets/images/people/"},
    "sync-cost.yml": {"data/bios.json", "data/wg.json", "data/mc-members.json",
                      "data/cost-wg-state.json"},
    "sync-indico.yml": {"data/indico.json", "data/events.json"},
    "news-publish.yml": {"data/news.json"},
    "spotlight-rotate.yml": {"data/spotlight.json", "data/social-posted.json"},
    "social-bluesky.yml": {"data/social-posted.json"},
    "roadmap-refresh.yml": {"data/roadmap-progress.json", "docs/roadmap-2026.md"},
    "linkedin-version-check.yml": {"data/linkedin-api-version.json"},
}

SKILL = ROOT / ".claude/skills/rebuild-gates/SKILL.md"

# `NAME = ROOT / "data" / "bios.json"`, the way every builder declares a path.
# Indented too: build-network-map.py reaches data/indico.json from a local
# inside load_programmes(), and that is still an input.
PATH_CONST = re.compile(
    r'^ *(\w+) *= *(?:ROOT|REPO|BASE) *((?:/ *"[^"]+" *)+)', re.M)
# A path written out in full, as a glob argument or in a docstring. Picked up
# so a builder that never binds its input to a name is not read as inputless.
PATH_LITERAL = re.compile(r'"((?:data|assets)/[^"\s]+)"')
# The same path expression unbound, as a list element or an inline argument.
ANY_PATH = re.compile(r'(?:ROOT|REPO|BASE) *((?:/ *"[^"]+" *)+)')
# A real command, not a mention of one. Both workflows and scripts describe
# builders in their comments, and sync-cost.py's prose names two it never runs.
RUN_LINE = re.compile(
    r"^\s*(?:(?:run|command):\s*)?(?:python3|bash|node) +scripts/([a-zA-Z0-9._-]+)",
    re.M)
# Named in a comment in autopr-token-health.yml, so match the step that uses it.
OPENS_PR = re.compile(r"^\s*uses:.*create-pull-request", re.M)

# Builders a workflow's own script runs, which no run line in the YAML shows.
# Kept explicit rather than parsed: sync-indico.py builds the path from parts
# (ROOT / "scripts" / "build-calendar.py") and hands it to subprocess, and a
# regex that found that would also find every builder named in a comment.
INVOKED_BY_SCRIPT = {"sync-indico.py": {"build-calendar.py"}}


def declared_paths(text):
    """Constant name -> repo-relative path, for every path a script names."""
    return {m.group(1): "/".join(re.findall(r'"([^"]+)"', m.group(2)))
            for m in PATH_CONST.finditer(text)}


def inputs(script):
    """The repo paths a builder reads: every path it names bar the ones it
    writes. An over-read is safe here, since it can only demand a rerun the
    builder did not strictly need."""
    text = (ROOT / "scripts" / script).read_text()
    paths = declared_paths(text)
    written = {p for n, p in paths.items()
               if re.search(rf"\b{n}\.write_text\(", text)}
    named = (set(paths.values()) | set(PATH_LITERAL.findall(text))
             | {"/".join(re.findall(r'"([^"]+)"', m))
                for m in ANY_PATH.findall(text)})
    return named - written


def gated_builders():
    """Builder script -> the gate that fails when its output is stale."""
    out = {}
    for name, _paths, cmds in wtr.gates():
        for script, extra in cmds:
            if "--check" in extra:
                out.setdefault(pathlib.Path(script).name, name)
    return out


def runs(workflow):
    """Builders a workflow gets run, whether from its own YAML or from a
    script it calls."""
    ran = set(RUN_LINE.findall((wtr.WORKFLOWS / workflow).read_text()))
    for script in list(ran):
        ran |= INVOKED_BY_SCRIPT.get(script, set())
    return ran


def touches(written, read):
    return read == written or (written.endswith("/") and read.startswith(written))


def test_every_auto_pr_workflow_is_accounted_for():
    """A new auto-PR workflow has to declare what it writes before it can
    pass. Without this the table above rots into a list of the workflows that
    happened to exist the day it was written."""
    opens_pr = {wf.name for wf in wtr.WORKFLOWS.glob("*.yml")
                if OPENS_PR.search(wf.read_text())}
    undeclared = opens_pr - set(WRITES)
    assert not undeclared, (
        f"auto-PR workflow(s) missing from WRITES in {__file__}: "
        f"{sorted(undeclared)}. Add what each one commits.")


def test_declared_workflows_still_exist():
    missing = [w for w in WRITES if not (wtr.WORKFLOWS / w).exists()]
    assert not missing, f"WRITES names workflows that are gone: {missing}"


def test_each_workflow_reruns_the_builders_its_writes_invalidate():
    builders = gated_builders()
    assert builders, "no --check gates found. The gate parser has broken."
    reads = {b: inputs(b) for b in builders}

    gaps = []
    for workflow, written in sorted(WRITES.items()):
        ran = runs(workflow)
        for builder, gate in sorted(builders.items()):
            stale = {(w, r) for w in written for r in reads[builder]
                     if touches(w, r)}
            if stale and builder not in ran:
                w, r = sorted(stale)[0]
                gaps.append(f"{workflow} writes {w}, which {builder} reads "
                            f"as {r}, but never runs it. {gate} will fail.")
    assert not gaps, "\n".join(gaps)


def test_the_declared_subprocess_invocations_are_real():
    """INVOKED_BY_SCRIPT is the one hand-kept edge in runs(). Check the caller
    still names the builder, so removing the subprocess call does not leave a
    workflow looking covered."""
    for caller, builders in INVOKED_BY_SCRIPT.items():
        text = (ROOT / "scripts" / caller).read_text()
        for builder in builders:
            assert f'"{builder}"' in text, f"{caller} no longer runs {builder}"


def test_every_gated_builder_declares_an_input():
    """A builder whose inputs cannot be read comes back needed by nobody, and
    the audit passes without having checked it. Fail instead."""
    blind = [b for b in gated_builders() if not inputs(b)]
    assert not blind, (
        f"cannot tell what these read, so they are exempt by accident: {blind}")


def test_the_skill_carries_the_same_write_sets():
    """The rebuild-gates skill prints WRITES for a reader deciding what a
    workflow change has to rerun. Two copies of a table is how the gaps above
    got in, so the second one has to say what the first one says."""
    text = SKILL.read_text()
    for workflow, written in sorted(WRITES.items()):
        row = f"| `{workflow}` | " + ", ".join(f"`{p}`" for p in sorted(written))
        assert row + " |" in text, f"{SKILL.name} should carry this row:\n{row} |"
