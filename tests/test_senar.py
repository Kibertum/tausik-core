"""Tests for SENAR methodology integration: QG-0, QG-2, metrics, dead ends, explorations."""

from __future__ import annotations

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError


@pytest.fixture
def svc(tmp_path):
    db = str(tmp_path / "test.db")
    be = SQLiteBackend(db)
    return ProjectService(be)


@pytest.fixture
def seeded(svc):
    """Service with epic/story/task for common tests."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t1", "Task 1", goal="Implement login", role="developer")
    svc.task_update(
        "t1",
        acceptance_criteria="1. POST /login returns 200\n2. Invalid creds return 401",
    )
    return svc


class TestQG0ContextGate:
    """SENAR QG-0: task_start blocks without goal + acceptance_criteria."""

    def test_start_without_goal_fails(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1")
        with pytest.raises(ServiceError, match="QG-0"):
            svc.task_start("t1")

    def test_start_with_goal_no_ac_fails(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="Do something")
        with pytest.raises(ServiceError, match="acceptance_criteria"):
            svc.task_start("t1")

    def test_start_with_goal_and_ac_passes(self, seeded):
        msg = seeded.task_start("t1")
        assert "started" in msg

    def test_start_force_bypasses_qg0(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1")
        msg = svc.task_start("t1", _internal_force=True)
        assert "started" in msg


class TestQG0NegativeScenario:
    """SENAR Core Start Gate #3: AC must contain negative scenario."""

    def test_start_ac_without_negative_fails(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="Add button")
        svc.task_update(
            "t1", acceptance_criteria="1. Button is displayed. 2. Button is clickable."
        )
        with pytest.raises(ServiceError, match="negative scenario"):
            svc.task_start("t1")

    def test_start_ac_with_negative_passes(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="Add button")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Button displayed. 2. Returns error on empty input.",
        )
        msg = svc.task_start("t1")
        assert "started" in msg

    def test_start_ac_with_401_passes(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="Add login")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Returns 200 on valid creds. 2. Returns 401 on invalid.",
        )
        msg = svc.task_start("t1")
        assert "started" in msg

    def test_start_ac_with_russian_negative_passes(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="Форма")
        svc.task_update(
            "t1", acceptance_criteria="1. Форма работает. 2. Ошибка при пустом поле."
        )
        msg = svc.task_start("t1")
        assert "started" in msg

    def test_force_bypasses_negative_check(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1", goal="No negative")
        svc.task_update("t1", acceptance_criteria="1. It works.")
        msg = svc.task_start("t1", _internal_force=True)
        assert "started" in msg


class TestQG2ACVerification:
    """SENAR QG-2: task_done requires AC verification when AC exists."""

    def test_done_without_ac_verified_fails(self, seeded):
        seeded.task_start("t1")
        with pytest.raises(ServiceError, match="QG-2"):
            seeded.task_done("t1")

    def test_done_ac_verified_without_evidence_fails(self, seeded):
        """ac_verified alone is not enough — need evidence in notes."""
        seeded.task_start("t1")
        with pytest.raises(ServiceError, match="verification evidence"):
            seeded.task_done("t1", ac_verified=True)

    def test_done_with_evidence_and_ac_verified_passes(self, seeded):
        seeded.task_start("t1")
        seeded.task_log(
            "t1", "AC verified: 1. POST /login returns 200 ✓ 2. Invalid return 401 ✓"
        )
        msg = seeded.task_done("t1", ac_verified=True)
        assert "completed" in msg

    def test_done_no_ac_skips_qg2(self, svc):
        """Tasks without AC should not require --ac-verified."""
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "T1")
        svc.task_start("t1", _internal_force=True)
        msg = svc.task_done("t1")  # no AC set, should pass without ac_verified
        assert "completed" in msg


