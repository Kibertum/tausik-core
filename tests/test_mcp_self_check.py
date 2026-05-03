"""Tests for the MCP project server's self-check diagnostic.

Covers v14b-mcp-stale-module-detector — detection of stale in-memory
modules that cause silent hangs in `tausik_verify` /
`tausik_task_done_v2` (gotchas #77 / #79 / #80).
"""

from __future__ import annotations

import importlib
import os
import sys

import pytest


@pytest.fixture
def self_check_mod():
    """Import self_check fresh, with the MCP project dir on sys.path."""
    mcp_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "agents",
            "claude",
            "mcp",
            "project",
        )
    )
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    if "self_check" in sys.modules:
        mod = importlib.reload(sys.modules["self_check"])
    else:
        import self_check as mod  # type: ignore[import-not-found]
    return mod


def test_startup_snapshot_populated(self_check_mod):
    """Eager-import + snapshot must run at module import.

    The snapshot dict can be empty in stripped environments, but the
    startup-time string MUST be set the first time the module loads.
    """
    assert self_check_mod._STARTUP_TIME_ISO
    assert isinstance(self_check_mod._MODULE_MTIMES_AT_STARTUP, dict)
    # In a healthy dev env at least one of the watched modules resolves
    # to a real file under scripts/. Allow zero only if the dev tree is
    # incomplete (CI-stripped tarball) — but the dict shape is required.
    for path, mtime in self_check_mod._MODULE_MTIMES_AT_STARTUP.items():
        assert os.path.isabs(path)
        assert isinstance(mtime, float)


def test_no_drift_when_files_unchanged(self_check_mod):
    """`collect()` reports drift_detected=False when nothing has moved."""
    report = self_check_mod.collect()
    assert report["server"] == "tausik-project"
    assert report["drift_detected"] is False
    assert report["stale_modules"] == []
    assert isinstance(report["sibling_mcp_count"], int)
    assert report["watched_modules_count"] == len(report["watched_modules"])


def test_drift_detected_when_mtime_advances(self_check_mod, tmp_path, monkeypatch):
    """Bump a snapshot file's mtime and confirm drift surfaces."""
    fake = tmp_path / "fake_module.py"
    fake.write_text("# placeholder\n", encoding="utf-8")
    snap = os.path.getmtime(fake)
    fake_path = str(fake)
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {fake_path: snap},
    )
    # Advance the on-disk mtime by 30s — well beyond float-precision noise.
    os.utime(fake, (snap + 30, snap + 30))

    report = self_check_mod.collect()

    assert report["drift_detected"] is True
    stale = report["stale_modules"]
    assert len(stale) == 1
    assert stale[0]["path"] == fake_path
    assert stale[0]["module"] == "fake_module.py"
    assert stale[0]["delta_seconds"] >= 30
    assert "Restart your IDE" in report["remediation"]


def test_collect_handles_missing_file_gracefully(self_check_mod, tmp_path, monkeypatch):
    """A snapshotted path that vanishes on disk must not crash collect()."""
    ghost = str(tmp_path / "deleted.py")
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {ghost: 1700000000.0},
    )
    # Path never existed — getmtime raises OSError, the loop skips it.
    report = self_check_mod.collect()
    assert report["drift_detected"] is False
    assert report["stale_modules"] == []


def test_sibling_count_is_safe_int(self_check_mod):
    """Sibling enumeration returns an int (or -1) without raising."""
    report = self_check_mod.collect()
    assert isinstance(report["sibling_mcp_count"], int)
    assert report["sibling_mcp_count"] >= -1
    assert isinstance(report["sibling_mcp_pids"], list)


def test_remediation_silent_when_count_unknown(self_check_mod, monkeypatch):
    """When sibling introspection failed (count=-1) and no drift, the
    remediation must NOT contain 'Restart your IDE' — that would be a
    false positive on hosts where wmic/PowerShell aren't usable.
    """
    # Force unknown-sibling state and zero drift.
    monkeypatch.setattr(self_check_mod, "_MODULE_MTIMES_AT_STARTUP", {})
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {
            "count": -1,
            "pids": [],
            "error": "wmic and powershell both missing: stub",
        },
    )
    report = self_check_mod.collect()
    assert report["drift_detected"] is False
    assert report["sibling_mcp_count"] == -1
    assert "Restart your IDE" not in report["remediation"]
    assert "drift check" in report["remediation"].lower()


def test_remediation_fires_on_real_drift(self_check_mod, tmp_path, monkeypatch):
    """With real drift, the remediation MUST tell the user to restart.

    Pinpoints the regression: previously, count=-1 also fired this path.
    """
    fake = tmp_path / "drifted.py"
    fake.write_text("# x\n", encoding="utf-8")
    snap = os.path.getmtime(fake)
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {str(fake): snap},
    )
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 0, "pids": [], "error": None},
    )
    os.utime(fake, (snap + 30, snap + 30))

    report = self_check_mod.collect()
    assert report["drift_detected"] is True
    assert "Restart your IDE" in report["remediation"]


def test_handler_returns_json_envelope(self_check_mod):
    """The MCP `_handle_self_check` dispatch wraps `collect()` in JSON.

    Not strictly necessary — but documents the integration surface for
    the agent so the JSON shape stays stable.
    """
    import json

    handlers_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "agents",
            "claude",
            "mcp",
            "project",
        )
    )
    if handlers_dir not in sys.path:
        sys.path.insert(0, handlers_dir)
    if "handlers" in sys.modules:
        importlib.reload(sys.modules["handlers"])
    import handlers as handlers_mod  # type: ignore[import-not-found]

    raw = handlers_mod._handle_self_check()
    parsed = json.loads(raw)
    assert parsed["server"] == "tausik-project"
    assert "drift_detected" in parsed
