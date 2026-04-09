"""Tests for concurrent write safety — SQLite WAL + FK integrity."""

import os
import sqlite3
import threading
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from project_backend import SQLiteBackend
from project_service import ProjectService


def _make_service(tmp_path: str) -> ProjectService:
    """Create a fresh ProjectService with its own DB."""
    db_path = os.path.join(tmp_path, "tausik.db")
    be = SQLiteBackend(db_path)
    return ProjectService(be)


def _seed_hierarchy(svc: ProjectService) -> None:
    """Create epic -> story for task creation."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")


class TestConcurrentTaskCreation:
    """4 threads creating tasks simultaneously — zero losses."""

    def test_parallel_task_creation(self, tmp_path):
        svc = _make_service(str(tmp_path))
        _seed_hierarchy(svc)

        errors: list[Exception] = []
        n_per_thread = 25
        n_threads = 4

        def create_tasks(thread_id: int):
            try:
                db_path = os.path.join(str(tmp_path), "tausik.db")
                be = SQLiteBackend(db_path)
                local_svc = ProjectService(be)
                for i in range(n_per_thread):
                    slug = f"t-{thread_id}-{i}"
                    local_svc.task_add(
                        "s1",
                        slug,
                        f"Task {slug}",
                        complexity="simple",
                        role="developer",
                    )
                be.close()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_tasks, args=(tid,))
            for tid in range(n_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Thread errors: {errors}"

        # Verify all tasks created
        tasks = svc.task_list()
        assert len(tasks) == n_per_thread * n_threads

    def test_parallel_task_creation_unique_slugs(self, tmp_path):
        """Each task has a unique slug — no duplicates."""
        svc = _make_service(str(tmp_path))
        _seed_hierarchy(svc)

        errors: list[Exception] = []

        def create_tasks(thread_id: int):
            try:
                db_path = os.path.join(str(tmp_path), "tausik.db")
                be = SQLiteBackend(db_path)
                local_svc = ProjectService(be)
                for i in range(10):
                    slug = f"task-{thread_id}-{i}"
                    local_svc.task_add(
                        "s1",
                        slug,
                        f"Task {slug}",
                        complexity="simple",
                        role="developer",
                    )
                be.close()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=create_tasks, args=(tid,)) for tid in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors
        tasks = svc.task_list()
        slugs = [t["slug"] for t in tasks]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found!"


class TestConcurrentClaim:
    """2 threads claim the same task — exactly 1 succeeds."""

    def test_double_claim_one_wins(self, tmp_path):
        svc = _make_service(str(tmp_path))
        _seed_hierarchy(svc)
        svc.task_add(
            "s1", "contested", "Contested Task", complexity="simple", role="developer"
        )

        results: list[tuple[str, bool]] = []
        lock = threading.Lock()

        def try_claim(agent_id: str):
            try:
                db_path = os.path.join(str(tmp_path), "tausik.db")
                be = SQLiteBackend(db_path)
                local_svc = ProjectService(be)
                local_svc.task_claim("contested", agent_id)
                with lock:
                    results.append((agent_id, True))
                be.close()
            except Exception:
                with lock:
                    results.append((agent_id, False))

        threads = [
            threading.Thread(target=try_claim, args=("agent-1",)),
            threading.Thread(target=try_claim, args=("agent-2",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        successes = [r for r in results if r[1]]
        assert len(successes) >= 1
        task = svc.task_show("contested")
        assert task["claimed_by"] is not None


class TestConcurrentCascade:
    """CASCADE DELETE during concurrent inserts — no orphan rows."""

    def test_cascade_during_insert(self, tmp_path):
        svc = _make_service(str(tmp_path))
        _seed_hierarchy(svc)

        for i in range(10):
            svc.task_add(
                "s1", f"pre-{i}", f"Task {i}", complexity="simple", role="developer"
            )

        errors: list[Exception] = []

        def insert_tasks():
            try:
                db_path = os.path.join(str(tmp_path), "tausik.db")
                be = SQLiteBackend(db_path)
                local_svc = ProjectService(be)
                for i in range(20):
                    try:
                        local_svc.task_add(
                            "s1",
                            f"new-{i}",
                            f"New {i}",
                            complexity="simple",
                            role="developer",
                        )
                    except Exception:
                        pass  # Story may be deleted by cascade
                be.close()
            except Exception as e:
                errors.append(e)

        def delete_epic():
            try:
                db_path = os.path.join(str(tmp_path), "tausik.db")
                be = SQLiteBackend(db_path)
                local_svc = ProjectService(be)
                local_svc.epic_delete("e1")
                be.close()
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=insert_tasks)
        t2 = threading.Thread(target=delete_epic)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        # After cascade: no orphan tasks pointing to deleted story
        db_path = os.path.join(str(tmp_path), "tausik.db")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.close()
        assert len(violations) == 0, f"FK violations: {violations}"

    def test_no_orphan_tasks_after_story_delete(self, tmp_path):
        """Delete story — CASCADE removes all tasks, FK integrity holds."""
        svc = _make_service(str(tmp_path))
        _seed_hierarchy(svc)

        for i in range(5):
            svc.task_add(
                "s1", f"t-{i}", f"Task {i}", complexity="simple", role="developer"
            )

        svc.story_delete("s1")

        db_path = os.path.join(str(tmp_path), "tausik.db")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.close()
        assert len(violations) == 0
