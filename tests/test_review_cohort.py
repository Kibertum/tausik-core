"""Behavioral contract for bounded task-indexed L3 review cohorts."""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from threading import Barrier, Lock

import pytest

from project_backend import SQLiteBackend
from project_cli_review import cmd_review
from project_parser import build_parser
from project_service import ProjectService
from review_cohort import (
    cohort_status,
    decide_review_cohort,
    open_review_cohort,
    record_review_round,
)
from review_routing import review_record_blockers


AUTHOR = "gpt-5.6-sol"
REVIEWER = "gpt-6-astra"


@pytest.fixture
def cohort_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("review_cohort._head", lambda _root: "fixture-head")
    service = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    service.epic_add("e", "E")
    service.story_add("e", "s", "S")
    for slug in ("a", "b"):
        path = tmp_path / "src" / f"{slug}.py"
        path.parent.mkdir(exist_ok=True)
        path.write_text(f"VALUE = {slug!r}\n", encoding="utf-8")
        service.task_add("s", slug, slug.upper())
        service.task_update(
            slug,
            goal=f"change {slug}",
            acceptance_criteria="AC-1: behavior is correct. AC-2: invalid input is refused.",
            scope=f"src/{slug}.py",
            rollback_plan="git revert",
            relevant_files=json.dumps([f"src/{slug}.py"]),
            assurance_profiles=["executable"],
            assurance_impact={
                "level": "high",
                "blast_radius": "local",
                "reversibility": "reversible",
            },
        )
        service.task_start(slug)
        service.be._conn.execute("UPDATE tasks SET started_model_id=? WHERE slug=?", (AUTHOR, slug))
        service.be._conn.commit()
        service.task_log(slug, "AC-1: ✓ behavior exercised")
    yield service, tmp_path
    service.be.close()


def _result(task: str, *, high: int = 0, critical: int = 0, warnings: int = 0):
    result = {
        "task": task,
        "high": high,
        "critical": critical,
        "warnings": warnings,
        "dependency_map_complete": True,
    }
    if critical:
        result.update(critical_reason="demonstrated critical impact", finding_refs=["finding-1"])
    return result


def _record(service, cohort_id, round_number, results):
    packet = cohort_status(service, cohort_id)["packet"]
    return record_review_round(
        service,
        cohort_id,
        round_number,
        results,
        packet_digest=packet["packet_digest"],
        author_model=AUTHOR,
        reviewer_model=REVIEWER,
        usage={"tokens_total": 123},
    )


def _owner_decision_cohort(service, tmp_path):
    opened = open_review_cohort(service, tasks=["a"])
    _record(service, opened["cohort_id"], 1, [_result("a", high=1)])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair'\n", encoding="utf-8")
    _record(service, opened["cohort_id"], 2, [_result("a", high=1)])
    routes = json.loads(service.be._q1("SELECT routes_json FROM review_cohorts")["routes_json"])
    routes["a"]["hard_floor"] = None
    service.be._conn.execute(
        "UPDATE review_cohorts SET routes_json=? WHERE id=?",
        (json.dumps(routes), opened["cohort_id"]),
    )
    service.be._conn.commit()
    return opened


def test_round_one_green_is_a_current_composite_close_receipt(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, story="s")
    assert [item["slug"] for item in opened["packet"]["tasks"]] == ["a", "b"]
    assert opened["packet"]["tasks"][0]["goal"] == "change a"
    assert opened["packet"]["tasks"][0]["author_model"] == AUTHOR
    assert opened["packet"]["tasks"][0]["numbered_ac_evidence"][0]["message"].startswith("AC-1:")

    issued = service.be._q1(
        "SELECT packet_digest,issued_at FROM review_cohort_packets WHERE cohort_pk=?",
        (opened["cohort_id"],),
    )
    repeated = cohort_status(service, opened["cohort_id"])["packet"]
    assert repeated == opened["packet"]
    assert (
        service.be._q1(
            "SELECT packet_digest,issued_at FROM review_cohort_packets WHERE cohort_pk=?",
            (opened["cohort_id"],),
        )
        == issued
    )

    done = _record(service, opened["cohort_id"], 1, [_result("a"), _result("b", warnings=2)])

    assert (done["state"], done["green"], done["advisory"], done["red"], done["rounds"]) == (
        "green",
        1,
        1,
        0,
        "1/2",
    )
    for slug in ("a", "b"):
        route = json.loads(service.be._q1("SELECT routes_json FROM review_cohorts")["routes_json"])[
            slug
        ]
        assert review_record_blockers(service.be._conn, slug, route, tmp_path) == []


