"""`--global` routes the write, and a failure to write globally is never a local write.

The last class is the one that matters. Every other property here would survive
a lazy implementation; the fallback property would not. A person who typed
`--global` believes the knowledge is now available everywhere, so a silent
fallback leaves it in one repository while reporting success — a defect
invisible at the moment it is committed and discovered months later, in another
project, as an absence.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_write  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_write.py", "scripts/service_decide.py"]


@pytest.fixture(autouse=True)
def home(monkeypatch, tmp_path):
    monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """A real ProjectService on a throwaway project, so both branches are exercised."""
    from project_backend import SQLiteBackend
    from project_service import ProjectService

    root = tmp_path / "proj"
    (root / ".tausik").mkdir(parents=True)
    monkeypatch.chdir(root)
    monkeypatch.setenv("TAUSIK_DIR", str(root / ".tausik"))
    return ProjectService(SQLiteBackend(str(root / ".tausik" / "tausik.db")))


def _shared_rows(table: str) -> list:
    conn = knowledge_db.connect_knowledge_db(create=False)
    if conn is None:
        return []
    try:
        return conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()


class TestTheFlagRoutesTheWrite:
    """AC1: with the flag it goes shared, without it it goes to the project."""

    def test_memory_without_the_flag_stays_in_the_project(self, svc):
        svc.memory_add("pattern", "локальная", "тело")
        assert _shared_rows("memory") == []
        assert len(svc.memory_list()) == 1

    def test_memory_with_the_flag_goes_to_the_shared_store(self, svc):
        out = svc.memory_add("pattern", "общая", "тело", None, None, True)
        assert "SHARED" in out
        rows = _shared_rows("memory")
        assert len(rows) == 1
        assert rows[0]["title"] == "общая"
        assert svc.memory_list() == [], "the project database was written to as well"

    def test_decision_without_the_flag_stays_in_the_project(self, svc):
        svc.decide("локальное решение", "some-task")
        assert _shared_rows("decisions") == []
        assert len(svc.decisions()) == 1

    def test_decision_with_the_flag_goes_to_the_shared_store(self, svc):
        out = svc.decide("общее решение", None, "обоснование", True)
        assert "SHARED" in out
        rows = _shared_rows("decisions")
        assert len(rows) == 1
        assert rows[0]["decision"] == "общее решение"
        assert svc.decisions() == [], "the project database was written to as well"

    def test_a_task_linked_decision_still_honours_the_flag(self, svc):
        """The one place in this feature where branch ORDER carries the guarantee.

        `record()` has a pre-existing rule — a decision carrying a task_slug is
        project-specific and never leaves — and the shared branch sits ABOVE it.
        Swap the two `if`s, which is an entirely reasonable-looking edit ("a
        decision with a task is always local"), and `--global` on a task-linked
        decision goes silently to the project database: exactly the fallback the
        whole feature promises cannot happen. `memory_add` has no competing
        branch, so this is the only input combination where the promise rests on
        ordering rather than on structure — and it was the only one untested.
        """
        out = svc.decide("решение с задачей", "some-task", "обоснование", True)
        assert "SHARED" in out
        rows = _shared_rows("decisions")
        assert len(rows) == 1
        assert rows[0]["origin_slug"] == "some-task"
        assert svc.decisions() == [], (
            "a task-linked decision with --global fell through to the project "
            "database — the branch order was inverted"
        )

    def test_snippet_goes_to_the_shared_store_and_dedupes(self):
        first = knowledge_write.write_snippet("def f():\n    pass\n", "python")
        again = knowledge_write.write_snippet("def f():\n    pass\n", "python")
        assert "saved" in first
        assert "already" in again
        assert len(_shared_rows("snippets")) == 1


class TestNoPromptAndNoClassifier:
    """AC2: the route is the flag, and nothing else gets a vote."""

    def test_the_universality_hint_does_not_fire_on_the_shared_path(self, svc, monkeypatch):
        """The nudge asks a question the flag has already answered."""
        import brain_universality

        called: list[str] = []
        monkeypatch.setattr(
            brain_universality,
            "emit_universality_hint",
            lambda text: called.append(text),
        )
        svc.memory_add("pattern", "общая", "тело", None, None, True)
        assert called == [], "the shared path consulted the brain classifier"

    def test_the_local_path_still_fires_it(self, svc, monkeypatch):
        """The control: the hint is genuinely reachable, so the test above means something."""
        import brain_universality

        called: list[str] = []
        monkeypatch.setattr(
            brain_universality,
            "emit_universality_hint",
            lambda text: called.append(text),
        )
        svc.memory_add("pattern", "локальная", "тело")
        assert len(called) == 1


class TestAttribution:
    """AC3: a shared row names the project it came from."""

    def test_origin_is_a_label_and_not_the_absolute_root(self, svc):
        """The row says which project, without saying where on disk it lives.

        The absolute root used to be stored here, which put the parent
        directories — client names on a machine like this one — into every row
        of a store readable from every other project.
        """
        svc.memory_add("context", "запись", "тело", None, "some-task", True)
        row = _shared_rows("memory")[0]
        assert not os.path.isabs(row["origin_project"])
        assert "/" not in row["origin_project"] and "\\" not in row["origin_project"]
        assert row["origin_project"].startswith("proj@")
        assert row["origin_slug"] == "some-task"

    def test_origin_survives_being_run_from_a_subdirectory(self, svc, tmp_path, monkeypatch):
        """Attribution follows the project handle, not the shell's cwd."""
        deep = tmp_path / "proj" / "a" / "b"
        deep.mkdir(parents=True)
        monkeypatch.chdir(deep)
        svc.memory_add("context", "из подкаталога", "тело", None, None, True)
        assert _shared_rows("memory")[0]["origin_project"].startswith("proj@")


class TestNoScrubber:
    """AC4: redaction belongs at the Notion boundary, not on this path."""

    def test_content_reaches_the_shared_store_verbatim(self, svc, monkeypatch):
        import brain_scrubbing

        monkeypatch.setattr(
            brain_scrubbing,
            "scrub",
            lambda *a, **k: pytest.fail("the scrubber ran on the shared-write path"),
        )
        secretish = "token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 /Users/real/path"
        svc.memory_add("context", "как есть", secretish, None, None, True)
        assert _shared_rows("memory")[0]["content"] == secretish


class TestAFailedSharedWriteIsNeverALocalWrite:
    """AC5 — the negative scenario, and the reason this task exists as written."""

    def test_an_unwritable_home_raises_and_leaves_the_project_untouched(
        self, svc, monkeypatch, tmp_path
    ):
        # A path whose parent is a FILE cannot be turned into a directory, on
        # every platform — unlike a chmod'd directory, which root ignores and
        # Windows does not honour.
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("x", encoding="utf-8")
        monkeypatch.setenv("TAUSIK_HOME", str(blocker / "nested"))

        with pytest.raises(ServiceError) as e:
            svc.memory_add("pattern", "должна упасть", "тело", None, None, True)

        # Both halves, because either alone would pass a broken implementation.
        assert str(blocker) in str(e.value), "the error does not name the path it failed on"
        assert svc.memory_list() == [], (
            "a failed shared write fell back to the project database — the exact "
            "defect this criterion exists to forbid"
        )

    def test_the_same_holds_for_decisions(self, svc, monkeypatch, tmp_path):
        blocker = tmp_path / "not-a-dir-2"
        blocker.write_text("x", encoding="utf-8")
        monkeypatch.setenv("TAUSIK_HOME", str(blocker / "nested"))

        with pytest.raises(ServiceError):
            svc.decide("должно упасть", None, "обоснование", True)
        assert svc.decisions() == []

    def test_the_error_says_there_was_no_fallback(self, monkeypatch, tmp_path):
        """The message has to tell the reader what did NOT happen, not only what failed."""
        blocker = tmp_path / "not-a-dir-3"
        blocker.write_text("x", encoding="utf-8")
        monkeypatch.setenv("TAUSIK_HOME", str(blocker / "nested"))

        with pytest.raises(ServiceError) as e:
            knowledge_write.write_memory("pattern", "t", "c")
        assert "NOT used as a fallback" in str(e.value)
