"""Explicit memory-only governance profile for low-ceremony project work."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bootstrap"))

from bootstrap_codex import build_codex_hooks, generate_codex_hooks  # noqa: E402
from bootstrap_config import resolve_governance_profile  # noqa: E402
from bootstrap_generate import generate_agents_md  # noqa: E402
from bootstrap_hooks import MEMORY_ONLY_HOOKS, build_hooks_dict  # noqa: E402
from bootstrap_opencode import scaffold_opencode  # noqa: E402
from bootstrap_opencode_assets import PLUGIN_FILE, PLUGINS_SUBDIR  # noqa: E402
from bootstrap_qwen import generate_settings_qwen  # noqa: E402
from bootstrap_templates import build_full_body  # noqa: E402


def _scripts(hooks: dict) -> set[str]:
    return {
        os.path.basename(hook["command"].split()[3 if "-X utf8" in hook["command"] else -1])
        for entries in hooks.values()
        for entry in entries
        for hook in entry["hooks"]
    }


def test_profile_is_explicit_fail_safe_and_never_inferred_from_stack():
    assert resolve_governance_profile({}) == "full"
    assert resolve_governance_profile({"bootstrap": {"stacks": ["ansible"]}}) == "full"
    assert resolve_governance_profile({"governance_profile": " MEMORY-ONLY "}) == "memory-only"
    for invalid in ("light", "", None, False):
        with pytest.raises(ValueError, match="governance_profile"):
            resolve_governance_profile({"governance_profile": invalid})


def test_shared_and_codex_memory_only_hooks_retain_exactly_the_memory_pair(tmp_path):
    command = lambda script, suffix="": f"python -X utf8 hooks/{script}{suffix}"  # noqa: E731
    assert build_hooks_dict(command) == build_hooks_dict(command, "full")
    assert _scripts(build_hooks_dict(command, "memory-only")) == MEMORY_ONLY_HOOKS
    assert _scripts(build_codex_hooks(str(tmp_path), governance_profile="memory-only")) == (
        MEMORY_ONLY_HOOKS
    )


def test_memory_only_rules_name_retained_and_lost_guarantees_without_rituals():
    body = build_full_body(
        "infra",
        ["ansible"],
        "an agent",
        ".codex",
        governance_profile="memory-only",
    )
    for retained in ("tausik-project", "codebase-rag", "memory_pretool_block.py"):
        assert retained in body
    for ritual in ("No code without a task", "task start", "verify --task", "/start"):
        assert ritual not in body
    assert "Not guaranteed in this profile" in body


def test_generated_rules_switch_profiles_idempotently_but_custom_rules_survive(tmp_path):
    generate_agents_md(str(tmp_path), "infra", ["ansible"])
    generate_agents_md(str(tmp_path), "infra", ["ansible"], governance_profile="memory-only")
    path = tmp_path / "AGENTS.md"
    memory_only = path.read_bytes()
    assert b"TAUSIK:GOVERNANCE-PROFILE:memory-only" in memory_only
    generate_agents_md(str(tmp_path), "infra", ["ansible"], governance_profile="memory-only")
    assert path.read_bytes() == memory_only
    generate_agents_md(str(tmp_path), "infra", ["ansible"], governance_profile="full")
    assert b"No code without a task" in path.read_bytes()

    custom = tmp_path / "custom"
    custom.mkdir()
    custom_path = custom / "AGENTS.md"
    original = b"# My project rules\nkeep me byte-exact\n"
    custom_path.write_bytes(original)
    generate_agents_md(str(custom), "infra", ["ansible"], governance_profile="memory-only")
    assert custom_path.read_bytes() == original


def test_qwen_keeps_mcp_and_only_memory_hooks(tmp_path):
    target = tmp_path / ".qwen"
    for rel in ("mcp/project/server.py", "mcp/codebase-rag/rag_server.py"):
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    generate_settings_qwen(
        str(target),
        str(tmp_path),
        sys.executable,
        governance_profile="memory-only",
    )
    data = json.loads((target / "settings.json").read_text(encoding="utf-8"))
    assert set(data["mcpServers"]) == {"tausik-project", "codebase-rag"}
    assert _scripts(data["hooks"]) == MEMORY_ONLY_HOOKS


def test_codex_rerun_replaces_heavy_hooks_and_preserves_foreign_keys(tmp_path):
    target = tmp_path / ".codex"
    target.mkdir()
    path = target / "hooks.json"
    path.write_text('{"theme":"dark"}', encoding="utf-8")
    generate_codex_hooks(str(tmp_path), str(target), governance_profile="memory-only")
    first = path.read_bytes()
    generate_codex_hooks(str(tmp_path), str(target), governance_profile="memory-only")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert path.read_bytes() == first
    assert data["theme"] == "dark"
    assert _scripts(data["hooks"]) == MEMORY_ONLY_HOOKS


def test_opencode_removes_qg0_plugin_but_keeps_mcp_and_memory_rules(tmp_path):
    target = tmp_path / ".opencode"
    plugin = target / PLUGINS_SUBDIR / PLUGIN_FILE
    plugin.parent.mkdir(parents=True)
    plugin.write_text("heavy", encoding="utf-8")
    for rel in ("mcp/project/server.py", "mcp/codebase-rag/rag_server.py"):
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    scaffold_opencode(
        str(tmp_path),
        str(target),
        sys.executable,
        str(ROOT),
        {},
        ["ansible"],
        governance_profile="memory-only",
    )

    assert not plugin.exists()
    config = json.loads((tmp_path / "opencode.json").read_text(encoding="utf-8"))
    assert set(config["mcp"]) >= {"tausik-project", "codebase-rag"}
    rules = (target / "tausik-rules.md").read_text(encoding="utf-8")
    assert "governance profile: memory-only" in rules.lower()
    assert "No code without a task" not in rules
