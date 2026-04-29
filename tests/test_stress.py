"""Stress tests: 1000 tasks, 100 sessions, bulk operations.

Verifies SQLite backend handles large volumes without errors
or performance degradation.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "stress.db"))
    s = ProjectService(be)
    yield s
    be.close()


class TestStressTasks:
    def test_1000_tasks_creation(self, svc):
        """Create 1000 tasks across 10 stories."""
        svc.epic_add("stress-epic", "Stress Epic")
        for si in range(10):
            svc.story_add("stress-epic", f"story-{si:02d}", f"Story {si}")
            for ti in range(100):
                svc.task_add(
                    f"story-{si:02d}", f"task-{si:02d}-{ti:03d}",
                    f"Task {si}.{ti}", goal=f"Goal for task {si}.{ti}",
                )
        tasks = svc.task_list()
        assert len(tasks) == 1000

    def test_bulk_status_transitions(self, svc):
        """Transition 200 tasks through full lifecycle."""
        svc.epic_add("lifecycle", "Lifecycle")
        svc.story_add("lifecycle", "lc-story", "LC Story")
        for i in range(200):
            svc.task_add("lc-story", f"lc-{i:03d}", f"LC Task {i}")
        for i in range(200):
            svc.task_start(f"lc-{i:03d}", _internal_force=True)
        active = svc.task_list(status="active")
        assert len(active) == 200
        for i in range(200):
            svc.task_done(f"lc-{i:03d}")
        done = svc.task_list(status="done")
        assert len(done) == 200

    def test_fts_search_large_dataset(self, svc):
        """FTS search across 500 tasks with varied content."""
        svc.epic_add("search-epic", "Search")
        svc.story_add("search-epic", "search-story", "Search Story")
        keywords = ["authentication", "database", "frontend", "deployment", "testing"]
        for i in range(500):
            kw = keywords[i % len(keywords)]
            svc.task_add(
                "search-story", f"s-{i:03d}", f"Task about {kw} #{i}",
                goal=f"Implement {kw} feature",
            )
        for kw in keywords:
            results = svc.search(kw)
            assert len(results.get("tasks", [])) >= 20  # limited to 20 by search_all

    def test_roadmap_with_many_entities(self, svc):
        """Roadmap generation with 5 epics, 20 stories, 200 tasks."""
        for ei in range(5):
            svc.epic_add(f"re-{ei}", f"Road Epic {ei}")
            for si in range(4):
                slug = f"rs-{ei}-{si}"
                svc.story_add(f"re-{ei}", slug, f"Road Story {ei}.{si}")
                for ti in range(10):
                    svc.task_add(slug, f"rt-{ei}-{si}-{ti}", f"Road Task {ei}.{si}.{ti}")
        roadmap = svc.get_roadmap()
        assert len(roadmap) == 5
        total_tasks = sum(
            len(s["tasks"]) for e in roadmap for s in e["stories"]
        )
        assert total_tasks == 200


class TestStressSessions:
    def test_100_sessions(self, svc):
        """Create and close 100 sessions."""
        for i in range(100):
            svc.session_start()
            svc.session_end(f"Session {i} summary")
        sessions = svc.session_list(100)
        assert len(sessions) == 100

    def test_session_handoff_chain(self, svc):
        """Chain of 50 sessions with handoffs."""
        for i in range(50):
            svc.session_start()
            svc.session_handoff({
                "completed": [f"task-{i}"],
                "next_steps": [f"task-{i+1}"],
                "session": i,
            })
            svc.session_end(f"Done session {i}")
        last = svc.session_last_handoff()
        assert last["session"] == 49


class TestStressMemory:
    def test_500_memory_entries(self, svc):
        """Create 500 memory entries and search."""
        types = ["pattern", "gotcha", "convention", "context"]
        for i in range(500):
            t = types[i % len(types)]
            svc.memory_add(t, f"Memory {i}", f"Content for memory entry {i}")
        mems = svc.memory_list(n=500)
        assert len(mems) == 500
        patterns = svc.memory_list("pattern", n=500)
        assert len(patterns) == 125  # 500 / 4

    def test_bulk_decisions(self, svc):
        """Create 300 decisions."""
        for i in range(300):
            svc.decide(f"Decision {i}", rationale=f"Rationale {i}")
        decs = svc.decisions(n=300)
        assert len(decs) == 300


class TestStressPerformance:
    def test_status_under_load(self, svc):
        """Status query performance with 500 tasks."""
        svc.epic_add("perf", "Perf")
        svc.story_add("perf", "perf-story", "Perf Story")
        for i in range(500):
            svc.task_add("perf-story", f"p-{i:03d}", f"Perf Task {i}")
        # Mark some tasks active/done
        for i in range(0, 200):
            svc.task_start(f"p-{i:03d}", _internal_force=True)
        for i in range(0, 100):
            svc.task_done(f"p-{i:03d}")
        start = time.time()
        status = svc.get_status()
        elapsed = time.time() - start
        assert elapsed < 1.0  # should be <100ms, 1s is generous
        assert status["task_counts"]["done"] == 100
        assert status["task_counts"]["active"] == 100
        assert status["task_counts"]["planning"] == 300

    def test_metrics_under_load(self, svc):
        """Metrics query with 500 tasks."""
        svc.epic_add("m", "M")
        svc.story_add("m", "ms", "MS")
        for i in range(500):
            svc.task_add("ms", f"m-{i:03d}", f"Metric Task {i}")
        for i in range(100):
            svc.task_start(f"m-{i:03d}", _internal_force=True)
            svc.task_done(f"m-{i:03d}")
        start = time.time()
        metrics = svc.get_metrics()
        elapsed = time.time() - start
        assert elapsed < 1.0
        assert metrics["tasks_done"] == 100
        assert metrics["completion_pct"] == 20.0
