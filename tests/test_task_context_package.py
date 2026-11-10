"""Bounded task context keeps intent whole and optional retrieval explicit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_backend import SQLiteBackend
from project_service import ProjectService
from task_context_package import (
    TaskPackageError,
    build_task_context_package,
    load_task_context_package,
    package_is_current,
    serialize_task_context_package,
)


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
    assert required["scope_tools"] == []
    assert required["stack"] is None
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


@pytest.mark.parametrize(
    ("field", "value"), [("stack", "python"), ("scope_tools", ["apply_patch"])]
)
def test_governance_input_changes_invalidate_fingerprint(svc, field, value):
    before = build_task_context_package(svc, "work")["fingerprint"]
    svc.task_update("work", **{field: value})
    assert build_task_context_package(svc, "work")["fingerprint"] != before


def test_package_carries_complete_plan_progress(svc):
    svc.task_plan("work", ["first", "negative boundary"])
    svc.task_start("work")
    svc.task_step("work", 1)

    plan = build_task_context_package(svc, "work")["required"]["plan"]

    assert plan == [
        {"id": 1, "step": "first", "done": True},
        {"id": 2, "step": "negative boundary", "done": False},
    ]


def test_superseded_decision_is_excluded(svc):
    svc.decide("old route", task_slug="work")
    svc.decide("new route", task_slug="work", supersedes=1, rationale="old is stale")
    package = build_task_context_package(svc, "work")
    assert [row["id"] for row in package["required"]["decisions"]] == [2]


def test_all_active_decisions_are_included_or_make_the_package_overflow(svc):
    for index in range(101):
        svc.decide(f"decision {index}", task_slug="work")

    package = build_task_context_package(svc, "work", max_bytes=512)

    assert len(package["required"]["decisions"]) == 101
    assert package["overflow"] is True


def test_task_decisions_are_not_hidden_by_newer_project_decisions(svc):
    svc.decide("old but active", task_slug="work")
    svc.task_add("s", "other", "Other", complexity="simple")
    svc.be._conn.executemany(
        "INSERT INTO decisions(decision,task_slug,created_at,slug) VALUES(?,?,?,?)",
        [
            (f"other {index}", "other", "2026-11-01T00:00:00Z", f"other-{index}")
            for index in range(10_001)
        ],
    )
    svc.be._conn.commit()

    package = build_task_context_package(svc, "work")

    assert [row["decision"] for row in package["required"]["decisions"]] == ["old but active"]


def test_required_overflow_is_explicit_and_never_truncates_ac(svc):
    ac = "AC-1 " + "x" * 2000 + " Negative: y"
    svc.task_update("work", acceptance_criteria=ac)
    package = build_task_context_package(svc, "work", max_bytes=512)
    assert package["overflow"] is True
    assert package["overflow_reason"] == "canonical_package_exceeds_budget"
    assert package["required"]["acceptance_criteria"] == ac
    assert package["bytes"] > package["max_bytes"]


def test_selected_memory_is_inline_and_never_replaced_by_ids(svc):
    svc.memory_add(
        "context",
        "Work package memory",
        "payload " * 100,
        tags=["work"],
        provenance="observed",
    )
    memory = build_task_context_package(svc, "work")["relevant_memory"]
    assert memory
    assert memory[0]["content"].startswith("payload")
    assert memory[0]["source_hash"]
    assert memory[0]["provenance"] in {"observed", "inferred", "told"}
    assert memory[0]["content_truncated"] is True


@pytest.mark.parametrize("delta,overflow", [(-1, True), (0, False), (1, False)])
def test_utf8_limit_is_inclusive_at_limit_minus_one_limit_plus_one(svc, delta, overflow):
    """Exact UTF-8 accounting makes limit-1 fail and limit/limit+1 fit."""
    svc.task_update("work", goal="доставка поведения")
    measured = build_task_context_package(svc, "work", max_bytes=8192)["bytes"]
    package = build_task_context_package(svc, "work", max_bytes=measured + delta)
    assert package["overflow"] is overflow
    encoded = json.dumps(package, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert package["bytes"] == len(encoded.encode("utf-8"))


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


def test_plain_start_persists_package_before_activation(svc):
    result = svc.task_start("work")
    stored = load_task_context_package(svc, "work")
    assert "Task package:" in result
    assert stored is not None
    assert stored["required"]["status"] == "active"
    assert svc.task_show("work")["status"] == "active"
    repeated = svc.task_start("work")
    assert "Task package:" in repeated
    assert load_task_context_package(svc, "work")["fingerprint"] == stored["fingerprint"]


def test_package_overflow_never_activates_or_persists(svc):
    with pytest.raises(TaskPackageError, match="PACKAGE_TOO_LARGE"):
        svc.task_start("work", package_max_bytes=512)
    assert svc.task_show("work")["status"] == "planning"
    assert load_task_context_package(svc, "work") is None


@pytest.mark.parametrize("race", ["task", "memory"])
def test_revision_conflict_rolls_back_the_whole_start(svc, monkeypatch, race):
    import task_context_package
    from project_backend import SQLiteBackend

    svc.memory_add("context", "Work race", "stable payload", tags=["work"], provenance="observed")
    memory_id = svc.be._q1("SELECT id FROM memory WHERE title='Work race'")["id"]
    real = task_context_package.build_task_context_package
    attempt = 0

    def racing_build(*args, **kwargs):
        nonlocal attempt
        package = real(*args, **kwargs)
        attempt += 1
        competitor = SQLiteBackend(svc.be.db_path)
        try:
            if race == "task":
                competitor.task_update("work", goal=f"durable competing contract {attempt}")
            else:
                competitor._conn.execute(
                    "UPDATE memory SET content=?,updated_at=? WHERE id=?",
                    (
                        f"durable competing payload {attempt}",
                        f"2099-01-01T00:00:0{attempt}Z",
                        memory_id,
                    ),
                )
                competitor._conn.commit()
        finally:
            competitor.close()
        return package

    monkeypatch.setattr(task_context_package, "build_task_context_package", racing_build)
    with pytest.raises(TaskPackageError, match="REVISION_CONFLICT"):
        svc.task_start("work")
    task = svc.task_show("work")
    assert task["status"] == "planning"
    if race == "task":
        assert task["goal"] == "durable competing contract 2"
    else:
        assert svc.be.memory_get(memory_id)["content"] == "durable competing payload 2"
    assert load_task_context_package(svc, "work") is None


def test_revision_conflict_retries_once_from_a_fresh_snapshot(svc, monkeypatch):
    import task_context_package
    from project_backend import SQLiteBackend

    real = task_context_package.build_task_context_package
    raced = False

    def racing_once(*args, **kwargs):
        nonlocal raced
        package = real(*args, **kwargs)
        if not raced:
            raced = True
            competitor = SQLiteBackend(svc.be.db_path)
            try:
                competitor.task_update("work", goal="durable competing winner")
            finally:
                competitor.close()
        return package

    monkeypatch.setattr(task_context_package, "build_task_context_package", racing_once)
    svc.task_start("work")
    assert svc.task_show("work")["status"] == "active"
    assert load_task_context_package(svc, "work")["required"]["goal"] == "durable competing winner"


def test_resume_status_change_cannot_persist_or_bind_a_package(svc, monkeypatch):
    import task_context_package
    from project_backend import SQLiteBackend

    svc.task_start("work", include_memory=False)
    before = load_task_context_package(svc, "work")["fingerprint"]
    real = task_context_package.build_task_context_package
    raced = False

    def racing_once(*args, **kwargs):
        nonlocal raced
        package = real(*args, **kwargs)
        if not raced:
            raced = True
            competitor = SQLiteBackend(svc.be.db_path)
            try:
                competitor.task_update("work", status="review")
            finally:
                competitor.close()
        return package

    monkeypatch.setattr(task_context_package, "build_task_context_package", racing_once)
    with pytest.raises(TaskPackageError, match="REVISION_CONFLICT.*status changed"):
        svc.task_start("work", include_memory=False)
    assert svc.task_show("work")["status"] == "review"
    assert load_task_context_package(svc, "work")["fingerprint"] == before


def test_resume_refuses_active_legacy_task_with_incomplete_package_contract(svc):
    svc.be.task_update("work", status="active", scope=None, scope_paths="[]")
    with pytest.raises(TaskPackageError, match="PACKAGE_INVALID.*scope_or_scope_paths"):
        svc.task_start("work")
    assert load_task_context_package(svc, "work") is None


def test_persisted_package_survives_relevance_backend_failure(svc, monkeypatch):
    svc.task_start("work", include_memory=False)

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("memory backend unavailable")

    monkeypatch.setattr("memory_relevance.relevant_memory", unavailable)
    payload = json.loads(serialize_task_context_package(svc, "work", max_bytes=16384))
    assert payload["required"]["goal"] == "ship behavior"


def test_selected_memory_revision_invalidates_package(svc):
    svc.memory_add(
        "context", "Work revision", "first payload", tags=["work"], provenance="observed"
    )
    memory_id = svc.be._q1("SELECT id FROM memory WHERE title='Work revision'")["id"]
    svc.task_start("work", include_memory=False)
    package = load_task_context_package(svc, "work")
    assert package is not None and package_is_current(svc, package)
    svc.be._ex(
        "UPDATE memory SET content='changed payload',updated_at='2099-01-01T00:00:00Z' WHERE id=?",
        (memory_id,),
    )
    assert package_is_current(svc, package) is False


@pytest.mark.parametrize("status", ["planning", "active"])
def test_complex_legacy_row_is_normalized_on_start_or_resume(svc, status):
    svc.task_update("work", complexity="complex", task_package_legacy=1)
    if status == "active":
        svc.be.task_update("work", status="active")
    svc.task_start("work", include_memory=False)
    assert svc.task_show("work")["call_budget"] == 80
    assert json.loads(svc.task_show("work")["assurance_profiles"]) == ["executable"]
    package = load_task_context_package(svc, "work")
    assert package is not None
    assert package["required"]["call_budget"] == 80


def test_new_complex_task_requires_explicit_package_declarations(svc):
    svc.task_update("work", complexity="complex")
    with pytest.raises(TaskPackageError, match="PACKAGE_INVALID.*call_budget"):
        svc.task_start("work")
    assert svc.task_show("work")["status"] == "planning"


@pytest.mark.parametrize("corruption", ["payload", "metadata"])
def test_persisted_package_integrity_is_rechecked(svc, corruption):
    svc.task_start("work", include_memory=False)
    row = svc.be._q1("SELECT payload_json FROM task_context_packages WHERE task_slug='work'")
    if corruption == "payload":
        payload = json.loads(row["payload_json"])
        payload["required"]["goal"] = "tampered"
        svc.be._ex(
            "UPDATE task_context_packages SET payload_json=? WHERE task_slug='work'",
            (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),),
        )
    else:
        svc.be._ex("UPDATE task_context_packages SET bytes=bytes+1 WHERE task_slug='work'")
    with pytest.raises(TaskPackageError, match="PACKAGE_CORRUPT"):
        load_task_context_package(svc, "work")


def test_persisted_package_payload_must_belong_to_its_row_slug(svc):
    svc.task_start("work", include_memory=False)
    svc.task_add("s", "other", "Other", complexity="simple")
    svc.task_update(
        "other",
        goal="ship other",
        acceptance_criteria="AC-1 works. Negative: malformed input is refused.",
    )
    other = build_task_context_package(svc, "other")
    svc.be._ex(
        "UPDATE task_context_packages SET fingerprint=?,payload_json=?,bytes=?,max_bytes=?,"
        "task_revision=?,selected_memory_revisions=? WHERE task_slug='work'",
        (
            other["fingerprint"],
            json.dumps(other, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            other["bytes"],
            other["max_bytes"],
            other["task_revision"],
            json.dumps(other["selected_memory_revisions"], sort_keys=True, separators=(",", ":")),
        ),
    )

    with pytest.raises(TaskPackageError, match="payload task slug"):
        load_task_context_package(svc, "work")
