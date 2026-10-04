"""Behavioral contract for residual-assurance review routing."""

from __future__ import annotations

import json

import pytest

from assurance_policy import evaluate_assurance
from project_backend import SQLiteBackend
from project_service import ProjectService
from review_routing import (
    build_review_route,
    force_deep_route,
    review_record_blockers,
    validate_review_record,
)


LOW = {
    "level": "low",
    "blast_radius": "local",
    "reversibility": "reversible",
}


@pytest.mark.parametrize(
    "assurance, expected_depth, calls, different_model",
    [
        (
            evaluate_assurance(
                profiles=["executable"],
                impact=LOW,
                observed_evidence=["behavior", "rollback", "postconditions"],
            ),
            "L1",
            0,
            False,
        ),
        (
            evaluate_assurance(profiles=["executable"], impact=LOW, observed_evidence=["behavior"]),
            "L2",
            1,
            False,
        ),
        (
            evaluate_assurance(
                profiles=["executable"],
                impact={**LOW, "security_boundary": True},
                observed_evidence=["behavior", "rollback", "postconditions"],
            ),
            "L3",
            1,
            True,
        ),
    ],
)
def test_route_fanout_follows_residual_assurance(assurance, expected_depth, calls, different_model):
    route = build_review_route(assurance)
    assert route["depth"] == expected_depth
    assert route["execution"]["reviewer_invocations"] == calls
    assert route["execution"]["different_model_required"] is different_model


def test_mixed_profiles_retain_the_union_and_executable_gaps():
    assurance = evaluate_assurance(
        profiles=["research", "executable"],
        impact={**LOW, "level": "high"},
        observed_evidence=["reproducibility", "provenance"],
    )
    route = build_review_route(assurance)
    assert route["profiles"] == ["executable", "research"]
    assert {"behavior", "rollback", "postconditions"} <= set(route["residual_gaps"])
    assert route["depth"] == "L3"


@pytest.mark.parametrize(
    "impact",
    [
        {"security_boundary": True},
        {"governance_boundary": True},
        {"privileged": True},
        {"reversibility": "irreversible"},
        {"data_change": "destructive"},
    ],
)
def test_critical_boundaries_keep_the_hard_l3_floor(impact):
    assurance = evaluate_assurance(
        profiles=["executable"],
        impact={**LOW, **impact},
        observed_evidence=["behavior", "rollback", "postconditions"],
    )
    route = build_review_route(assurance)
    assert (route["depth"], route["hard_floor"], route["deep"]) == ("L3", "L3", False)


def test_deep_fanout_needs_an_explicit_or_configured_trigger():
    assurance = evaluate_assurance(
        profiles=["executable"], impact={**LOW, "security_boundary": True}, observed_evidence=[]
    )
    assert build_review_route(assurance)["execution"]["reviewer_invocations"] == 1
    forced = build_review_route(assurance, explicit_deep=True)
    configured = build_review_route(assurance, configured_extreme_floor=True)
    assert forced["deep"] is configured["deep"] is True
    assert forced["execution"]["reviewer_invocations"] == 7


def test_missing_metadata_stays_l2_and_names_inputs():
    route = build_review_route(
        evaluate_assurance(profiles=[], impact={}, observed_evidence=[], metadata_complete=False)
    )
    assert route["depth"] == "L2"
    assert route["missing_inputs"] == [
        "assurance_profiles",
        "assurance_impact.level",
        "assurance_impact.blast_radius",
        "assurance_impact.reversibility",
    ]


def test_l1_and_l2_records_require_available_identities():
    l1 = build_review_route(
        evaluate_assurance(
            profiles=["executable"],
            impact=LOW,
            observed_evidence=["behavior", "rollback", "postconditions"],
        )
    )
    assert "author model" in "; ".join(
        validate_review_record(
            l1,
            run_type="L1",
            author_model=None,
            reviewer_model=None,
            reviewer_context="author",
            reviewer_invocations=0,
        )
    )
    l2 = build_review_route(
        evaluate_assurance(profiles=["executable"], impact=LOW, observed_evidence=[])
    )
    assert "reviewer model" in "; ".join(
        validate_review_record(
            l2,
            run_type="L2",
            author_model="gpt-5.6-sol",
            reviewer_model=None,
            reviewer_context="fresh",
            reviewer_invocations=1,
        )
    )


