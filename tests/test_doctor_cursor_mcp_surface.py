"""doctor warns when Cursor mcp.json lists non-TAUSIK servers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "bootstrap"), str(ROOT / "scripts")]

from bootstrap_copy import copy_scripts  # noqa: E402
from bootstrap_generate import generate_cursor_hooks_json  # noqa: E402
from service_doctor_cursor import check_cursor_mcp_surface  # noqa: E402


def _managed_entry(tmp_path: Path, name: str) -> dict:
    relative = (
        ".cursor/mcp/project/server.py"
        if name == "tausik-project"
        else f".cursor/mcp/{name}/rag_server.py"
    )
    server = tmp_path / relative
    server.parent.mkdir(parents=True, exist_ok=True)
    server.write_text("# probe\n", encoding="utf-8")
    entry = {
        "type": "stdio",
        "command": sys.executable,
        "args": [f"${{workspaceFolder}}/{relative}", "--project", "${workspaceFolder}"],
    }
    if name == "tausik-project":
        entry["env"] = {
            "TAUSIK_ENFORCE_EXECUTION_LEASE": "1",
            "TAUSIK_TRUSTED_HOST": "cursor",
        }
    return entry


def _install_cursor_capability(tmp_path: Path) -> None:
    profile = tmp_path / ".cursor"
    profile.mkdir(exist_ok=True)
    copy_scripts(str(ROOT), str(profile))
    generate_cursor_hooks_json(str(tmp_path), str(profile), venv_python=sys.executable)


def test_silent_without_cursor_mcp(tmp_path: Path):
    assert check_cursor_mcp_surface(str(tmp_path)) == []


def test_ok_when_only_tausik_servers(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    name: _managed_entry(tmp_path, name)
                    for name in ("tausik-project", "codebase-rag")
                }
            }
        ),
        encoding="utf-8",
    )
    _install_cursor_capability(tmp_path)
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert len(rows) == 1 and rows[0][0] == "ok"
    assert "no extra MCP" in rows[0][2]


def test_warns_when_managed_server_cannot_start(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"tausik-project": {}}}), encoding="utf-8"
    )
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert rows[0][0] == "warn"
    assert rows[0][1] == "Cursor MCP transport"
    assert "type=stdio" in rows[0][2]


def test_warns_when_managed_transport_is_empty(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert rows[0][0] == "warn"
    assert "tausik-project" in rows[0][2]


def test_warns_on_extra_servers_without_metering_claim(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "tausik-project": _managed_entry(tmp_path, "tausik-project"),
                    "plugin-office": {},
                    "browser": {},
                }
            }
        ),
        encoding="utf-8",
    )
    _install_cursor_capability(tmp_path)
    rows = check_cursor_mcp_surface(str(tmp_path))
    assert len(rows) == 1 and rows[0][0] == "warn"
    detail = rows[0][2]
    assert "plugin-office" in detail and "browser" in detail
    assert "same Cursor plan" in detail
    assert ".cursor/mcp.json" in detail
    assert "cannot meter" in detail
    assert "only `~/.cursor/mcp.json`" in detail or "not only" in detail.lower()


def test_fails_when_mcp_is_valid_but_hook_capability_is_missing(tmp_path: Path):
    mcp = tmp_path / ".cursor"
    mcp.mkdir()
    (mcp / "mcp.json").write_text(
        json.dumps({"mcpServers": {"tausik-project": _managed_entry(tmp_path, "tausik-project")}}),
        encoding="utf-8",
    )

    rows = check_cursor_mcp_surface(str(tmp_path))

    assert rows == [
        (
            "fail",
            "Cursor hook capability",
            "hook/config attestation is missing or stale — rerun bootstrap --ide cursor",
        )
    ]
