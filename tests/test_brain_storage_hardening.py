"""Tests for the brain storage-group hardening batch (MED-tier fixes).

Covers six tasks shipped together because they touch the same ~50 lines
of brain_sync + brain_config:

  brain-schema-wal-mode            — open_brain_db enables WAL
  brain-sync-iso-timestamp-compare — max_edited uses parsed epoch
  brain-sync-transaction-atomicity — success=single commit, error=rollback
  brain-sync-cursor-advance        — filter uses strict `after`, no boundary re-fetch
  brain-config-unicode-nfc         — compute_project_hash NFC-normalizes
  brain-config-mirror-path-contract — brain_runtime wrappers honor user mirror path
"""

from __future__ import annotations

import os
import sqlite3
import sys
from unittest.mock import patch

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_config  # noqa: E402
import brain_runtime  # noqa: E402
import brain_sync  # noqa: E402


# ---- brain-schema-wal-mode ----------------------------------------------


class TestOpenBrainDbWalMode:
    def test_file_db_reports_wal(self, tmp_path):
        path = tmp_path / "brain.db"
        conn = brain_sync.open_brain_db(str(path))
        try:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        assert mode.lower() == "wal"

    def test_wal_failure_does_not_raise(self, tmp_path, monkeypatch):
        """If the WAL pragma errors out, open_brain_db still returns a usable DB.

        sqlite3.Connection.execute is a C-level attribute and can't be
        monkey-patched; wrap the connection in a proxy that intercepts
        `execute(journal_mode...)` instead.
        """
        original_connect = sqlite3.connect

        class _FailingWalProxy:
            def __init__(self, inner: sqlite3.Connection):
                self._inner = inner
                self.row_factory = inner.row_factory

            def execute(self, sql, *a, **k):
                if isinstance(sql, str) and "journal_mode" in sql.lower():
                    raise sqlite3.OperationalError("wal refused")
                return self._inner.execute(sql, *a, **k)

            def executescript(self, *a, **k):
                return self._inner.executescript(*a, **k)

            def commit(self):
                return self._inner.commit()

            def rollback(self):
                return self._inner.rollback()

            def close(self):
                return self._inner.close()

            def __setattr__(self, name, value):
                if name in ("_inner", "row_factory"):
                    object.__setattr__(self, name, value)
                else:
                    setattr(self._inner, name, value)

            def __getattr__(self, name):
                return getattr(object.__getattribute__(self, "_inner"), name)

        def _wrap(path, *a, **k):
            return _FailingWalProxy(original_connect(path, *a, **k))

        monkeypatch.setattr(sqlite3, "connect", _wrap)
        conn = brain_sync.open_brain_db(str(tmp_path / "brain-wal-fail.db"))
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='brain_decisions'"
            ).fetchone()
            assert row is not None
        finally:
            conn.close()


# ---- brain-sync-iso-timestamp-compare ------------------------------------


class TestIsoEpochCompare:
    def test_mixed_format_picks_later_moment(self):
        # These two strings describe different moments but lexicographic
        # order puts '...Z' (0x5A) > '....000Z' (0x2E) for the same instant.
        earlier = brain_sync._iso_epoch("2026-01-01T00:00:00.000Z")
        later_terse = brain_sync._iso_epoch("2026-04-01T00:00:00Z")
        assert later_terse > earlier

    def test_unparseable_sorts_lowest(self):
        good = brain_sync._iso_epoch("2026-04-01T00:00:00Z")
        assert brain_sync._iso_epoch("garbage") < good
        assert brain_sync._iso_epoch("") < good


# ---- brain-sync-cursor-advance -------------------------------------------


def test_filter_uses_strict_after_when_cursor_set():
    f = brain_sync._make_filter("2026-04-01T00:00:00Z")
    assert f is not None
    assert f["last_edited_time"] == {"after": "2026-04-01T00:00:00Z"}


def test_filter_none_when_no_cursor():
    assert brain_sync._make_filter(None) is None
    assert brain_sync._make_filter("") is None


# ---- brain-sync-transaction-atomicity ------------------------------------


