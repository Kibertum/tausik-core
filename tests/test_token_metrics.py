"""Tests for v14b-baseline-token-metrics — aggregator + SessionEnd emitter.

After defect v14b-defect-token-metrics-no-realworld-write (decision #61),
per-tool token rows are produced by the SessionEnd transcript-parser in
scripts/hooks/session_metrics.py (extract_token_rows / replace_session_token_rows /
resolve_session_id), NOT by a PostToolUse hook. The aggregator
(scripts/service_token_metrics.py) reads the same JSONL schema as before.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from conftest import canonical_ddl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from service_token_metrics import _percentile, aggregate, format_table  # noqa: E402
from session_metrics import (  # noqa: E402
    replace_session_token_rows,
    extract_token_rows,
    resolve_session_id,
)


# ---------- aggregator unit tests ----------


class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert _percentile([], 50) == 0

    def test_single_value(self):
        assert _percentile([42], 90) == 42

    def test_p50_of_evens(self):
        assert _percentile([10, 20, 30, 40], 50) == 25

    def test_p90_takes_high_end(self):
        assert _percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9


class TestAggregate:
    def _write_jsonl(self, project_dir: Path, rows: list[dict]) -> None:
        d = project_dir / ".tausik"
        d.mkdir(exist_ok=True)
        with open(d / "token_metrics.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")

    def test_no_jsonl_returns_zero_state(self, tmp_path):
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["events"] == 0
        assert agg["sessions_observed"] == 0
        assert agg["per_tool"] == []
        assert agg["totals"] == {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}

    def test_last_n_zero_returns_empty_window(self, tmp_path):
        self._write_jsonl(
            tmp_path,
            [{"ts": "x", "session_id": 1, "tool_name": "Read", "input_tokens": 100}],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=0)
        assert agg["events"] == 0
        assert agg["sessions_observed"] == 1

    def test_aggregates_per_tool_with_p50_p90(self, tmp_path):
        rows = [
            {
                "ts": "1",
                "session_id": 1,
                "tool_name": "Read",
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read": 0,
                "cache_create": 0,
            },
            {
                "ts": "2",
                "session_id": 1,
                "tool_name": "Read",
                "input_tokens": 20,
                "output_tokens": 5,
                "cache_read": 0,
                "cache_create": 0,
            },
            {
                "ts": "3",
                "session_id": 1,
                "tool_name": "Read",
                "input_tokens": 30,
                "output_tokens": 5,
                "cache_read": 0,
                "cache_create": 0,
            },
            {
                "ts": "4",
                "session_id": 1,
                "tool_name": "Edit",
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read": 200,
                "cache_create": 100,
            },
        ]
        self._write_jsonl(tmp_path, rows)
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["events"] == 4
        assert agg["sessions_observed"] == 1

        per_tool = {t["tool_name"]: t for t in agg["per_tool"]}
        assert per_tool["Read"]["events"] == 3
        assert per_tool["Read"]["input_tokens_total"] == 60
        assert per_tool["Read"]["input_tokens_p50"] == 20
        assert per_tool["Edit"]["cache_read_total"] == 200
        assert per_tool["Edit"]["cache_create_total"] == 100
        assert agg["per_tool"][0]["tool_name"] == "Edit"

    def test_filter_keeps_only_last_n_sessions(self, tmp_path):
        rows = [
            {"ts": "1", "session_id": 1, "tool_name": "Read", "input_tokens": 10},
            {"ts": "2", "session_id": 2, "tool_name": "Read", "input_tokens": 20},
            {"ts": "3", "session_id": 3, "tool_name": "Read", "input_tokens": 30},
            {"ts": "4", "session_id": 4, "tool_name": "Read", "input_tokens": 40},
        ]
        self._write_jsonl(tmp_path, rows)
        agg = aggregate(project_dir=str(tmp_path), last_n=2)
        assert agg["events"] == 2
        assert agg["sessions_observed"] == 4
        assert agg["sessions_in_window"] == 2

    def test_skips_malformed_lines(self, tmp_path):
        d = tmp_path / ".tausik"
        d.mkdir()
        path = d / "token_metrics.jsonl"
        path.write_text(
            '{"ts":"a","session_id":1,"tool_name":"X","input_tokens":5}\n'
            "not json at all\n"
            "\n"
            '{"ts":"b","session_id":1,"tool_name":"X","input_tokens":15}\n',
            encoding="utf-8",
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["events"] == 2
        assert agg["per_tool"][0]["input_tokens_total"] == 20

    def test_format_table_handles_empty(self, tmp_path):
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        out = format_table(agg)
        assert "No token metrics recorded yet" in out

    def test_format_table_renders_rows(self, tmp_path):
        self._write_jsonl(
            tmp_path,
            [
                {
                    "ts": "1",
                    "session_id": 1,
                    "tool_name": "Read",
                    "input_tokens": 100,
                    "output_tokens": 10,
                    "cache_read": 50,
                    "cache_create": 0,
                }
            ],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        out = format_table(agg)
        assert "Read" in out
        assert "Token metrics" in out


# ---------- SessionEnd transcript-parser tests ----------


def _write_transcript(path: Path, entries: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


class TestExtractTokenRows:
    def test_empty_transcript_yields_no_rows(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(path, [])
        assert extract_token_rows(str(path), session_id=1) == []

    def test_skips_non_assistant_entries(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [
                {"type": "human", "content": "hi", "usage": {"input_tokens": 100}},
                {"type": "system", "content": "x"},
            ],
        )
        assert extract_token_rows(str(path), session_id=1) == []

    def test_skips_assistant_with_no_usage(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [{"type": "assistant", "content": [{"type": "tool_use", "name": "Read"}]}],
        )
        assert extract_token_rows(str(path), session_id=1) == []

    def test_skips_assistant_text_only_no_tool_use(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [
                {
                    "type": "assistant",
                    "content": [{"type": "text", "text": "ok"}],
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                }
            ],
        )
        assert extract_token_rows(str(path), session_id=1) == []

    def test_single_tool_use_attributes_full_usage(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [
                {
                    "type": "assistant",
                    "timestamp": "2026-05-06T10:00:00Z",
                    "model": "claude-opus-4-7",
                    "content": [{"type": "tool_use", "name": "Read"}],
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 50,
                        "cache_read_input_tokens": 4000,
                        "cache_creation_input_tokens": 200,
                    },
                }
            ],
        )
        rows = extract_token_rows(str(path), session_id=42)
        assert len(rows) == 1
        r = rows[0]
        assert r["session_id"] == 42
        assert r["tool_name"] == "Read"
        assert r["input_tokens"] == 1000
        assert r["output_tokens"] == 50
        assert r["cache_read"] == 4000
        assert r["cache_create"] == 200
        assert r["model"] == "claude-opus-4-7"
        assert r["ts"] == "2026-05-06T10:00:00Z"

    def test_multi_tool_use_splits_evenly_with_remainder_on_last(self, tmp_path):
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [
                {
                    "type": "assistant",
                    "content": [
                        {"type": "tool_use", "name": "Read"},
                        {"type": "tool_use", "name": "Grep"},
                        {"type": "tool_use", "name": "Glob"},
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                }
            ],
        )
        rows = extract_token_rows(str(path), session_id=1)
        assert len(rows) == 3
        # 100 // 3 = 33; last row absorbs 100 - 33*2 = 34
        assert [r["input_tokens"] for r in rows] == [33, 33, 34]
        assert sum(r["input_tokens"] for r in rows) == 100
        # 10 // 3 = 3; last absorbs 10 - 3*2 = 4
        assert [r["output_tokens"] for r in rows] == [3, 3, 4]
        assert [r["tool_name"] for r in rows] == ["Read", "Grep", "Glob"]

    def test_usage_inside_message_field(self, tmp_path):
        # Some Claude Code transcript variants nest usage under "message"
        path = tmp_path / "t.jsonl"
        _write_transcript(
            path,
            [
                {
                    "type": "assistant",
                    "message": {
                        "model": "claude-sonnet-4-6",
                        "content": [{"type": "tool_use", "name": "Edit"}],
                        "usage": {"input_tokens": 500, "output_tokens": 25},
                    },
                }
            ],
        )
        rows = extract_token_rows(str(path), session_id=1)
        assert len(rows) == 1
        assert rows[0]["model"] == "claude-sonnet-4-6"
        assert rows[0]["input_tokens"] == 500

    def test_skips_malformed_lines(self, tmp_path):
        path = tmp_path / "t.jsonl"
        path.write_text(
            json.dumps(
                {
                    "type": "assistant",
                    "content": [{"type": "tool_use", "name": "Read"}],
                    "usage": {"input_tokens": 100, "output_tokens": 5},
                }
            )
            + "\n"
            + "not json at all\n"
            + "\n",
            encoding="utf-8",
        )
        rows = extract_token_rows(str(path), session_id=1)
        assert len(rows) == 1


class TestReplaceSessionTokenRows:
    """The writer REPLACES a session's rows rather than appending to them.

    `extract_token_rows` re-derives a session's complete set from the transcript
    on every call, so the caller always hands over the whole set. Appending
    duplicated every row on every SessionEnd re-run — that is how the file
    reached 191 MB. Replace-by-session is idempotent by construction.
    """

    def _lines(self, tmp_path):
        path = tmp_path / ".tausik" / "token_metrics.jsonl"
        return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    def test_no_rows_returns_none(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        assert replace_session_token_rows([], project_dir=str(tmp_path)) is None

    def test_no_tausik_dir_returns_none(self, tmp_path):
        rows = [{"ts": "x", "session_id": 1, "tool_name": "Read", "input_tokens": 5}]
        assert replace_session_token_rows(rows, project_dir=str(tmp_path)) is None
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_rerun_with_the_same_set_does_not_duplicate(self, tmp_path):
        """The real caller's pattern: the same complete set, written twice."""
        (tmp_path / ".tausik").mkdir()
        rows = [
            {"ts": "a", "session_id": 1, "tool_name": "Read", "input_tokens": 5},
            {"ts": "b", "session_id": 1, "tool_name": "Edit", "input_tokens": 7},
        ]
        replace_session_token_rows(rows, project_dir=str(tmp_path))
        replace_session_token_rows(rows, project_dir=str(tmp_path))
        lines = self._lines(tmp_path)
        assert len(lines) == 2
        assert [json.loads(ln)["tool_name"] for ln in lines] == ["Read", "Edit"]

    def test_grown_set_replaces_the_session_wholesale(self, tmp_path):
        """A later run sees more of the transcript; the session's rows are
        swapped for the new set, not merged with the old one."""
        (tmp_path / ".tausik").mkdir()
        first = [{"ts": "a", "session_id": 1, "tool_name": "Read", "input_tokens": 5}]
        grown = first + [{"ts": "b", "session_id": 1, "tool_name": "Edit", "input_tokens": 7}]
        replace_session_token_rows(first, project_dir=str(tmp_path))
        replace_session_token_rows(grown, project_dir=str(tmp_path))
        lines = self._lines(tmp_path)
        assert len(lines) == 2
        assert [json.loads(ln)["tool_name"] for ln in lines] == ["Read", "Edit"]

    def test_other_sessions_are_not_erased(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        replace_session_token_rows(
            [{"ts": "a", "session_id": 1, "tool_name": "Read", "input_tokens": 5}],
            project_dir=str(tmp_path),
        )
        replace_session_token_rows(
            [{"ts": "b", "session_id": 2, "tool_name": "Edit", "input_tokens": 7}],
            project_dir=str(tmp_path),
        )
        assert {json.loads(ln)["session_id"] for ln in self._lines(tmp_path)} == {1, 2}


class TestResolveSessionId:
    def _make_db(self, project_dir: Path, sessions: list[tuple[str, str | None]]) -> None:
        tausik = project_dir / ".tausik"
        tausik.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(tausik / "tausik.db"))
        conn.execute(canonical_ddl("sessions"))
        for started, ended in sessions:
            conn.execute(
                "INSERT INTO sessions(started_at, ended_at) VALUES (?, ?)",
                (started, ended),
            )
        conn.commit()
        conn.close()

    def test_no_db_returns_none(self, tmp_path):
        assert resolve_session_id(project_dir=str(tmp_path)) is None

    def test_empty_table_returns_none(self, tmp_path):
        self._make_db(tmp_path, [])
        assert resolve_session_id(project_dir=str(tmp_path)) is None

    def test_returns_most_recent_id_regardless_of_ended_at(self, tmp_path):
        self._make_db(
            tmp_path,
            [
                ("2026-05-06T10:00:00Z", "2026-05-06T10:30:00Z"),
                ("2026-05-06T11:00:00Z", None),  # in-progress
            ],
        )
        sid = resolve_session_id(project_dir=str(tmp_path))
        assert sid == 2


