"""Commit gate: refuse generated TAUSIK harness copies in the index."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import gate_outcome
import gate_harness_projection as gate
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "bootstrap"))

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def test_forbidden_paths_catch_profile_and_unpacked_lib():
    bad = gate.forbidden_staged_paths(
        [
            "src/app.py",
            ".cursor/scripts/hooks/cursor_hook.py",
            ".tausik-lib",
            ".tausik-lib/scripts/project.py",
            "opencode.json",
            ".tausik/config.json",
            "tausik/tasks/x.md",
        ]
    )
    assert bad == [
        ".cursor/scripts/hooks/cursor_hook.py",
        ".tausik-lib/scripts/project.py",
        "opencode.json",
        ".tausik/config.json",
    ]


def test_product_and_export_and_submodule_pointer_are_allowed():
    assert (
        gate.forbidden_staged_paths(["README.md", "tausik/memory/a.md", ".tausik-lib", "AGENTS.md"])
        == []
    )


def test_consumer_lib_tree_refuses_framework_source_copies():
    staged = [
        "src/app.py",
        "bootstrap/bootstrap.py",
        "harness/skills/start/SKILL.md",
        "scripts/hooks/cursor_hook.py",
        "scripts/app_deploy.py",
        "tausik/tasks/x.md",
        ".tausik-lib",
    ]
    assert gate.forbidden_staged_paths(staged, consumer=False) == []
    assert gate.forbidden_staged_paths(staged, consumer=True) == [
        "bootstrap/bootstrap.py",
        "harness/skills/start/SKILL.md",
        "scripts/hooks/cursor_hook.py",
    ]


def test_consumer_refuses_paths_that_shadow_tausik_lib(tmp_path):
    root = tmp_path / "proj"
    lib = root / ".tausik-lib" / "scripts"
    lib.mkdir(parents=True)
    (lib / "project.py").write_text("# framework\n", encoding="utf-8")
    staged = [
        "src/app.py",
        "scripts/project.py",
        "scripts/app_deploy.py",
        "tausik/tasks/x.md",
        ".tausik-lib",
    ]
    assert gate.forbidden_staged_paths(staged, consumer=True, root=str(root)) == [
        "scripts/project.py",
    ]


def test_gate_blocks_when_index_holds_a_profile_copy(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / ".cursor" / "scripts").mkdir(parents=True)
    target = root / ".cursor" / "scripts" / "x.py"
    target.write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "add", "-f", ".cursor/scripts/x.py"], cwd=root, check=True)
    monkeypatch.setattr(gate, "_repo_root", lambda: str(root))
    outcome = gate.run_harness_projection_gate_for({"enabled": True}, [])
    assert outcome.outcome == gate_outcome.FAILED
    assert "harness_projection" in outcome.detail
    assert ".cursor/scripts/x.py" in outcome.detail


def test_gate_passes_when_only_export_is_staged(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    export = root / "tausik" / "tasks"
    export.mkdir(parents=True)
    (export / "a.md").write_text("# a\n", encoding="utf-8")
    subprocess.run(["git", "add", "tausik/tasks/a.md"], cwd=root, check=True)
    monkeypatch.setattr(gate, "_repo_root", lambda: str(root))
    outcome = gate.run_harness_projection_gate_for({"enabled": True}, [])
    assert outcome.outcome == gate_outcome.PASSED


def test_ensure_gitignore_appends_missing_rules(tmp_path):
    from bootstrap_gitignore import ensure_tausik_gitignore

    root = tmp_path / "proj"
    root.mkdir()
    gi = root / ".gitignore"
    gi.write_text("node_modules/\n", encoding="utf-8")
    added = ensure_tausik_gitignore(str(root))
    assert ".tausik/" in added
    assert any(x.startswith(".cursor") for x in added)
    assert "bootstrap/" not in added
    assert "harness/" not in added
    (root / ".tausik-lib").mkdir()
    added_consumer = ensure_tausik_gitignore(str(root))
    assert "bootstrap/" in added_consumer
    assert "harness/" in added_consumer
    assert "scripts/hooks/" in added_consumer
    text = gi.read_text(encoding="utf-8")
    assert ".tausik/" in text
    assert ensure_tausik_gitignore(str(root)) == []


def test_harness_projection_is_registered_on_commit():
    import gate_registry as reg

    spec = reg.GATE_REGISTRY["harness_projection"]
    assert "commit" in spec.default_config["trigger"]
    assert spec.default_config["severity"] == "block"
