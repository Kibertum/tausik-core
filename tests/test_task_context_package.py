"""Bounded task context keeps intent whole and optional retrieval explicit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from task_context_package import build_task_context_package


@pytest.fixture
def svc(tmp_path):
    service = ProjectService(SQLiteBackend(str(tmp_path / "t.db")))
    service.epic_add("e", "E")
    service.story_add("e", "s", "S")
    service.task_add("s", "work", "Work", complexity="medium")
    service.task_update(
        "work",
        goal="ship behavior",
        acceptance_criteria="AC-1 works. Negative: malformed input is refused.",
        scope="src",
        scope_exclude="secrets",
        scope_paths=["scripts/a.py"],
        relevant_files=json.dumps(["scripts/a.py", "tests/test_a.py"]),
        rollback_plan="git revert",
    )
    yield service
    service.be.close()


def test_package_carries_required_intent_and_commands(svc):
    package = build_task_context_package(svc, "work")
    required = package["required"]
    assert required["goal"] == "ship behavior"
    assert "Negative:" in required["acceptance_criteria"]
    assert required["scope_paths"] == ["scripts/a.py"]
    assert required["relevant_files"] == ["scripts/a.py", "tests/test_a.py"]
    assert required["plan"] == []
    assert required["verification"]["verify"].endswith("--task work")
    assert required["review_route"]["depth"] == "L2"
    assert "assurance_profiles" in required["review_route"]["missing_inputs"]
    assert package["bytes"] <= package["max_bytes"]
    encoded = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert package["bytes"] == len(encoded.encode())


def test_package_exposes_residual_assurance_without_fabricating_l1(svc):
    svc.task_update(
        "work",
        assurance_profiles=["declarative"],
        assurance_impact={
            "level": "low",
            "blast_radius": "local",
            "reversibility": "reversible",
        },
    )
    assurance = build_task_context_package(svc, "work")["required"]["assurance"]
    assert assurance["profiles"] == ["declarative"]
    assert assurance["observed_evidence"] == []
    assert assurance["depth"] == "L2"
    assert "behavior" in assurance["residual_gaps"]
    route = build_task_context_package(svc, "work")["required"]["review_route"]
    assert route["depth"] == "L2"
    assert route["execution"]["reviewer_invocations"] == 1


def test_review_route_reads_the_service_project_config_not_ambient_cwd(svc, tmp_path, monkeypatch):
    service_tausik = Path(svc.tausik_dir())
    service_tausik.mkdir(parents=True, exist_ok=True)
    (service_tausik / "config.json").write_text(
        json.dumps({"review": {"extreme_hard_floor": True}}), encoding="utf-8"
    )
    ambient = tmp_path / "ambient"
    (ambient / ".tausik").mkdir(parents=True)
    (ambient / ".tausik" / "config.json").write_text(
        json.dumps({"review": {"extreme_hard_floor": False}}), encoding="utf-8"
    )
    monkeypatch.chdir(ambient)
    svc.task_update(
        "work",
        assurance_profiles=["executable"],
        assurance_impact={
            "level": "high",
            "blast_radius": "broad",
            "reversibility": "conditional",
            "security_boundary": True,
        },
    )

    route = build_task_context_package(svc, "work")["required"]["review_route"]

    assert route["depth"] == "L3"
    assert route["deep"] is True
    assert route["execution"]["reviewer_invocations"] == 7


def test_assurance_uses_target_project_stack_override_not_ambient_cwd(svc, tmp_path, monkeypatch):
    service_tausik = Path(svc.tausik_dir())
    target_stack = service_tausik / "stacks" / "python"
    target_stack.mkdir(parents=True)
    (target_stack / "stack.json").write_text(
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
    ambient = tmp_path / "ambient-stack"
    (ambient / ".tausik" / "stacks").mkdir(parents=True)
    monkeypatch.chdir(ambient)
    svc.task_update("work", stack="python")

    package = build_task_context_package(svc, "work")["required"]

    assert package["assurance"]["profiles"] == ["executable"]
    assert package["assurance"]["hard_floor"] == "L3"
    assert package["review_route"]["depth"] == "L3"


def test_fingerprint_changes_with_task_context(svc):
    before = build_task_context_package(svc, "work")["fingerprint"]
    svc.task_update("work", goal="ship changed behavior")
    after = build_task_context_package(svc, "work")["fingerprint"]
    assert before != after


def test_package_carries_complete_plan_progress(svc):
    svc.task_plan("work", ["first", "negative boundary"])
    svc.task_start("work")
    svc.task_step("work", 1)

    plan = build_task_context_package(svc, "work")["required"]["plan"]

    assert plan == [
        {"step": "first", "done": True},
        {"step": "negative boundary", "done": False},
    ]


def test_superseded_decision_is_excluded(svc):
    svc.decide("old route", task_slug="work")
    svc.decide("new route", task_slug="work", supersedes=1, rationale="old is stale")
    package = build_task_context_package(svc, "work")
    assert [row["id"] for row in package["required"]["decisions"]] == [2]


def test_required_overflow_is_explicit_and_never_truncates_ac(svc):
    ac = "AC-1 " + "x" * 2000 + " Negative: y"
    svc.task_update("work", acceptance_criteria=ac)
    package = build_task_context_package(svc, "work", max_bytes=512)
    assert package["overflow"] is True
    assert package["overflow_reason"] == "required_fields_exceed_budget"
    assert package["required"]["acceptance_criteria"] == ac
    assert package["bytes"] > package["max_bytes"]


def test_optional_memory_overflow_names_omission(svc, monkeypatch):
    task = svc.task_show("work")
    task["relevant_memory"] = ["m" * 300, "n" * 300]
    monkeypatch.setattr(svc, "task_show", lambda slug: task)
    package = build_task_context_package(svc, "work", max_bytes=1024)
    assert package["overflow"] is True
    assert package["omitted"]
    assert len(package["relevant_memory"]) < 2


@pytest.mark.parametrize("value", [0, 511, 65_537, "8192", True])
def test_invalid_budget_is_refused(svc, value):
    with pytest.raises(ValueError, match="max_bytes"):
        build_task_context_package(svc, "work", max_bytes=value)


def test_package_is_deterministic_json(svc):
    first = build_task_context_package(svc, "work")
    second = build_task_context_package(svc, "work")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_mcp_task_show_exposes_package_without_adding_a_tool(svc, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _handle_task_show
    from tools import TOOLS

    result = json.loads(_handle_task_show(svc, {"slug": "work", "mode": "package"}))
    schema = next(tool for tool in TOOLS if tool["name"] == "tausik_task_show")["inputSchema"]
    assert result["required"]["slug"] == "work"
    assert schema["properties"]["mode"]["enum"] == ["full", "package"]


def test_mcp_task_update_accepts_assurance_declarations(svc, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _do_task_update
    from tools import TOOLS

    _do_task_update(
        svc,
        {
            "slug": "work",
            "assurance_profiles": ["declarative"],
            "assurance_impact": {
                "level": "low",
                "blast_radius": "local",
                "reversibility": "reversible",
            },
        },
    )
    task = svc.task_show("work")
    schema = next(tool for tool in TOOLS if tool["name"] == "tausik_task_update")
    assert json.loads(task["assurance_profiles"]) == ["declarative"]
    assert json.loads(task["assurance_impact"])["reversibility"] == "reversible"
    assert {"assurance_profiles", "assurance_impact"} <= schema["inputSchema"]["properties"].keys()


def test_task_update_rejects_non_string_assurance_impact_enum(svc):
    from tausik_utils import ServiceError

    with pytest.raises(ServiceError, match="assurance_impact.level must be one of"):
        svc.task_update("work", assurance_impact={"level": []})
