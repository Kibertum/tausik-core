"""Tip scripts must win without an MCP/host restart (release DX)."""

from __future__ import annotations

import importlib
import sys
import textwrap

import pytest

from memory_preflight_classification import (
    ProtectedActionClassificationError,
    classify_action,
)
from memory_preflight_tip_load import prefer_project_scripts, refresh_preflight_modules

_TIP_NAMES = (
    "memory_preflight_query",
    "memory_preflight_classification",
    "memory_relevance",
)


def _purge_tip_modules() -> None:
    for name in _TIP_NAMES:
        sys.modules.pop(name, None)


def test_prefer_project_scripts_puts_tip_first(tmp_path, monkeypatch):
    tip = tmp_path / "scripts"
    tip.mkdir()
    (tip / "memory_preflight_query.py").write_text("# tip\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    deployed = tmp_path / "deployed"
    deployed.mkdir()
    before = list(sys.path)
    sys.path.insert(0, str(deployed))
    try:
        found = prefer_project_scripts()
        assert found == str(tip.resolve()) or found == str(tip)
        assert sys.path[0] == found
    finally:
        sys.path[:] = before
        _purge_tip_modules()


def test_refresh_rebinds_after_tip_edit(tmp_path, monkeypatch):
    tip = tmp_path / "scripts"
    tip.mkdir()
    monkeypatch.chdir(tmp_path)
    before = list(sys.path)

    def _write_query(marker: str) -> None:
        (tip / "memory_preflight_query.py").write_text(
            textwrap.dedent(
                f"""
                TIP_MARKER = {marker!r}
                def fts_or(terms):
                    return " OR ".join(terms)
                def has_quarantined_conflict(be, terms):
                    return False
                def live_conflict_count(be, terms):
                    return 0
                def preflight_terms(tool_name, tool_input, kind):
                    return [TIP_MARKER]
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

    (tip / "memory_preflight_classification.py").write_text(
        "PROTECTED_KINDS=()\n"
        "def binding_payload(*a, **k): return {}\n"
        "def classify_action(*a, **k): return None\n"
        "def normalize_host_shell_tool(x): return x\n"
        "def within_reserve_grace(*a, **k): return False\n",
        encoding="utf-8",
    )
    (tip / "memory_relevance.py").write_text("MAX_ENTRIES = 8\n", encoding="utf-8")
    try:
        _purge_tip_modules()
        _write_query("first")
        prefer_project_scripts()
        importlib.import_module("memory_preflight_query")
        ns = {
            "fts_or": None,
            "has_quarantined_conflict": None,
            "live_conflict_count": None,
            "preflight_terms": None,
            "MAX_ENTRIES": 0,
        }
        refresh_preflight_modules(ns)
        assert ns["preflight_terms"]("Bash", {}, "release_shell") == ["first"]

        _write_query("second")
        refresh_preflight_modules(ns)
        assert ns["preflight_terms"]("Bash", {}, "release_shell") == ["second"]
        assert ns["MAX_ENTRIES"] == 8
    finally:
        sys.path[:] = before
        _purge_tip_modules()


def test_refresh_preserves_classification_exception_identity():
    """Reload must not break pytest.raises on the pre-refresh exception class."""
    before = ProtectedActionClassificationError
    refresh_preflight_modules()
    with pytest.raises(before, match="spans protected kinds"):
        classify_action("Bash", {"command": "git commit -m x && git push origin main"})