class TestEndToEndEmitter:
    """Wire the three functions together against a realistic transcript."""

    def test_real_transcript_to_jsonl(self, tmp_path, monkeypatch):
        # Build a tausik project + DB
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        conn = sqlite3.connect(str(tausik / "tausik.db"))
        conn.execute(canonical_ddl("sessions"))
        conn.execute(
            "INSERT INTO sessions(started_at, ended_at) VALUES (?, NULL)",
            ("2026-05-06T10:00:00Z",),
        )
        conn.commit()
        conn.close()

        # Build a transcript with two assistant turns
        transcript = tmp_path / "transcript.jsonl"
        _write_transcript(
            transcript,
            [
                {
                    "type": "assistant",
                    "timestamp": "2026-05-06T10:00:00Z",
                    "model": "claude-opus-4-7",
                    "content": [{"type": "tool_use", "name": "Read"}],
                    "usage": {"input_tokens": 1000, "output_tokens": 50},
                },
                {
                    "type": "assistant",
                    "timestamp": "2026-05-06T10:01:00Z",
                    "content": [
                        {"type": "tool_use", "name": "Grep"},
                        {"type": "tool_use", "name": "Glob"},
                    ],
                    "usage": {"input_tokens": 200, "output_tokens": 20},
                },
            ],
        )

        monkeypatch.chdir(tmp_path)
        sid = resolve_session_id()
        assert sid == 1
        rows = extract_token_rows(str(transcript), session_id=sid)
        assert len(rows) == 3  # 1 + 2 tool_uses
        out = replace_session_token_rows(rows)
        assert out is not None
        assert (tausik / "token_metrics.jsonl").exists()

        # Aggregator should now read it back as 3 events
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["events"] == 3
        assert agg["sessions_observed"] == 1
        per_tool = {t["tool_name"]: t for t in agg["per_tool"]}
        assert "Read" in per_tool
        assert "Grep" in per_tool
        assert "Glob" in per_tool
        assert per_tool["Read"]["input_tokens_total"] == 1000
        # Grep+Glob split 200 → 100/100
        assert (
            per_tool["Grep"]["input_tokens_total"] + per_tool["Glob"]["input_tokens_total"] == 200
        )