class _RaisingClient:
    """Yields one good page, then raises — simulates mid-batch Notion failure."""

    def __init__(self, good_pages: list[dict], raise_after: int = 1):
        self._good = good_pages
        self._raise_after = raise_after

    def iter_database_query(self, database_id, *, filter=None, sorts=None):
        for i, p in enumerate(self._good):
            if i >= self._raise_after:
                raise RuntimeError("simulated notion failure")
            yield p


def _minimal_decision_page(pid: str, edited: str) -> dict:
    return {
        "id": pid,
        "created_time": edited,
        "last_edited_time": edited,
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "n"}]},
            "Context": {"type": "rich_text", "rich_text": []},
            "Decision": {"type": "rich_text", "rich_text": [{"plain_text": "d"}]},
            "Rationale": {"type": "rich_text", "rich_text": []},
            "Tags": {"type": "multi_select", "multi_select": []},
            "Stack": {"type": "multi_select", "multi_select": []},
            "Date": {"type": "date", "date": {"start": "2026-04-01"}},
            "Source Project Hash": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "hashA"}],
            },
            "Generalizable": {"type": "checkbox", "checkbox": True},
        },
    }


def test_midbatch_error_rolls_back_partial_upserts(tmp_path):
    path = tmp_path / "brain.db"
    conn = brain_sync.open_brain_db(str(path))
    try:
        pages = [
            _minimal_decision_page("page-1", "2026-04-01T00:00:00Z"),
            _minimal_decision_page("page-2", "2026-04-02T00:00:00Z"),
        ]
        client = _RaisingClient(pages, raise_after=1)
        with pytest.raises(RuntimeError):
            brain_sync.sync_category(client, conn, "db-dec", "decisions")
        # The one page that was upserted before the error must be rolled back.
        rows = conn.execute("SELECT COUNT(*) FROM brain_decisions").fetchone()
        assert rows[0] == 0
        # Error recorded in sync_state.
        state = conn.execute(
            "SELECT last_error FROM sync_state WHERE category='decisions'"
        ).fetchone()
        assert state is not None and "notion failure" in (state[0] or "")
    finally:
        conn.close()


def test_success_path_commits_once_with_cursor(tmp_path):
    path = tmp_path / "brain.db"
    conn = brain_sync.open_brain_db(str(path))
    try:
        pages = [_minimal_decision_page("page-ok", "2026-04-05T00:00:00Z")]

        class _GoodClient:
            def iter_database_query(self, database_id, *, filter=None, sorts=None):
                for p in pages:
                    yield p

        result = brain_sync.sync_category(_GoodClient(), conn, "db-dec", "decisions")
        assert result["upserted"] == 1
        assert result["last_edited_time"] == "2026-04-05T00:00:00Z"
        state = conn.execute(
            "SELECT last_pull_at, last_error FROM sync_state WHERE category='decisions'"
        ).fetchone()
        assert state[0] == "2026-04-05T00:00:00Z"
        assert state[1] is None
    finally:
        conn.close()


# ---- brain-config-unicode-nfc --------------------------------------------


class TestNfcProjectHash:
    def test_nfc_and_nfd_forms_collapse_to_same_hash(self):
        import unicodedata

        name_nfc = unicodedata.normalize("NFC", "Café-Project")
        name_nfd = unicodedata.normalize("NFD", "Café-Project")
        assert name_nfc != name_nfd  # sanity: they differ bytewise
        assert brain_config.compute_project_hash(
            name_nfc
        ) == brain_config.compute_project_hash(name_nfd)

    def test_cyrillic_passes_through(self):
        # Pure-NFC Cyrillic input — hash deterministic, non-empty.
        h = brain_config.compute_project_hash("МойПроект")
        assert isinstance(h, str) and len(h) == 16

    def test_empty_still_raises(self):
        with pytest.raises(ValueError):
            brain_config.compute_project_hash("")


# ---- brain-config-mirror-path-contract -----------------------------------