def test_round_two_reviews_red_and_changed_only_then_carries_green(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["b", "a", "a"])
    cohort_id = opened["cohort_id"]
    first = _record(service, cohort_id, 1, [_result("a", high=1), _result("b")])
    assert first["state"] == "round1_red"

    (tmp_path / "src" / "a.py").write_text("VALUE = 'fixed'\n", encoding="utf-8")
    packet = cohort_status(service, cohort_id)
    assert [item["slug"] for item in packet["packet"]["tasks"]] == ["a"]
    assert packet["carried_tasks"] == ["b"]

    second = _record(service, cohort_id, 2, [_result("a")])
    assert (second["state"], second["green"], second["carried"], second["rounds"]) == (
        "green",
        2,
        1,
        "2/2",
    )
    with pytest.raises(ValueError, match="automatic round 3"):
        record_review_round(
            service,
            cohort_id,
            2,
            [_result("a")],
            packet_digest=packet["packet"]["packet_digest"],
            author_model=AUTHOR,
            reviewer_model=REVIEWER,
        )


def test_changed_green_joins_round_two_and_missing_result_fails_closed(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, story="s")
    cohort_id = opened["cohort_id"]
    _record(service, cohort_id, 1, [_result("a", high=1), _result("b")])
    (tmp_path / "src" / "b.py").write_text("VALUE = 'also changed'\n", encoding="utf-8")

    assert [item["slug"] for item in cohort_status(service, cohort_id)["packet"]["tasks"]] == [
        "a",
        "b",
    ]
    with pytest.raises(ValueError, match="cover exactly"):
        _record(service, cohort_id, 2, [_result("a")])


def test_changed_shared_file_selects_green_member_and_carries_unrelated(cohort_project):
    service, tmp_path = cohort_project
    shared = tmp_path / "src" / "shared.py"
    shared.write_text("VALUE = 'shared'\n", encoding="utf-8")
    service.task_update("a", relevant_files=json.dumps(["src/a.py", "src/shared.py"]))
    service.task_update("b", relevant_files=json.dumps(["src/b.py", "src/shared.py"]))

    (tmp_path / "src" / "c.py").write_text("VALUE = 'c'\n", encoding="utf-8")
    service.task_add("s", "c", "C")
    service.task_update(
        "c",
        goal="change c",
        acceptance_criteria="AC-1: behavior is correct. AC-2: invalid input is refused.",
        scope="src/c.py",
        rollback_plan="git revert",
        relevant_files=json.dumps(["src/c.py"]),
        assurance_profiles=["executable"],
        assurance_impact={
            "level": "high",
            "blast_radius": "local",
            "reversibility": "reversible",
        },
    )
    service.task_start("c")
    service.be._conn.execute("UPDATE tasks SET started_model_id=? WHERE slug='c'", (AUTHOR,))
    service.be._conn.commit()
    service.task_log("c", "AC-1: ✓ behavior exercised")

    opened = open_review_cohort(service, tasks=["a", "b", "c"])
    cohort_id = opened["cohort_id"]
    _record(
        service,
        cohort_id,
        1,
        [_result("a", high=1), _result("b"), _result("c")],
    )
    shared.write_text("VALUE = 'changed shared'\n", encoding="utf-8")

    status = cohort_status(service, cohort_id)
    assert [item["slug"] for item in status["packet"]["tasks"]] == ["a", "b"]
    assert status["carried_tasks"] == ["c"]


def test_uncertain_scope_widens_round_two_and_stale_green_cannot_close(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, story="s")
    cohort_id = opened["cohort_id"]
    _record(service, cohort_id, 1, [_result("a", high=1), _result("b")])
    service.task_update("a", relevant_files=json.dumps([]))
    assert [item["slug"] for item in cohort_status(service, cohort_id)["packet"]["tasks"]] == [
        "a",
        "b",
    ]

    second = open_review_cohort(service, tasks=["b"])
    _record(service, second["cohort_id"], 1, [_result("b")])
    (tmp_path / "src" / "b.py").write_text("VALUE = 'stale'\n", encoding="utf-8")
    route = json.loads(
        service.be._q1("SELECT routes_json FROM review_cohorts WHERE id=?", (second["cohort_id"],))[
            "routes_json"
        ]
    )["b"]
    assert review_record_blockers(service.be._conn, "b", route, tmp_path) == [
        "L3 cohort receipt is stale: task contract, reviewed files, or dependencies changed"
    ]


