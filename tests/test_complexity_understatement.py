"""l26-complexity-self-declared: an understated complexity is VISIBLE at close.

The pure `understatement` decision is pinned exhaustively (declared vs implied by
touched-file count), then the task_done integration confirms the detection emits
a supervision event and surfaces a warning — and stays SILENT for honestly
declared tasks so it adds no false noise.
"""

from __future__ import annotations

import os
import sqlite3
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from complexity_understatement import implied_complexity, understatement  # noqa: E402


def _files(n: int) -> list[str]:
    return [f"scripts/f{i}.py" for i in range(n)]


class TestImpliedComplexity:
    def test_boundaries(self):
        # <=3 files -> simple; 4..10 -> medium; >10 -> complex.
        assert implied_complexity(0) == "simple"
        assert implied_complexity(3) == "simple"
        assert implied_complexity(4) == "medium"
        assert implied_complexity(10) == "medium"
        assert implied_complexity(11) == "complex"


class TestUnderstatement:
    def test_simple_touching_many_is_understated(self):
        u = understatement("simple", _files(4))
        assert u == {"declared": "simple", "implied": "medium", "file_count": 4}

    def test_simple_touching_a_lot_implies_complex(self):
        u = understatement("simple", _files(11))
        assert u["implied"] == "complex"

    def test_honest_simple_is_none(self):
        assert understatement("simple", _files(2)) is None
        assert understatement("simple", []) is None

    def test_unset_complexity_treated_as_simple(self):
        # An unset complexity dodges the same gates as 'simple' — same scrutiny.
        assert understatement(None, _files(5)) == {
            "declared": "simple",
            "implied": "medium",
            "file_count": 5,
        }
        assert understatement("", _files(2)) is None

    def test_unknown_label_treated_as_simple(self):
        assert understatement("weird", _files(4)) is not None

    def test_medium_within_ceiling_is_none(self):
        assert understatement("medium", _files(10)) is None

    def test_medium_touching_a_lot_is_understated(self):
        u = understatement("medium", _files(11))
        assert u == {"declared": "medium", "implied": "complex", "file_count": 11}

    def test_complex_is_never_understated(self):
        assert understatement("complex", _files(50)) is None

    def test_none_entries_are_ignored_in_count(self):
        assert understatement("simple", ["a.py", "", "b.py"]) is None  # 2 real files


# --- Integration through the real task_done flow -----------------------------


def _supervision_events(be) -> list[tuple[str, str]]:
    row = be._conn.execute("PRAGMA database_list").fetchone()
    conn = sqlite3.connect(row[2])
    try:
        return conn.execute(
            "SELECT entity_id, action FROM events WHERE entity_type='supervision' ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


class TestMetricSeparation:
    """A detection (supervision WORKED) must never be counted as a bypass
    (supervision was switched off) — they are opposite meanings (l26 review)."""

    def test_bypass_and_detection_counted_separately(self, tmp_path):
        from project_backend import SQLiteBackend

        be = SQLiteBackend(str(tmp_path / "m.db"))
        be.event_add("supervision", "hook", "bypass_skip_hooks")
        be.event_add("supervision", "t1", "complexity_understated", "files=5")
        assert be.supervision_bypasses_summary() == {
            "total": 1,
            "by_action": {"bypass_skip_hooks": 1},
        }
        assert be.supervision_detections_summary() == {
            "total": 1,
            "by_action": {"complexity_understated": 1},
        }
        be.close()


class TestTaskDoneIntegration:
    def _make(self, tmp_path, monkeypatch, complexity):
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TAUSIK_QUIET", "1")
        svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
        svc.task_add(None, "t-cx", "Complexity task")
        svc.task_update(
            "t-cx",
            goal="g",
            acceptance_criteria="1. ok\n2. errors on bad input",
            scope="x.py",
            rollback_plan="git revert",
            complexity=complexity,
        )
        svc.task_start("t-cx")
        return svc

    def test_understated_simple_emits_event_and_warns(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "simple")
        try:
            result = svc.task_done(
                "t-cx", _files(5), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            assert "COMPLEXITY UNDERSTATED" in result
            assert svc.be.task_get("t-cx")["status"] == "done"  # advisory, not blocking
            assert _supervision_events(svc.be) == [("t-cx", "complexity_understated")]
        finally:
            svc.be.close()

    def test_honest_simple_is_silent(self, tmp_path, monkeypatch):
        svc = self._make(tmp_path, monkeypatch, "simple")
        try:
            result = svc.task_done(
                "t-cx", _files(2), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            assert "COMPLEXITY UNDERSTATED" not in result
            assert svc.be.task_get("t-cx")["status"] == "done"
            assert _supervision_events(svc.be) == []
        finally:
            svc.be.close()

    def test_emit_failure_does_not_block_close(self, tmp_path, monkeypatch):
        """Fail-open (gotcha #271): a telemetry error must not crash the close."""
        svc = self._make(tmp_path, monkeypatch, "simple")

        real_event_add = svc.be.event_add

        def _boom(entity_type, *a, **k):
            if entity_type == "supervision":
                raise RuntimeError("db on fire")
            return real_event_add(entity_type, *a, **k)

        monkeypatch.setattr(svc.be, "event_add", _boom)
        try:
            result = svc.task_done(
                "t-cx", _files(5), True, True, evidence="AC verified: 1. ok 2. ok"
            )
            # The warning is still surfaced; only the event write failed, silently.
            assert "COMPLEXITY UNDERSTATED" in result
            assert svc.be.task_get("t-cx")["status"] == "done"
        finally:
            svc.be.close()
