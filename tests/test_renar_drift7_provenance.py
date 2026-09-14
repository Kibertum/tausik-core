"""drift-7 must date a VERIFICATION, not the moment a link was created.

drift7-dates-the-link-not-the-verification (Sortula #49 → our #10, release 1.9).

The detector compared `spec.updated_at` against `task_specs.created_at` — when
the task was LINKED to the requirement. A task finished a day AFTER a SPEC edit
was therefore declared stale and the gate failed on every `task done`. The false
positive also MASKED a real one, which appeared at the consumer only once this
was fixed; that is why both directions are asserted here and neither on its own
would be evidence.

Every layout is built by writing rows and then CALLING the detector.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from renar_drift import detect_provenance_drift  # noqa: E402

# Ordered so the story reads off the constants themselves.
T1_EARLY = "2026-08-01T10:00:00Z"
T2_SPEC_EDIT = "2026-08-02T10:00:00Z"
T3_LATE = "2026-08-03T10:00:00Z"


@pytest.fixture
def svc(tmp_path):
    """REAL schema, never a hand-written copy.

    tests/test_ddl_fixture_parity.py forbids a fixture from declaring a schema
    table itself, and it caught this file doing exactly that. The reasoning is
    the same one this release keeps re-learning: a copy of the schema in a test
    proves the COPY conforms, not production, and it drifts silently — twice
    paid for on `verification_runs`, where twenty tests stayed green while
    every write to a live DB failed a CHECK the hand-written DDL omitted.
    """
    s = ProjectService(SQLiteBackend(str(tmp_path / "drift7.db")))
    yield s
    s.be.close()


def _layout(svc, *, linked_at, spec_updated, completed_at, ran_at=None,
            spec_status="active"):
    """Build the task<->SPEC layout under test through the real schema."""
    svc.epic_add("e1", "Epic 1")
    svc.story_add("e1", "s1", "Story 1")
    svc.task_add("s1", "t", "Task", role="developer", goal="g")
    svc.spec_add("s", "API", "Spec", "v2", status=spec_status)
    svc.spec_link("t", "s", "implements")

    conn = svc.be._conn
    conn.execute(
        "UPDATE task_specs SET created_at = ? WHERE task_slug='t' AND spec_slug='s'",
        (linked_at,),
    )
    conn.execute("UPDATE specs SET updated_at = ? WHERE slug='s'", (spec_updated,))
    conn.execute(
        "UPDATE tasks SET status='done', completed_at = ? WHERE slug='t'", (completed_at,)
    )
    if ran_at is not None:
        conn.execute(
            "INSERT INTO verification_runs "
            "(task_slug, scope, command, exit_code, files_hash, ran_at, no_tests_declared) "
            "VALUES ('t', 'standard', 'pytest', 0, 'h', ?, 0)",
            (ran_at,),
        )
    conn.commit()
    return detect_provenance_drift(conn)


def _kinds(findings):
    return [f["kind"] if isinstance(f, dict) else getattr(f, "kind", None) for f in findings]


class TestTheConsumerLayout:
    def test_a_task_verified_after_the_spec_edit_is_not_stale(self, svc):
        """AC3 — the reported false positive, built exactly as described.

        Linked early, SPEC edited, task verified LAST. The old rule compared the
        edit against the LINK time and flagged it; the verification is in fact
        newer than the requirement, so there is nothing stale here.
        """
        findings = _layout(
            svc,
            linked_at=T1_EARLY,
            spec_updated=T2_SPEC_EDIT,
            completed_at=T3_LATE,
            ran_at=T3_LATE,
        )
        assert findings == [], _kinds(findings)

    def test_a_spec_edited_after_the_verification_is_stale(self, svc):
        """AC4 — the other direction, which must SURVIVE the fix.

        Verified first, SPEC edited afterwards: the verification really does
        predate the requirement. A one-sided experiment cannot tell a fix from
        a detector that was simply switched off, and at the consumer this real
        finding was what the broken version had been hiding.
        """
        findings = _layout(
            svc,
            linked_at=T1_EARLY,
            spec_updated=T3_LATE,
            completed_at=T2_SPEC_EDIT,
            ran_at=T2_SPEC_EDIT,
        )
        assert _kinds(findings) == ["stale-verification"]

    def test_the_link_time_is_no_longer_an_operand(self, svc):
        """The link date is now irrelevant to the verdict, which is the whole
        point. Same verification and same edit, absurdly old link time: the
        answer must not move."""
        findings = _layout(
            svc,
            linked_at="1999-01-01T00:00:00Z",
            spec_updated=T2_SPEC_EDIT,
            completed_at=T3_LATE,
            ran_at=T3_LATE,
        )
        assert findings == []


class TestTheFallbackIsNamed:
    def test_without_a_run_the_completion_time_is_used(self, svc):
        """AC2 — an honest second approximation: a task cannot have been
        verified after it was closed. Closed AFTER the edit, so not stale."""
        findings = _layout(
            svc, linked_at=T1_EARLY, spec_updated=T2_SPEC_EDIT, completed_at=T3_LATE
        )
        assert findings == []

    def test_without_a_run_a_later_edit_is_still_caught(self, svc):
        """The fallback must still be able to say yes, or it is just an off switch."""
        findings = _layout(
            svc, linked_at=T1_EARLY, spec_updated=T3_LATE, completed_at=T2_SPEC_EDIT
        )
        assert _kinds(findings) == ["stale-verification"]

    def test_datable_by_neither_is_reported_not_skipped(self, svc):
        """ "Could not be checked" must not read as "checked and fine"."""
        findings = _layout(svc, linked_at=T1_EARLY, spec_updated=T2_SPEC_EDIT, completed_at=None)
        assert _kinds(findings) == ["undateable-verification"]


class TestBoundaryIsUnchanged:
    def test_equal_instants_are_still_not_flagged(self, svc):
        """AC5 — the compare stays STRICT, and that is a decision, not an
        accident: a spec verified and last-edited in the same instant is not
        stale. Changing strictness silently would be a behaviour change in a
        gate, so it is pinned here."""
        findings = _layout(
            svc,
            linked_at=T1_EARLY,
            spec_updated=T2_SPEC_EDIT,
            completed_at=T2_SPEC_EDIT,
            ran_at=T2_SPEC_EDIT,
        )
        assert findings == []


class TestScopeIsUnchanged:
    def test_a_deprecated_spec_is_not_a_stale_verification(self, svc):
        """Pre-existing promise the fix must not disturb: deprecated specs are
        a settled requirement, reported by `deprecated-requirement` instead."""
        findings = _layout(
            svc,
            linked_at=T1_EARLY,
            spec_updated=T3_LATE,
            completed_at=T2_SPEC_EDIT,
            ran_at=T2_SPEC_EDIT,
            spec_status="deprecated",
        )
        assert _kinds(findings) == []
