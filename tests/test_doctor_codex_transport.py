"""Doctor reports whether the installed Codex MCP transport can authorize mutations."""

from __future__ import annotations

import json
import hashlib

import pytest

from service_doctor_codex import check_codex_mcp_transport
from hooks.codex_capability import serialize_hook_argv


def _install(
    root,
    *,
    env: str,
    capability_version: int = 5,
    modes=None,
    adapter_state: str = "valid",
    hook_state: str = "valid",
):
    codex = root / ".codex"
    codex.mkdir()
    hooks_dir = codex / "scripts" / "hooks"
    hooks_dir.mkdir(parents=True)
    adapters = {}
    for name in (
        "codex_write_gate.py",
        "memory_preflight_posttool.py",
        "codex_composite_mcp.py",
        "user_prompt_submit.py",
        "can_stop_gate.py",
    ):
        content = f"# {name}\n".encode()
        (hooks_dir / name).write_bytes(content)
        adapters[name] = hashlib.sha256(content).hexdigest()
    if adapter_state == "missing":
        (hooks_dir / "codex_composite_mcp.py").unlink()
    elif adapter_state == "drifted":
        (hooks_dir / "codex_composite_mcp.py").write_text("# drift\n", encoding="utf-8")
    elif adapter_state == "malformed":
        adapters = "invalid"
    (codex / "config.toml").write_text(
        "[mcp_servers.tausik-project]\n"
        'command = "python"\n'
        "[mcp_servers.tausik-project.env]\n"
        f"{env}\n",
        encoding="utf-8",
    )
    (codex / "tausik-capability.json").write_text(
        json.dumps(
            {
                "capability_version": capability_version,
                "mcp_transport_modes": modes or ["direct", "functions.exec"],
                "python_executable": "python",
                "adapters": adapters,
            }
        ),
        encoding="utf-8",
    )
    write_event, post_event = "PreToolUse", "PostToolUse"
    write_matcher = post_matcher = ""
    write_type = post_type = "command"
    write_script = hooks_dir / "codex_write_gate.py"
    post_script = hooks_dir / "memory_preflight_posttool.py"
    hook_project = root
    if hook_state == "swapped_events":
        write_event, post_event = post_event, write_event
    elif hook_state == "wrong_matcher":
        write_matcher = "functions.exec"
    elif hook_state == "wrong_type":
        write_type = "prompt"
    elif hook_state == "decoy_substring":
        write_script = hooks_dir / "prefix-codex_write_gate.py-decoy"
    elif hook_state == "wrong_project":
        hook_project = root / "other"
    elif hook_state == "wrong_path":
        write_script = root / "elsewhere" / "codex_write_gate.py"
    elif hook_state == "duplicate_project":
        hook_project = str(root) + '" --project "' + str(root / "other")
    python = "python-evil.exe" if hook_state == "wrong_python" else "python"
    trailing = ["--unknown"] if hook_state == "trailing_argument" else []
    document = {"hooks": {"PreToolUse": [], "PostToolUse": [], "UserPromptSubmit": [], "Stop": []}}
    document["hooks"][write_event].append(
        {
            "matcher": write_matcher,
            "hooks": [
                {
                    "type": write_type,
                    "command": serialize_hook_argv(
                        [
                            python,
                            "-X",
                            "utf8",
                            str(write_script),
                            "--project",
                            str(hook_project),
                            *trailing,
                        ]
                    ),
                }
            ],
        }
    )
    document["hooks"][post_event].append(
        {
            "matcher": post_matcher,
            "hooks": [
                {
                    "type": post_type,
                    "command": serialize_hook_argv(
                        ["python", "-X", "utf8", str(post_script), "--project", str(root)]
                    ),
                }
            ],
        }
    )
    for event, name in (
        ("UserPromptSubmit", "user_prompt_submit.py"),
        ("Stop", "can_stop_gate.py"),
    ):
        document["hooks"][event].append(
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": serialize_hook_argv(
                            [
                                "python",
                                "-X",
                                "utf8",
                                str(hooks_dir / name),
                                "--trusted-host",
                                "codex",
                            ]
                        ),
                    }
                ],
            }
        )
    (codex / "hooks.json").write_text(
        json.dumps(document),
        encoding="utf-8",
    )


def test_doctor_is_silent_when_codex_mcp_is_not_installed(tmp_path):
    assert check_codex_mcp_transport(str(tmp_path)) == []


def test_doctor_accepts_attested_direct_and_composite_transport(tmp_path):
    _install(tmp_path, env='TAUSIK_ENFORCE_EXECUTION_LEASE = "1"')
    rows = check_codex_mcp_transport(str(tmp_path))
    assert [row[0] for row in rows] == ["ok"]


def test_doctor_fails_on_bootstrap_capability_error(tmp_path):
    _install(
        tmp_path,
        env='TAUSIK_MCP_CAPABILITY_ERROR = "CAPABILITY_MISMATCH: rerun bootstrap"',
    )
    rows = check_codex_mcp_transport(str(tmp_path))
    assert [row[0] for row in rows] == ["fail"]
    assert "bootstrap" in rows[0][2]


def test_doctor_fails_on_stale_composite_manifest(tmp_path):
    _install(
        tmp_path,
        env='TAUSIK_ENFORCE_EXECUTION_LEASE = "1"',
        capability_version=2,
        modes=["direct"],
    )
    assert [row[0] for row in check_codex_mcp_transport(str(tmp_path))] == ["fail"]


@pytest.mark.parametrize("adapter_state", ["missing", "drifted", "malformed"])
def test_doctor_fails_when_an_attested_adapter_is_not_exact(tmp_path, adapter_state):
    _install(
        tmp_path,
        env='TAUSIK_ENFORCE_EXECUTION_LEASE = "1"',
        adapter_state=adapter_state,
    )
    rows = check_codex_mcp_transport(str(tmp_path))
    assert [row[0] for row in rows] == ["fail"]
    assert "CAPABILITY_MISMATCH" in rows[0][2]


def test_doctor_fails_when_hook_registration_is_missing(tmp_path):
    _install(tmp_path, env='TAUSIK_ENFORCE_EXECUTION_LEASE = "1"')
    (tmp_path / ".codex" / "hooks.json").write_text('{"hooks": {}}', encoding="utf-8")
    rows = check_codex_mcp_transport(str(tmp_path))
    assert [row[0] for row in rows] == ["fail"]
    assert "hook registrations" in rows[0][2]


@pytest.mark.parametrize(
    "hook_state",
    [
        "swapped_events",
        "wrong_matcher",
        "wrong_type",
        "decoy_substring",
        "wrong_project",
        "wrong_path",
        "duplicate_project",
        "trailing_argument",
        "wrong_python",
    ],
)
def test_doctor_fails_when_hook_registration_is_not_exact(tmp_path, hook_state):
    _install(
        tmp_path,
        env='TAUSIK_ENFORCE_EXECUTION_LEASE = "1"',
        hook_state=hook_state,
    )
    rows = check_codex_mcp_transport(str(tmp_path))
    assert [row[0] for row in rows] == ["fail"]
    assert "hook registrations" in rows[0][2]
