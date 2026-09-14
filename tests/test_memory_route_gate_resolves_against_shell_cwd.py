"""The memory-route gate must read the script the command actually runs.

memory-route-gate-did-not-get-the-base-directory. Session #205 threaded the
shell's working directory into `shell_channel.write_targets`, and stopped there.
Its twin `write_targets_with_confidence` did not get the argument, and that twin
is the ONLY entry `memory_pretool_block` calls — so the write gate was repaired
and the memory-route gate, judging the same commands with the same parser, was
not. Review #6 found it and reproduced it on the live hooks.

WHY THE MISS IS WORSE THAN A PLAIN MISS. The answer the hook produced was a
HYBRID: the script's CONTENTS were read out of a file the command does not run,
while the targets found inside were resolved against the shell's directory. The
resulting path matches no file on disk. That is wrong in both directions at
once, and both are asserted below — a real leak into home-scope memory passes
ungated from a second checkout, and an innocent command in that checkout is
accused of leaking because the gate read the MAIN tree's same-named script.

THE THIRD DIRECTORY, WHICH IS THE POINT. Fixing only the argument leaves the
`cd` case broken, and the tests below would have passed anyway. Session #205's
own repair for a moving shell took the union of two guesses — the pre-command
cwd and the project root — which covers a command walking INTO the project and
nothing else. Two checkouts open is the ordinary case, and there the command
walks into a THIRD directory that is neither guess. Measured on the live hook:
`cd <other tree> && python helper.py` missed the leak with the argument
threaded and the union in place. The union had to stop guessing roots and start
reading where the command GOES (`shell_roots`), which is the same correction,
for the fourth time, that memory #524 records.

MEASURED BEFORE AND AFTER, live hook, six cells: 5 wrong before, 0 after.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_TESTS, "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import shell_channel  # noqa: E402

_MEMORY_HOOK = os.path.join(_HOOKS, "memory_pretool_block.py")

#: A home-scope sink from `memory_sinks.DEFAULT_SINKS` (`.claude/**/memory/**`).
#: Absolute, so the gate's verdict turns on WHICH script was read rather than on
#: which directory the target was joined to — the two failure modes are then
#: distinguishable instead of masking each other.
_LEAK_SINK = (
    os.path.expanduser("~").replace("\\", "/") + "/.claude/projects/pytest-probe/memory/x.md"
)

_LEAKY_SCRIPT = "f = open({!r}, 'w')\nf.write('project knowledge')\n".format(_LEAK_SINK)
_HARMLESS_SCRIPT = "f = open('notes.txt', 'w')\nf.write('local scratch')\n"


def _make_tree(root, helper_body):
    """A minimal TAUSIK project holding a `helper.py` with the given body."""
    (root / ".tausik").mkdir(parents=True, exist_ok=True)
    (root / ".tausik" / "config.json").write_text("{}\n", encoding="utf-8")
    (root / "helper.py").write_text(helper_body, encoding="utf-8")
    return root


def _run_hook(project_dir, event_cwd, command):
    """The real hook, as a subprocess. 0 = allow, 2 = block."""
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(event_cwd),
        "transcript_path": "",
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    for skip in ("TAUSIK_SKIP_HOOKS", "TAUSIK_SKIP_MEMORY_HOOK"):
        env.pop(skip, None)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", _MEMORY_HOOK],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(project_dir),
    )
    return proc.returncode


@pytest.fixture()
def two_trees(tmp_path):
    """Two projects, each with its own `helper.py`, so the trees disagree."""

    def build(body_main, body_other):
        main = _make_tree(tmp_path / "main", body_main)
        other = _make_tree(tmp_path / "other", body_other)
        return main, other

    return build


def test_leak_from_a_second_checkout_is_not_missed(two_trees):
    """The script the command runs is the OTHER tree's, and it leaks."""
    main, other = two_trees(_HARMLESS_SCRIPT, _LEAKY_SCRIPT)
    assert _run_hook(main, other, "python helper.py") == 2


def test_an_innocent_command_in_a_second_checkout_is_not_accused(two_trees):
    """The mirror image: reading the MAIN tree's script invents a leak."""
    main, other = two_trees(_LEAKY_SCRIPT, _HARMLESS_SCRIPT)
    assert _run_hook(main, other, "python helper.py") == 0