def test_measured_high_can_raise_an_earlier_l1_route():
    assurance = evaluate_assurance(
        profiles=["executable"],
        impact=LOW,
        observed_evidence=["behavior", "rollback", "postconditions"],
    )
    assert build_review_route(assurance)["depth"] == "L1"
    assert build_review_route(assurance, measured_high=True)["depth"] == "L3"


@pytest.mark.parametrize("run_type", ["L2", "L3"])
def test_stronger_record_cannot_borrow_zero_invocations_from_l1_route(run_type):
    route = build_review_route(
        evaluate_assurance(
            profiles=["executable"],
            impact=LOW,
            observed_evidence=["behavior", "rollback", "postconditions"],
        )
    )
    errors = validate_review_record(
        route,
        run_type=run_type,
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-6-astra",
        reviewer_context="different-model" if run_type == "L3" else "fresh",
        reviewer_invocations=0,
    )
    assert "route requires 1 reviewer invocation(s); recorded 0" in errors


def test_bound_l3_record_with_l1_route_and_zero_invocations_fails_closed(tmp_path):
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.task_add(None, "t", "T")
    current = build_review_route(
        evaluate_assurance(
            profiles=["executable"],
            impact={**LOW, "governance_boundary": True},
            observed_evidence=[],
        )
    )
    stored = build_review_route(
        evaluate_assurance(
            profiles=["executable"],
            impact=LOW,
            observed_evidence=["behavior", "rollback", "postconditions"],
        )
    )
    service.be.review_record(
        "t",
        "L3",
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-6-astra",
        reviewer_context="different-model",
        reviewer_invocations=0,
        route_json=json.dumps(stored),
    )
    assert "route requires 1 reviewer invocation(s); recorded 0" in review_record_blockers(
        service.be._conn, "t", current
    )
    service.be.close()


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"reviewer_available": False}, "unavailable"),
        ({"reviewer_context": "fresh"}, "different-model"),
        ({"reviewer_model": "claude-opus-4-8"}, "same-family"),
        ({"verification_passed": False}, "verification failed"),
        ({"critical_findings": 1}, "HIGH/CRITICAL"),
        ({"high_findings": 1}, "HIGH/CRITICAL"),
        (
            {"substantive_repair": True, "post_repair_verification_passed": False},
            "fresh passing verification",
        ),
    ],
)
def test_l3_negative_cases_never_validate_as_a_lower_or_passing_route(overrides, fragment):
    route = build_review_route(
        evaluate_assurance(
            profiles=["executable"],
            impact={**LOW, "security_boundary": True},
            observed_evidence=[],
        )
    )
    values = {
        "run_type": "L3",
        "author_model": "claude-opus-5-5",
        "reviewer_model": "claude-fable-5-1",
        "reviewer_context": "different-model",
        "reviewer_invocations": 1,
    }
    values.update(overrides)
    assert fragment in "; ".join(validate_review_record(route, **values))


def test_structured_review_record_persists_route_identity_and_available_usage(tmp_path):
    service = ProjectService(SQLiteBackend(str(tmp_path / "review.db")))
    service.epic_add("e", "E")
    service.story_add("e", "s", "S")
    service.task_add("s", "t", "T")
    route = build_review_route(
        evaluate_assurance(profiles=["executable"], impact=LOW, observed_evidence=[])
    )
    rid = service.be.review_record(
        "t",
        "L2",
        profiles_json=json.dumps(route["profiles"]),
        reasons_json=json.dumps(route["reasons"]),
        author_model="claude-opus-5-5",
        reviewer_model="claude-opus-5-5",
        reviewer_context="fresh",
        reviewer_invocations=1,
        usage_json=json.dumps({"event_count": 0, "tokens_total": None}),
        route_json=json.dumps(route),
    )
    row = service.be.review_list(task_slug="t")[0]
    assert row["id"] == rid
    assert row["reviewer_invocations"] == 1
    assert json.loads(row["profiles_json"]) == ["executable"]
    assert json.loads(row["usage_json"])["tokens_total"] is None
    service.be.close()


