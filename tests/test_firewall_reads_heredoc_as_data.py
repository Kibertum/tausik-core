"""The firewall blocks a dangerous command, not a text that quotes one
(firewall-scans-heredoc-payload-not-just-the-command).

Found live in session #160: a handoff that described the guard against wiping
the home directory was blocked as if it were that command. Measured in session
#267 as already fixed by the statement scanner; this pins both halves, so the
channel cannot quietly close again and the guard cannot quietly open.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

# Runs the hook as a subprocess, so no import edge selects it: declared by path.
CROSSCUTTING_SCOPE = ["scripts/hooks/"]

_HOOK = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "bash_firewall.py")


def _verdict(cmd: str) -> int:
    env = {k: v for k, v in os.environ.items() if k != "TAUSIK_SKIP_HOOKS"}
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    return subprocess.run(
        [sys.executable, _HOOK],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    ).returncode


@pytest.mark.parametrize(
    "cmd",
    [
        "cat > notes.md <<'EOF'\nthe guard stops rm -rf ~ now\nEOF",
        "cat >> CHANGELOG.md <<EOF\nBlocks DROP TABLE and git push --force.\nEOF",
        'echo "the guard stops rm -rf / and DROP TABLE users" > notes.md',
    ],
    ids=["heredoc-quoted-delimiter", "heredoc-plain-delimiter", "quoted-argument"],
)
def test_text_that_quotes_a_danger_is_not_blocked(cmd):
    assert _verdict(cmd) == 0


@pytest.mark.parametrize(
    "cmd",
    [
        "rm -rf ~",
        "cat > a <<'EOF'\nharmless\nEOF\nrm -rf /",
        "sqlite3 app.db 'DROP TABLE users'",
        "git push --force origin main",
    ],
    ids=["wipe-home", "wipe-root-after-heredoc", "drop-table", "force-push"],
)
def test_the_danger_itself_is_still_blocked(cmd):
    assert _verdict(cmd) == 2