def test_second_red_stops_automation_and_owner_acceptance_keeps_findings(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, story="s")
    cohort_id = opened["cohort_id"]
    _record(service, cohort_id, 1, [_result("a", high=1), _result("b")])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair'\n", encoding="utf-8")
    terminal = _record(service, cohort_id, 2, [_result("a", high=1)])
    assert terminal["state"] == "owner_decision"
    assert "accept risk" in terminal["owner_action"]

    accepted = decide_review_cohort(
        service,
        cohort_id,
        "accept-risk",
        owner="release-owner",
        reason="bounded known impact",
        finding_refs=["finding-1"],
    )
    assert accepted["state"] == "accepted_risk"
    result = service.be._q1(
        "SELECT verdict, high_findings FROM review_cohort_results "
        "WHERE cohort_pk=? AND task_slug='a' AND round_number=2",
        (cohort_id,),
    )
    assert result == {"verdict": "accepted_risk", "high_findings": 1}
    assert accepted["green"] == 1
    assert accepted["accepted_risk"] == 1
    assert accepted["red"] == 0
    assert "accepted-risk 1" in __import__("review_cohort").cohort_summary(accepted)


def test_latest_evidence_wins_and_route_drift_cannot_reuse_cohort(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    cohort_id = opened["cohort_id"]
    green = _record(service, cohort_id, 1, [_result("a")])
    route = json.loads(
        service.be._q1("SELECT routes_json FROM review_cohorts WHERE id=?", (cohort_id,))[
            "routes_json"
        ]
    )["a"]
    drifted = {**route, "reasons": [*route["reasons"], "policy changed"]}
    assert review_record_blockers(service.be._conn, "a", drifted, tmp_path) == [
        "L3 cohort receipt is stale: review route or policy changed"
    ]

    service.be.review_record(
        "a",
        "L3",
        author_model=AUTHOR,
        reviewer_model=REVIEWER,
        reviewer_context="different-model",
        reviewer_invocations=1,
        route_json=json.dumps(route),
    )
    service.be._conn.execute("UPDATE reviews SET run_at='9999-01-01T00:00:00Z'")
    service.be._conn.commit()
    assert green["state"] == "green"
    assert review_record_blockers(service.be._conn, "a", route, tmp_path) == []


def test_membership_and_model_family_drift_are_refused(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, story="s")
    with pytest.raises(ValueError, match="invalid L3 reviewer evidence"):
        record_review_round(
            service,
            opened["cohort_id"],
            1,
            [_result("a"), _result("b")],
            packet_digest=opened["packet"]["packet_digest"],
            author_model=AUTHOR,
            reviewer_model=AUTHOR,
        )
    with pytest.raises(ValueError, match="trusted per-task provenance"):
        record_review_round(
            service,
            opened["cohort_id"],
            1,
            [_result("a"), _result("b")],
            packet_digest=opened["packet"]["packet_digest"],
            author_model="claude-opus-4.8",
            reviewer_model=REVIEWER,
        )

    (tmp_path / "src" / "c.py").write_text("VALUE = 'c'\n", encoding="utf-8")
    service.task_add("s", "c", "C")
    service.task_update(
        "c",
        goal="change c",
        acceptance_criteria="AC-1: works. AC-2: invalid input is refused.",
        scope="src/c.py",
        rollback_plan="git revert",
        relevant_files=json.dumps(["src/c.py"]),
        assurance_profiles=["executable"],
        assurance_impact={
            "level": "high",
            "blast_radius": "local",
            "reversibility": "reversible",
        },
    )
    service.task_start("c")
    service.be._conn.execute("UPDATE tasks SET started_model_id=? WHERE slug='c'", (AUTHOR,))
    service.be._conn.commit()
    service.task_log("c", "AC-1: ✓ AC-2: ✓")
    with pytest.raises(ValueError, match="membership drift"):
        cohort_status(service, opened["cohort_id"])


def test_cli_and_mcp_render_the_same_canonical_status(cohort_project, monkeypatch):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from handlers_review import _handle_review_cohort

    service, _ = cohort_project
    opened = open_review_cohort(service, story="s")
    args = build_parser().parse_args(["review", "cohort-status", str(opened["cohort_id"])])
    stdout = StringIO()
    with redirect_stdout(stdout):
        cmd_review(service, args)
    mcp = _handle_review_cohort(service, {"action": "status", "cohort_id": opened["cohort_id"]})
    assert stdout.getvalue().strip() == mcp


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"action": "record", "cohort_id": 1, "round": 1, "results": "bad"}, "array"),
        ({"action": "record", "cohort_id": 1, "round": 1, "results": ["bad"]}, "objects"),
        ({"action": "status", "cohort_id": True}, "positive integer"),
        ({"action": "open", "tasks": ["a"], "story": "s"}, "exactly one"),
        (
            {
                "action": "decide",
                "cohort_id": 1,
                "decision": "manual-review",
                "owner": "owner",
                "reason": "reason",
                "finding_refs": "finding-1",
            },
            "array",
        ),
    ],
)
def test_mcp_malformed_cohort_payloads_are_controlled(payload, message, monkeypatch):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from handlers_review import _handle_review_cohort

    assert message in _handle_review_cohort(object(), payload)


