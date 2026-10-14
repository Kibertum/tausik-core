"""Behavioral coverage for the bounded-L3 baseline counter."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from review_baseline import format_baseline_line, review_baseline


def _backend(tmp_path):
    return SQLiteBackend(str(tmp_path / "review-baseline.db"))


def _seed_story(backend, story, slugs):
    if backend.epic_get("e") is None:
        backend.epic_add("e", "E")
    backend.story_add("e", story, story)
    for slug in slugs:
        backend.task_add(story, slug, slug, goal="g", role="developer")


def _record(backend, slug, *, tokens=None, cost=None, critical=0, high=0, warnings=0):
    usage = {"tokens_total": tokens, "cost_usd": cost}
    return backend.review_record(
        slug,
        "L3",
        critical_findings=critical,
        high_findings=high,
        warnings=warnings,
        author_model="gpt-5.6-sol",
        reviewer_model="gpt-6-astra",
        reviewer_context="different-model",
        reviewer_invocations=1,
        usage_json=json.dumps(usage),
    )


def _record_cohort(backend, slugs, *, critical=0):
    stamp = "2026-10-13T12:00:01+00:00"
    cohort_id = backend._ins(
        "INSERT INTO review_cohorts(cohort_key,selector_kind,selector_value,members_json,"
        "routes_json,policy_signature,opening_lineage,state,current_round,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,'green',1,?,?)",
        ("cohort-key", "tasks", json.dumps(slugs), json.dumps(slugs), "{}", "p", "h", stamp, stamp),
    )
    backend._ins(
        "INSERT INTO review_cohort_rounds(cohort_pk,round_number,packet_json,author_model,"
        "reviewer_model,reviewer_context,reviewer_invocations,usage_json,recorded_at) "
        "VALUES(?,1,'{}','gpt-5.6-sol','gpt-6-astra','different-model',1,?,?)",
        (cohort_id, json.dumps({"tokens_total": 50}), stamp),
    )
    for index, slug in enumerate(slugs):
        backend._ins(
            "INSERT INTO review_cohort_results(cohort_pk,round_number,task_slug,verdict,"
            "critical_findings,high_findings,warnings,reviewed_state_fingerprint,route_json,"
            "carried_forward,notes,created_at,author_model,dependency_map_complete) "
            "VALUES(?,1,?,'green',?,0,0,?,'{}',?,?,?,'gpt-5.6-sol',1)",
            (
                cohort_id,
                slug,
                critical if index == 0 else 0,
                f"fp-{slug}",
                1 if index == len(slugs) - 1 and len(slugs) > 1 else 0,
                "carried" if index == len(slugs) - 1 and len(slugs) > 1 else None,
                stamp,
            ),
        )
    return cohort_id


def test_counts_repeated_unchanged_state_and_measured_tokens(tmp_path):
    backend = _backend(tmp_path)
    try:
        _seed_story(backend, "solo-story", ["solo"])
        _record(backend, "solo", tokens=120, cost=0.25, high=1)
        _record(backend, "solo", warnings=2)

        stats = review_baseline(backend.db_path)["cohort-of-1"]
        assert stats == {
            "cohorts": 1,
            "tasks": 1,
            "task_seats": 1,
            "review_records": 2,
            "reviewer_invocations_paid": 2,
            "invocation_records_measured": 2,
            "repeated_task_reviews": 1,
            "fingerprint_records_measured": 2,
            "repeated_unchanged_state_reviews": 1,
            "critical_findings": 0,
            "high_findings": 1,
            "warnings": 2,
            "token_records_measured": 1,
            "tokens_total_measured": 120,
            "cost_records_measured": 1,
            "cost_usd_measured": 0.25,
        }
        line = format_baseline_line("cohort-of-1", stats)
        assert "tokens=120 (1/2 records)" in line
        assert "cost_usd=0.250000 (1/2 records)" in line
    finally:
        backend.close()


def test_buckets_task_cohorts_by_distinct_membership(tmp_path):
    backend = _backend(tmp_path)
    try:
        _seed_story(backend, "pair", ["p1", "p2"])
        _seed_story(backend, "large", [f"b{i}" for i in range(5)])
        for slug in ["p1", "p2", *[f"b{i}" for i in range(5)]]:
            _record(backend, slug)

        stats = review_baseline(backend.db_path)
        assert stats["cohort-of-2"]["task_seats"] == 2
        assert stats["cohort-of-2"]["review_records"] == 2
        assert stats["cohort-of-5+"]["task_seats"] == 5
        assert stats["cohort-of-5+"]["review_records"] == 5
    finally:
        backend.close()


def test_legacy_record_is_unknown_not_fabricated_measurement(tmp_path):
    backend = _backend(tmp_path)
    try:
        _seed_story(backend, "legacy", ["legacy-task"])
        review_id = _record(backend, "legacy-task")
        backend._conn.execute(
            "UPDATE reviews SET reviewer_invocations=0, usage_json=NULL, "
            "reviewed_state_fingerprint=NULL WHERE id=?",
            (review_id,),
        )
        backend._conn.commit()

        stats = review_baseline(backend.db_path)["cohort-of-1"]
        assert stats["review_records"] == 1
        assert stats["reviewer_invocations_paid"] == 0
        assert stats["invocation_records_measured"] == 0
        assert stats["token_records_measured"] == 0
        assert stats["fingerprint_records_measured"] == 0
        assert stats["repeated_unchanged_state_reviews"] is None
        line = format_baseline_line("cohort-of-1", stats)
        assert "unavailable repeated unchanged-state" in line
        assert "tokens=unavailable (0/1 records)" in line
        assert "cost_usd=unavailable (0/1 records)" in line
    finally:
        backend.close()


def test_mixed_legacy_and_cohort_history_excludes_carried_rows(tmp_path):
    backend = _backend(tmp_path)
    try:
        _seed_story(backend, "mixed", ["legacy", "cohort", "carried"])
        legacy_id = _record(backend, "legacy", critical=1)
        backend._conn.execute(
            "UPDATE reviews SET run_at='2026-10-13T12:00:00Z' WHERE id=?", (legacy_id,)
        )
        _record_cohort(backend, ["cohort", "carried"], critical=2)
        backend._conn.commit()

        listed = backend.review_list(run_type="L3")
        assert {(row["source"], row["task_slug"]) for row in listed} == {
            ("legacy", "legacy"),
            ("cohort", "cohort"),
        }
        assert backend.review_metrics() == {
            "l3_reviewed_tasks": 2,
            "l3_critical_findings": 3,
            "adr_pct": 150.0,
        }
        stats = review_baseline(backend.db_path)["cohort-of-2"]
        assert stats["review_records"] == 2
        assert stats["reviewer_invocations_paid"] == 2
        assert stats["critical_findings"] == 3
    finally:
        backend.close()
