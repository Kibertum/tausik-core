"""Behavioral contract for the 1.11.8 Codex adherence baseline."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import adherence_contract as ac
from adherence_evidence import build_evidence
from adherence_policy import policy_artifact
from adherence_registry import registry_artifact
from adherence_runtime import AdherenceRecorder, evaluate
from project_backend import SQLiteBackend
from project_cli_task import cmd_task
from project_service import ProjectService


ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "adherence"


def _integration_census() -> list[dict[str, object]]:
    return json.loads((FIXTURES / "integration-census-v1.json").read_text(encoding="utf-8"))


def _route(fragment: str, *, prefix: str | None = None) -> str:
    matches = [
        row["route"]
        for row in registry_artifact()["routes"]
        if fragment in row["route"] and (prefix is None or row["route"].startswith(prefix))
    ]
    assert matches, fragment
    return sorted(matches)[0]


def _valid_events() -> list[dict[str, object]]:
    recorder = AdherenceRecorder(task_slug="contract-task", thread_id="thread-1")
    recorder.record_action(
        "service.session_start", {"execution_lease": "valid", "handoff_resume": "correct"}
    )
    recorder.record_action(
        "service.task_start", {"execution_lease": "valid", "task_package": "complete"}
    )
    recorder.record_action(
        "service.task_step", {"execution_lease": "valid", "continuity": "satisfied"}
    )
    recorder.record_action(
        "service.reasoning_step_add",
        {
            "execution_lease": "valid",
            "continuity": "satisfied",
            "dead_end_repeat": "overridden",
        },
    )
    recorder.record_action(
        _route("git_push_gate.py", prefix="hook.PreToolUse"),
        {"execution_lease": "valid", "memory_preflight": "valid"},
    )
    recorder.record_action(
        _route("session_cleanup_check.py", prefix="hook.Stop"),
        {"execution_lease": "valid", "stop_decision": "safe"},
    )
    return recorder.events


def _red_events() -> list[dict[str, object]]:
    recorder = ac.AdherenceRecorder(task_slug="contract-task", thread_id="thread-1")
    for route in (
        "service.session_start",
        "service.task_start",
        "service.task_step",
        "service.reasoning_step_add",
        _route("git_push_gate.py", prefix="hook.PreToolUse"),
        _route("session_cleanup_check.py", prefix="hook.Stop"),
    ):
        results = {"dead_end_repeat": "unoverridden"} if "reasoning" in route else {}
        recorder.record_red_action(route, results)
    return recorder.events


def test_policy_artifact_contains_the_full_formula_and_schema_contract():
    policy = policy_artifact()
    assert policy["event_fields"] == sorted(ac.EVENT_FIELDS)
    assert policy["sentinels"] == list(ac.SENTINEL_NAMES)
    assert policy["canonicalization_version"] == 1
    assert set(policy["metric_specs"]) == {"rates", "zero_counts"}
    assert policy["change_rule"] == "version-bump-and-L3-review"


def test_registry_is_derived_from_live_service_cli_mcp_and_hook_surfaces():
    routes = ac.registry_artifact()["routes"]
    assert len(routes) > 500
    assert {row["boundary"] for row in routes} == {"cli", "hook", "mcp", "service"}
    assert len({row["route"] for row in routes}) == len(routes)
    assert all(row["classification"] in {"mutation", "protected", "read", "stop"} for row in routes)
    assert all(row["required_events"] for row in routes if row["classification"] != "read")
    assert all(not row["required_events"] for row in routes if row["classification"] == "read")
    assert any(row["route"] == "service.task_start" for row in routes)
    assert any(row["route"] == "mcp.tausik_task_start" for row in routes)
    assert any(row["route"] == "cli.task.start" for row in routes)
    assert any(row["route"].startswith("hook.Stop.") for row in routes)
    assert any("codex_write_gate.py" in row["route"] for row in routes)
    discovered = {row["route"] for row in routes}
    assert ac._READ_ROUTES <= discovered
    assert (
        next(row for row in routes if row["route"] == "cli.doc.roadmap")["classification"]
        == "mutation"
    )
    assert (
        next(row for row in routes if row["route"] == "service.metrics_record_session")[
            "classification"
        ]
        == "mutation"
    )


@pytest.mark.parametrize("route", ["service.get_or_create", "cli.task.status.update"])
def test_unknown_route_names_fail_closed_as_mutations(route):
    assert ac._classification("service", route) == "mutation"


def test_hook_route_identity_includes_the_full_command():
    first = ac._hook_route("PreToolUse", "PowerShell", "hook.py --mode first")
    second = ac._hook_route("PreToolUse", "PowerShell", "hook.py --mode second")
    assert first != second


def test_one_action_must_supply_its_exact_registered_event_set():
    recorder = ac.AdherenceRecorder("t", "th")
    with pytest.raises(ac.ContractError, match="requires events"):
        recorder.record_action("service.task_start", {"task_package": "complete"})
    with pytest.raises(ac.ContractError, match="does not require"):
        recorder.record_action(
            "service.task_start",
            {
                "execution_lease": "valid",
                "task_package": "complete",
                "memory_preflight": "valid",
            },
        )


@pytest.mark.parametrize(
    "field",
    ["action_id", "boundary", "lease_id", "package_fingerprint", "route", "task_id", "thread_id"],
)
def test_action_identity_cannot_be_borrowed_across_routes(field):
    events = _valid_events()
    action_id = events[0]["action_id"]
    action = [event for event in events if event["action_id"] == action_id]
    if field == "task_id":
        action[-1][field] = "task-0000000000000000"
    elif field == "thread_id":
        action[-1][field] = "thread-0000000000000000"
    else:
        action[-1][field] = events[-1][field]
    with pytest.raises(ac.ContractError):
        ac.evaluate(events)


@pytest.mark.parametrize("kind", [kind for kind in ac.RESULTS if kind != "dead_end_repeat"])
def test_removing_any_required_event_rejects_the_action(kind):
    events = _valid_events()
    events.remove(next(event for event in events if event["kind"] == kind))
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
    with pytest.raises(ac.ContractError, match="requires ordered events"):
        ac.evaluate(events)


def test_valid_actions_satisfy_every_exact_threshold():
    verdict = evaluate(_valid_events())
    assert verdict.accepted
    assert all(metric["passed"] for metric in verdict.metrics.values())
    assert all(metric["denominator"] > 0 for metric in verdict.metrics.values())


def test_red_actions_fail_every_exact_threshold():
    verdict = ac.evaluate(_red_events())
    assert not verdict.accepted
    assert all(not metric["passed"] for metric in verdict.metrics.values())


def test_zero_observations_satisfy_a_zero_count_threshold():
    valid = _valid_events()
    stop_action = next(event["action_id"] for event in valid if event["kind"] == "stop_decision")
    events = [event for event in valid if event["action_id"] != stop_action]
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
    metric = ac.evaluate(events).metrics["premature_stops"]
    assert metric == {"count": 0, "denominator": 0, "passed": True, "threshold": 0}


@pytest.mark.parametrize(
    ("field", "value"),
    [("schema_version", True), ("policy_version", 1.0), ("sequence", True)],
)
def test_numeric_schema_fields_require_exact_integers(field, value):
    events = _valid_events()
    events[0][field] = value
    with pytest.raises(ac.ContractError):
        ac.evaluate(events)


def test_negative_control_executes_and_rejects_the_frozen_inventory():
    report = ac.run_negative_control(_valid_events())
    assert report["passed"]
    assert report["executed"] == report["expected"] == len(ac.SENTINEL_NAMES)
    assert report["rejected"] == report["expected"]
    assert report["accepted"] == 0
    assert {row["name"] for row in report["results"]} == set(ac.SENTINEL_NAMES)


def test_negative_control_evidence_runs_sentinels_instead_of_relabeling_acceptance():
    evidence = build_evidence(_valid_events(), "negative-control", "a" * 40, _integration_census())
    count = len(ac.SENTINEL_NAMES)
    assert evidence["accepted"]
    assert evidence["counts"] == {
        "collected": count,
        "deselected": 0,
        "failed": 0,
        "passed": count,
        "executed": count,
        "expected": count,
    }
    assert len(evidence["results"]) == count
    assert evidence["sentinel_sha256"] == ac.artifact_hash(list(ac.SENTINEL_NAMES))


def test_acceptance_evidence_hashes_the_evaluated_cohort_and_itself():
    events = _red_events()
    evidence = ac.build_evidence(events, "acceptance", "b" * 40, _integration_census())
    assert evidence["fixture_sha256"] == ac.artifact_hash(events)
    content_hash = evidence.pop("content_sha256")
    assert content_hash == ac.artifact_hash(evidence)
    assert not evidence["accepted"]


def test_acceptance_cannot_borrow_a_green_arithmetic_cohort_over_zero_real_emissions():
    evidence = ac.build_evidence(_valid_events(), "acceptance", "b" * 40, _integration_census())
    assert not evidence["accepted"]
    assert not evidence["census_reconciliation"]["passed"]


def test_census_only_drift_changes_bundle_and_content_hashes():
    census = _integration_census()
    original = ac.build_evidence(_red_events(), "acceptance", "b" * 40, census)
    census[0]["action_id"] = "action-0000000000000000"
    drifted = ac.build_evidence(_red_events(), "acceptance", "b" * 40, census)
    assert drifted["integration_census_sha256"] != original["integration_census_sha256"]
    assert drifted["contract_bundle_sha256"] != original["contract_bundle_sha256"]
    assert drifted["content_sha256"] != original["content_sha256"]


def test_zero_collected_cannot_produce_evidence():
    with pytest.raises(ac.ContractError, match="zero events"):
        ac.build_evidence([], "acceptance", "c" * 40, _integration_census())


@pytest.mark.parametrize(
    "field", ["action_id", "event_id", "lease_id", "package_fingerprint", "task_id", "thread_id"]
)
def test_identifier_fields_reject_prose_and_canaries(field):
    events = _valid_events()
    events[0][field] = "TAUSIK-SECRET-CANARY"
    with pytest.raises(ac.ContractError, match="opaque bounded identifier"):
        ac.evaluate(events)


@pytest.mark.parametrize("sink", ["db", "stdout", "stderr", "json"])
@pytest.mark.parametrize("encoding", ["plain", "base64"])
def test_canary_scan_detects_every_sink_and_supported_encoding(sink, encoding):
    canary = "TAUSIK-SECRET-CANARY"
    value = canary if encoding == "plain" else base64.b64encode(canary.encode()).decode()
    sinks = {name: "safe" for name in ("db", "stdout", "stderr", "json")}
    sinks[sink] = value
    assert ac.scan_canary(sinks, canary) == [sink]


def test_canary_scan_requires_all_four_sinks():
    with pytest.raises(ac.ContractError, match="exactly"):
        ac.scan_canary({"db": "safe"}, "canary")


def test_real_service_cli_mcp_and_hook_entry_points_produce_a_red_observation(tmp_path, capsys):
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    backend = SQLiteBackend(str(tausik_dir / "tausik.db"))
    svc = ProjectService(backend)
    svc.epic_add("e", "E")
    svc.story_add("e", "s", "S")
    svc.task_add("s", "contract-task", "T")

    recorder = ac.AdherenceRecorder("contract-task", "thread-1")
    recorder.probe_service(svc.session_start, "thread-1")
    recorder.probe_service(svc.task_start, "contract-task", _internal_force=True)
    recorder.probe_service(svc.reasoning_step_add, "contract-task", "action", "probe")

    cli_args = SimpleNamespace(task_cmd="log", slug="contract-task", message="cli-probe")
    recorder.probe_cli(cmd_task, svc, cli_args)
    capsys.readouterr()

    handler_dir = ROOT / "harness" / "claude" / "mcp" / "project"
    sys.path.insert(0, str(handler_dir))
    from handlers import _dispatch_tool

    recorder.probe_mcp(
        _dispatch_tool,
        svc,
        "tausik_task_log",
        {"slug": "contract-task", "message": "mcp-probe"},
    )

    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path))
    git_hook = ROOT / "scripts" / "hooks" / "git_push_gate.py"
    stop_hook = ROOT / "scripts" / "hooks" / "session_cleanup_check.py"

    push_result = recorder.probe_hook(
        "PreToolUse",
        git_hook,
        {"tool_name": "PowerShell", "tool_input": {"command": "git push origin main"}},
        env,
        expected_returncodes=frozenset({2}),
    )
    assert "push ticket" in push_result.stderr
    recorder.probe_hook(
        "Stop",
        stop_hook,
        {},
        env,
        expected_returncodes=frozenset({0}),
    )
    expected_actions = frozenset(probe["action_id"] for probe in recorder.probes)
    with pytest.raises(ac.ContractError, match="trusted invocation census"):
        ac.evaluate(recorder.events, expected_actions=expected_actions)
    assert recorder.events == []
    observed_routes = {probe["route"] for probe in recorder.probes}
    assert {
        "service.session_start",
        "service.task_start",
        "service.reasoning_step_add",
        "cli.task.log",
        "mcp.tausik_task_log",
    }.issubset(observed_routes)
    assert len(recorder.probes) == 7
    assert {probe["status"] for probe in recorder.probes} == {"executed"}
    assert recorder.probes == json.loads(
        (FIXTURES / "integration-census-v1.json").read_text(encoding="utf-8")
    )
    assert len(svc.task_logs("contract-task")) == 2
    backend.close()


def test_failed_integration_probe_records_neither_census_nor_events():
    recorder = ac.AdherenceRecorder("t", "thread")
    with pytest.raises(ac.ContractError, match="bound ProjectService"):
        recorder.probe_service(lambda: None)
    assert recorder.probes == []
    assert recorder.events == []


def test_probe_captures_events_emitted_to_its_active_sink():
    recorder = ac.AdherenceRecorder("t", "thread")

    def instrumented_entry_point():
        active = ac.active_recorder()
        assert active is recorder
        active.record_action(
            "service.task_start",
            {"execution_lease": "valid", "task_package": "complete"},
        )

    recorder._probe("service.task_start", instrumented_entry_point)
    assert recorder.probes[0]["event_count"] == 2
    assert recorder.probes[0]["event_sha256"] == ac.artifact_hash(recorder.events)
    assert recorder.probes[0]["action_id"] == recorder.events[0]["action_id"]


def test_hook_probe_collects_events_from_a_real_child_process(tmp_path):
    route = _route("session_cleanup_check.py", prefix="hook.Stop")
    child = tmp_path / "instrumented_hook.py"
    child.write_text(
        "\n".join(
            [
                "import sys",
                f"sys.path.insert(0, {str(ROOT / 'scripts')!r})",
                "import adherence_contract as ac",
                "recorder = ac.AdherenceRecorder('child-task', 'child-thread')",
                f"recorder.record_action({route!r}, "
                "{'execution_lease': 'valid', 'stop_decision': 'safe'})",
                "ac.append_sink_events(recorder.events)",
            ]
        ),
        encoding="utf-8",
    )
    recorder = ac.AdherenceRecorder("parent-task", "parent-thread")
    completed = recorder._probe_hook_process(
        route,
        child,
        {},
        os.environ,
        expected_returncodes=frozenset({0}),
    )
    assert completed.returncode == 0
    assert len(recorder.events) == 2
    assert recorder.probes[0]["event_count"] == 2
    assert recorder.probes[0]["event_sha256"] == ac.artifact_hash(recorder.events)


def test_manifest_and_recorded_baseline_recompute_independently():
    manifest = json.loads((FIXTURES / "manifest-v1.json").read_text(encoding="utf-8"))
    red_events = json.loads((FIXTURES / "red-events-v1.json").read_text(encoding="utf-8"))
    valid_events = json.loads((FIXTURES / "valid-events-v1.json").read_text(encoding="utf-8"))
    baseline = json.loads((FIXTURES / "red-baseline-v1.json").read_text(encoding="utf-8"))
    frozen_policy = json.loads((FIXTURES / "policy-v1.json").read_text(encoding="utf-8"))
    integration_census = json.loads(
        (FIXTURES / "integration-census-v1.json").read_text(encoding="utf-8")
    )
    assert red_events == _red_events()
    assert valid_events == _valid_events()
    assert frozen_policy == ac.policy_artifact()
    assert manifest["policy_sha256"] == ac.artifact_hash(frozen_policy)
    assert manifest["registry_sha256"] == ac.artifact_hash(ac.registry_artifact())
    assert manifest["red_fixture_sha256"] == ac.artifact_hash(red_events)
    assert manifest["valid_fixture_sha256"] == ac.artifact_hash(valid_events)
    assert manifest["baseline_sha256"] == ac.artifact_hash(baseline)
    assert manifest["integration_census_sha256"] == ac.artifact_hash(integration_census)
    assert manifest["base_commit_sha"] == baseline["base_commit_sha"]
    assert manifest["evaluator_sha256"] == baseline["evaluator_sha256"]

    evaluator_digest = hashlib.sha256()
    evaluator_sources = (
        "adherence_contract.py",
        "adherence_evidence.py",
        "adherence_policy.py",
        "adherence_registry.py",
        "adherence_runtime.py",
    )
    for name in evaluator_sources:
        encoded_name = name.encode("utf-8")
        content = (ROOT / "scripts" / name).read_bytes()
        evaluator_digest.update(len(encoded_name).to_bytes(8, "big"))
        evaluator_digest.update(encoded_name)
        evaluator_digest.update(len(content).to_bytes(8, "big"))
        evaluator_digest.update(content)
    assert manifest["evaluator_sha256"] == evaluator_digest.hexdigest()

    rebuilt = ac.build_evidence(
        red_events, "acceptance", manifest["base_commit_sha"], integration_census
    )
    assert rebuilt == baseline
    baseline_without_hash = dict(baseline)
    content_hash = baseline_without_hash.pop("content_sha256")
    assert content_hash == ac.artifact_hash(baseline_without_hash)

    drifted_policy = dict(frozen_policy, policy_version=2)
    assert ac.artifact_hash(drifted_policy) != manifest["policy_sha256"]


def test_privacy_pipeline_persists_only_opaque_ids_and_clean_evidence(tmp_path, capsys):
    canary = "TAUSIK-SECRET-CANARY"
    recorder = ac.AdherenceRecorder(canary, canary)
    recorder.record_action(
        "service.task_start", {"execution_lease": "valid", "task_package": "complete"}
    )
    evidence = ac.build_evidence(recorder.events, "acceptance", "d" * 40, _integration_census())
    payload = json.dumps(evidence, sort_keys=True)

    db = sqlite3.connect(tmp_path / "evidence.db")
    db.execute("CREATE TABLE evidence(payload TEXT NOT NULL)")
    db.execute("INSERT INTO evidence(payload) VALUES (?)", (payload,))
    db.commit()
    db_payload = db.execute("SELECT payload FROM evidence").fetchone()[0]
    print(payload)
    captured = capsys.readouterr()
    sinks = {"db": db_payload, "stdout": captured.out, "stderr": captured.err, "json": payload}
    assert ac.scan_canary(sinks, canary) == []