def test_mcp_schema_discriminates_every_cohort_action(monkeypatch):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from tools import TOOLS

    tool = next(item for item in TOOLS if item["name"] == "tausik_task_review")
    variants = tool["inputSchema"]["properties"]["cohort"]["oneOf"]
    assert [variant["properties"]["action"]["const"] for variant in variants] == [
        "open",
        "status",
        "record",
        "decide",
    ]
    record = variants[2]
    assert {"packet_digest", "author_model", "reviewer_model", "results"} <= set(record["required"])
    result = tool["inputSchema"]["properties"]["cohort"]["properties"]["results"]["items"]
    assert result["additionalProperties"] is False
    assert "dependency_map_complete" in result["required"]


@pytest.mark.parametrize(
    ("payload", "valid"),
    [
        ({"action": "open", "tasks": ["a"]}, True),
        ({"action": "status", "cohort_id": 1}, True),
        (
            {
                "action": "record",
                "cohort_id": 1,
                "round": 1,
                "results": [_result("a")],
                "packet_digest": "digest",
                "author_model": AUTHOR,
                "reviewer_model": REVIEWER,
            },
            True,
        ),
        (
            {
                "action": "decide",
                "cohort_id": 1,
                "decision": "repair-open",
                "owner": "owner",
                "reason": "repair",
            },
            True,
        ),
        ({"action": "status", "cohort_id": 1, "tasks": ["a"]}, False),
        ({"action": "open", "tasks": ["a"], "owner": "owner"}, False),
        (
            {
                "action": "record",
                "cohort_id": 1,
                "round": 1,
                "results": [_result("a")],
                "packet_digest": "digest",
                "author_model": AUTHOR,
                "reviewer_model": REVIEWER,
                "decision": "repair-open",
            },
            False,
        ),
    ],
)
def test_mcp_schema_and_decoder_agree_on_action_fields(payload, valid, monkeypatch):
    from jsonschema import Draft202012Validator
    from review_cohort_request import decode_cohort_request

    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from tools import TOOLS

    tool = next(item for item in TOOLS if item["name"] == "tausik_task_review")
    schema = tool["inputSchema"]["properties"]["cohort"]
    assert Draft202012Validator(schema).is_valid(payload) is valid
    if valid:
        assert decode_cohort_request(payload)["action"] == payload["action"]
    else:
        with pytest.raises(ValueError, match="unknown cohort field"):
            decode_cohort_request(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"slug": "a", "cohort": {"action": "open", "tasks": ["a"]}},
        {"slug": "a", "cohort": None},
        {"slug": "a", "unexpected": True},
    ],
)
def test_mcp_task_review_envelope_refuses_ambiguous_or_unknown_fields(
    cohort_project, payload, monkeypatch
):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from handlers_task import _do_task_review

    service, _ = cohort_project
    assert _do_task_review(service, payload).startswith("Error:")
    assert service.task_show("a")["status"] == "active"
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohorts")["n"] == 0


def test_cli_and_mcp_reject_the_same_malformed_results(cohort_project, monkeypatch, capsys):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from handlers_review import _handle_review_cohort

    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    malformed = {
        "action": "record",
        "cohort_id": opened["cohort_id"],
        "round": 1,
        "results": "bad",
        "packet_digest": opened["packet"]["packet_digest"],
        "author_model": AUTHOR,
        "reviewer_model": REVIEWER,
    }
    mcp = _handle_review_cohort(service, malformed)
    args = build_parser().parse_args(
        [
            "review",
            "cohort-record",
            str(opened["cohort_id"]),
            "--round",
            "1",
            "--results-json",
            '"bad"',
            "--packet-digest",
            opened["packet"]["packet_digest"],
            "--author-model",
            AUTHOR,
            "--reviewer-model",
            REVIEWER,
        ]
    )
    with pytest.raises(SystemExit):
        cmd_review(service, args)
    cli = capsys.readouterr().err
    assert "results must be an array of objects" in cli
    assert "results must be an array of objects" in mcp