class TestSENARMetrics:
    """SENAR mandatory metrics: Throughput, Lead Time, FPSR, DER."""

    def test_metrics_structure(self, seeded):
        seeded.session_start()
        seeded.task_start("t1")
        seeded.task_log(
            "t1",
            "AC verified: 1. POST /login returns 200 ✓ 2. Invalid creds return 401 ✓",
        )
        seeded.task_done("t1", ac_verified=True)
        m = seeded.get_metrics()
        assert "throughput" in m
        assert "lead_time_hours" in m
        assert "fpsr" in m
        assert "der" in m
        assert "cycle_time_hours" in m
        assert "knowledge_capture_rate" in m

    def test_fpsr_first_attempt(self, seeded):
        seeded.session_start()
        seeded.task_start("t1")
        seeded.task_log(
            "t1",
            "AC verified: 1. POST /login returns 200 ✓ 2. Invalid creds return 401 ✓",
        )
        seeded.task_done("t1", ac_verified=True)
        m = seeded.get_metrics()
        assert m["fpsr"] == 100.0  # First attempt = 100% FPSR

    def test_der_with_defect(self, seeded):
        seeded.session_start()
        seeded.task_start("t1")
        seeded.task_log(
            "t1",
            "AC verified: 1. POST /login returns 200 ✓ 2. Invalid creds return 401 ✓",
        )
        seeded.task_done("t1", ac_verified=True)
        # Create a defect task linked to t1
        seeded.task_add(
            "s1", "defect-1", "Defect of T1", defect_of="t1", goal="Fix bug"
        )
        seeded.task_update(
            "defect-1",
            acceptance_criteria="1. Bug is fixed. 2. Returns error on invalid input.",
        )
        seeded.task_start("defect-1")
        seeded.task_log(
            "defect-1",
            "Root cause: missing validation. AC verified: 1. Bug is fixed ✓ 2. Returns error on invalid input ✓",
        )
        seeded.task_done("defect-1", ac_verified=True)
        m = seeded.get_metrics()
        assert m["der"] > 0  # 1 parent task with defect / 1 non-defect done task

    def test_throughput(self, seeded):
        seeded.session_start()
        seeded.task_start("t1")
        seeded.task_log(
            "t1",
            "AC verified: 1. POST /login returns 200 ✓ 2. Invalid creds return 401 ✓",
        )
        seeded.task_done("t1", ac_verified=True)
        m = seeded.get_metrics()
        assert m["throughput"] > 0


class TestSessionDurationEnforcement:
    """SENAR Rule 9.2: session duration hard-block at task_start."""

    def test_session_extend(self, svc):
        svc.session_start()
        msg = svc.session_extend(60)
        assert "extended" in msg
        assert "60 min" in msg

    def test_session_extend_cumulative(self, svc):
        svc.session_start()
        svc.session_extend(60)
        msg = svc.session_extend(30)
        # Should be 180 + 60 + 30 = 270
        assert "270 min" in msg

    def test_session_extend_no_session_raises(self, svc):
        with pytest.raises(ServiceError, match="No active session"):
            svc.session_extend()

    def test_session_check_duration_accounts_for_extend(self, svc):
        svc.session_start()
        svc.session_extend(60)
        # Duration check should use extended limit (240), not default (180)
        result = svc.session_check_duration()
        assert result is None  # Session just started, not over any limit


class TestDeadEnds:
    """SENAR Rule 9.4: Dead end documentation."""

    def test_dead_end_creates_memory(self, svc):
        msg = svc.dead_end("Tried bcrypt", "Import fails on Python 3.14")
        assert "documented" in msg
        memories = svc.memory_list("dead_end")
        assert len(memories) == 1
        assert "bcrypt" in memories[0]["title"]
        assert "Approach:" in memories[0]["content"]
        assert "Reason:" in memories[0]["content"]

    def test_dead_end_with_tags(self, svc):
        svc.dead_end("Tried X", "Failed", tags=["auth", "security"])
        memories = svc.memory_list("dead_end")
        assert memories[0]["tags"] is not None

    def test_dead_end_searchable(self, svc):
        svc.dead_end("Tried ChromaDB for RAG", "Too heavy")
        results = svc.memory_search("ChromaDB")
        assert len(results) > 0


