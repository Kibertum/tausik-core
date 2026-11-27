"""TB-009: Codex L3 conformance matrix + infrastructure receipt preserves budget."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from review_cohort_request import execute_cohort_request
from review_l3_preflight import (
    READONLY_READ_PROBES,
    READONLY_WRITE_PROBES,
    RECEIPT_KIND,
    assess_read_probe_results,
)

AUTHOR = "gpt-5.6-sol"
REVIEWER = "gpt-6-astra"


@pytest.fixture
def cohort_svc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("review_cohort._head", lambda _root: "fixture-head")
    # Enforced Codex-like host: tools look read-only, but probes show reads blocked.
    cfg = {
        "review": {
            "l3_host": {
                "tools": ["Read", "Grep", "Bash"],
                "read_probe_results": {
                    **{name: False for name in READONLY_READ_PROBES},
                    **{name: False for name in READONLY_WRITE_PROBES},
                },
            }
        }
    }
    monkeypatch.setattr("project_config.load_config", lambda *a, **k: cfg)
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    path = tmp_path / "src" / "a.py"
    path.parent.mkdir(exist_ok=True)
    path.write_text("VALUE = 'a'\n", encoding="utf-8")
    svc.task_add("s", "a", "A")
    svc.task_update(
        "a",
        goal="change a",
        acceptance_criteria="AC-1: behavior is correct. AC-2: invalid input is refused.",
        scope="src/a.py",
        rollback_plan="git revert",
        relevant_files=json.dumps(["src/a.py"]),
        assurance_profiles=["executable"],
        assurance_impact={
            "level": "high",
            "blast_radius": "local",
            "reversibility": "reversible",
        },
    )
    svc.task_start("a")
    svc.be._conn.execute("UPDATE tasks SET started_model_id=? WHERE slug=?", (AUTHOR, "a"))
    svc.be._conn.commit()
    svc.task_log("a", "AC-1: ✓ behavior exercised")
    yield svc
    svc.be.close()


def test_powershell_read_matrix_documents_required_probes():
    """AC-1: Windows PowerShell / rg / type are the documented read side."""
    assert "Get-Content" in READONLY_READ_PROBES
    assert "rg" in READONLY_READ_PROBES
    assert "cmd /c type" in READONLY_READ_PROBES
    blocked = assess_read_probe_results({name: False for name in READONLY_READ_PROBES})
    assert not blocked.ok
    allowed = assess_read_probe_results(
        {
            **{name: True for name in READONLY_READ_PROBES},
            **{name: False for name in READONLY_WRITE_PROBES},
        }
    )
    assert allowed.ok


def test_open_reports_delegation_and_blocked_capability(cohort_svc):
    out, _ = execute_cohort_request(cohort_svc, {"action": "open", "tasks": ["a"], "json": True})
    assert "Author model:" in out["delegation"]
    assert AUTHOR in out["delegation"]
    assert out["l3_capability"]["enforced"] is True
    assert out["l3_capability"]["ok"] is False
    assert out["l3_capability"]["receipt_kind"] == RECEIPT_KIND
    assert "INFRASTRUCTURE" in out["next"]


def test_infrastructure_blocked_preserves_round_budget(cohort_svc):
    opened, _ = execute_cohort_request(cohort_svc, {"action": "open", "tasks": ["a"], "json": True})
    digest = opened["packet"]["packet_digest"]
    cid = opened["cohort_id"]
    assert opened["rounds"] == "0/2"

    with pytest.raises(ValueError, match=RECEIPT_KIND):
        execute_cohort_request(
            cohort_svc,
            {
                "action": "record",
                "cohort_id": cid,
                "round": 1,
                "results": [
                    {
                        "task": "a",
                        "high": 1,
                        "critical": 0,
                        "warnings": 0,
                        "dependency_map_complete": True,
                    }
                ],
                "packet_digest": digest,
                "author_model": AUTHOR,
                "reviewer_model": REVIEWER,
                "json": True,
            },
        )

    infra, _ = execute_cohort_request(
        cohort_svc,
        {
            "action": "infrastructure-blocked",
            "cohort_id": cid,
            "round": 1,
            "packet_digest": digest,
            "reason": "Codex read-only policy blocked Get-Content/rg",
            "code": "L3_READONLY_POLICY_BLOCKS_READS",
            "detail": "Windows PowerShell",
            "json": True,
        },
    )
    assert infra["receipt_kind"] == RECEIPT_KIND
    assert infra["budget_preserved"] is True
    assert infra["rounds"] == "0/2"
    assert infra["state"] == "open"
    row = cohort_svc.be._q1(
        "SELECT code, round_number FROM review_cohort_infrastructure_events WHERE cohort_pk=?",
        (cid,),
    )
    assert row["code"] == "L3_READONLY_POLICY_BLOCKS_READS"
    assert int(row["round_number"]) == 1
    live = cohort_svc.be._q1("SELECT current_round, state FROM review_cohorts WHERE id=?", (cid,))
    assert int(live["current_round"]) == 0
    assert live["state"] == "open"


def test_write_capable_host_must_not_be_l3_pass(cohort_svc, monkeypatch):
    """Negative: write-capable surface stays infrastructure, never product green."""
    cfg = {"review": {"l3_host": {"tools": ["Read", "Write", "Grep"]}}}
    monkeypatch.setattr("project_config.load_config", lambda *a, **k: cfg)
    opened, _ = execute_cohort_request(cohort_svc, {"action": "open", "tasks": ["a"], "json": True})
    assert opened["l3_capability"]["ok"] is False
    with pytest.raises(ValueError, match=RECEIPT_KIND):
        execute_cohort_request(
            cohort_svc,
            {
                "action": "record",
                "cohort_id": opened["cohort_id"],
                "round": 1,
                "results": [
                    {
                        "task": "a",
                        "high": 0,
                        "critical": 0,
                        "warnings": 0,
                        "dependency_map_complete": True,
                    }
                ],
                "packet_digest": opened["packet"]["packet_digest"],
                "author_model": AUTHOR,
                "reviewer_model": REVIEWER,
                "json": True,
            },
        )
