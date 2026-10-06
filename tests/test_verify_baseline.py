"""r1112-verification-cohort-contract — the reproducible verify-cost baseline.

Cohorts are story-scoped 2h windows; the baseline must bucket 1 / 2 / 5+
correctly and count invocations and fallback reasons from real rows.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from verify_baseline import cohort_baseline


def _seed(be, story_slugs):
    be.epic_add("e", "E")
    for i, (story, members) in enumerate(story_slugs):
        be.story_add("e", story, f"Story {i}")
        for j, slug in enumerate(members):
            be.task_add(story, slug, "T", goal="g", role="developer")
            be._conn.execute(
                "INSERT INTO verification_runs(task_slug, scope, command, exit_code, duration_ms, "
                "files_hash, declared_scope_status, ran_at) VALUES (?,?,?,?,?,?,?,?)",
                (
                    slug,
                    "manual",
                    "verify",
                    0,
                    1000 + j,
                    "h1",
                    "complete",
                    f"2026-10-0{i + 1}T10:0{j}:00Z",
                ),
            )
    be._conn.commit()


def _be(tmp_path):
    b = SQLiteBackend(str(tmp_path / "vb.db"))
    return b


def test_buckets_and_invocations(tmp_path):
    be = _be(tmp_path)
    try:
        _seed(
            be,
            [
                ("s-solo", ["solo"]),  # 1 task, 1 run
                ("s-pair", ["p1", "p2"]),  # 2 tasks, 2 runs
                ("s-big", ["b1", "b2", "b3", "b4", "b5"]),  # 5 tasks, 5 runs
            ],
        )
        # A duplicate run on the solo task: re-pay without a new task.
        be._conn.execute(
            "INSERT INTO verification_runs(task_slug, scope, command, exit_code, duration_ms, "
            "files_hash, declared_scope_status, ran_at) VALUES (?,?,?,?,?,?,?,?)",
            ("solo", "manual", "verify", 0, 500, "h1", "under-declared", "2026-10-01T10:05:00Z"),
        )
        be._conn.commit()
        stats = cohort_baseline(be.db_path)
        assert stats["cohort-of-1"]["cohorts"] == 1
        assert stats["cohort-of-1"]["invocations_paid"] == 2
        assert stats["cohort-of-2"]["cohorts"] == 1
        assert stats["cohort-of-2"]["invocations_paid"] == 2
        assert stats["cohort-of-5+"]["cohorts"] == 1
        assert stats["cohort-of-5+"]["tasks"] == 5
        assert stats["cohort-of-5+"]["invocations_paid"] == 5
        assert stats["cohort-of-1"]["fallback_reasons"] == {"complete": 1, "under-declared": 1}
    finally:
        be.close()


def test_empty_db_buckets_are_zero_not_crash(tmp_path):
    be = _be(tmp_path)
    try:
        stats = cohort_baseline(be.db_path)
        for name in ("cohort-of-1", "cohort-of-2", "cohort-of-5+"):
            assert stats[name]["cohorts"] == 0
            assert stats[name]["invocations_paid"] == 0
    finally:
        be.close()
