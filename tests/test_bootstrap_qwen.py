"""Tests for bootstrap_qwen.generate_settings_qwen — MCP server registration."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

import bootstrap_qwen  # noqa: E402


def _touch(path: str, content: str = "# stub\n") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@pytest.fixture
def qwen_layout(tmp_path):
    """Simulate .qwen/mcp/{codebase-rag,project}/server.py."""
    target_dir = tmp_path / ".qwen"
    for name in ("codebase-rag", "project"):
        _touch(str(target_dir / "mcp" / name / "server.py"))
    return {"target_dir": str(target_dir), "project_dir": str(tmp_path)}


def _load_settings(target_dir: str) -> dict:
    with open(os.path.join(target_dir, "settings.json"), encoding="utf-8") as f:
        return json.load(f)


def test_qwen_preserves_user_added_servers(qwen_layout):
    """User-added MCP entries must survive regeneration."""
    target_dir = qwen_layout["target_dir"]
    os.makedirs(target_dir, exist_ok=True)
    existing = {
        "mcpServers": {
            "user-custom": {"command": "node", "args": ["custom.js"]},
        }
    }
    with open(os.path.join(target_dir, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_qwen.generate_settings_qwen(
        target_dir, qwen_layout["project_dir"], venv_python="python"
    )
    cfg = _load_settings(target_dir)
    assert "user-custom" in cfg["mcpServers"]
    assert "tausik-brain" not in cfg["mcpServers"]
    assert "tausik-project" in cfg["mcpServers"]


def test_qwen_removes_a_retired_managed_server(qwen_layout):
    target_dir = qwen_layout["target_dir"]
    os.makedirs(target_dir, exist_ok=True)
    existing = {
        "mcpServers": {
            "user-custom": {"command": "node", "args": ["custom.js"]},
            "tausik-brain": {"command": "python", "args": ["mcp/brain/server.py"]},
        }
    }
    with open(os.path.join(target_dir, "settings.json"), "w", encoding="utf-8") as f:
        json.dump(existing, f)

    bootstrap_qwen.generate_settings_qwen(target_dir, qwen_layout["project_dir"], venv_python="python")

    with open(os.path.join(target_dir, "settings.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    assert "tausik-brain" not in cfg["mcpServers"]
    assert "user-custom" in cfg["mcpServers"]
