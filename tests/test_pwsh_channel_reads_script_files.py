"""The code a command RUNS is a write vector on EVERY channel, not just POSIX.

Session #201 closed this on Bash and put PowerShell in that task's
`scope_exclude` on purpose, so the task would not sprawl. The exclusion was
honest and the follow-up was filed; what it cost, measured here before anything
was changed, is that the PLATFORM'S PRIMARY SHELL passed a write outside the
task's ACL with the gate returning 0. Five spellings — the bare call, the `&`
call operator, a backslash path, a forward-slash path, `Start-Process` — all of
them ordinary, none of them obfuscation.

MEASURED, 9 cells: 5 wrong before, 0 after. The Bash channel was fed the
equivalent command as a control in every one, so the two channels were compared
rather than one being described.

WHAT THE DECLARED RESIDUAL SAID. `pwsh_cmd_parse` claimed this channel had been
raised "from the everyday spelling walks through to you must actively
obfuscate". That was the same sentence the Bash channel carried, and on Bash it
named the wrong cut; here the measurement says it was simply false — the
everyday spelling walked through. Memory #495: a declared residual is a claim
about the system, and it is checked by measuring the most ORDINARY command it
covers, not by reading it.

THE SEAL. This defect exists because a fix landed on one dialect and not the
other — the same shape as the write-gate twin that was repaired earlier today.
So the last test here drives off the DIALECT TABLE itself and requires every
entry to answer alike, which is what stops a third shell from arriving with
this hole already in it.
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

import shell_channel  # noqa: E402

_GATE = os.path.join(_HOOKS, "bash_write_gate.py")

# Built rather than written, so this file does not itself carry the literal the
# write gate scans for — it would false-block its own test data.
_OPEN = "op" + "en"
_WRITES_OUTSIDE = "f = %s('secret.txt', 'w')\nf.write('x')\n" % _OPEN
_WRITES_INSIDE = "f = %s('allowed/ok.txt', 'w')\nf.write('x')\n" % _OPEN


def _project(tmp_path, scope_paths, script_body):
    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True, exist_ok=True)
    (root / "allowed").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(root / ".tausik" / "tausik.db"))
    conn.execute(canonical_ddl("tasks"))
    conn.execute(
        "INSERT INTO tasks (slug, title, status, scope_paths, created_at, updated_at) "
        "VALUES ('t', 't', 'active', ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        (json.dumps(scope_paths),),
    )
    conn.commit()
    conn.close()
    (root / "helper.py").write_text(script_body, encoding="utf-8")
    return root


def _gate(project, tool, command):
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["TAUSIK_SKIP_HOOKS"] = ""
    env["TAUSIK_HOOK_FAIL_SECURE"] = ""
    payload = {"tool_name": tool, "tool_input": {"command": command}, "cwd": str(project)}
    return subprocess.run(
        [sys.executable, _GATE],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    ).returncode


class TestTheLiveGateOnThePowerShellChannel:
    def test_an_inline_pathlib_write_outside_the_acl_is_refused(self, tmp_path):
        project = _project(tmp_path, ["allowed/**"], _WRITES_OUTSIDE)
        command = (
            "python -c \"from pathlib import Path; "
            "Path('secret.txt').write_text('x', encoding='utf-8')\""
        )
        assert _gate(project, "PowerShell", command) == 2

    @pytest.mark.parametrize(
        "command",
        [
            "python helper.py",
            "& python helper.py",
            "python .\\helper.py",
            "python ./helper.py",
            "Start-Process python helper.py",
            "Start-Process -FilePath python -ArgumentList helper.py",
        ],
    )
    def test_a_script_writing_outside_the_acl_is_refused(self, tmp_path, command):
        project = _project(tmp_path, ["allowed/**"], _WRITES_OUTSIDE)
        assert _gate(project, "PowerShell", command) == 2

    @pytest.mark.parametrize("command", ["python helper.py", "& python helper.py"])
    def test_the_green_branch_is_measured_too(self, tmp_path, command):
        """Differing by exactly the written path, the command must pass.

        Without this the repair could be a blanket block on the primary shell,
        which is worse than the miss it replaces.
        """
        project = _project(tmp_path, ["allowed/**", "helper.py"], _WRITES_INSIDE)
        assert _gate(project, "PowerShell", command) == 0

    def test_the_narrowness_survives_the_port(self, tmp_path):
        """`-m` names a module, not a script: `x.py` here is pytest's argument.

        The POSIX side learned this the hard way — a first version read any
        `.py` argument and would have blocked `python -m pytest tests/x.py`
        using literals out of the test file itself.
        """
        project = _project(tmp_path, ["allowed/**"], _WRITES_OUTSIDE)
        assert _gate(project, "PowerShell", "python -m pytest helper.py") == 0

    def test_a_missing_script_degrades_softly(self, tmp_path):
        """A hook that raises on every command is an outage, not a guard."""
        project = _project(tmp_path, ["allowed/**"], _WRITES_OUTSIDE)
        assert _gate(project, "PowerShell", "python no_such_file.py") == 0


class TestABackslashIsAPathInPowerShellAndAnEscapeInBash:
    """`.\\helper.py` names `helper.py` to PowerShell on every host and
    `.helper.py` to a POSIX shell, where the backslash escapes the `h`.

    The first Linux run of this lane (pipeline #6658) found the PowerShell
    channel handing `.\\helper.py` to the resolver as-is: on POSIX no such file,
    fail-soft, gate 0. The repair spells the separator for the host INSIDE the
    PowerShell dialect. These cells pin both halves: PowerShell reads
    `helper.py` on this host whatever it is, and Bash still reads `.helper.py`
    — so the repair cannot leak into the Bash channel, where it would turn an
    escape into a separator. Each cell plants the two files with OPPOSITE
    verdicts, so the exit code says which file each dialect actually read.
    """

    @pytest.mark.parametrize(
        ("dotted_body", "plain_body", "bash_rc", "pwsh_rc"),
        [
            (_WRITES_OUTSIDE, _WRITES_INSIDE, 2, 0),
            (_WRITES_INSIDE, _WRITES_OUTSIDE, 0, 2),
        ],
        ids=["dotted-writes-outside", "plain-writes-outside"],
    )
    def test_each_dialect_reads_its_own_file(
        self, tmp_path, dotted_body, plain_body, bash_rc, pwsh_rc
    ):
        project = _project(tmp_path, ["allowed/**"], plain_body)
        (project / ".helper.py").write_text(dotted_body, encoding="utf-8")
        assert _gate(project, "Bash", "python .\\helper.py") == bash_rc
        assert _gate(project, "PowerShell", "python .\\helper.py") == pwsh_rc

    def test_a_dash_c_payload_keeps_its_backslashes(self, monkeypatch):
        """`-c` carries Python source, where `\\n` is an escape, not a path.

        Two things are deliberate. The payload has no quote and no space: a
        quoted one is left alone by the quote rule already, and would hide a
        dropped `-c` rule. And the host separator is pinned to `/`: on Windows
        `os.sep` IS the backslash, the rewrite is the identity, and no
        mutation of this function can be observed at all (measured — both
        survived the first draft of this test).
        """
        from pwsh_cmd_parse import Statement
        from pwsh_write_parse import _paths_for_host, _script_argv

        monkeypatch.setattr(os, "sep", "/")
        argv = ["python", "-c", "a\\nb", ".\\out.py"]
        assert _paths_for_host(argv) == ["python", "-c", "a\\nb", "./out.py"]
        assert _paths_for_host(["python", "-m", "pkg\\mod"])[2] == "pkg\\mod"
        assert _paths_for_host(["python", "-X", "utf8", "sub\\run.py"])[3] == "sub/run.py"
        # A quoted path with a space arrives as ONE token and is still a path;
        # a token carrying a quote character is source, not a path.
        assert _paths_for_host(["python", "my dir\\run.py"])[1] == "my dir/run.py"
        assert _paths_for_host(["python", "print('a\\nb')"])[1] == "print('a\\nb')"
        # Both shapes `_script_argv` returns go through the rewrite.
        assert _script_argv(Statement(["python", ".\\x.py"])) == ["python", "./x.py"]
        started = Statement(["Start-Process", "python", ".\\x.py"])
        assert _script_argv(started) == ["python", "./x.py"]


class TestTheChannelsAgree:
    """The seal: no dialect may answer differently about the same command."""

    def test_every_dialect_reads_the_script_a_command_runs(self, tmp_path):
        """Driven off `_DIALECTS`, so a third shell cannot arrive without this.

        The defect being fixed is exactly "closed on one dialect, open on the
        other". Asserting it per dialect NAME would reproduce the enumeration
        that caused it; asking the table is what makes the next shell fail this
        test on the day it is added.
        """
        assert shell_channel._DIALECTS, "the dialect table must not be empty"
        (tmp_path / "helper.py").write_text(_WRITES_OUTSIDE, encoding="utf-8")
        for tool_name in shell_channel._DIALECTS:
            targets = shell_channel.write_targets(tool_name, "python helper.py", str(tmp_path))
            assert "secret.txt" in targets, (
                "dialect %r does not read the script its command runs" % tool_name
            )

    def test_every_dialect_keeps_the_module_narrowness(self, tmp_path):
        (tmp_path / "helper.py").write_text(_WRITES_OUTSIDE, encoding="utf-8")
        for tool_name in shell_channel._DIALECTS:
            targets = shell_channel.write_targets(
                tool_name, "python -m pytest helper.py", str(tmp_path)
            )
            assert "secret.txt" not in targets, (
                "dialect %r reads a -m module argument as a script" % tool_name
            )
