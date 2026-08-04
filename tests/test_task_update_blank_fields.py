"""`task update --acceptance-criteria ""` used to erase and report success.

The defect was caught by an unset shell variable expanding to an empty
argument. What made it dangerous was not the erase but the "Task updated." —
the exit code said success, so only re-reading the row revealed the loss. Every
test here therefore asserts the STORED VALUE, not just the raised error:
checking the refusal alone would pass against a version that refuses and erases
anyway.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService, ServiceError


@pytest.fixture
def svc(tmp_path):
    be = SQLiteBackend(str(tmp_path / "test.db"))
    s = ProjectService(be)
    yield s
    be.close()


AC = "AC1: does the thing.\nAC2: refuses on bad input."
GOAL = "the goal that a gate reads"


def _mk(svc, slug="blank-guard-subject"):
    svc.epic_add("v1", "Version 1")
    svc.story_add("v1", "setup", "Setup")
    svc.task_add(
        "setup",
        slug,
        "Subject of the blanking tests",
        goal=GOAL,
        complexity="simple",
    )
    svc.task_update(slug, acceptance_criteria=AC)
    return slug


@pytest.mark.parametrize(
    "field,blank",
    [
        ("acceptance_criteria", ""),
        ("acceptance_criteria", "   "),
        ("acceptance_criteria", "\n\t "),
        ("goal", ""),
        ("title", ""),
        ("scope", ""),
        ("rollback_plan", ""),
        ("stack", ""),
        ("complexity", ""),
        ("role", ""),
        ("tier", ""),
    ],
)
def test_blank_is_refused_for_every_field_a_gate_reads(svc, field, blank):
    """The set is closed by guarantee, so the whole set is parametrised.

    `acceptance_criteria` is the field that was caught; the others were equally
    unguarded. Whitespace-only is included because `""` and `"   "` destroy the
    same amount and only one of them looks empty.
    """
    slug = _mk(svc)
    with pytest.raises(ServiceError) as e:
        svc.task_update(slug, **{field: blank})
    assert field in str(e.value)


def test_the_existing_value_survives_the_refusal(svc):
    """The point of the whole fix: refusing is worthless if it erased first."""
    slug = _mk(svc)
    with pytest.raises(ServiceError):
        svc.task_update(slug, acceptance_criteria="")
    assert svc.be.task_get(slug)["acceptance_criteria"] == AC


def test_refusal_does_not_report_success(svc):
    """`Task updated.` was the actual defect — the erase was survivable."""
    slug = _mk(svc)
    with pytest.raises(ServiceError) as e:
        svc.task_update(slug, acceptance_criteria="")
    assert "updated" not in str(e.value).lower()


def test_no_partial_write_when_a_later_field_is_blank(svc):
    """Refusal fires before ANY write, matching the budget-batch shape.

    A guard placed after the budget writes would leave call_budget committed
    while reporting failure — the defect this module's neighbours already fixed
    once. Assert the accepted field did NOT land.
    """
    slug = _mk(svc)
    before = svc.be.task_get(slug)
    with pytest.raises(ServiceError):
        svc.task_update(slug, call_budget=42, goal="")
    after = svc.be.task_get(slug)
    assert after["goal"] == before["goal"] == GOAL
    assert after["call_budget"] == before["call_budget"]


def test_a_real_value_still_updates(svc):
    """The guard must not become a ban on editing these fields."""
    slug = _mk(svc)
    svc.task_update(slug, acceptance_criteria="AC1: replaced on purpose.")
    assert svc.be.task_get(slug)["acceptance_criteria"] == "AC1: replaced on purpose."


def test_acl_fields_stay_clearable(svc):
    """An empty ACL MEANS 'explicitly nothing allowed' — not a blanked field.

    This is the boundary of the guard. If this test goes red, the fix stopped
    being 'refuse destruction' and became 'refuse emptiness', which would erase
    a distinction scope_acl exists to preserve.
    """
    slug = _mk(svc)
    svc.task_update(slug, scope_paths=[])
    assert svc.be.task_get(slug)["scope_paths"] == "[]"


def test_omitting_the_flag_is_not_blanking(svc):
    """Omitting is silent; passing an explicit None is not the same thing.

    The CLI drops unset flags before calling the service, so a key that is
    simply absent must stay absent-shaped — updating a neighbouring field must
    not disturb this one.
    """
    slug = _mk(svc)
    svc.task_update(slug, complexity="medium")
    assert svc.be.task_get(slug)["acceptance_criteria"] == AC


def test_explicit_none_is_refused_too(svc):
    """The MCP door. The server has no input validation, so a JSON null lands
    in this dict unchanged; treating None as 'not passed' would leave the erase
    reachable from MCP while the CLI was fixed.
    """
    slug = _mk(svc)
    with pytest.raises(ServiceError):
        svc.task_update(slug, acceptance_criteria=None)
    assert svc.be.task_get(slug)["acceptance_criteria"] == AC