class TestMirrorPathContract:
    """The bug: get_brain_mirror_path(merged_brain_dict) silently ignores the
    user's local_mirror_path because load_brain() re-unpacks `cfg["brain"]`.

    Initial fix (brain-config-mirror-path-contract): brain_runtime.try_brain_write_*
    call `get_brain_mirror_path()` with no arg.
    Review3 fix (brain-review3-fixes): get_brain_mirror_path itself now detects
    the merged-dict shape and unpacks correctly either way, so the no-arg
    workaround is no longer load-bearing — but we keep it for clarity.
    """

    def test_get_brain_mirror_path_accepts_merged_dict(self, tmp_path):
        """The function must honor local_mirror_path from a merged brain dict
        (the shape load_brain() returns), not just a top-level project config."""
        custom = str(tmp_path / "merged-brain.db")
        merged = {
            "enabled": True,
            "local_mirror_path": custom,
            "notion_integration_token_env": "X",
            "database_ids": {
                "decisions": "d",
                "web_cache": "w",
                "patterns": "p",
                "gotchas": "g",
            },
        }
        path = brain_config.get_brain_mirror_path(merged)
        assert path == os.path.abspath(custom)

    def test_get_brain_mirror_path_still_accepts_top_level_config(self, tmp_path):
        """The legacy shape — {"brain": {...}} — must keep working."""
        custom = str(tmp_path / "top-level-brain.db")
        top_level = {
            "brain": {
                "enabled": True,
                "local_mirror_path": custom,
                "database_ids": {
                    "decisions": "d",
                    "web_cache": "w",
                    "patterns": "p",
                    "gotchas": "g",
                },
            }
        }
        path = brain_config.get_brain_mirror_path(top_level)
        assert path == os.path.abspath(custom)

    def test_try_brain_write_decision_opens_user_mirror_path(
        self, tmp_path, monkeypatch
    ):
        user_mirror = tmp_path / "custom-brain.db"
        monkeypatch.setenv("TOK", "t")
        # Fake full project config as load_config would return.
        full_cfg = {
            "brain": {
                "enabled": True,
                "local_mirror_path": str(user_mirror),
                "notion_integration_token_env": "TOK",
                "database_ids": {
                    "decisions": "d",
                    "web_cache": "w",
                    "patterns": "p",
                    "gotchas": "g",
                },
            }
        }
        captured: dict[str, str] = {}

        def fake_open(path):
            captured["path"] = path
            return sqlite3.connect(":memory:")

        with (
            patch("brain_config.load_config", return_value=full_cfg),
            patch("brain_notion_client.NotionClient", autospec=True),
            patch("brain_sync.open_brain_db", side_effect=fake_open),
            patch(
                "brain_mcp_write.store_record",
                return_value={"status": "ok", "notion_page_id": "p1"},
            ),
        ):
            brain_runtime.try_brain_write_decision(
                "some decision", None, brain_config.load_brain(full_cfg)
            )

        # Path actually opened must be the user's, not DEFAULT_BRAIN's.
        assert captured["path"] == os.path.abspath(str(user_mirror))

    def test_try_brain_write_web_cache_opens_user_mirror_path(
        self, tmp_path, monkeypatch
    ):
        user_mirror = tmp_path / "custom2-brain.db"
        monkeypatch.setenv("TOK2", "t")
        full_cfg = {
            "brain": {
                "enabled": True,
                "local_mirror_path": str(user_mirror),
                "notion_integration_token_env": "TOK2",
                "database_ids": {
                    "decisions": "d",
                    "web_cache": "w",
                    "patterns": "p",
                    "gotchas": "g",
                },
            }
        }
        captured: dict[str, str] = {}

        def fake_open(path):
            captured["path"] = path
            return sqlite3.connect(":memory:")

        with (
            patch("brain_config.load_config", return_value=full_cfg),
            patch("brain_notion_client.NotionClient", autospec=True),
            patch("brain_sync.open_brain_db", side_effect=fake_open),
            patch(
                "brain_mcp_write.store_record",
                return_value={"status": "ok", "notion_page_id": "p1"},
            ),
        ):
            brain_runtime.try_brain_write_web_cache(
                "https://example.com/a",
                "body",
                brain_config.load_brain(full_cfg),
            )

        assert captured["path"] == os.path.abspath(str(user_mirror))
