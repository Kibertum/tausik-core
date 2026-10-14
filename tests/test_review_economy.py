"""Acceptance economics for bounded two-round L3 review."""

from __future__ import annotations

from review_economy import economy_benchmark, format_row


def test_one_two_five_task_scenarios_bound_calls_and_green_rechecks():
    rows = economy_benchmark(repeats=10)
    assert [(row["tasks"], row["legacy"]["reviewer_invocations"]) for row in rows] == [
        (1, 2),
        (2, 4),
        (5, 10),
    ]
    assert [row["bounded"]["reviewer_invocations"] for row in rows] == [2, 2, 2]
    assert [row["legacy"]["re_reviewed_green_tasks"] for row in rows] == [0, 1, 4]
    assert all(row["bounded"]["re_reviewed_green_tasks"] == 0 for row in rows)


def test_unmeasured_tokens_are_reported_not_estimated():
    row = economy_benchmark(sizes=(5,), repeats=1)[0]
    assert row["legacy"]["tokens_total"] is None
    assert row["bounded"]["tokens_total"] is None
    assert row["evidence_kind"] == "protocol-model"
    assert format_row(row).count("tokens=unavailable") == 2
    assert "scheduler_elapsed_ms" not in row["legacy"]
    assert "scheduler_elapsed_ms" not in row["bounded"]


def test_measured_tokens_are_preserved_and_rendered():
    row = economy_benchmark(
        sizes=(2,), repeats=1, token_telemetry={2: {"legacy": 1200, "bounded": 700}}
    )[0]
    assert row["legacy"]["tokens_total"] == 1200
    assert row["bounded"]["tokens_total"] == 700
    assert "tokens=1200" in format_row(row)
    assert "tokens=700" in format_row(row)


def test_negative_token_telemetry_is_refused():
    try:
        economy_benchmark(sizes=(1,), repeats=1, token_telemetry={1: {"legacy": -1}})
    except ValueError as exc:
        assert "cannot be negative" in str(exc)
    else:
        raise AssertionError("negative telemetry must be refused")
