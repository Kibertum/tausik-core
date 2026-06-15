"""Tests for brain_status — collect_status + format_status helpers."""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_config  # noqa: E402
import brain_project_registry as bpr  # noqa: E402
import brain_status  # noqa: E402
import brain_sync  # noqa: E402


@pytest.fixture
def tmp_registry(tmp_path, monkeypatch):
    p = tmp_path / "projects.json"
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(p))
    return p


@pytest.fixture
def tmp_mirror(tmp_path):
    db_path = tmp_path / "brain.db"
    conn = brain_sync.open_brain_db(str(db_path))
    conn.close()
    return str(db_path)


# --- collect_status branches ----------------------------------------------


def test_disabled_returns_minimal_status(monkeypatch, tmp_registry):
    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": False, "local_mirror_path": "/nope"},
    )
    snap = brain_status.collect_status()
    assert snap["enabled"] is False
    assert snap["mirror_path"] is None
    assert snap["categories"] == {}
    assert snap["error"] is None


def test_config_load_error_caught(monkeypatch):
    def boom():
        raise RuntimeError("config gone")

    monkeypatch.setattr(brain_config, "load_brain", boom)
    snap = brain_status.collect_status()
    assert snap["enabled"] is False
    assert snap["error"] is not None
    assert "config" in snap["error"]


def test_missing_mirror_db_reports_error(monkeypatch, tmp_path, tmp_registry):
    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": True, "local_mirror_path": str(tmp_path / "absent.db")},
    )
    monkeypatch.setattr(
        brain_config, "get_brain_mirror_path", lambda: str(tmp_path / "absent.db")
    )
    snap = brain_status.collect_status()
    assert snap["enabled"] is True
    assert snap["mirror_size_bytes"] is None
    assert snap["error"] and "missing" in snap["error"]


def test_enabled_empty_mirror_returns_zero_rows(monkeypatch, tmp_mirror, tmp_registry):
    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": True, "local_mirror_path": tmp_mirror},
    )
    monkeypatch.setattr(brain_config, "get_brain_mirror_path", lambda: tmp_mirror)
    snap = brain_status.collect_status()
    assert snap["enabled"] is True
    assert snap["mirror_path"] == tmp_mirror
    assert snap["mirror_size_bytes"] is not None and snap["mirror_size_bytes"] > 0
    assert set(snap["categories"].keys()) == {
        "decisions",
        "web_cache",
        "patterns",
        "gotchas",
    }
    for cat in snap["categories"].values():
        assert cat["row_count"] == 0
    assert snap["last_web_cache_write"] is None
    assert snap["error"] is None


def test_enabled_with_data_surfaces_counts_and_sync_state(
    monkeypatch, tmp_mirror, tmp_registry
):
    # Insert one decision row + one sync_state entry + one web_cache row
    conn = sqlite3.connect(tmp_mirror)
    conn.execute(
        """INSERT INTO brain_decisions(notion_page_id, name, context, decision,
           rationale, tags, stack, date_value, source_project_hash, generalizable,
           last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "p1",
            "Adopt X",
            "ctx",
            "decided",
            "rat",
            "[]",
            "[]",
            None,
            "h" * 16,
            1,
            "2026-04-25T10:00:00Z",
            "2026-04-25T10:00:00Z",
        ),
    )
    conn.execute(
        """INSERT INTO sync_state(category, last_pull_at, last_error)
           VALUES (?,?,?)""",
        ("decisions", "2026-04-25T10:30:00Z", "rate-limited"),
    )
    conn.execute(
        """INSERT INTO brain_web_cache(notion_page_id, name, url, query, content,
           tags, fetched_at, ttl_days, domain, source_project_hash, content_hash,
           last_edited_time, created_time)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "w1",
            "doc",
            "https://x",
            "q",
            "c",
            "[]",
            "2026-04-25T11:00:00Z",
            30,
            "x",
            "h" * 16,
            "ch",
            "2026-04-25T11:00:00Z",
            "2026-04-25T11:00:00Z",
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": True, "local_mirror_path": tmp_mirror},
    )
    monkeypatch.setattr(brain_config, "get_brain_mirror_path", lambda: tmp_mirror)
    snap = brain_status.collect_status()
    assert snap["categories"]["decisions"]["row_count"] == 1
    assert snap["categories"]["decisions"]["last_pull_at"] == "2026-04-25T10:30:00Z"
    assert snap["categories"]["decisions"]["last_error"] == "rate-limited"
    assert snap["categories"]["web_cache"]["row_count"] == 1
    assert snap["last_web_cache_write"] == "2026-04-25T11:00:00Z"


def test_registered_projects_listed(monkeypatch, tmp_registry, tmp_mirror):
    bpr.register_project("alpha", "/path/to/alpha")
    bpr.register_project("beta", "/path/to/beta")
    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": True, "local_mirror_path": tmp_mirror},
    )
    monkeypatch.setattr(brain_config, "get_brain_mirror_path", lambda: tmp_mirror)
    snap = brain_status.collect_status()
    names = [p["name"] for p in snap["projects"]]
    assert "alpha" in names
    assert "beta" in names


def test_registry_missing_returns_empty_projects(monkeypatch, tmp_registry):
    monkeypatch.setattr(
        brain_config,
        "load_brain",
        lambda: {"enabled": False, "local_mirror_path": "/nope"},
    )
    snap = brain_status.collect_status()
    assert snap["projects"] == []


# --- format_status --------------------------------------------------------


def test_format_status_renders_disabled():
    snap = {
        "collected_at": "2026-04-25T12:00:00Z",
        "enabled": False,
        "mirror_path": None,
        "mirror_size_bytes": None,
        "mirror_last_modified": None,
        "categories": {},
        "projects": [],
        "last_web_cache_write": None,
        "error": None,
    }
    md = brain_status.format_status(snap)
    assert "Brain status" in md
    assert "enabled: **False**" in md
    assert "No projects registered" in md


def test_format_status_renders_with_data():
    snap = {
        "collected_at": "2026-04-25T12:00:00Z",
        "enabled": True,
        "mirror_path": "/tmp/brain.db",
        "mirror_size_bytes": 12345,
        "mirror_last_modified": "2026-04-25T10:00:00Z",
        "categories": {
            "decisions": {
                "row_count": 5,
                "last_pull_at": "2026-04-25T11:00:00Z",
                "last_error": None,
                "last_error_at": None,
            },
            "web_cache": {
                "row_count": 99,
                "last_pull_at": None,
                "last_error": "rate-limited",
                "last_error_at": "2026-04-25T11:30:00Z",
            },
            "patterns": {
                "row_count": 0,
                "last_pull_at": None,
                "last_error": None,
                "last_error_at": None,
            },
            "gotchas": {
                "row_count": 0,
                "last_pull_at": None,
                "last_error": None,
                "last_error_at": None,
            },
        },
        "projects": [
            {"name": "alpha", "canonical": "alpha", "hash": "a" * 16},
        ],
        "last_web_cache_write": "2026-04-25T11:00:00Z",
        "error": None,
    }
    md = brain_status.format_status(snap)
    assert "/tmp/brain.db" in md
    assert "12,345 bytes" in md
    assert "decisions" in md and "5 rows" in md
    assert "rate-limited" in md
    assert "alpha" in md
    assert "Registered projects" in md