@pytest.mark.parametrize("stored_kind", ["l2-over-l1", "deep-over-l3"])
def test_a_valid_stronger_record_satisfies_a_cheaper_current_route(tmp_path, stored_kind):
    service = ProjectService(SQLiteBackend(str(tmp_path / f"{stored_kind}.db")))
    service.task_add(None, "t", "T")
    fully_evidenced = evaluate_assurance(
        profiles=["executable"],
        impact=LOW,
        observed_evidence=["behavior", "rollback", "postconditions"],
    )
    if stored_kind == "l2-over-l1":
        current = build_review_route(fully_evidenced)
        stored = build_review_route(
            evaluate_assurance(profiles=["executable"], impact=LOW, observed_evidence=[])
        )
        record = {
            "run_type": "L2",
            "author_model": "gpt-5.6-sol",
            "reviewer_model": "gpt-5.6-sol",
            "reviewer_context": "fresh",
            "reviewer_invocations": 1,
        }
    else:
        current = build_review_route(
            evaluate_assurance(
                profiles=["executable"],
                impact={**LOW, "security_boundary": True},
                observed_evidence=[],
            )
        )
        stored = force_deep_route(current)
        record = {
            "run_type": "L3",
            "author_model": "gpt-5.6-sol",
            "reviewer_model": "gpt-6-astra",
            "reviewer_context": "different-model",
            "reviewer_invocations": 7,
        }
    service.be.review_record("t", route_json=json.dumps(stored), **record)
    assert review_record_blockers(service.be._conn, "t", current) == []
    service.be.close()


@pytest.mark.parametrize("change_kind", ["file", "task-contract"])
def test_review_record_becomes_stale_after_reviewed_state_changes(tmp_path, change_kind):
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    reviewed = tmp_path / "scripts" / "subject.py"
    reviewed.parent.mkdir()
    reviewed.write_text("VALUE = 1\n", encoding="utf-8")
    service.task_add(None, "t", "T")
    service.task_update("t", relevant_files=json.dumps(["scripts/subject.py"]))
    route = build_review_route(
        evaluate_assurance(profiles=["executable"], impact=LOW, observed_evidence=[])
    )
    service.be.review_record(
        "t",
        "L2",
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-5.6-sol",
        reviewer_context="fresh",
        reviewer_invocations=1,
        route_json=json.dumps(route),
    )
    assert review_record_blockers(service.be._conn, "t", route, tmp_path) == []
    if change_kind == "file":
        reviewed.write_text("VALUE = 2\n", encoding="utf-8")
    else:
        service.task_update("t", title="Changed after review")
    assert review_record_blockers(service.be._conn, "t", route, tmp_path) == [
        "review record is stale: task contract or reviewed files changed"
    ]
    service.be.close()