def test_external_reviewer_sample_is_accepted_by_real_cli_recorder(cohort_project):
    service, _ = cohort_project
    prompt = (
        Path(__file__).resolve().parents[1]
        / "harness"
        / "claude"
        / "subagents"
        / "tausik-external-reviewer.md"
    ).read_text(encoding="utf-8")
    sample = json.loads(
        next(line for line in prompt.splitlines() if '"persistence_command"' in line)
    )
    result = {**sample["results"][0], "task": "a"}
    assert all(isinstance(result[key], int) for key in ("critical", "high", "warnings"))

    opened = open_review_cohort(service, tasks=["a"])
    args = build_parser().parse_args(
        [
            "review",
            "cohort-record",
            str(opened["cohort_id"]),
            "--round",
            "1",
            "--results-json",
            json.dumps([result]),
            "--author-model",
            sample["meta"]["author_model"],
            "--packet-digest",
            opened["packet"]["packet_digest"],
            "--reviewer-model",
            sample["meta"]["reviewer_model"],
        ]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        cmd_review(service, args)
    assert "state green" in stdout.getvalue()


def test_record_refuses_packet_rebinding_after_review_scope_changes(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'unreviewed'\n", encoding="utf-8")

    with pytest.raises(ValueError, match="packet is stale"):
        record_review_round(
            service,
            opened["cohort_id"],
            1,
            [_result("a")],
            packet_digest=opened["packet"]["packet_digest"],
            author_model=AUTHOR,
            reviewer_model=REVIEWER,
        )


def test_open_after_issued_packet_drift_creates_fresh_generation(cohort_project):
    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    service.task_log("a", "AC-2: review evidence added after packet issue")

    fresh = open_review_cohort(service, tasks=["a"])

    assert fresh["generation"] == opened["generation"] + 1
    assert fresh["cohort_id"] != opened["cohort_id"]
    assert fresh["packet"]["packet_digest"] != opened["packet"]["packet_digest"]
    assert (
        service.be._q1("SELECT state FROM review_cohorts WHERE id=?", (opened["cohort_id"],))[
            "state"
        ]
        == "invalidated"
    )
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohort_results")["n"] == 0


def test_open_refuses_unavailable_repository_lineage(cohort_project, monkeypatch):
    service, _ = cohort_project
    monkeypatch.setattr(
        "review_cohort._head",
        lambda _root: (_ for _ in ()).throw(ValueError("repository lineage is unavailable")),
    )
    with pytest.raises(ValueError, match="lineage is unavailable"):
        open_review_cohort(service, tasks=["a"])


@pytest.mark.parametrize(
    ("results", "message"),
    [
        ([0], "must be an object"),
        ([{**_result("a"), "high": -1}], "non-negative integer"),
        ([{**_result("a"), "critical": 1}], "CRITICAL requires"),
        ([{**_result("a"), "warnings": True}], "non-negative integer"),
        ([{key: value for key, value in _result("a").items() if key != "high"}], "missing"),
        ([{**_result("a"), "hgh": 1}], "unknown"),
    ],
)
def test_malformed_results_fail_closed_without_writes(cohort_project, results, message):
    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    with pytest.raises(ValueError, match=message):
        record_review_round(
            service,
            opened["cohort_id"],
            1,
            results,
            packet_digest=opened["packet"]["packet_digest"],
            author_model=AUTHOR,
            reviewer_model=REVIEWER,
        )
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohort_rounds")["n"] == 0


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda result: result.pop("high"), "missing result field(s): high"),
        (lambda result: result.update(hgh=1), "unknown result field(s): hgh"),
    ],
)
def test_cli_and_mcp_refuse_incomplete_result_objects_without_writes(
    cohort_project, monkeypatch, capsys, mutate, message
):
    mcp_dir = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
    monkeypatch.syspath_prepend(str(mcp_dir))
    from handlers_review import _handle_review_cohort

    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    result = _result("a")
    mutate(result)
    request = {
        "action": "record",
        "cohort_id": opened["cohort_id"],
        "round": 1,
        "results": [result],
        "packet_digest": opened["packet"]["packet_digest"],
        "author_model": AUTHOR,
        "reviewer_model": REVIEWER,
    }

    mcp = _handle_review_cohort(service, request)
    args = build_parser().parse_args(
        [
            "review",
            "cohort-record",
            str(opened["cohort_id"]),
            "--round",
            "1",
            "--results-json",
            json.dumps([result]),
            "--packet-digest",
            opened["packet"]["packet_digest"],
            "--author-model",
            AUTHOR,
            "--reviewer-model",
            REVIEWER,
        ]
    )
    with pytest.raises(SystemExit):
        cmd_review(service, args)
    cli = capsys.readouterr().err

    assert message in mcp
    assert message in cli
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohort_rounds")["n"] == 0
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohort_results")["n"] == 0
    assert service.be._q1("SELECT state FROM review_cohorts")["state"] == "open"


