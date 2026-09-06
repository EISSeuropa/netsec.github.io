"""Checks for scripts/what-to-rebuild.py.

The script derives its answer from the real workflows, so these run against
the real workflows too. A failure here means either the deriver broke or a
gate changed shape, and both are worth being told about.
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("wtr", ROOT / "scripts/what-to-rebuild.py")
wtr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wtr)


def run(*paths):
    return subprocess.run(
        [sys.executable, "scripts/what-to-rebuild.py", *paths],
        capture_output=True, text=True, cwd=ROOT).stdout


def test_a_bios_change_names_the_builders_it_invalidates():
    out = run("data/bios.json")
    for builder in ("build-directory-index.py", "build-network-map.py",
                    "build-sitemap.py", "build-bio-search-stubs.py"):
        assert builder in out, builder


def test_a_readme_change_names_no_builder():
    assert "No path-filtered builder gate matches" in run("README.md")


def test_deploy_time_builders_are_never_suggested():
    # pages-deploy.yml has no pull_request trigger. Its output is written at
    # deploy and committing it by hand is the bug this must not cause.
    for paths in (["data/bios.json"], ["assets/css/site.css"], ["index.html"]):
        assert "build-og-cards.py" not in run(*paths)


def test_a_check_command_becomes_the_builder_that_fixes_it():
    out = run("data/bios.json")
    assert "python3 scripts/build-directory-index.py" in out
    assert "--check" not in out


def test_unfiltered_gates_are_reported_separately_and_without_commands():
    out = run("README.md")
    assert "implies nothing about this change" in out
    assert "seo-asset-check.yml" in out.split("implies nothing about this change")[1]


def test_path_filters_are_read_off_the_real_workflows():
    wf = (ROOT / ".github/workflows").glob("*.yml")
    parsed = {p.name: wtr.pull_request_paths(p.read_text()) for p in wf}
    assert "data/bios.json" in parsed["data-shape-check.yml"]   # filtered
    assert parsed["seo-asset-check.yml"] == []                  # every PR
    assert parsed["pages-deploy.yml"] is None                   # not a PR gate


def test_glob_matching_handles_the_shapes_the_workflows_use():
    assert wtr.matches(["scripts/x.py"], ["scripts/**"])
    assert wtr.matches(["a.fr.html"], ["*.html"])
    assert not wtr.matches(["docs/x.md"], ["data/*.json"])
    assert wtr.matches(["anything"], [])                        # unfiltered
