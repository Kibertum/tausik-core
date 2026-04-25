"""Tests for agent-native planning units (call_budget / call_actual / tier).

Schema migration v17 + helpers in backend_crud.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_crud import derive_tier_from_budget
from backend_schema import SCHEMA_VERSION
from project_backend import SQLiteBackend


@pytest.fixture
def db(tmp_path):
    be = SQLiteBackend(str(tmp_path / "agent_units.db"))
    yield be
    be.close()


def _seed_task(db, slug: str = "t1") -> None:
    """Insert minimal epic→story→task chain for helper tests."""
    db._ex(
        "INSERT INTO epics(slug,title,status,created_at) VALUES(?,?,?,?)",
        ("e1", "Epic 1", "active", "2026-04-25T00:00:00Z"),
    )
    db._ex(
        "INSERT INTO stories(epic_id,slug,title,status,created_at) VALUES(?,?,?,?,?)",
        (1, "s1", "Story 1", "open", "2026-04-25T00:00:00Z"),
    )
    db._ex(
        "INSERT INTO tasks(story_id,slug,title,status,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?)",
        (1, slug, "Task", "planning", "2026-04-25T00:00:00Z", "2026-04-25T00:00:00Z"),
    )


class TestSchemaV17:
    def test_schema_version_at_least_17(self):
        assert SCHEMA_VERSION >= 17

    def test_columns_present(self, db):
        cols = {row["name"] for row in db._q("PRAGMA table_info(tasks)")}
        assert "call_budget" in cols
        assert "call_actual" in cols
        assert "tier" in cols

    def test_tier_check_constraint(self, db):
        _seed_task(db)
        with pytest.raises(sqlite3.IntegrityError):
            db._ex(
                "UPDATE tasks SET tier=? WHERE slug='t1'",
                ("bogus",),
            )

    def test_tier_accepts_known_labels(self, db):
        _seed_task(db)
        for label in ("trivial", "light", "moderate", "substantial", "deep"):
            db._ex("UPDATE tasks SET tier=? WHERE slug='t1'", (label,))
            row = db._q1("SELECT tier FROM tasks WHERE slug='t1'")
            assert row["tier"] == label

    def test_tier_accepts_null(self, db):
        _seed_task(db)
        db._ex("UPDATE tasks SET tier=NULL WHERE slug='t1'")
        row = db._q1("SELECT tier FROM tasks WHERE slug='t1'")
        assert row["tier"] is None


class TestDeriveTier:
    @pytest.mark.parametrize(
        "budget,expected",
        [
            (None, None),
            (0, None),
            (1, "trivial"),
            (10, "trivial"),
            (11, "light"),
            (25, "light"),
            (26, "moderate"),
            (60, "moderate"),
            (61, "substantial"),
            (150, "substantial"),
            (151, "deep"),
            (400, "deep"),
            (401, "deep"),
            (10_000, "deep"),
        ],
    )
    def test_boundaries(self, budget, expected):
        assert derive_tier_from_budget(budget) == expected


class TestTaskSetCallBudget:
    def test_sets_budget_and_derives_tier(self, db):
        _seed_task(db)
        assert db.task_set_call_budget("t1", 30) is True
        row = db._q1("SELECT call_budget, tier FROM tasks WHERE slug='t1'")
        assert row["call_budget"] == 30
        assert row["tier"] == "moderate"

    def test_clears_with_none(self, db):
        _seed_task(db)
        db.task_set_call_budget("t1", 50)
        assert db.task_set_call_budget("t1", None) is True
        row = db._q1("SELECT call_budget, tier FROM tasks WHERE slug='t1'")
        assert row["call_budget"] is None
        assert row["tier"] is None

    def test_negative_rejected(self, db):
        _seed_task(db)
        with pytest.raises(ValueError):
            db.task_set_call_budget("t1", -1)

    def test_unknown_slug_returns_false(self, db):
        assert db.task_set_call_budget("nope", 10) is False

    def test_updates_updated_at(self, db):
        _seed_task(db)
        before = db._q1("SELECT updated_at FROM tasks WHERE slug='t1'")["updated_at"]
        db.task_set_call_budget("t1", 5)
        after = db._q1("SELECT updated_at FROM tasks WHERE slug='t1'")["updated_at"]
        assert after >= before


class TestTaskSetCallActual:
    def test_sets_actual_without_changing_tier(self, db):
        _seed_task(db)
        db.task_set_call_budget("t1", 30)  # tier='moderate'
        assert db.task_set_call_actual("t1", 80) is True
        row = db._q1("SELECT call_actual, tier FROM tasks WHERE slug='t1'")
        assert row["call_actual"] == 80
        # Tier reflects PLAN, not actual — must remain 'moderate'.
        assert row["tier"] == "moderate"

    def test_clears_with_none(self, db):
        _seed_task(db)
        db.task_set_call_actual("t1", 42)
        db.task_set_call_actual("t1", None)
        row = db._q1("SELECT call_actual FROM tasks WHERE slug='t1'")
        assert row["call_actual"] is None

    def test_negative_rejected(self, db):
        _seed_task(db)
        with pytest.raises(ValueError):
            db.task_set_call_actual("t1", -5)

    def test_unknown_slug_returns_false(self, db):
        assert db.task_set_call_actual("nope", 10) is False


class TestBackwardsCompat:
    def test_existing_task_works_without_units(self, db):
        _seed_task(db)
        row = db._q1("SELECT call_budget, call_actual, tier FROM tasks WHERE slug='t1'")
        assert row["call_budget"] is None
        assert row["call_actual"] is None
        assert row["tier"] is None

    def test_task_get_returns_full_row(self, db):
        _seed_task(db)
        task = db.task_get("t1")
        assert task is not None
        # Columns present even when NULL.
        assert "call_budget" in task
        assert "call_actual" in task
        assert "tier" in task
