"""Checks for .claude/hooks/guard-bulk-read.py.

The guard refuses whole-file reads of very large files. What matters is the
pair: it fires on a bulk read, and it stays out of the way of a targeted one.
"""
import importlib.util
import pathlib

HOOK = pathlib.Path(__file__).resolve().parent.parent / ".claude/hooks/guard-bulk-read.py"
_spec = importlib.util.spec_from_file_location("guard_bulk_read", HOOK)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def call(tool, cwd, **args):
    return guard.check({"tool_name": tool, "cwd": str(cwd), "tool_input": args}, 800)


def write(tmp_path, name, lines):
    path = tmp_path / name
    path.write_text("x\n" * lines)
    return path


def test_blocks_a_whole_file_read(tmp_path):
    big = write(tmp_path, "big.css", 5000)
    assert "5000 lines" in call("Read", tmp_path, file_path=str(big))


def test_allows_a_targeted_read(tmp_path):
    big = write(tmp_path, "big.css", 5000)
    assert call("Read", tmp_path, file_path=str(big), offset=10, limit=40) is None


def test_allows_a_file_under_the_threshold(tmp_path):
    small = write(tmp_path, "small.html", 800)
    assert call("Read", tmp_path, file_path=str(small)) is None


def test_blocks_a_bare_cat(tmp_path):
    write(tmp_path, "big.json", 5000)
    assert call("Bash", tmp_path, command="cat big.json") is not None


def test_allows_a_piped_or_ranged_read(tmp_path):
    write(tmp_path, "big.json", 5000)
    assert call("Bash", tmp_path, command="cat big.json | head -50") is None
    assert call("Bash", tmp_path, command="sed -n '1,80p' big.json") is None
    assert call("Bash", tmp_path, command="grep -n hero big.json") is None


def test_ignores_other_tools_and_missing_files(tmp_path):
    assert call("Grep", tmp_path, pattern="hero") is None
    assert call("Bash", tmp_path, command="cat nothing-here.txt") is None
    assert call("Read", tmp_path, file_path=str(tmp_path / "nothing-here.txt")) is None


def test_reports_the_alternatives_in_the_refusal(tmp_path):
    big = write(tmp_path, "big.css", 5000)
    message = call("Read", tmp_path, file_path=str(big))
    assert "offset" in message and "CLAUDE_READ_MAX_LINES" in message
