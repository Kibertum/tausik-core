"""Tests for bootstrap_generate.generate_mcp_json — tausik-brain registration."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import bootstrap_generate  # noqa: E402


def _touch(path: str, content: str = "# stub\n") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
def ide_layout(tmp_path):
    """Simulate .claude/mcp/{codebase-rag,project,brain}/server.py."""
    ide_dir = tmp_path / ".claude"
    for name in ("codebase-rag", "project", "brain"):
        _touch(str(ide_dir / "mcp" / name / "server.py"))
    return {"project_dir": str(tmp_path), "ide_dir": str(ide_dir)}


def _load_config(project_dir: str) -> dict:
    with open(os.path.join(project_dir, ".mcp.json"), encoding="utf-8") as f:
        return json.load(f)


def test_registers_brain_when_server_present(ide_layout):
    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"],
        ide_layout["ide_dir"],
        venv_python="C:/py/python.exe",
    )
    cfg = _load_config(ide_layout["project_dir"])
    assert "tausik-brain" in cfg["mcpServers"]
    entry = cfg["mcpServers"]["tausik-brain"]
    assert entry["command"] == "C:/py/python.exe"
    assert entry["args"][0].endswith("mcp/brain/server.py")
    assert entry["args"][1] == "--project"


def test_skips_brain_when_server_missing(tmp_path):
    ide_dir = tmp_path / ".claude"
    # Only project server, no brain
    _touch(str(ide_dir / "mcp" / "project" / "server.py"))
    bootstrap_generate.generate_mcp_json(
        str(tmp_path), str(ide_dir), venv_python="python"
    )
    cfg = _load_config(str(tmp_path))
    assert "tausik-brain" not in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


def test_preserves_user_added_servers(ide_layout):
    # Pre-existing user server
    existing = {
        "mcpServers": {
            "my-custom": {"command": "node", "args": ["custom.js"]},
        }
    }
    with open(
        os.path.join(ide_layout["project_dir"], ".mcp.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(existing, f)

    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"], ide_layout["ide_dir"], venv_python="python"
    )
    cfg = _load_config(ide_layout["project_dir"])
    assert "my-custom" in cfg["mcpServers"]
    assert "tausik-brain" in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


def test_updates_managed_server_entries(ide_layout):
    # Stale tausik-project entry should be replaced
    existing = {
        "mcpServers": {
            "tausik-project": {"command": "stale-python", "args": ["old.py"]},
        }
    }
    with open(
        os.path.join(ide_layout["project_dir"], ".mcp.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(existing, f)

    bootstrap_generate.generate_mcp_json(
        ide_layout["project_dir"], ide_layout["ide_dir"], venv_python="fresh-py"
    )
    cfg = _load_config(ide_layout["project_dir"])
    assert cfg["mcpServers"]["tausik-project"]["command"] == "fresh-py"


def test_uses_forward_slashes_in_paths(tmp_path):
    ide_dir = tmp_path / ".claude"
    _touch(str(ide_dir / "mcp" / "brain" / "server.py"))
    bootstrap_generate.generate_mcp_json(
        str(tmp_path), str(ide_dir), venv_python="C:\\Python\\python.exe"
    )
    cfg = _load_config(str(tmp_path))
    entry = cfg["mcpServers"]["tausik-brain"]
    assert "\\" not in entry["command"]
    assert "\\" not in entry["args"][0]
    assert "\\" not in entry["args"][2]
