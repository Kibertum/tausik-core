"""Tests for bootstrap_generate.generate_mcp_json — MCP server registration."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import bootstrap_generate


def _touch(path: str, content: str = "# stub\n") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
def ide_layout(tmp_path):
    """Simulate .claude/mcp/codebase-rag/rag_server.py and .claude/mcp/project/server.py."""
    ide_dir = tmp_path / ".claude"
    for name, entry in {"codebase-rag": "rag_server.py", "project": "server.py"}.items():
        _touch(str(ide_dir / "mcp" / name / entry))
    return {"project_dir": str(tmp_path), "ide_dir": str(ide_dir)}


def _load_config(project_dir: str) -> dict:
    with open(os.path.join(project_dir, ".mcp.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_cursor_config(project_dir: str) -> dict:
    with open(os.path.join(project_dir, ".cursor", "mcp.json"), encoding="utf-8") as f:
        return json.load(f)


def test_preserves_user_added_servers(ide_layout):
    # Pre-existing user server
    existing = {
        "mcpServers": {
            "my-custom": {"command": "node", "args": ["custom.js"]},
        }
    }
    with open(os.path.join(ide_layout["project_dir"], ".mcp.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"], ide_layout["ide_dir"], venv_python="python"
    )
    cfg = _load_config(ide_layout["project_dir"])
    assert "my-custom" in cfg["mcpServers"]
    assert "tausik-brain" not in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


def test_updates_managed_server_entries(ide_layout):
    # Stale tausik-project entry should be replaced
    existing = {
        "mcpServers": {
            "tausik-project": {"command": "stale-python", "args": ["old.py"]},
        }
    }
    with open(os.path.join(ide_layout["project_dir"], ".mcp.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"], ide_layout["ide_dir"], venv_python="fresh-py"
    )
    cfg = _load_config(ide_layout["project_dir"])
    assert cfg["mcpServers"]["tausik-project"]["command"] == "fresh-py"
    assert cfg["mcpServers"]["tausik-project"]["type"] == "stdio"


def test_uses_forward_slashes_in_paths(tmp_path):
    ide_dir = tmp_path / ".claude"
    _touch(str(ide_dir / "mcp" / "project" / "server.py"))
    bootstrap_generate.generate_mcp_json(
        str(tmp_path), str(ide_dir), venv_python="C:\\Python\\python.exe"
    )
    cfg = _load_config(str(tmp_path))
    entry = cfg["mcpServers"]["tausik-project"]
    assert "\\" not in entry["command"]
    assert "\\" not in entry["args"][0]
    assert "\\" not in entry["args"][2]


def test_generates_cursor_project_mcp_json(ide_layout):
    cursor_ide = os.path.join(ide_layout["project_dir"], ".cursor")
    os.makedirs(cursor_ide, exist_ok=True)
    for name, entry in {"codebase-rag": "rag_server.py", "project": "server.py"}.items():
        _touch(os.path.join(cursor_ide, "mcp", name, entry))

    bootstrap_generate.generate_cursor_mcp_json(
        ide_layout["project_dir"], cursor_ide, venv_python="C:/py/python.exe"
    )
    cfg = _load_cursor_config(ide_layout["project_dir"])
    assert "tausik-project" in cfg["mcpServers"]
    assert "tausik-brain" not in cfg["mcpServers"]
    assert cfg["mcpServers"]["tausik-project"]["type"] == "stdio"
    assert cfg["mcpServers"]["tausik-project"]["command"] == "C:/py/python.exe"
    env = cfg["mcpServers"]["tausik-project"]["env"]
    assert env == {
        "TAUSIK_ENFORCE_EXECUTION_LEASE": "1",
        "TAUSIK_TRUSTED_HOST": "cursor",
        "TAUSIK_PROFILE_BUILD": env["TAUSIK_PROFILE_BUILD"],
    }
    assert len(env["TAUSIK_PROFILE_BUILD"]) == 16


def test_cursor_runtime_content_changes_mcp_process_identity(ide_layout):
    cursor_ide = os.path.join(ide_layout["project_dir"], ".cursor")
    server = os.path.join(cursor_ide, "mcp", "project", "server.py")
    _touch(server, "# first\n")
    bootstrap_generate.generate_cursor_mcp_json(ide_layout["project_dir"], cursor_ide)
    first = _load_cursor_config(ide_layout["project_dir"])["mcpServers"]["tausik-project"]["env"][
        "TAUSIK_PROFILE_BUILD"
    ]

    _touch(server, "# second\n")
    bootstrap_generate.generate_cursor_mcp_json(ide_layout["project_dir"], cursor_ide)
    second = _load_cursor_config(ide_layout["project_dir"])["mcpServers"]["tausik-project"]["env"][
        "TAUSIK_PROFILE_BUILD"
    ]

    assert first != second


def test_cursor_memory_only_profile_does_not_enable_execution_lease(ide_layout):
    cursor_ide = os.path.join(ide_layout["project_dir"], ".cursor")
    os.makedirs(cursor_ide, exist_ok=True)
    _touch(os.path.join(cursor_ide, "mcp", "project", "server.py"))

    bootstrap_generate.generate_cursor_mcp_json(
        ide_layout["project_dir"],
        cursor_ide,
        venv_python="python",
        governance_profile="memory-only",
    )

    entry = _load_cursor_config(ide_layout["project_dir"])["mcpServers"]["tausik-project"]
    assert "env" not in entry


def test_cursor_mcp_json_preserves_user_servers(ide_layout):
    cursor_dir = os.path.join(ide_layout["project_dir"], ".cursor")
    os.makedirs(cursor_dir, exist_ok=True)
    _touch(os.path.join(cursor_dir, "mcp", "project", "server.py"))
    existing = {
        "mcpServers": {
            "custom": {"command": "node", "args": ["custom.js"]},
        }
    }
    with open(os.path.join(cursor_dir, "mcp.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_generate.generate_cursor_mcp_json(
        ide_layout["project_dir"], cursor_dir, venv_python="python"
    )
    cfg = _load_cursor_config(ide_layout["project_dir"])
    assert "custom" in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


def test_a_retired_managed_server_is_removed_while_user_servers_survive(ide_layout):
    """A 1.8 consumer keeps a `tausik-brain` entry that points at a server.py no
    1.9 bootstrap ships; leaving it would make the host log an MCP error on every
    start. User-added entries are not ours to remove."""
    existing = {
        "mcpServers": {
            "my-custom": {"command": "node", "args": ["custom.js"]},
            "tausik-brain": {"command": "python", "args": [".claude/mcp/brain/server.py"]},
        }
    }
    with open(os.path.join(ide_layout["project_dir"], ".mcp.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"], ide_layout["ide_dir"], venv_python="python"
    )

    with open(os.path.join(ide_layout["project_dir"], ".mcp.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    assert "tausik-brain" not in cfg["mcpServers"]
    assert "my-custom" in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


@pytest.mark.parametrize("cursor", [False, True])
def test_malformed_existing_mcp_is_preserved_byte_exact(ide_layout, cursor):
    project = ide_layout["project_dir"]
    target = (
        os.path.join(project, ".cursor", "mcp.json")
        if cursor
        else os.path.join(project, ".mcp.json")
    )
    os.makedirs(os.path.dirname(target), exist_ok=True)
    original = b'{"mcpServers": {"private": '
    with open(target, "wb") as file:
        file.write(original)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        if cursor:
            bootstrap_generate.generate_cursor_mcp_json(project, os.path.join(project, ".cursor"))
        else:
            bootstrap_generate.generate_mcp_json(project, ide_layout["ide_dir"])
    with open(target, "rb") as file:
        assert file.read() == original


@pytest.mark.parametrize("value", [[], {"mcpServers": []}])
def test_invalid_existing_mcp_shape_is_preserved(ide_layout, value):
    target = os.path.join(ide_layout["project_dir"], ".mcp.json")
    original = json.dumps(value).encode()
    with open(target, "wb") as file:
        file.write(original)
    with pytest.raises(RuntimeError, match="refusing to overwrite"):
        bootstrap_generate.generate_mcp_json(ide_layout["project_dir"], ide_layout["ide_dir"])
    with open(target, "rb") as file:
        assert file.read() == original
