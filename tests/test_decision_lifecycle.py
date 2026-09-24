"""A decision records what it turned down and what replaced it (decisions-have-no-lifecycle)."""

from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from service_knowledge_aggregates import build_memory_block  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402


@pytest.fixture
def svc(tmp_path):
    s = ProjectService(SQLiteBackend(str(tmp_path / "d.db")))
    yield s
    s.be.close()


def _id(msg: str) -> int:
    return int(re.search(r"Decision #(\d+)", msg).group(1))


def test_rejected_alternatives_are_a_field_and_are_searchable(svc):
    svc.decide("Use SQLite", rejected=["Postgres :: a server for a CLI", "JSON files :: no FTS"])
    svc.decide("Ship weekly")
    hits = svc.decisions(status="all", rejected="postgres")
    assert [h["decision"] for h in hits] == ["Use SQLite"]
    assert "Postgres :: a server for a CLI" in hits[0]["rejected"]


def test_a_decision_without_alternatives_is_recorded_as_before(svc):
    msg = svc.decide("No alternative was on the table")
    assert svc.be.decision_get(_id(msg))["rejected"] is None


def test_superseding_needs_a_reason_and_an_existing_target(svc):
    old = _id(svc.decide("GitHub is the primary"))
    with pytest.raises(ServiceError, match="needs a reason"):
        svc.decide("GitLab is the primary", supersedes=old)
    with pytest.raises(ServiceError, match="not found"):
        svc.decide("GitLab is the primary", rationale="moved", supersedes=999)
    assert len(svc.decisions(status="all")) == 1  # the refused ones wrote nothing


def test_a_superseded_decision_leaves_active_and_stays_findable(svc):
    old = _id(svc.decide("GitHub is the primary", rejected=["GitLab :: slower CI"]))
    new = _id(svc.decide("GitLab is the primary", rationale="CI moved", supersedes=old))
    active = {d["id"] for d in svc.decisions(status="active")}
    superseded = svc.decisions(status="superseded")
    assert old not in active and new in active
    assert [(d["id"], d["superseded_by"]) for d in superseded] == [(old, new)]
    assert old in {d["id"] for d in svc.decisions(status="all")}
    assert [d["id"] for d in svc.decisions(rejected="slower CI")] == [old]
    assert svc.be.decision_get(old) is not None  # never deleted


def test_the_memory_block_does_not_carry_the_superseded_one(svc):
    old = _id(svc.decide("Old way of doing it"))
    svc.decide("New way of doing it", rationale="measured", supersedes=old)
    block = build_memory_block(svc.be)
    assert "New way of doing it" in block and "Old way of doing it" not in block


def test_filters_by_task(svc):
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "t", "T", role="developer", goal="g")
    svc.decide("Linked", task_slug="t")
    svc.decide("Free")
    assert [d["decision"] for d in svc.decisions(task="t")] == ["Linked"]


def test_the_shared_store_refuses_what_it_cannot_hold(svc):
    with pytest.raises(ServiceError, match="shared"):
        svc.decide("Global", to_global=True, rejected=["x :: y"])
    with pytest.raises(ServiceError, match="empty entry"):
        svc.decide("Local", rejected=["  "])