@pytest.mark.parametrize(
    "form",
    [
        "cd {dest} && python helper.py",
        "pushd {dest} && python helper.py",
        "(cd {dest} ; python helper.py)",
    ],
)
def test_a_command_that_walks_into_a_third_directory_is_judged_there(two_trees, form):
    """Ask where the command GOES, not where the shell stands (memory #524).

    The event's `cwd` is the MAIN tree here, and so is the project root, so both
    of session #205's guessed roots are the wrong one. Only reading the `cd`
    destination out of the command text finds the script that actually runs.

    Forward slashes deliberately: the Bash tool runs a POSIX shell, where a
    backslash is an escape and `cd C:\\a\\b` is not a directory change at all.
    Spelling the destination the way no shell honours would make this pass
    without testing anything.
    """
    main, other = two_trees(_HARMLESS_SCRIPT, _LEAKY_SCRIPT)
    dest = str(other).replace("\\", "/")
    assert _run_hook(main, main, form.format(dest=dest)) == 2


def test_walking_elsewhere_does_not_manufacture_a_leak(two_trees):
    """The widening must not become a block on a command that leaks nowhere."""
    main, other = two_trees(_HARMLESS_SCRIPT, _HARMLESS_SCRIPT)
    dest = str(other).replace("\\", "/")
    assert _run_hook(main, main, "cd {} && python helper.py".format(dest)) == 0


def test_an_event_without_a_cwd_still_gates_against_the_project(two_trees):
    """No measurement of where the shell stands means keep gating, not stop."""
    main, _other = two_trees(_LEAKY_SCRIPT, _HARMLESS_SCRIPT)
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "python helper.py"},
        "transcript_path": "",
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(main)
    env["PYTHONIOENCODING"] = "utf-8"
    for skip in ("TAUSIK_SKIP_HOOKS", "TAUSIK_SKIP_MEMORY_HOOK"):
        env.pop(skip, None)
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", _MEMORY_HOOK],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(main),
    )
    assert proc.returncode == 2


def test_every_dialect_takes_the_base_directory(tmp_path):
    """The rule that replaced the enumeration, asserted over the whole table.

    `shell_channel.write_targets` used to ask `if module is bash_write_parse`
    before deciding whether to pass the base directory — a dialect enumeration
    inside the module written to abolish dialect enumerations, covered by no
    test. That is how the argument reached one entry point and not its twin.

    Driven off `_DIALECTS` itself rather than a list repeated here, so a third
    shell cannot join the table without accepting the argument: the test fails
    on the day it is added, not on the day a gate silently stops resolving.
    """
    assert shell_channel._DIALECTS, "the dialect table must not be empty"
    for tool_name, module in shell_channel._DIALECTS.items():
        for entry in ("write_targets", "write_targets_with_confidence"):
            fn = getattr(module, entry)
            assert (
                fn(  # both signatures accept it positionally
                    "echo hi", str(tmp_path)
                )
                is not None
            ), "{}.{} rejected a base directory".format(tool_name, entry)


def test_the_dispatcher_hands_the_base_directory_to_a_dialect_it_has_never_seen(monkeypatch):
    """The property the removed enumeration broke, stated as behaviour.

    A grep for `module is bash_write_parse` would have been the easy test and
    the wrong one: the phrase belongs in the prose that records why the branch
    existed, and a test forbidding the words would forbid the lesson while
    leaving a rewritten branch to pass.

    So a stub dialect is registered instead — a shell the dispatcher has never
    heard of — and the assertion is that it RECEIVED the directory. That fails
    on any dispatcher which decides per-dialect whether to pass it, however the
    decision is spelled.
    """
    seen = {}

    class _StubDialect:
        @staticmethod
        def write_targets(command, base_dir=None):
            seen["write_targets"] = base_dir
            return []

        @staticmethod
        def write_targets_with_confidence(command, base_dir=None):
            seen["write_targets_with_confidence"] = base_dir
            return [], "parsed"

    monkeypatch.setitem(shell_channel._DIALECTS, "StubShell", _StubDialect)
    shell_channel.write_targets("StubShell", "echo hi", "/work/elsewhere")
    shell_channel.write_targets_with_confidence("StubShell", "echo hi", "/work/elsewhere")
    assert seen == {
        "write_targets": "/work/elsewhere",
        "write_targets_with_confidence": "/work/elsewhere",
    }
