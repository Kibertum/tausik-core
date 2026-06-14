"""v15mr-routing-telemetry: recommended-vs-actual model adherence telemetry."""

from __future__ import annotations

import json
import os
from pathlib import Path

from model_routing_adherence import aggregate_adherence, record_adherence
from project_backend import SQLiteBackend
from project_service import ProjectService


def _read_rows(tausik_dir: str) -> list[dict]:
    path = os.path.join(tausik_dir, "routing_adherence.jsonl")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --- AC1: record a recommended/actual pair -----------------------------------


class TestRecord:
    def test_records_matching_pair(self, tmp_path):
        row = record_adherence(str(tmp_path), "t1", "claude-sonnet-4-6", "claude-sonnet-4-6")
        assert row is not None
        assert row["match"] is True
        assert row["recommended_family"] == "sonnet"
        assert row["actual_family"] == "sonnet"
        assert _read_rows(str(tmp_path)) == [row]

    def test_records_mismatch_by_family(self, tmp_path):
        row = record_adherence(str(tmp_path), "t1", "claude-opus-4-8", "claude-sonnet-4-6")
        assert row is not None
        assert row["match"] is False
        assert row["recommended_family"] == "opus"
        assert row["actual_family"] == "sonnet"

    def test_point_release_counts_as_match(self, tmp_path):
        # Same family, different point release / 1M suffix -> still adherent.
        row = record_adherence(str(tmp_path), "t1", "claude-opus-4-8", "claude-opus-4-7[1m]")
        assert row is not None and row["match"] is True


# --- AC3: negative — missing / unknown inputs skip without error -------------


class TestNegative:
    def test_missing_actual_skips_no_file(self, tmp_path):
        assert record_adherence(str(tmp_path), "t1", "claude-sonnet-4-6", None) is None
        assert _read_rows(str(tmp_path)) == []

    def test_empty_slug_skips(self, tmp_path):
        assert record_adherence(str(tmp_path), "", "claude-sonnet-4-6", "claude-sonnet-4-6") is None

    def test_unknown_family_skips(self, tmp_path):
        # An unrecognised model id must not produce a bogus adherence row.
        assert record_adherence(str(tmp_path), "t1", "gpt-9-turbo", "claude-sonnet-4-6") is None
        assert record_adherence(str(tmp_path), "t1", "claude-sonnet-4-6", "gpt-9-turbo") is None
        assert _read_rows(str(tmp_path)) == []


# --- AC2: aggregation (%, n, deviations) -------------------------------------


class TestAggregate:
    def test_empty_dir_yields_zero(self, tmp_path):
        agg = aggregate_adherence(str(tmp_path))
        assert agg == {"n": 0, "matches": 0, "pct": 0.0, "top_deviations": []}

    def test_pct_and_deviations(self, tmp_path):
        record_adherence(str(tmp_path), "a", "claude-sonnet-4-6", "claude-sonnet-4-6")
        record_adherence(str(tmp_path), "b", "claude-sonnet-4-6", "claude-sonnet-4-6")
        record_adherence(str(tmp_path), "c", "claude-opus-4-8", "claude-sonnet-4-6")
        agg = aggregate_adherence(str(tmp_path))
        assert agg["n"] == 3
        assert agg["matches"] == 2
        assert agg["pct"] == 66.7
        assert agg["top_deviations"] == [{"shift": "opus->sonnet", "count": 1}]

    def test_malformed_lines_skipped(self, tmp_path):
        path = tmp_path / "routing_adherence.jsonl"
        path.write_text(
            "not-json\n"
            + json.dumps({"recommended_family": "opus", "actual_family": "opus", "match": True})
            + "\n",
            encoding="utf-8",
        )
        agg = aggregate_adherence(str(tmp_path))
        assert agg["n"] == 1 and agg["matches"] == 1

    def test_recomputes_match_ignoring_persisted_flag(self, tmp_path):
        # M3: a hand-edited match=true with mismatched families is NOT trusted.
        path = tmp_path / "routing_adherence.jsonl"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "recommended_family": "opus",
                    "actual_family": "haiku",
                    "match": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        agg = aggregate_adherence(str(tmp_path))
        assert agg["n"] == 1
        assert agg["matches"] == 0  # recomputed from families, flag ignored
        assert agg["top_deviations"] == [{"shift": "opus->haiku", "count": 1}]

    def test_future_schema_rows_skipped(self, tmp_path):
        # L1: a row from a future schema is skipped rather than misread.
        path = tmp_path / "routing_adherence.jsonl"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "recommended_family": "opus",
                    "actual_family": "opus",
                    "match": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        agg = aggregate_adherence(str(tmp_path))
        assert agg["n"] == 0


# --- AC1 + AC3: task_done integration ----------------------------------------


def _make_service(tmp_path: Path) -> ProjectService:
    return ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))


def _seed(svc: ProjectService, slug: str) -> None:
    svc.session_start()
    svc.task_quick(slug, "stub")
    svc.be.task_update(
        slug,
        goal="g",
        acceptance_criteria="1. does x. negative: errors on y",
        complexity="medium",
        rollback_plan="git revert",
        scope="x.py",
    )


def _write_transcript(tmp_path: Path, model: str) -> str:
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps({"type": "assistant", "model": model}) + "\n", encoding="utf-8")
    return str(p)


class TestTaskDoneIntegration:
    def test_task_done_records_adherence(self, tmp_path, monkeypatch):
        store = tmp_path / "store"
        store.mkdir()
        monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(store))
        # medium -> implement/medium -> Sonnet; active also Sonnet -> match.
        monkeypatch.setattr(
            "model_routing._auto_find_transcript",
            lambda: _write_transcript(tmp_path, "claude-sonnet-4-6"),
        )
        svc = _make_service(tmp_path)
        try:
            _seed(svc, "adh-1")
            svc.task_start("adh-1")
            svc.task_done("adh-1", ac_verified=True, evidence="1. does x ✓ negative: y ✓")
            rows = _read_rows(str(store))
            assert len(rows) == 1
            assert rows[0]["slug"] == "adh-1"
            assert rows[0]["match"] is True
        finally:
            svc.be.close()

    def test_task_done_without_transcript_skips_no_error(self, tmp_path, monkeypatch):
        store = tmp_path / "store2"
        store.mkdir()
        monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(store))
        monkeypatch.setattr("model_routing._auto_find_transcript", lambda: None)
        svc = _make_service(tmp_path)
        try:
            _seed(svc, "adh-2")
            svc.task_start("adh-2")
            # NEGATIVE: no transcript -> actual unknown -> no row, close still succeeds.
            out = svc.task_done("adh-2", ac_verified=True, evidence="1. does x ✓ negative: y ✓")
            assert "adh-2" in out
            assert _read_rows(str(store)) == []
        finally:
            svc.be.close()
