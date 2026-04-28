"""Edge case tests — boundary values, unicode, validation limits."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from tausik_utils import ServiceError, validate_content, validate_length, validate_slug
from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """Force brain disabled so decide() doesn't hit the real project's enabled
    brain config (which would route writes to Notion instead of local)."""
    import brain_config

    monkeypatch.setattr(brain_config, "load_brain", lambda: {"enabled": False})
    db_path = os.path.join(str(tmp_path), "tausik.db")
    be = SQLiteBackend(db_path)
    s = ProjectService(be)
    s.epic_add("e1", "Epic")
    s.story_add("e1", "s1", "Story")
    return s


# --- Slug validation ---


class TestSlugValidation:
    def test_slug_max_length_ok(self):
        validate_slug("a" * 64)  # exactly at limit

    def test_slug_over_max_length(self):
        with pytest.raises(ValueError, match="max 64"):
            validate_slug("a" * 65)

    def test_slug_empty(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("")

    def test_slug_starts_with_dash(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("-bad")

    def test_slug_uppercase(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("BadSlug")

    def test_slug_spaces(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("bad slug")

    def test_slug_unicode(self):
        with pytest.raises(ValueError, match="Invalid slug"):
            validate_slug("задача")

    def test_slug_single_char(self):
        validate_slug("a")  # minimal valid slug

    def test_slug_with_numbers(self):
        validate_slug("task-123-abc")


# --- Title/content validation ---


class TestLengthValidation:
    def test_title_max_length(self):
        validate_length("title", "x" * 512)  # at limit

    def test_title_over_max(self):
        with pytest.raises(ValueError, match="max 512"):
            validate_length("title", "x" * 513)

    def test_content_max(self):
        validate_content("content", "x" * 100_000)

    def test_content_over_max(self):
        with pytest.raises(ValueError, match="max 100000"):
            validate_content("content", "x" * 100_001)

    def test_content_none_ok(self):
        validate_content("content", None)  # None is valid

    def test_content_empty_ok(self):
        validate_content("content", "")  # Empty is valid


# --- Unicode in data ---


class TestUnicode:
    def test_unicode_epic_title(self, svc):
        svc.epic_add("unicode-ep", "Юникод эпик 🚀")
        epic = svc.be.epic_get("unicode-ep")
        assert epic["title"] == "Юникод эпик 🚀"

    def test_unicode_task_title(self, svc):
        svc.task_add(
            "s1",
            "unicode-task",
            "Задача на кириллице",
            goal="Цель задачи",
            role="developer",
        )
        task = svc.task_show("unicode-task")
        assert task["title"] == "Задача на кириллице"
        assert task["goal"] == "Цель задачи"

    def test_unicode_memory(self, svc):
        svc.memory_add("pattern", "Паттерн", "Контент на русском")
        results = svc.be.memory_list()
        assert results[0]["title"] == "Паттерн"

    def test_unicode_decision(self, svc):
        svc.decide("Решение: использовать SQLite", rationale="Нет зависимостей")
        decisions = svc.decisions()
        assert "SQLite" in decisions[0]["decision"]

    def test_unicode_search(self, svc):
        svc.memory_add("pattern", "Авторизация", "JWT токены для аутентификации")
        results = svc.memory_search("авторизация")
        assert len(results) >= 1


# --- FTS5 special characters ---


class TestFTS5EdgeCases:
    def test_search_with_quotes(self, svc):
        svc.memory_add("pattern", "Test", "Content")
        # Should not crash
        results = svc.search('test"quote')
        assert isinstance(results, dict)

    def test_search_with_parens(self, svc):
        results = svc.search("test()")
        assert isinstance(results, dict)

    def test_search_with_asterisk(self, svc):
        results = svc.search("test*")
        assert isinstance(results, dict)

    def test_search_only_special_chars(self, svc):
        results = svc.search('"*()^:')
        assert isinstance(results, dict)

    def test_search_phrase_in_quotes(self, svc):
        svc.memory_add(
            "pattern",
            "Connection pooling",
            "Always use connection pools for PostgreSQL databases",
        )
        svc.memory_add(
            "pattern", "Pool maintenance", "Clean the swimming pool regularly"
        )
        results = svc.search('"connection pools"', "memory")
        assert len(results.get("memory", [])) >= 1
        # Phrase match should find "connection pools"
        assert any(
            "connection" in r["content"].lower() for r in results.get("memory", [])
        )

    def test_search_mixed_phrase_and_words(self, svc):
        svc.memory_add("pattern", "Auth patterns", "Use JWT tokens for authentication")
        results = svc.search('JWT "authentication"', "memory")
        assert isinstance(results, dict)


# --- Empty/boundary operations ---


class TestBoundaryOperations:
    def test_task_add_minimal(self, svc):
        """Task with only required fields."""
        svc.task_add("s1", "minimal", "Minimal task")
        task = svc.task_show("minimal")
        assert task["status"] == "planning"
        assert task["role"] is None
        assert task["complexity"] is None

    def test_empty_task_list(self, svc):
        tasks = svc.task_list(status="done")
        assert tasks == []

    def test_session_double_start(self, svc):
        result1 = svc.session_start()
        result2 = svc.session_start()
        assert "already active" in result2

    def test_session_end_without_start(self, svc):
        with pytest.raises(ServiceError, match="No active session"):
            svc.session_end()

    def test_task_done_already_done(self, svc):
        svc.task_add("s1", "t1", "Task", role="developer")
        svc.task_start("t1", _internal_force=True)
        svc.task_done("t1")
        with pytest.raises(ServiceError, match="already done"):
            svc.task_done("t1")

    def test_invalid_status_in_update(self, svc):
        svc.task_add("s1", "t1", "Task", role="developer")
        with pytest.raises(ServiceError, match="Invalid status"):
            svc.task_update("t1", status="invalid")

    def test_invalid_complexity_in_add(self, svc):
        with pytest.raises(ServiceError, match="Invalid complexity"):
            svc.task_add("s1", "t1", "Task", complexity="huge")

    def test_free_text_role_in_add(self, svc):
        """v2.0: roles are free-text, any string is valid."""
        result = svc.task_add("s1", "t1", "Task", role="manager")
        assert "created" in result.lower()
