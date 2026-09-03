"""Where a relative path may point once the command has moved the shell.

`shell_roots` exists because the same question got three successive wrong
answers, each a guess rather than a reading: the project directory (#204), the
event's pre-command `cwd` (#205), and the union of those two (#205's own
regression fix). All three are guesses about a root. The command names its
destination in plain text, and this module reads it.

The rule these tests pin is the widening direction. A containment gate that
cannot compute where the shell ends up must keep MORE roots, not choose one:
an extra root costs a task the write would have needed anyway, while dropping
the real one loses the write. So `resolution_roots` never shrinks below the
starting directory, and never drops the project root when the shell moved.
"""

from __future__ import annotations

import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_HOOKS = os.path.abspath(os.path.join(_TESTS, "..", "scripts", "hooks"))
if _HOOKS not in sys.path:
    sys.path.insert(0, _HOOKS)

import shell_roots  # noqa: E402


@pytest.mark.parametrize(
    "command,expected",
    [
        ("cd /tmp/build && make", ["/tmp/build"]),
        ("pushd /tmp/build && make", ["/tmp/build"]),
        ("chdir /tmp/build", ["/tmp/build"]),
        ("(cd /tmp/build ; make)", ["/tmp/build"]),
        ("env -C /tmp/build python x.py", ["/tmp/build"]),
        ("env --chdir=/tmp/build python x.py", ["/tmp/build"]),
        ("cd -P /tmp/build && make", ["/tmp/build"]),
        ("cd /a && cd /b", ["/a", "/b"]),
    ],
)
def test_a_literal_destination_is_read_out_of_the_command(command, expected):
    assert shell_roots.destinations(command) == expected


@pytest.mark.parametrize(
    "command",
    [
        "make",  # moves nowhere
        "cp cd.txt out.txt",  # the word appears as a PATH, not a command
        'echo "cd /tmp"',  # ...and as quoted prose
        "cd",  # bare `cd` names no destination
        "cd -",  # back to the previous directory, which is not in the text
        "popd",  # a stack this parser never saw
        'cd "$BUILD_DIR" && make',  # unexpanded: genuinely unresolvable
    ],
)
def test_no_literal_destination_yields_nothing(command):
    """Silence here is not a hole: `resolution_roots` widens for these anyway."""
    assert shell_roots.destinations(command) == []


def test_a_command_that_stays_put_resolves_against_one_root():
    assert shell_roots.resolution_roots("python helper.py", "/work/main") == ["/work/main"]


def test_a_destination_is_added_without_dropping_the_starting_directory():
    """Both, because only the last move before the interpreter runs decides."""
    roots = shell_roots.resolution_roots("cd /work/other && python helper.py", "/work/main")
    assert roots[0] == "/work/main"
    assert "/work/other" in roots


def test_a_relative_destination_resolves_against_where_the_shell_started():
    roots = shell_roots.resolution_roots("cd sub && python helper.py", "/work/main")
    assert os.path.join("/work/main", "sub") in roots


@pytest.mark.parametrize("command", ["popd && python helper.py", 'cd "$D" && python helper.py'])
def test_an_uncomputable_move_still_widens_to_the_project_root(command, monkeypatch):
    """The case the fallback root exists for — measured, not assumed."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", os.path.join(os.sep, "work", "project"))
    roots = shell_roots.resolution_roots(command, os.path.join(os.sep, "work", "main"))
    assert os.path.join(os.sep, "work", "main") in roots
    assert os.path.join(os.sep, "work", "project") in roots


def test_an_unparseable_command_keeps_the_starting_directory(monkeypatch):
    """`command_changes_directory` assumes the worst; the roots must not shrink."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", os.path.join(os.sep, "work", "project"))
    roots = shell_roots.resolution_roots(
        "python 'unterminated", os.path.join(os.sep, "work", "main")
    )
    assert os.path.join(os.sep, "work", "main") in roots


def test_roots_are_unique():
    """The starting directory and the destination can name the same place."""
    roots = shell_roots.resolution_roots("cd /work/main && python helper.py", "/work/main")
    assert len(roots) == len(set(roots))


def test_end_of_options_is_honoured_in_a_destination():
    """`cd -- -weird-dir` names a directory, not a flag.

    Review #7. Filtering operands with `startswith("-")` dropped the real
    destination, so the widening this module exists for silently lost the root
    it was supposed to add. `bash_write_parse._positionals` already reads `--`
    this way; not doing so here was an inconsistency inside one package.
    """
    assert shell_roots.destinations("cd -- -weird-dir && python helper.py") == ["-weird-dir"]
    roots = shell_roots.resolution_roots("cd -- -weird-dir && python helper.py", "/work/main")
    assert os.path.join("/work/main", "-weird-dir") in roots


def test_a_flag_before_the_separator_is_still_a_flag():
    """The narrowing must not swing the other way: `-P` is not a directory."""
    assert shell_roots.destinations("cd -P /tmp/build && make") == ["/tmp/build"]
