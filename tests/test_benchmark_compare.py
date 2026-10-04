"""Natural cohort comparison remains observational, priced, and fail-closed."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

import pytest

from benchmark_cohorts import capture_observations
from benchmark_compare import compare_cohorts, persist_snapshot
from project_backend import SQLiteBackend
from project_parser import build_parser
from usage_observation import observation

_MCP_PROJECT = Path(__file__).resolve().parents[1] / "harness" / "claude" / "mcp" / "project"
sys.path.insert(0, str(_MCP_PROJECT))


@pytest.fixture
def backend(tmp_path):
    value = SQLiteBackend(str(tmp_path / "state.db"))
    yield value
    value.close()


def _task(conn, slug, version, *, resolution=None, completed="2026-10-01T00:01:00Z"):
    conn.execute(
        """INSERT INTO tasks(
            slug,title,status,attempts,complexity,assurance_profiles,assurance_impact,
            started_tausik_version,done_tausik_version,resolution,started_at,completed_at,
            created_at,updated_at
        ) VALUES(?,?,'done',2,'medium','["executable"]','{"level":"medium"}',
                 ?,?,?, '2026-10-01T00:00:00Z',?,'2026-10-01','2026-10-02')""",
        (slug, slug, version, version, resolution, completed),
    )


def _response(slug, response, *, model="gpt-5", timestamp="2026-10-01T00:00:30Z"):
    row = observation(
        {"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20},
        "codex",
        observed={
            "host": "codex",
            "host_version": "1",
            "provider": "openai",
            "model": model,
            "reasoning": "high",
            "speed": "standard",
        },
        source={
            "timestamp": timestamp,
            "project": "p",
            "thread": slug,
            "response": response,
            "task": slug,
        },
        attribution="exact",
    )
    row["tool_calls"] = 3
    row["active_duration_ms"] = 1_000
    return row


def _card(*, model="gpt-5", valid_until="2026-12-31"):
    return {
        "api_equivalent_usd_rate_card": {
            "source": "https://provider.example/pricing/2026-10-01",
            "as_of": "2026-10-01",
            "valid_until": valid_until,
            "unit": "usd_per_million_tokens",
            "models": {
                f"openai/{model}": {
                    "uncached_input": 2,
                    "cached_input": 1,
                    "output": 10,
                }
            },
        }
    }


def _seed_pair(conn):
    for version in ("1.11.0", "1.11.1"):
        for number in (1, 2):
            slug = f"v{version[-1]}-{number}"
            _task(conn, slug, version)
            capture_observations(conn, [_response(slug, f"r-{slug}")])


def test_version_comparison_reports_task_distributions_price_quality_and_strata(backend):
    conn = backend._conn
    _seed_pair(conn)
    report = compare_cohorts(
        conn,
        {"label": "before", "tausik_version": "1.11.0", "model": "gpt-5"},
        {"label": "after", "tausik_version": "1.11.1", "model": "gpt-5"},
        config=_card(),
        minimum_sample=2,
        generated_at="2026-10-04T00:00:00Z",
    )

    assert report["status"] == "comparable"
    left = report["cohorts"]["left"]
    assert left["metrics"]["uncached_input"] == {
        "median": 60,
        "p90": 60,
        "coverage": {"known": 2, "total": 2},
    }
    assert left["metrics"]["total_tokens"]["median"] == 120
    assert left["api_equivalent_usd"]["total"] == pytest.approx(0.00072)
    assert left["api_equivalent_usd"]["breakdown"] == {
        "uncached_input": 0.00024,
        "cached_input": 0.00008,
        "output": 0.0004,
        "coverage": {"known": 2, "total": 2},
    }
    assert left["quality"]["verification_failure_rate"] is None
    assert left["quality"]["reviewer_invocations"] is None
    assert left["strata"][0]["profiles"] == ["executable"]
    assert report["subscription"]["credits"] is None


def test_legacy_review_zero_stays_unknown_while_modern_zero_is_measured(backend):
    conn = backend._conn
    _seed_pair(conn)
    for slug, route in (("v0-1", "{}"), ("v0-2", None), ("v1-1", "{}"), ("v1-2", "{}")):
        conn.execute(
            "INSERT INTO reviews(task_slug,run_type,critical_findings,warnings,run_at,"
            "reviewer_invocations,route_json) VALUES (?, 'L1', 0, 0, '2026-10-02', 0, ?)",
            (slug, route),
        )

    report = compare_cohorts(
        conn,
        {"tausik_version": "1.11.0"},
        {"tausik_version": "1.11.1"},
        config=_card(),
        minimum_sample=2,
        generated_at="2026-10-04T00:00:00Z",
    )

    assert report["cohorts"]["left"]["quality"]["reviewer_invocations"] is None
    assert report["cohorts"]["right"]["quality"]["reviewer_invocations"] == 0


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        ("below-sample", "left-below-minimum-sample"),
        ("mixed-model", "left-mixed-version-or-model-settings"),
        ("version-crossing", "left-below-minimum-sample"),
    ],
)
def test_ineligible_natural_cohorts_are_inconclusive(backend, mutation, expected_reason):
    conn = backend._conn
    _task(conn, "one", "1.11.0")
    capture_observations(conn, [_response("one", "r1")])
    if mutation == "mixed-model":
        capture_observations(conn, [_response("one", "r2", model="gpt-6")])
        left = {"label": "mixed"}
    elif mutation == "version-crossing":
        conn.execute("UPDATE tasks SET done_tausik_version='1.11.1' WHERE slug='one'")
        conn.execute("DELETE FROM benchmark_observations")
        capture_observations(conn, [_response("one", "r3")])
        left = {"tausik_version": "1.11.0"}
    else:
        left = {"tausik_version": "1.11.0"}
    report = compare_cohorts(
        conn,
        left,
        {"tausik_version": "1.11.1"},
        minimum_sample=2,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert report["status"] == "inconclusive"
    assert expected_reason in report["reasons"]


def test_duplicates_obsolete_missing_and_stale_prices_never_become_zero(backend):
    conn = backend._conn
    _task(conn, "kept", "1.11.0")
    _task(conn, "obsolete", "1.11.0", resolution="obsolete")
    kept = _response("kept", "same")
    assert capture_observations(conn, [kept, kept])["repeated"] == 1
    capture_observations(conn, [_response("obsolete", "r-obsolete")])

    missing = compare_cohorts(
        conn,
        {"tausik_version": "1.11.0"},
        {"tausik_version": "1.11.1"},
        minimum_sample=1,
        generated_at="2026-10-04T00:00:00Z",
    )
    stale = compare_cohorts(
        conn,
        {"tausik_version": "1.11.0"},
        {"tausik_version": "1.11.1"},
        config=_card(valid_until="2026-10-02"),
        minimum_sample=1,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert missing["cohorts"]["left"]["sample_size"] == 1
    assert missing["cohorts"]["left"]["api_equivalent_usd"]["total"] is None
    assert missing["rate_card"]["status"] == "rate-card-unconfigured"
    assert stale["rate_card"]["status"] == "rate-card-stale"
    assert stale["cohorts"]["left"]["api_equivalent_usd"]["total"] is None


def test_immature_defect_window_is_unknown_and_snapshot_omits_members(backend, tmp_path):
    conn = backend._conn
    _task(conn, "parent", "1.11.0")
    capture_observations(conn, [_response("parent", "r-parent")])
    conn.execute(
        """INSERT INTO tasks(slug,title,status,defect_of,created_at,updated_at)
           VALUES('escaped','escaped','active','parent','2026-10-03','2026-10-03')"""
    )
    report = compare_cohorts(
        conn,
        {"tausik_version": "1.11.0"},
        {"tausik_version": "1.11.1"},
        minimum_sample=1,
        maturation_days=30,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert report["cohorts"]["left"]["quality"]["downstream_defect_escapes"] is None
    path = persist_snapshot(report, tmp_path / "comparison.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "tasks" not in payload["cohorts"]["left"]
    assert payload["membership_hashes"]["left"]
    assert "parent" not in path.read_text(encoding="utf-8")


def test_cli_accepts_version_model_and_time_selectors():
    args = build_parser().parse_args(
        [
            "metrics",
            "compare",
            "--left-version",
            "1.11.0",
            "--right-version",
            "1.11.1",
            "--left-model",
            "gpt-5",
            "--right-model",
            "gpt-5",
            "--left-since",
            "2026-09-01",
            "--right-until",
            "2026-10-31",
        ]
    )
    assert args.metrics_cmd == "compare"
    assert args.left_version == "1.11.0" and args.right_model == "gpt-5"
    assert args.left_since == "2026-09-01" and args.right_until == "2026-10-31"


def test_time_selector_normalizes_z_and_offset_timestamps(backend):
    conn = backend._conn
    _task(conn, "inside", "1.11.0")
    capture_observations(
        conn,
        [_response("inside", "r-time", timestamp="2026-10-01T00:00:00.500Z")],
    )
    report = compare_cohorts(
        conn,
        {"since": "2026-10-01T00:00:00+00:00", "until": "2026-10-01T00:00:01Z"},
        {"since": "2026-11-01T00:00:00Z"},
        minimum_sample=1,
        generated_at="2026-10-04T00:00:00Z",
    )
    assert report["cohorts"]["left"]["sample_size"] == 1
    assert report["cohorts"]["right"]["sample_size"] == 0


def test_mcp_comparison_uses_the_same_service(tmp_path, backend):
    from handlers_status import _handle_metrics

    class Service:
        be = backend

        @staticmethod
        def tausik_dir():
            return str(tmp_path / ".tausik")

    payload = json.loads(
        _handle_metrics(
            Service(),
            {
                "view": "comparison",
                "compare": {
                    "left": {"tausik_version": "1.11.0"},
                    "right": {"tausik_version": "1.11.1"},
                    "minimum_sample": 1,
                },
            },
        )
    )
    assert payload["status"] == "inconclusive"
    assert payload["query"]["minimum_sample"] == 1


def test_mcp_comparison_writes_only_a_new_project_artifact(tmp_path, backend):
    from handlers_status import _handle_metrics

    class Service:
        be = backend

        @staticmethod
        def tausik_dir():
            return str(tmp_path / ".tausik")

    args = {
        "view": "comparison",
        "compare": {
            "left": {"tausik_version": "1.11.0"},
            "right": {"tausik_version": "1.11.1"},
            "minimum_sample": 1,
            "snapshot_path": "release-comparison.json",
        },
    }
    _handle_metrics(Service(), args)
    target = (
        tmp_path / ".tausik" / "artifacts" / "benchmark-comparisons" / "release-comparison.json"
    )
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "inconclusive"
    with pytest.raises(FileExistsError, match="already exists"):
        _handle_metrics(Service(), args)


def test_snapshot_creation_is_atomic_under_competing_writers(tmp_path):
    target = tmp_path / "comparison.json"
    barrier = Barrier(2)

    def create(status):
        barrier.wait()
        try:
            return persist_snapshot({"status": status, "cohorts": {}}, target)
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ["left", "right"]))

    assert sum(result is not None for result in results) == 1
    assert json.loads(target.read_text(encoding="utf-8"))["status"] in {"left", "right"}


@pytest.mark.parametrize("requested", ["../escape.json", "nested/escape.json"])
def test_mcp_comparison_rejects_snapshot_traversal(tmp_path, backend, requested):
    from handlers_status import _handle_metrics

    class Service:
        be = backend

        @staticmethod
        def tausik_dir():
            return str(tmp_path / ".tausik")

    with pytest.raises(ValueError, match="snapshot_path"):
        _handle_metrics(
            Service(),
            {
                "view": "comparison",
                "compare": {
                    "left": {},
                    "right": {},
                    "minimum_sample": 1,
                    "snapshot_path": requested,
                },
            },
        )


def test_mcp_comparison_rejects_an_absolute_snapshot_path(tmp_path, backend):
    from handlers_status import _handle_metrics

    class Service:
        be = backend

        @staticmethod
        def tausik_dir():
            return str(tmp_path / ".tausik")

    with pytest.raises(ValueError, match="snapshot_path"):
        _handle_metrics(
            Service(),
            {
                "view": "comparison",
                "compare": {
                    "left": {},
                    "right": {},
                    "minimum_sample": 1,
                    "snapshot_path": str((tmp_path / "outside.json").resolve()),
                },
            },
        )
