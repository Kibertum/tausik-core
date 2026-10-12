"""r14-senar-context-hygiene: PreToolUse secret scanner.

Scans Write/Edit/MultiEdit tool_input for likely secret patterns and warns
on stderr (or blocks under TAUSIK_SECRET_SCAN_STRICT=1). The hook is
deliberately non-blocking by default to avoid over-fitting on legitimate
changes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK = str(REPO / "scripts" / "hooks" / "secret_scan.py")


def _run(payload: dict, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ}
    env.pop("TAUSIK_SKIP_HOOKS", None)
    env.pop("TAUSIK_SECRET_SCAN_STRICT", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=5,
        env=env,
    )


def test_clean_payload_passes():
    res = _run(
        {
            "tool_name": "Write",
            "tool_input": {"file_path": "x.py", "content": "print('hello')"},
        }
    )
    assert res.returncode == 0
    assert "TAUSIK secret-scan" not in res.stderr


def test_aws_key_warns_but_does_not_block():
    res = _run(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env",
                "content": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
            },
        }
    )
    assert res.returncode == 0
    assert "aws_access_key" in res.stderr


def test_strict_mode_blocks():
    res = _run(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env",
                "content": "OPENAI_KEY=sk-abcdefghijklmnopqrstuvwxyz0123456789",
            },
        },
        env_extra={"TAUSIK_SECRET_SCAN_STRICT": "1"},
    )
    assert res.returncode == 2
    assert "openai_key" in res.stderr


def test_skip_hooks_short_circuits():
    res = _run(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": ".env",
                "content": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
            },
        },
        env_extra={"TAUSIK_SKIP_HOOKS": "1"},
    )
    assert res.returncode == 0
    assert "TAUSIK secret-scan" not in res.stderr


def test_non_write_tool_ignored():
    res = _run(
        {
            "tool_name": "Read",
            "tool_input": {"path": "/tmp/AKIAIOSFODNN7EXAMPLE.txt"},
        }
    )
    assert res.returncode == 0
    assert res.stderr == ""


def test_private_key_block_detected():
    res = _run(
        {
            "tool_name": "Edit",
            "tool_input": {
                "new_string": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpQIBAAKCAQEA...\n",
            },
        }
    )
    assert res.returncode == 0
    assert "private_key_block" in res.stderr


# secret-scan-covers-no-shell-channel (Decision #178): the same content that
# the Write path warns on must warn when a shell writes it — on BOTH dialects,
# or the weaker channel becomes the route around the guard.

# A well-known AWS DOCUMENTATION example key id (not a live credential),
# assembled at runtime so the literal is not itself in this file's source.
_AKIA = "AKIA" + "IOSFODNN7EXAMPLE"


def test_bash_heredoc_secret_warns():
    res = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"cat > .env <<EOF\n{_AKIA}\nEOF"},
        }
    )
    assert res.returncode == 0
    assert "aws_access_key" in res.stderr
    assert "Bash" in res.stderr  # the message names the channel actually used


def test_powershell_set_content_secret_warns():
    res = _run(
        {
            "tool_name": "PowerShell",
            "tool_input": {"command": f"Set-Content -Path .env -Value '{_AKIA}'"},
        }
    )
    assert res.returncode == 0
    assert "aws_access_key" in res.stderr


def test_bash_export_literal_warns():
    # Rule 10.12 covers a secret literal in CONTEXT, not only one written to a
    # file: `export KEY=<literal>` is the credential in the command itself.
    res = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"export AWS_ACCESS_KEY_ID={_AKIA}"},
        }
    )
    assert res.returncode == 0
    assert "aws_access_key" in res.stderr


def test_shell_secret_via_variable_not_flagged():
    # Documented residual: a secret passed by variable/env is not a literal
    # anywhere, so there is nothing to match — the correct, non-flagged way.
    res = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'curl -H "Authorization: Bearer $TOKEN" https://api'},
        }
    )
    assert res.returncode == 0
    assert res.stderr == ""


def test_shell_strict_mode_blocks():
    res = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"echo {_AKIA} > .env"},
        },
        env_extra={"TAUSIK_SECRET_SCAN_STRICT": "1"},
    )
    assert res.returncode == 2
    assert "aws_access_key" in res.stderr


def test_clean_shell_command_passes():
    res = _run(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "pytest -q tests/"},
        }
    )
    assert res.returncode == 0
    assert "TAUSIK secret-scan" not in res.stderr
