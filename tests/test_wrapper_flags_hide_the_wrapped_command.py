"""A wrapper's own flag must not be mistaken for the command it wraps.

three-preexisting-write-gate-gaps-from-review-6, subject one. `_strip_prefixes`
already dropped `env`, `sudo`, `timeout` and friends, so the diagnosis carried
into this task — "the `env` wrapper is not unwrapped at all" — was wrong, and
measuring first is what said so. The stripping runs. What it never did was
consume the VALUE its flags take: `sudo -u bob python h.py` dropped `sudo` and
`-u`, stopped at `bob`, called that the command, and never reached the
interpreter.

MEASURED BEFORE ANY DESIGN, 19 wrapper forms: 8 blind, and every blind cell was
a flag with a separate value. `nice -n 5 python h.py` was passing by accident —
`5` was being eaten as `timeout`'s duration, not as `-n`'s argument.

THE OTHER DIRECTION IS PART OF THE FIX, not a nicety. Consuming a token the
wrapper does not actually take would swallow the command itself and blind the
gate where it currently sees. So the forms with valueless flags and with
attached values (`env -i`, `stdbuf -o0`, `--chdir=/tmp`) are asserted in the
same matrix as the ones being repaired, and a mutation that eats one token too
many fails on them.

Subject two, the tilde: of the five sites resolving an externally supplied path,
three expanded `~` and two did not — `bash_write_parse` (the script path, long
standing) and `shell_roots` (the `cd` destination, introduced one commit
earlier by the fix for the memory-route gate). Both are asserted below.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys

import pytest
from conftest import canonical_ddl

_TESTS = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_TESTS, "..", "scripts"))
_HOOKS = os.path.join(_SCRIPTS, "hooks")
for _p in (_SCRIPTS, _HOOKS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bash_write_parse  # noqa: E402
import shell_roots  # noqa: E402
from bash_cmd_norm import _strip_prefixes  # noqa: E402

_BASH_GATE = os.path.join(_HOOKS, "bash_write_gate.py")

#: The measured matrix. Each entry is a way of putting a wrapper in front of an
#: interpreter; the parser must end up looking at `python` in every one.
#: Kept as data so the count in the task title stays checkable.
_WRAPPED = [
    "python h.py",
    "env python h.py",
    "env FOO=1 python h.py",
    "env -C /tmp python h.py",
    "env --chdir=/tmp python h.py",
    "env -i python h.py",
    "env -u FOO python h.py",
    "timeout 10 python h.py",
    "timeout -s KILL 10 python h.py",
    "timeout --signal KILL 10 python h.py",
    "nice -n 5 python h.py",
    "nice python h.py",
    "ionice -c 2 -n 7 python h.py",
    "stdbuf -o0 python h.py",
    "stdbuf -o 0 python h.py",
    "sudo -u bob python h.py",
    "sudo python h.py",
    "nohup python h.py",
    "sudo env -C /tmp python h.py",
    # Review #7. `-S` does NOT carry data: GNU env splits its value into a
    # command line and appends the argv that follows. Treating it as an ordinary
    # value flag dropped the real program and turned a block into an allow — the
    # regression this very file failed to catch, now measured here.
    "env -S python h.py",
    "env --split-string=python h.py",
    "sudo env -S python h.py",
]


@pytest.mark.parametrize("form", _WRAPPED)
def test_the_interpreter_is_found_behind_every_measured_wrapper(form):
    assert _strip_prefixes(form.split())[0] == "python", form


def test_the_matrix_has_not_quietly_shrunk():
    """A matrix nobody counts stops being a measurement."""
    assert len(_WRAPPED) == 22


@pytest.mark.parametrize(
    "form,expected",
    [
        # A valueless flag consumes ONLY itself; eating the next token here
        # would swallow the command and blind the gate where it now sees.
        ("env -i python h.py", "python"),
        ("sudo -n python h.py", "python"),
        ("stdbuf -o0 python h.py", "python"),
        ("env --chdir=/tmp python h.py", "python"),
        # A wrapper with nothing after it must not walk off the end.
        ("sudo", None),
        ("env -u", None),
    ],
)
def test_a_flag_that_takes_no_value_does_not_eat_the_command(form, expected):
    stripped = _strip_prefixes(form.split())
    assert (stripped[0] if stripped else None) == expected


def test_a_wrapper_name_is_still_only_stripped_in_command_position():
    """`cp env out` copies a file called `env`; it is not a wrapped command."""
    assert _strip_prefixes(["cp", "env", "out"]) == ["cp", "env", "out"]


class TestTildeIsExpanded:
    """`~` joined as a literal directory name names a path nothing has."""

    def test_a_script_named_with_a_tilde_is_read(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        (tmp_path / "helper.py").write_text("open('out.txt', 'w')\n", encoding="utf-8")
        targets = bash_write_parse.write_targets("python ~/helper.py", str(tmp_path))
        assert "out.txt" in targets

    def test_a_tilde_destination_becomes_a_real_root(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        roots = shell_roots.resolution_roots("cd ~/other && python helper.py", str(tmp_path))
        assert os.path.join(str(tmp_path), "other") in [os.path.normpath(r) for r in roots]
        assert not any("~" in r for r in roots)


class TestTheLiveGateSeesThroughTheWrapper:
    """End to end: the real QG-0 hook, a real script, a real ACL."""

    @staticmethod
    def _project(tmp_path, scope_paths):
        root = tmp_path / "proj"
        (root / ".tausik").mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(root / ".tausik" / "tausik.db"))
        conn.execute(canonical_ddl("tasks"))
        conn.execute(
            "INSERT INTO tasks (slug, title, status, scope_paths, created_at, updated_at) "
            "VALUES ('t', 't', 'active', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
            (json.dumps(scope_paths),),
        )
        conn.commit()
        conn.close()
        return root

    @staticmethod
    def _run(project_dir, command):
        env = os.environ.copy()
        env["TAUSIK_SKIP_HOOKS"] = ""
        env["TAUSIK_HOOK_FAIL_SECURE"] = ""
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": str(project_dir),
        }
        return subprocess.run(
            [sys.executable, _BASH_GATE],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=20,
        ).returncode

    @pytest.mark.parametrize(
        "form",
        [
            "sudo -u bob python helper.py",
            "env -C . python helper.py",
            "timeout -s KILL 10 python helper.py",
            "stdbuf -o 0 python helper.py",
            "ionice -c 2 -n 7 python helper.py",
            # Review #7: `env -S` runs a real writer. Asserted through the LIVE
            # gate and not only the pure function, because the pure-function
            # matrix is exactly what missed this — it asked "is the interpreter
            # found" of forms carrying an interpreter, and `-S` can carry any
            # writer at all.
            "env -S python helper.py",
            "env --split-string=python helper.py",
            "env -S tee secret.txt",
            "sudo env -S tee secret.txt",
        ],
    )
    def test_a_write_outside_the_acl_is_refused_behind_a_flagged_wrapper(self, tmp_path, form):
        project = self._project(tmp_path, ["allowed/**"])
        (project / "helper.py").write_text("open('secret.txt', 'w')\n", encoding="utf-8")
        assert self._run(project, form) == 2

    @pytest.mark.parametrize(
        "form",
        [
            "sudo -u bob python helper.py",
            "env -C . python helper.py",
        ],
    )
    def test_a_write_inside_the_acl_is_still_allowed(self, tmp_path, form):
        """The repair must not become a new false block."""
        project = self._project(tmp_path, ["allowed/**", "helper.py"])
        (project / "helper.py").write_text("open('allowed/ok.txt', 'w')\n", encoding="utf-8")
        assert self._run(project, form) == 0
