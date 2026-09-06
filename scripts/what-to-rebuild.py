#!/usr/bin/env python3
"""Say which generated files a change has invalidated, before CI does.

Thirteen builders write files that are committed, and a drift gate fails the
PR when one of them is stale. The mapping from an edited data file to the
builder that has to be re-run is not written down anywhere: it is implied by
the workflows, in the `paths:` a gate triggers on and the `--check` command it
runs. This reads that, so the answer cannot drift away from the gates the way
a hand-kept list would.

    python3 scripts/what-to-rebuild.py              # working tree vs origin/main
    python3 scripts/what-to-rebuild.py --base HEAD  # uncommitted work only
    python3 scripts/what-to-rebuild.py a.json b.css # explicit paths

Only workflows that gate a pull request are read, so deploy-time builders
(profile pages, OG cards, the ?v= stamp) are never suggested: those write at
deploy and must not be committed. A `--check` command means the committed
output is stale and the builder refreshes it. A builder without `--check` is a
build gate, which only has to not crash.

No dependencies, so it runs anywhere the repo does.
"""
import argparse
import fnmatch
import pathlib
import re
import subprocess
import sys

WORKFLOWS = pathlib.Path(".github/workflows")
CMD = re.compile(r"^\s+(?:run|command):\s*(?:python3|bash|node)\s+(scripts/\S+)(.*)$")


def pull_request_paths(text):
    """This workflow's pull_request path filter.

    None when it does not gate pull requests, [] when it gates every one of
    them, and otherwise the declared paths. The empty case matters: a gate
    with no filter has declared nothing about which paths affect it, so it
    cannot tell us a change made its output stale.
    """
    lines = text.split("\n")
    try:
        top = next(i for i, l in enumerate(lines) if re.match(r"^on:\s*$", l))
    except StopIteration:
        return None
    seen, trigger, paths, in_paths = False, None, [], False
    for line in lines[top + 1:]:
        if line and not line[0].isspace():
            break                                     # left the on: block
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 2 and stripped.rstrip(":") and stripped.endswith(":"):
            trigger = stripped[:-1]
            in_paths = False
            seen = seen or trigger == "pull_request"
        elif trigger == "pull_request" and stripped in ("paths:", "paths-ignore:"):
            in_paths = stripped == "paths:"
        elif in_paths and stripped.startswith("- "):
            paths.append(stripped[2:].strip().strip("'\""))
        elif not stripped.startswith("- "):
            in_paths = False
    return paths if seen else None


def matches(changed, patterns):
    """GitHub path-filter semantics, narrowed to the globs this repo uses."""
    if not patterns:
        return True                                   # unfiltered trigger
    for f in changed:
        for p in patterns:
            if fnmatch.fnmatch(f, p) or fnmatch.fnmatch(f, p.replace("/**", "/*")):
                return True
    return False


def gates():
    """Every pull-request gate, as (workflow, paths, [(script, args)])."""
    out = []
    for wf in sorted(WORKFLOWS.glob("*.yml")):
        text = wf.read_text()
        paths = pull_request_paths(text)
        if paths is None:
            continue
        cmds = [(m.group(1), m.group(2).strip()) for m in
                (CMD.match(l) for l in text.split("\n")) if m]
        if cmds:
            out.append((wf.name, paths, cmds))
    return out


def changed_files(base):
    def git(*a):
        r = subprocess.run(["git", *a], capture_output=True, text=True)
        return r.stdout.split() if r.returncode == 0 else []
    return sorted(set(git("diff", "--name-only", base) + git("diff", "--name-only")
                      + git("diff", "--name-only", "--cached")
                      + git("ls-files", "--others", "--exclude-standard")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", help="paths to test instead of the git diff")
    ap.add_argument("--base", default="origin/main", help="diff against this ref")
    args = ap.parse_args()

    changed = args.paths or changed_files(args.base)
    if not changed:
        print("Nothing changed.")
        return 0

    refresh, build, always = {}, {}, set()
    for name, paths, cmds in gates():
        if not paths:
            always.add(name)          # unfiltered: runs regardless, says nothing
            continue
        if not matches(changed, paths):
            continue
        for script, extra in cmds:
            cmd = f"{'bash' if script.endswith('.sh') else 'python3'} {script}"
            if "--check" in extra:
                rest = extra.replace("--check", "").strip()
                refresh.setdefault(f"{cmd} {rest}".strip(), set()).add(name)
            else:
                build.setdefault(cmd, set()).add(name)

    print(f"{len(changed)} changed file(s).\n")
    if refresh:
        print("Stale now. Run these, then commit what they write:")
        for cmd, wfs in sorted(refresh.items()):
            print(f"  {cmd:<50} {', '.join(sorted(wfs))}")
    if build:
        print("\nMust still build. Nothing to commit:")
        for cmd, wfs in sorted(build.items()):
            print(f"  {cmd:<50} {', '.join(sorted(wfs))}")
    if not refresh and not build:
        print("No path-filtered builder gate matches these paths.")
    if always:
        print(f"\nAlso runs on every PR, filter-free, so it implies nothing "
              f"about this change: {', '.join(sorted(always))}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