@pytest.mark.parametrize(
    "hard_impact",
    [
        {"security_boundary": True},
        {"governance_boundary": True},
        {"privileged": True},
        {"reversibility": "irreversible"},
        {"data_change": "destructive"},
    ],
    ids=["security", "governance", "privileged", "irreversible", "destructive"],
)
def test_qg2_enforces_explicit_hard_floor_and_rejects_a_lower_record(
    tmp_path, monkeypatch, hard_impact
):
    from risk_model import WEIGHTS
    from tausik_utils import ServiceError

    monkeypatch.chdir(tmp_path)
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.task_add(None, "hard", "Hard")
    service.task_update(
        "hard",
        goal="change governance behavior",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
        scope="scripts/x.py",
        assurance_profiles=["executable"],
        assurance_impact={
            **LOW,
            **hard_impact,
        },
    )
    service.task_start("hard")

    import risk_compute

    monkeypatch.setattr(
        risk_compute,
        "compute_task_risk",
        lambda *_a, **_k: {
            "score": 0.1,
            "level": "low",
            "factors": {name: 0.1 for name in WEIGHTS},
            "weights": dict(WEIGHTS),
            "defaulted": [],
        },
    )
    evidence = "AC verified: 1. behavior test passed 2. invalid input refused"
    with pytest.raises(ServiceError, match="L3 review record is required"):
        service.task_done("hard", None, True, True, evidence=evidence)

    service.be.review_record(
        "hard",
        "L2",
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-5.6-sol",
        reviewer_context="fresh",
        reviewer_invocations=1,
    )
    with pytest.raises(ServiceError, match="route requires L3"):
        service.task_done("hard", None, True, True, evidence=evidence)

    service.be.review_record(
        "hard",
        "L3",
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-6-astra",
        reviewer_context="different-model",
        reviewer_invocations=1,
    )
    assert "completed" in service.task_done("hard", None, True, True, evidence=evidence)
    service.be.close()


def test_qg2_enforces_a_stack_only_hard_floor(tmp_path, monkeypatch):
    from risk_model import WEIGHTS
    from tausik_utils import ServiceError

    class _Registry:
        def assurance_for(self, _stack):
            return {
                "profiles": ["executable"],
                "impact": {**LOW, "security_boundary": True},
                "gate_capabilities": {},
            }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("stack_registry.registry_for_project", lambda _path: _Registry())
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.task_add(None, "stack-hard", "Stack hard", stack="terraform")
    service.task_update(
        "stack-hard",
        goal="change declared stack behavior",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
        scope="main.tf",
    )
    service.task_start("stack-hard")
    import risk_compute

    monkeypatch.setattr(
        risk_compute,
        "compute_task_risk",
        lambda *_a, **_k: {
            "score": 0.1,
            "level": "low",
            "factors": {name: 0.1 for name in WEIGHTS},
            "weights": dict(WEIGHTS),
            "defaulted": [],
        },
    )
    with pytest.raises(ServiceError, match="L3 review record is required"):
        service.task_done(
            "stack-hard",
            None,
            True,
            True,
            evidence="AC verified: 1. behavior passed 2. invalid input refused",
        )
    service.be.close()


def test_qg2_uses_target_project_stack_floor_when_cwd_is_another_project(tmp_path, monkeypatch):
    from risk_model import WEIGHTS
    from tausik_utils import ServiceError

    target = tmp_path / "target"
    stack_dir = target / ".tausik" / "stacks" / "python"
    stack_dir.mkdir(parents=True)
    (stack_dir / "stack.json").write_text(
        json.dumps(
            {
                "name": "python",
                "extends": "builtin:python",
                "assurance_profiles": ["executable"],
                "assurance_impact": {"governance_boundary": True},
            }
        ),
        encoding="utf-8",
    )
    ambient = tmp_path / "ambient"
    (ambient / ".tausik" / "stacks").mkdir(parents=True)
    monkeypatch.chdir(ambient)
    service = ProjectService(SQLiteBackend(str(target / ".tausik" / "tausik.db")))
    service.task_add(None, "target-floor", "Target floor", stack="python")
    service.task_update(
        "target-floor",
        goal="change target project behavior",
        acceptance_criteria="AC-1 works. Negative: invalid input is refused.",
        scope="app.py",
    )
    service.task_start("target-floor")
    import risk_compute

    monkeypatch.setattr(
        risk_compute,
        "compute_task_risk",
        lambda *_a, **_k: {
            "score": 0.1,
            "level": "low",
            "factors": {name: 0.1 for name in WEIGHTS},
            "weights": dict(WEIGHTS),
            "defaulted": [],
        },
    )
    with pytest.raises(ServiceError, match="L3 review record is required"):
        service.task_done(
            "target-floor",
            None,
            True,
            True,
            evidence="AC verified: behavior passed; invalid input refused",
        )
    service.be.close()