def test_owner_decision_blocks_legacy_escape_until_manual_disposition(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    _record(service, opened["cohort_id"], 1, [_result("a", high=1)])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair'\n", encoding="utf-8")
    _record(service, opened["cohort_id"], 2, [_result("a", high=1)])
    route = json.loads(service.be._q1("SELECT routes_json FROM review_cohorts")["routes_json"])["a"]
    service.be.review_record(
        "a",
        "L3",
        author_model=AUTHOR,
        reviewer_model=REVIEWER,
        reviewer_context="different-model",
        reviewer_invocations=1,
        route_json=json.dumps(route),
    )
    service.be._conn.execute("UPDATE reviews SET run_at='2000-01-01T00:00:00Z'")
    service.be._conn.commit()
    assert "owner_decision" in review_record_blockers(service.be._conn, "a", route, tmp_path)[0]

    decide_review_cohort(
        service, opened["cohort_id"], "manual-review", owner="owner", reason="independent review"
    )
    assert (
        "awaiting_manual_review"
        in review_record_blockers(service.be._conn, "a", route, tmp_path)[0]
    )
    service.be._conn.execute(
        "UPDATE review_cohorts SET updated_at='2026-10-13T12:00:00+00:00' WHERE id=?",
        (opened["cohort_id"],),
    )
    service.be._conn.execute("UPDATE reviews SET run_at='2026-10-13T12:00:01Z'")
    service.be._conn.commit()
    assert review_record_blockers(service.be._conn, "a", route, tmp_path) == []


def test_pre_disposition_manual_receipt_stays_blocked(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    _record(service, opened["cohort_id"], 1, [_result("a", high=1)])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair'\n", encoding="utf-8")
    _record(service, opened["cohort_id"], 2, [_result("a", high=1)])
    route = json.loads(service.be._q1("SELECT routes_json FROM review_cohorts")["routes_json"])["a"]
    service.be.review_record(
        "a",
        "L3",
        author_model=AUTHOR,
        reviewer_model=REVIEWER,
        reviewer_context="different-model",
        reviewer_invocations=1,
        route_json=json.dumps(route),
    )
    service.be._conn.execute("UPDATE reviews SET run_at='2026-10-13T12:00:00Z'")
    service.be._conn.commit()
    decide_review_cohort(
        service, opened["cohort_id"], "manual-review", owner="owner", reason="fresh review"
    )
    service.be._conn.execute(
        "UPDATE review_cohorts SET updated_at='2026-10-13T12:00:01+00:00' WHERE id=?",
        (opened["cohort_id"],),
    )
    service.be._conn.commit()
    assert (
        "awaiting_manual_review"
        in review_record_blockers(service.be._conn, "a", route, tmp_path)[0]
    )


def test_parsed_timestamps_prefer_later_same_second_red_cohort(cohort_project):
    service, tmp_path = cohort_project
    route = open_review_cohort(service, tasks=["a"])
    stored_route = json.loads(
        service.be._q1("SELECT routes_json FROM review_cohorts")["routes_json"]
    )["a"]
    service.be.review_record(
        "a",
        "L3",
        author_model=AUTHOR,
        reviewer_model=REVIEWER,
        reviewer_context="different-model",
        reviewer_invocations=1,
        route_json=json.dumps(stored_route),
    )
    service.be._conn.execute("UPDATE reviews SET run_at='2026-10-13T12:00:00Z'")
    service.be._conn.commit()
    _record(service, route["cohort_id"], 1, [_result("a", high=1)])
    service.be._conn.execute(
        "UPDATE review_cohort_results SET created_at='2026-10-13T12:00:00.500000+00:00'"
    )
    service.be._conn.commit()
    assert "round1_red" in review_record_blockers(service.be._conn, "a", stored_route, tmp_path)[0]


def test_repair_open_creates_fresh_generation_without_head_change(cohort_project):
    service, tmp_path = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    _record(service, opened["cohort_id"], 1, [_result("a", high=1)])
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair-one'\n", encoding="utf-8")
    _record(service, opened["cohort_id"], 2, [_result("a", high=1)])
    decide_review_cohort(service, opened["cohort_id"], "repair-open", owner="owner", reason="retry")
    (tmp_path / "src" / "a.py").write_text("VALUE = 'repair-two'\n", encoding="utf-8")

    reopened = open_review_cohort(service, tasks=["a"])
    assert reopened["cohort_id"] != opened["cohort_id"]
    assert (reopened["generation"], reopened["state"], reopened["rounds"]) == (2, "open", "0/2")


def test_unattested_dependency_mapping_widens_round_two(cohort_project):
    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a", "b"])
    uncertain = _result("b")
    uncertain["dependency_map_complete"] = False
    _record(service, opened["cohort_id"], 1, [_result("a", high=1), uncertain])
    status = cohort_status(service, opened["cohort_id"])
    assert [item["slug"] for item in status["packet"]["tasks"]] == ["a", "b"]


def test_round_two_follows_transitive_dependents(cohort_project):
    service, tmp_path = cohort_project
    (tmp_path / "src" / "c.py").write_text("VALUE = 'c'\n", encoding="utf-8")
    service.task_add("s", "c", "C")
    service.task_update(
        "c",
        goal="change c safely",
        acceptance_criteria="AC-1: behavior is correct. AC-2: invalid input is refused.",
        scope="src/c.py",
        rollback_plan="git revert",
        relevant_files=json.dumps(["src/c.py"]),
        assurance_profiles=["executable"],
        assurance_impact={"level": "high", "blast_radius": "local", "reversibility": "reversible"},
    )
    service.task_start("c")
    service.be._conn.execute("UPDATE tasks SET started_model_id=? WHERE slug='c'", (AUTHOR,))
    service.task_log("c", "AC-1: ✓ AC-2: ✓")
    service.be._conn.executemany(
        "INSERT INTO task_deps(task_slug,depends_on_slug,created_at) VALUES(?,?,?)",
        [("b", "a", "2026-10-13T00:00:00Z"), ("c", "b", "2026-10-13T00:00:00Z")],
    )
    service.be._conn.commit()

    opened = open_review_cohort(service, tasks=["a", "b", "c"])
    _record(
        service,
        opened["cohort_id"],
        1,
        [_result("a", high=1), _result("b"), _result("c")],
    )
    (tmp_path / "src" / "a.py").write_text("VALUE = 'changed'\n", encoding="utf-8")
    status = cohort_status(service, opened["cohort_id"])
    assert [item["slug"] for item in status["packet"]["tasks"]] == ["a", "b", "c"]


def test_concurrent_round_record_has_one_winner_and_one_domain_refusal(cohort_project):
    service, _ = cohort_project
    opened = open_review_cohort(service, tasks=["a"])
    db_path = service.be.db_path

    def attempt():
        contender = ProjectService(SQLiteBackend(db_path))
        try:
            return record_review_round(
                contender,
                opened["cohort_id"],
                1,
                [_result("a")],
                packet_digest=opened["packet"]["packet_digest"],
                author_model=AUTHOR,
                reviewer_model=REVIEWER,
            )
        except ValueError as exc:
            return str(exc)
        finally:
            contender.be.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    refusal = next(outcome for outcome in outcomes if isinstance(outcome, str))
    assert "expected round" in refusal or "recorded concurrently" in refusal
    assert service.be._q1("SELECT COUNT(*) AS n FROM review_cohort_rounds")["n"] == 1


@pytest.mark.parametrize(
    "actions",
    [("accept-risk", "manual-review"), ("manual-review", "repair-open")],
)
def test_concurrent_owner_dispositions_have_one_consistent_winner(
    cohort_project, monkeypatch, actions
):
    service, tmp_path = cohort_project
    opened = _owner_decision_cohort(service, tmp_path)

    import review_cohort

    original_cohort = review_cohort._cohort
    pre_transaction_reads = Barrier(2)
    counter_lock = Lock()
    synchronized = 0

    def synchronize_old_read_window(backend, cohort_id):
        nonlocal synchronized
        row = original_cohort(backend, cohort_id)
        if row["state"] == "owner_decision" and not backend._in_tx:
            with counter_lock:
                synchronized += 1
                should_wait = synchronized <= 2
            if should_wait:
                pre_transaction_reads.wait(timeout=5)
        return row

    monkeypatch.setattr(review_cohort, "_cohort", synchronize_old_read_window)
    db_path = service.be.db_path

    def attempt(action):
        contender = ProjectService(SQLiteBackend(db_path))
        try:
            return decide_review_cohort(
                contender,
                opened["cohort_id"],
                action,
                owner=f"{action}-owner",
                reason=f"{action} reason",
                finding_refs=["finding-1"] if action == "accept-risk" else None,
            )
        except ValueError as exc:
            return str(exc)
        finally:
            contender.be.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, actions))

    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    refusal = next(outcome for outcome in outcomes if isinstance(outcome, str))
    assert "owner action is available only" in refusal or "decided concurrently" in refusal
    cohort = service.be._q1(
        "SELECT state, owner_identity, owner_reason, finding_refs_json, policy_result, "
        "updated_at FROM review_cohorts WHERE id=?",
        (opened["cohort_id"],),
    )
    result = service.be._q1(
        "SELECT verdict FROM review_cohort_results WHERE cohort_pk=? AND round_number=2",
        (opened["cohort_id"],),
    )
    expected = {
        "accepted_risk": (
            "accept-risk-owner",
            "accept-risk reason",
            '["finding-1"]',
            "HIGH risk accepted by owner; closure allowed",
            "accepted_risk",
        ),
        "awaiting_manual_review": (
            "manual-review-owner",
            "manual-review reason",
            "[]",
            "closure remains blocked",
            "red",
        ),
        "repair_open": (
            "repair-open-owner",
            "repair-open reason",
            "[]",
            "closure remains blocked",
            "red",
        ),
    }[cohort["state"]]
    assert (
        cohort["owner_identity"],
        cohort["owner_reason"],
        cohort["finding_refs_json"],
        cohort["policy_result"],
        result["verdict"],
    ) == expected
    assert cohort["updated_at"]