class TestExplorations:
    """SENAR Section 5.1: Time-bounded exploration."""

    def test_exploration_start(self, svc):
        msg = svc.exploration_start("Investigating auth patterns")
        assert "started" in msg

    def test_exploration_double_start(self, svc):
        svc.exploration_start("First")
        msg = svc.exploration_start("Second")
        assert "already active" in msg

    def test_exploration_end(self, svc):
        svc.exploration_start("Test")
        msg = svc.exploration_end(summary="Found nothing")
        assert "ended" in msg

    def test_exploration_end_no_active(self, svc):
        with pytest.raises(ServiceError, match="No active exploration"):
            svc.exploration_end()

    def test_exploration_current(self, svc):
        svc.exploration_start("Test", time_limit_min=15)
        exp = svc.exploration_current()
        assert exp is not None
        assert exp["title"] == "Test"
        assert "elapsed_min" in exp
        assert exp["time_limit_min"] == 15

    def test_exploration_end_create_task(self, svc):
        svc.exploration_start("Auth research")
        msg = svc.exploration_end(summary="Need OAuth2 support", create_task=True)
        assert "Task" in msg
        assert "created" in msg

    def test_exploration_end_create_task_requires_summary(self, svc):
        svc.exploration_start("Test")
        with pytest.raises(ServiceError, match="requires --summary"):
            svc.exploration_end(create_task=True)


class TestSessionDuration:
    """SENAR Rule 9.2: Session duration limit."""

    def test_check_duration_no_session(self, svc):
        assert svc.session_check_duration() is None

    def test_check_duration_within_limit(self, svc):
        svc.session_start()
        assert svc.session_check_duration(max_minutes=9999) is None

    def test_check_duration_over_limit(self, svc):
        svc.session_start()
        # v1.3: warning is gated on ACTIVE minutes (gap-based from events table).
        # Backdate started_at AND seed events with sub-threshold gaps so the
        # active-minute sum exceeds the limit.
        svc.be._ex(
            "UPDATE sessions SET started_at='2020-01-01T00:00:00Z' WHERE ended_at IS NULL"
        )
        # Seed 13 events at 5-min intervals → 12 gaps × 5 min = 60 min active
        # which exceeds max_minutes=30 below.
        for n in range(13):
            ts = f"2020-01-01T00:{n * 5:02d}:00Z"
            svc.be._ex(
                "INSERT INTO events(entity_type, entity_id, action, created_at) "
                "VALUES ('test', 'x', 'tick', ?)",
                (ts,),
            )
        warning = svc.session_check_duration(max_minutes=30)
        assert warning is not None
        assert "min" in warning


class TestChecklistTier:
    """SENAR Core Rule 5: Verification checklist with 4 tiers."""

    def test_tier_simple_lightweight(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Simple task", goal="Fix typo", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Typo fixed. 2. No error in display.",
            complexity="simple",
        )
        task = svc.task_show("t1")
        assert svc._determine_checklist_tier(task) == "lightweight"

    def test_tier_medium_standard(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Feature", goal="Add export", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. Export works. 2. Error on empty data.",
            complexity="medium",
        )
        task = svc.task_show("t1")
        assert svc._determine_checklist_tier(task) == "standard"

    def test_tier_auth_auto_high(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add(
            "s1", "t1", "Auth", goal="Add JWT authentication", role="developer"
        )
        svc.task_update(
            "t1",
            acceptance_criteria="1. JWT works. 2. Returns 401 on invalid.",
            complexity="medium",
        )
        task = svc.task_show("t1")
        assert svc._determine_checklist_tier(task) == "high"

    def test_tier_complex_critical(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        svc.task_add("s1", "t1", "Refactor", goal="Rewrite DB layer", role="developer")
        svc.task_update(
            "t1",
            acceptance_criteria="1. DB works. 2. Error on connection fail.",
            complexity="complex",
        )
        task = svc.task_show("t1")
        assert svc._determine_checklist_tier(task) == "critical"


class TestDefectOf:
    """defect_of field for DER tracking."""

    def test_task_add_with_defect_of(self, seeded):
        msg = seeded.task_add("s1", "d1", "Defect", defect_of="t1")
        assert "created" in msg
        task = seeded.task_show("d1")
        assert task["defect_of"] == "t1"

    def test_task_add_defect_of_nonexistent(self, svc):
        svc.epic_add("e1", "E1")
        svc.story_add("e1", "s1", "S1")
        with pytest.raises(ServiceError, match="not found"):
            svc.task_add("s1", "d1", "Defect", defect_of="nonexistent")
