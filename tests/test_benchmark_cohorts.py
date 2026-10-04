"""Natural-work benchmark storage and cohort projection behavior."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from benchmark_cohorts import (
    capture_for_project,
    capture_observations,
    cohort_inventory,
    render_inventory,
)
from model_pinning import model_done_updates, model_start_updates
from project_backend import SQLiteBackend
from project_cli_metrics import cmd_metrics
from project_parser import build_parser
from usage_observation import observation

_MCP_PROJECT = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
sys.path.insert(0, str(_MCP_PROJECT))


@pytest.fixture
def backend(tmp_path):
    value = SQLiteBackend(str(tmp_path / "state.db"))
    yield value
    value.close()


def _task(conn: sqlite3.Connection, slug: str, *, version="1.11.1", resolution=None):
    conn.execute(
        """INSERT INTO tasks(
            slug,title,status,attempts,started_tausik_version,done_tausik_version,resolution,
            started_at,completed_at,created_at,updated_at
        ) VALUES(?,?,'done',2,?,?,?, '2026-10-01T00:00:00Z',
            '2026-10-01T00:01:00Z','2026-10-01','2026-10-02')""",
        (slug, slug, version, version, resolution),
    )


def _row(task: str | None, response: str, *, model="gpt-5", missing_output=False):
    return observation(
        {"input_tokens": 100, **({} if missing_output else {"output_tokens": 20})},
        "codex",
        observed={
            "host": "codex",
            "host_version": "1.2.3",
            "provider": "openai",
            "model": model,
            "reasoning": "high",
            "speed": "standard",
        },
        source={
            "timestamp": "2026-10-02T00:00:00Z",
            "project": "project-hash",
            "thread": "thread-hash",
            "response": response,
            "task": task,
        },
        attribution="exact" if task else "project",
    )


def test_capture_is_idempotent_private_and_uses_boundary_version(backend):
    conn = backend._conn
    _task(conn, "accepted")
    row = _row("accepted", "response-hash")
    row["prompt"] = "SECRET-PROMPT-DO-NOT-PERSIST"
    row["source"]["transcript"] = "SECRET-RESPONSE-DO-NOT-PERSIST"

    first = capture_observations(conn, [row])
    second = capture_observations(conn, [row])

    assert first == {"inserted": 1, "updated": 0, "repeated": 0, "unkeyed": 0}
    assert second == {"inserted": 0, "updated": 0, "repeated": 1, "unkeyed": 0}
    stored = dict(conn.execute("SELECT * FROM benchmark_observations").fetchone())
    assert stored["tausik_version"] == "1.11.1"
    assert stored["tokens_input"] == 100 and stored["tokens_output"] == 20
    assert "prompt" not in stored and "response" not in stored
    assert stored["source_key"] != "response-hash"
    conn.commit()
    db_bytes = Path(backend.db_path).read_bytes()
    assert b"SECRET-PROMPT" not in db_bytes and b"SECRET-RESPONSE" not in db_bytes


def test_finalized_native_response_updates_partial_observation(backend):
    conn = backend._conn
    _task(conn, "accepted")
    partial = _row("accepted", "same-response")
    partial["tokens"]["output"] = 1
    finalized = _row("accepted", "same-response")
    finalized["tokens"]["output"] = 50

    capture_observations(conn, [partial])
    result = capture_observations(conn, [finalized])

    assert result == {"inserted": 0, "updated": 1, "repeated": 0, "unkeyed": 0}
    assert conn.execute("SELECT tokens_output FROM benchmark_observations").fetchone()[0] == 50


def test_cross_version_work_window_stays_unclassified(backend):
    conn = backend._conn
    _task(conn, "accepted")
    conn.execute(
        "UPDATE tasks SET started_tausik_version='1.11.0',done_tausik_version='1.11.1' "
        "WHERE slug='accepted'"
    )

    capture_observations(conn, [_row("accepted", "r1")])

    assert cohort_inventory(conn)["cohorts"][0]["identity"]["tausik_version"] is None


def test_configured_identity_basis_is_preserved(backend):
    conn = backend._conn
    _task(conn, "accepted")
    row = observation(
        {"input_tokens": 1, "output_tokens": 1},
        "codex",
        observed={"host": "codex", "provider": "openai"},
        configured={"model": "gpt-configured", "reasoning": "high", "speed": "fast"},
        source={"project": "p", "thread": "t", "response": "r", "task": "accepted"},
        attribution="exact",
    )

    capture_observations(conn, [row])
    cohort = cohort_inventory(conn)["cohorts"][0]

    assert cohort["identity"]["model"] == "gpt-configured"
    assert cohort["identity_basis"]["model"] == "configured"
    assert cohort["identity_basis"]["host"] == "observed"


def test_unknown_task_attribution_is_downgraded_without_fk_damage(backend):
    conn = backend._conn

    capture_observations(conn, [_row("missing-task", "r1")])

    stored = conn.execute(
        "SELECT task_slug,attribution_confidence FROM benchmark_observations"
    ).fetchone()
    assert tuple(stored) == (None, "project")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_identity_changes_form_distinct_cohorts_without_losing_task_cost(backend):
    conn = backend._conn
    _task(conn, "accepted")
    capture_observations(
        conn,
        [_row("accepted", "r1", model="gpt-5"), _row("accepted", "r2", model="gpt-6")],
    )

    result = cohort_inventory(conn)

    assert [item["identity"]["model"] for item in result["cohorts"]] == ["gpt-5", "gpt-6"]
    assert [item["sample_size"] for item in result["cohorts"]] == [1, 1]
    assert [item["totals"]["input"] for item in result["cohorts"]] == [100, 100]
    assert [item["attempts"] for item in result["cohorts"]] == [None, None]
    assert result["unsplit_task_evidence"]["tasks"] == ["accepted"]
    assert result["unsplit_task_evidence"]["attempts"] == 2
    assert result["coverage"]["accepted_tasks"] == 1


def test_missing_values_and_legacy_identity_stay_unknown(backend):
    conn = backend._conn
    _task(conn, "legacy", version=None)
    capture_observations(conn, [_row("legacy", "r1", missing_output=True)])

    cohort = cohort_inventory(conn)["cohorts"][0]

    assert cohort["classification"] == "legacy/unclassified"
    assert cohort["identity"]["tausik_version"] is None
    assert cohort["totals"]["output"] is None
    assert cohort["coverage"]["output"] == {"known": 0, "total": 1}


def test_obsolete_and_inexact_work_never_enters_accepted_cohorts(backend):
    conn = backend._conn
    _task(conn, "obsolete", resolution="obsolete")
    capture_observations(conn, [_row("obsolete", "r1"), _row(None, "r2")])

    result = cohort_inventory(conn)

    assert result["cohorts"] == []
    assert result["coverage"]["accepted_observations"] == 0
    assert result["unattributed"]["observations"] == 1
    assert result["unaccepted"]["observations"] == 1


def test_quality_and_retry_maturity_join_existing_evidence(backend):
    conn = backend._conn
    _task(conn, "accepted")
    row = _row("accepted", "r1")
    row["active_duration_ms"] = 60_000
    capture_observations(conn, [row])
    conn.executemany(
        """INSERT INTO reviews(
            task_slug,run_type,run_at,reviewer_invocations,route_json
        ) VALUES('accepted',?,?,1,'{}')""",
        [("L2", "2026-10-01"), ("L3", "2026-10-02")],
    )
    conn.execute(
        """INSERT INTO verification_runs(
            task_slug,scope,command,exit_code,files_hash,ran_at
        ) VALUES('accepted','critical','pytest',0,'hash','2026-10-02')"""
    )
    conn.executemany(
        """INSERT INTO usage_events(
            task_slug,source,recorded_at,tool_calls
        ) VALUES('accepted','posttool',?,0)""",
        [("2026-10-01T00:00:10Z",), ("2026-10-01T00:00:20Z",)],
    )

    cohort = cohort_inventory(conn)["cohorts"][0]

    assert cohort["attempts"] == 2 and cohort["retries"] == 1
    assert cohort["quality"]["review_levels"] == ["L2", "L3"]
    assert cohort["quality"]["reviewer_invocations"] == 2
    assert cohort["quality"]["verification"]["passed"] == 1
    assert cohort["quality"]["verification"]["runs"] == 1
    assert cohort["totals"]["tool_calls"] == 2
    assert cohort["totals"]["active_duration_ms"] == 60_000
    assert "1.11.1 | codex/openai/gpt-5" in render_inventory(cohort_inventory(conn))


def test_legacy_review_default_does_not_claim_observed_zero_invocations(backend):
    conn = backend._conn
    _task(conn, "accepted")
    capture_observations(conn, [_row("accepted", "r1")])
    conn.execute(
        "INSERT INTO reviews(task_slug,run_type,run_at) VALUES('accepted','L3','2026-10-02')"
    )

    quality = cohort_inventory(conn)["cohorts"][0]["quality"]

    assert quality["reviewed_tasks"] == 1
    assert quality["reviewer_invocations"] is None
    assert quality["review_invocation_coverage"] == {"known": 0, "total": 1}


def test_mixed_review_provenance_keeps_per_task_invocation_coverage(backend):
    conn = backend._conn
    for slug in ("modern", "legacy"):
        _task(conn, slug)
        capture_observations(conn, [_row(slug, f"{slug}-run")])
    conn.execute(
        """INSERT INTO reviews(
            task_slug,run_type,run_at,reviewer_invocations,route_json
        ) VALUES('modern','L3','2026-10-02',1,'{}')"""
    )
    conn.execute(
        "INSERT INTO reviews(task_slug,run_type,run_at) VALUES('legacy','L3','2026-10-02')"
    )

    quality = cohort_inventory(conn)["cohorts"][0]["quality"]

    assert quality["reviewer_invocations"] is None
    assert quality["review_invocation_coverage"] == {"known": 1, "total": 2}


def test_unsplit_review_total_requires_evidence_for_every_mixed_task(backend):
    conn = backend._conn
    for slug in ("one", "two"):
        _task(conn, slug)
        capture_observations(
            conn,
            [_row(slug, f"{slug}-a", model="gpt-5"), _row(slug, f"{slug}-b", model="gpt-6")],
        )
    conn.execute(
        """INSERT INTO reviews(
            task_slug,run_type,run_at,reviewer_invocations,route_json
        ) VALUES('one','L3','2026-10-02',1,'{}')"""
    )

    unsplit = cohort_inventory(conn)["unsplit_task_evidence"]

    assert unsplit["reviewer_invocations"] is None
    assert unsplit["review_invocation_coverage"] == {"known": 1, "total": 2}


def test_elapsed_boundaries_and_missing_attempts_stay_unknown(backend):
    conn = backend._conn
    _task(conn, "accepted")
    conn.execute(
        "UPDATE tasks SET attempts=NULL,completed_at='2026-10-03T00:00:00Z' WHERE slug='accepted'"
    )
    capture_observations(conn, [_row("accepted", "r1")])

    cohort = cohort_inventory(conn)["cohorts"][0]

    assert cohort["attempts"] is None and cohort["retries"] is None
    assert cohort["attempt_coverage"] == {"known": 0, "total": 1}
    assert cohort["totals"]["active_duration_ms"] is None
    assert cohort["quality"]["reviewer_invocations"] is None


def test_lifecycle_helpers_pin_installed_version_without_backfilling_history(backend):
    from tausik_version import __version__

    assert model_start_updates(backend)["started_tausik_version"] == __version__
    updates, _ = model_done_updates(backend, {"slug": "not-recorded", "started_model_id": None})
    assert updates["done_tausik_version"] == __version__


def test_cli_and_mcp_expose_the_same_inventory(backend):
    from handlers_status import _handle_metrics

    args = build_parser().parse_args(["metrics", "cohorts", "--json"])
    assert args.metrics_cmd == "cohorts" and args.as_json is True

    class Service:
        be = backend

    payload = _handle_metrics(Service(), {"view": "cohorts"})
    assert '"cohorts": []' in payload
    assert '"accepted_tasks": 0' in payload


def test_cli_renders_inventory_and_mcp_schema_advertises_it(backend, capsys):
    from tools import TOOLS

    class Service:
        be = backend

    args = build_parser().parse_args(["metrics", "cohorts"])
    cmd_metrics(Service(), args)
    assert "Coverage: 0/0 observation(s)" in capsys.readouterr().out
    metrics = next(tool for tool in TOOLS if tool["name"] == "tausik_metrics")
    assert metrics["inputSchema"]["properties"]["view"]["enum"] == [
        "summary",
        "cohorts",
        "comparison",
    ]


def test_project_capture_survives_restart_without_duplicate(tmp_path):
    db = tmp_path / ".tausik" / "tausik.db"
    db.parent.mkdir()
    backend = SQLiteBackend(str(db))
    _task(backend._conn, "accepted")
    backend._conn.commit()
    backend.close()

    first = capture_for_project(tmp_path, [_row("accepted", "r1")])
    second = capture_for_project(tmp_path, [_row("accepted", "r1")])

    assert first["inserted"] == 1 and second["repeated"] == 1
    reopened = SQLiteBackend(str(db), read_only=True)
    try:
        assert cohort_inventory(reopened._conn)["coverage"]["accepted_observations"] == 1
    finally:
        reopened.close()


def test_v70_upgrade_keeps_legacy_tasks_unclassified():
    from backend_migrations_v70 import MIGRATION_V70

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE tasks(slug TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO tasks(slug) VALUES('legacy')")
    for statement in MIGRATION_V70:
        conn.execute(statement)

    row = conn.execute(
        "SELECT started_tausik_version,done_tausik_version FROM tasks WHERE slug='legacy'"
    ).fetchone()
    assert row == (None, None)
    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='benchmark_observations'"
    ).fetchone()