def test_owner_disposition_lock_timeout_is_a_controlled_refusal(cohort_project):
    service, tmp_path = cohort_project
    opened = _owner_decision_cohort(service, tmp_path)
    winner = ProjectService(SQLiteBackend(service.be.db_path))
    contender = ProjectService(SQLiteBackend(service.be.db_path))
    contender.be._conn.execute("PRAGMA busy_timeout=1")
    try:
        with winner.be.transaction():
            decided = decide_review_cohort(
                winner,
                opened["cohort_id"],
                "manual-review",
                owner="winner",
                reason="held outer transaction",
            )
            assert decided["state"] == "awaiting_manual_review"
            with pytest.raises(ValueError, match="busy|concurrently"):
                decide_review_cohort(
                    contender,
                    opened["cohort_id"],
                    "repair-open",
                    owner="contender",
                    reason="must lose cleanly",
                )
    finally:
        winner.be.close()
        contender.be.close()
    stored = service.be._q1(
        "SELECT state, owner_identity FROM review_cohorts WHERE id=?", (opened["cohort_id"],)
    )
    assert stored == {"state": "awaiting_manual_review", "owner_identity": "winner"}


def test_owner_disposition_zero_row_cas_rolls_back(cohort_project, monkeypatch):
    service, tmp_path = cohort_project
    opened = _owner_decision_cohort(service, tmp_path)
    import review_cohort

    original_cohort = review_cohort._cohort
    changed = False

    def simulate_competing_transition(backend, cohort_id):
        nonlocal changed
        row = original_cohort(backend, cohort_id)
        if backend._in_tx and row["state"] == "owner_decision" and not changed:
            changed = True
            backend._conn.execute(
                "UPDATE review_cohorts SET state='repair_open' WHERE id=?", (cohort_id,)
            )
        return row

    monkeypatch.setattr(review_cohort, "_cohort", simulate_competing_transition)
    with pytest.raises(ValueError, match="decided concurrently"):
        decide_review_cohort(
            service,
            opened["cohort_id"],
            "manual-review",
            owner="owner",
            reason="zero-row CAS",
        )
    stored = service.be._q1(
        "SELECT state, owner_identity FROM review_cohorts WHERE id=?", (opened["cohort_id"],)
    )
    assert stored == {"state": "owner_decision", "owner_identity": None}


