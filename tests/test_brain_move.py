"""Tests for brain_move — move records between local TAUSIK and brain."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_config  # noqa: E402
import brain_move  # noqa: E402
import brain_runtime  # noqa: E402
import brain_sync  # noqa: E402


# --- Fakes ----------------------------------------------------------------


class _FakeBackend:
    """Minimal stand-in for ProjectService.be — exposes the methods brain_move calls."""

    def __init__(self):
        self.decisions: dict[int, dict] = {}
        self.memory: dict[int, dict] = {}
        self._next_dec_id = 1
        self._next_mem_id = 1
        self.deletes: list[tuple[str, int]] = []

    def decision_get(self, decision_id: int):
        return self.decisions.get(decision_id)

    def decision_add(self, text: str, *, rationale=None):
        new_id = self._next_dec_id
        self._next_dec_id += 1
        self.decisions[new_id] = {
            "id": new_id,
            "decision": text,
            "rationale": rationale,
        }
        return new_id

    def memory_add(self, mem_type, title, content, *, tags=None, task_slug=None):
        new_id = self._next_mem_id
        self._next_mem_id += 1
        self.memory[new_id] = {
            "id": new_id,
            "type": mem_type,
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        return new_id

    def _q1(self, sql, params=()):
        # only handles "SELECT * FROM memory WHERE id = ?"
        if "memory" in sql:
            return self.memory.get(int(params[0]))
        return None

    def _ex(self, sql, params=()):
        if "DELETE FROM decisions" in sql:
            self.decisions.pop(int(params[0]), None)
            self.deletes.append(("decisions", int(params[0])))
        elif "DELETE FROM memory" in sql:
            self.memory.pop(int(params[0]), None)
            self.deletes.append(("memory", int(params[0])))
        return 1


class _FakeService:
    def __init__(self, be):
        self.be = be


class _FakeNotionClient:
    """Stand-in for brain_notion_client.NotionClient with archive support."""

    def __init__(self, *, fail_create=False, fail_archive=False):
        self.create_calls: list[dict] = []
        self.archive_calls: list[str] = []
        self.fail_create = fail_create
        self.fail_archive = fail_archive

    def pages_create(self, *, parent, properties, children=None):
        self.create_calls.append({"parent": parent, "properties": properties})
        if self.fail_create:
            raise ConnectionError("network down")
        # Return Notion-shaped response
        return _fake_notion_response(
            page_id=f"npg-{len(self.create_calls)}",
            database_id=parent.get("database_id", ""),
            properties=properties,
        )

    def pages_update(self, page_id, *, archived=None, properties=None):
        self.archive_calls.append(page_id)
        if self.fail_archive:
            raise ConnectionError("notion down")
        return {"id": page_id, "archived": bool(archived)}


def _fake_notion_response(*, page_id, database_id, properties):
    """Mirror minimal Notion page shape used by brain_sync.map_page_to_row."""
    enriched: dict = {}
    for k, v in properties.items():
        if not isinstance(v, dict):
            enriched[k] = v
            continue
        if "title" in v:
            enriched[k] = {
                "title": [
                    {**it, "plain_text": it.get("text", {}).get("content", "")}
                    for it in v["title"]
                ]
            }
        elif "rich_text" in v:
            enriched[k] = {
                "rich_text": [
                    {**it, "plain_text": it.get("text", {}).get("content", "")}
                    for it in v["rich_text"]
                ]
            }
        else:
            enriched[k] = v
    return {
        "id": page_id,
        "parent": {"database_id": database_id},
        "properties": enriched,
        "last_edited_time": "2026-04-25T10:00:00Z",
        "created_time": "2026-04-25T10:00:00Z",
    }


@pytest.fixture
def cfg():
    return {
        "enabled": True,
        "project_names": [],
        "private_url_patterns": [],
        "notion_integration_token_env": "FAKE_TOK",
        "database_ids": {
            "decisions": "db-dec",
            "web_cache": "db-wc",
            "patterns": "db-pat",
            "gotchas": "db-got",
        },
    }


@pytest.fixture
def open_brain_deps(monkeypatch, tmp_path, cfg):
    """Stub brain_runtime.open_brain_deps to return (real_conn, fake_client, cfg)."""
    db_path = tmp_path / "brain.db"
    conn = brain_sync.open_brain_db(str(db_path))
    client = _FakeNotionClient()

    def stub():
        return conn, client, cfg

    monkeypatch.setattr(brain_runtime, "open_brain_deps", stub)
    yield {"conn": conn, "client": client, "cfg": cfg, "db_path": str(db_path)}
    conn.close()


# --- to-brain -------------------------------------------------------------


class TestMoveToBrain:
    def test_decision_happy_path(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        be = _FakeBackend()
        be.decision_add("Adopt PostgreSQL", rationale="ACID")
        svc = _FakeService(be)
        result = brain_move.move_to_brain(svc, "decision", 1)
        assert result["status"] == "ok"
        assert result["category"] == "decisions"
        assert result["notion_page_id"]
        # Source deleted by default
        assert ("decisions", 1) in be.deletes
        assert 1 not in be.decisions

    def test_pattern_happy_path(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        be = _FakeBackend()
        be.memory_add("pattern", "Backoff with jitter", "exp 2^n with ±20% jitter")
        svc = _FakeService(be)
        result = brain_move.move_to_brain(svc, "pattern", 1)
        assert result["status"] == "ok"
        assert result["category"] == "patterns"

    def test_kind_mismatch_returns_bad_input(self, open_brain_deps):
        be = _FakeBackend()
        be.memory_add("gotcha", "X", "Y")  # type=gotcha but we'll ask for pattern
        svc = _FakeService(be)
        result = brain_move.move_to_brain(svc, "pattern", 1)
        assert result["status"] == "bad_input"

    def test_keep_source_preserves_local_row(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        be = _FakeBackend()
        be.decision_add("Cache invalidation", rationale="speed")
        svc = _FakeService(be)
        result = brain_move.move_to_brain(svc, "decision", 1, keep_source=True)
        assert result["status"] == "ok"
        assert result["source_kept"] is True
        assert 1 in be.decisions  # not deleted

    def test_invalid_kind(self, open_brain_deps):
        result = brain_move.move_to_brain(_FakeService(_FakeBackend()), "manifesto", 1)
        assert result["status"] == "bad_input"

    def test_source_not_found(self, open_brain_deps):
        result = brain_move.move_to_brain(_FakeService(_FakeBackend()), "decision", 99)
        assert result["status"] == "not_found"

    def test_brain_disabled_fails(self, monkeypatch, cfg):
        be = _FakeBackend()
        be.decision_add("X")

        def stub():
            return None, None, {**cfg, "enabled": False}

        monkeypatch.setattr(brain_runtime, "open_brain_deps", stub)
        result = brain_move.move_to_brain(_FakeService(be), "decision", 1)
        assert result["status"] == "failed"
        assert "disabled" in result["reason"]

    def test_token_missing_fails(self, monkeypatch, tmp_path, cfg):
        be = _FakeBackend()
        be.decision_add("X")
        conn = brain_sync.open_brain_db(str(tmp_path / "b.db"))

        def stub():
            return conn, None, cfg  # client=None

        monkeypatch.setattr(brain_runtime, "open_brain_deps", stub)
        try:
            result = brain_move.move_to_brain(_FakeService(be), "decision", 1)
            assert result["status"] == "failed"
            assert "token" in result["reason"].lower()
        finally:
            conn.close()

    def test_notion_error_keeps_source(self, monkeypatch, tmp_path, cfg):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        be = _FakeBackend()
        be.decision_add("X")
        conn = brain_sync.open_brain_db(str(tmp_path / "b.db"))
        client = _FakeNotionClient(fail_create=True)
        monkeypatch.setattr(
            brain_runtime, "open_brain_deps", lambda: (conn, client, cfg)
        )
        try:
            result = brain_move.move_to_brain(_FakeService(be), "decision", 1)
            assert result["status"] == "failed"
            assert "notion_error" in result["reason"]
            # Source preserved
            assert 1 in be.decisions
        finally:
            conn.close()

    def test_scrub_blocked_keeps_source(self, monkeypatch, tmp_path):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        be = _FakeBackend()
        be.decision_add("Use api-secret-XXXXX-do-not-leak")
        cfg = {
            "enabled": True,
            "project_names": ["api-secret-XXXXX-do-not-leak"],
            "private_url_patterns": [],
            "notion_integration_token_env": "T",
            "database_ids": {
                "decisions": "db-dec",
                "web_cache": "db-wc",
                "patterns": "db-pat",
                "gotchas": "db-got",
            },
        }
        conn = brain_sync.open_brain_db(str(tmp_path / "b.db"))
        client = _FakeNotionClient()
        monkeypatch.setattr(
            brain_runtime, "open_brain_deps", lambda: (conn, client, cfg)
        )
        try:
            result = brain_move.move_to_brain(_FakeService(be), "decision", 1)
            assert result["status"] == "skipped"
            assert result["reason"] == "scrub_blocked"
            assert 1 in be.decisions  # source preserved
        finally:
            conn.close()


# --- to-local -------------------------------------------------------------


class TestMoveToLocal:
    def _seed_brain_decision(self, conn, *, notion_page_id="npg-1", project_hash):
        conn.execute(
            """INSERT INTO brain_decisions(notion_page_id, name, context, decision,
               rationale, tags, stack, date_value, source_project_hash, generalizable,
               last_edited_time, created_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                notion_page_id,
                "Adopt X",
                "ctx",
                "decided X",
                "rat",
                "[]",
                "[]",
                None,
                project_hash,
                1,
                "2026-04-25T10:00:00Z",
                "2026-04-25T10:00:00Z",
            ),
        )
        conn.commit()

    def test_web_cache_refused(self, open_brain_deps):
        result = brain_move.move_to_local(
            _FakeService(_FakeBackend()), "npg-1", "web_cache"
        )
        assert result["status"] == "bad_input"
        assert "web_cache" in result["reason"]

    def test_invalid_category(self, open_brain_deps):
        result = brain_move.move_to_local(
            _FakeService(_FakeBackend()), "npg-1", "manifestos"
        )
        assert result["status"] == "bad_input"

    def test_not_found(self, open_brain_deps):
        result = brain_move.move_to_local(
            _FakeService(_FakeBackend()), "npg-missing", "decisions"
        )
        assert result["status"] == "not_found"

    def test_decision_happy_path_same_project(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        my_hash = brain_config.compute_project_hash("demo")
        self._seed_brain_decision(open_brain_deps["conn"], project_hash=my_hash)
        be = _FakeBackend()
        result = brain_move.move_to_local(_FakeService(be), "npg-1", "decisions")
        assert result["status"] == "ok"
        assert result["category"] == "decisions"
        assert result["local_id"] == 1
        assert "decided X" in be.decisions[1]["decision"]
        # mirror row deleted
        row = (
            open_brain_deps["conn"]
            .execute(
                "SELECT 1 FROM brain_decisions WHERE notion_page_id = ?", ("npg-1",)
            )
            .fetchone()
        )
        assert row is None
        # Notion archive attempted
        assert "npg-1" in open_brain_deps["client"].archive_calls

    def test_cross_project_refused_without_force(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        other_hash = brain_config.compute_project_hash("other-project")
        self._seed_brain_decision(open_brain_deps["conn"], project_hash=other_hash)
        be = _FakeBackend()
        result = brain_move.move_to_local(_FakeService(be), "npg-1", "decisions")
        assert result["status"] == "skipped"
        assert "force" in result["reason"]
        assert be.decisions == {}

    def test_cross_project_accepted_with_force(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        other_hash = brain_config.compute_project_hash("other-project")
        self._seed_brain_decision(open_brain_deps["conn"], project_hash=other_hash)
        be = _FakeBackend()
        result = brain_move.move_to_local(
            _FakeService(be), "npg-1", "decisions", force=True
        )
        assert result["status"] == "ok"
        assert 1 in be.decisions

    def test_keep_source_skips_archive(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        my_hash = brain_config.compute_project_hash("demo")
        self._seed_brain_decision(open_brain_deps["conn"], project_hash=my_hash)
        be = _FakeBackend()
        result = brain_move.move_to_local(
            _FakeService(be), "npg-1", "decisions", keep_source=True
        )
        assert result["status"] == "ok"
        assert result["source_kept"] is True
        # Mirror NOT deleted
        row = (
            open_brain_deps["conn"]
            .execute(
                "SELECT 1 FROM brain_decisions WHERE notion_page_id = ?", ("npg-1",)
            )
            .fetchone()
        )
        assert row is not None
        # No archive call
        assert "npg-1" not in open_brain_deps["client"].archive_calls

    def test_pattern_happy_path(self, open_brain_deps, monkeypatch):
        monkeypatch.setenv("TAUSIK_PROJECT_NAME", "demo")
        my_hash = brain_config.compute_project_hash("demo")
        open_brain_deps["conn"].execute(
            """INSERT INTO brain_patterns(notion_page_id, name, description,
               when_to_use, example, tags, stack, source_project_hash, date_value,
               confidence, last_edited_time, created_time)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "npg-pat-1",
                "Backoff",
                "exp 2^n",
                "on retry",
                "code",
                '["retry"]',
                "[]",
                my_hash,
                None,
                "tested",
                "2026-04-25T10:00:00Z",
                "2026-04-25T10:00:00Z",
            ),
        )
        open_brain_deps["conn"].commit()
        be = _FakeBackend()
        result = brain_move.move_to_local(_FakeService(be), "npg-pat-1", "patterns")
        assert result["status"] == "ok"
        assert be.memory[1]["type"] == "pattern"
        assert be.memory[1]["title"] == "Backoff"
        assert be.memory[1]["tags"] == ["retry"]


# --- helpers / kind→category map ------------------------------------------


def test_kind_to_category_mapping():
    assert brain_move._kind_to_category("decision") == "decisions"
    assert brain_move._kind_to_category("pattern") == "patterns"
    assert brain_move._kind_to_category("gotcha") == "gotchas"