def test_owner_disposition_result_failure_rolls_back_only_its_savepoint(cohort_project):
    service, tmp_path = cohort_project
    opened = _owner_decision_cohort(service, tmp_path)
    service.be._conn.execute(
        "CREATE TRIGGER fail_accept BEFORE UPDATE OF verdict ON review_cohort_results "
        "BEGIN SELECT RAISE(ABORT, 'forced result failure'); END"
    )
    with service.be.transaction():
        service.be._conn.execute("UPDATE tasks SET title='caller survives' WHERE slug='b'")
        with pytest.raises(sqlite3.IntegrityError, match="forced result failure"):
            decide_review_cohort(
                service,
                opened["cohort_id"],
                "accept-risk",
                owner="owner",
                reason="must roll back",
                finding_refs=["finding-1"],
            )
    assert service.task_show("b")["title"] == "caller survives"
    cohort = service.be._q1(
        "SELECT state, owner_identity FROM review_cohorts WHERE id=?", (opened["cohort_id"],)
    )
    result = service.be._q1(
        "SELECT verdict FROM review_cohort_results WHERE cohort_pk=? AND round_number=2",
        (opened["cohort_id"],),
    )
    assert cohort == {"state": "owner_decision", "owner_identity": None}
    assert result["verdict"] == "red"
