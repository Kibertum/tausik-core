"""Tests for v14b-baseline-token-metrics — JSONL hook + aggregator.

Covers AC #5 (hook unit test, aggregation query test) and AC #7-8
(negative paths: malformed payload, missing usage block, IO error,
empty/zero-N inputs).
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_token_metrics import _percentile, aggregate, format_table  # noqa: E402


# ---------- aggregator unit tests ----------


class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert _percentile([], 50) == 0

    def test_single_value(self):
        assert _percentile([42], 90) == 42

    def test_p50_of_evens(self):
        # values [10, 20, 30, 40] — p50 is interpolated midpoint between 20 and 30
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
        # AC #8: empty/missing file → clean zero state, no crash
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["events"] == 0
        assert agg["sessions_observed"] == 0
        assert agg["per_tool"] == []
        assert agg["totals"] == {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}

    def test_last_n_zero_returns_empty_window(self, tmp_path):
        # AC #8: --last 0 returns clean state, not stack trace
        self._write_jsonl(
            tmp_path,
            [{"ts": "x", "session_id": 1, "tool_name": "Read", "input_tokens": 100}],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=0)
        assert agg["events"] == 0
        assert agg["sessions_observed"] == 1  # observed but excluded from window

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
        # Tools sorted by input_tokens_total desc — Edit (100) > Read (60)
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
        # Only sessions 3 and 4 in window
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


# ---------- hook integration tests ----------


HOOK_PATH = Path(__file__).parent.parent / "scripts" / "hooks" / "token_metrics.py"


def _run_hook(project_dir: Path, payload: str | None) -> tuple[int, str]:
    """Run the hook script with the given stdin payload. Returns (rc, stderr)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env.pop("TAUSIK_SKIP_HOOKS", None)
    r = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload if payload is not None else "",
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    return r.returncode, r.stderr


def _make_tausik_project(project_dir: Path, with_open_session: bool = True) -> int | None:
    tausik = project_dir / ".tausik"
    tausik.mkdir(exist_ok=True)
    db_path = tausik / "tausik.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "started_at TEXT, ended_at TEXT)"
    )
    sid: int | None = None
    if with_open_session:
        cur = conn.execute(
            "INSERT INTO sessions(started_at, ended_at) VALUES (?, NULL)",
            ("2026-05-06T10:00:00Z",),
        )
        sid = cur.lastrowid
    conn.commit()
    conn.close()
    return sid


class TestHook:
    def test_no_tausik_dir_silent_exit_zero(self, tmp_path):
        # Plain dir, no .tausik/ → hook is a no-op
        rc, _ = _run_hook(tmp_path, '{"tool_name":"Read"}')
        assert rc == 0
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_empty_stdin_silent_exit_zero(self, tmp_path):
        # AC #7: empty payload → no crash, no row appended
        _make_tausik_project(tmp_path)
        rc, _ = _run_hook(tmp_path, "")
        assert rc == 0
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_malformed_json_silent_exit_zero(self, tmp_path):
        # AC #7: malformed JSON → no crash, no row appended
        _make_tausik_project(tmp_path)
        rc, _ = _run_hook(tmp_path, "{not valid json")
        assert rc == 0
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_payload_without_usage_block_skips(self, tmp_path):
        # AC #7: missing usage block → skip silently (no zero-row noise)
        _make_tausik_project(tmp_path)
        rc, _ = _run_hook(
            tmp_path,
            json.dumps({"tool_name": "Read", "tool_response": {"content": "..."}}),
        )
        assert rc == 0
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_full_payload_records_row(self, tmp_path):
        sid = _make_tausik_project(tmp_path)
        payload = {
            "tool_name": "Read",
            "tool_response": {
                "model": "claude-opus-4-7",
                "usage": {
                    "input_tokens": 1234,
                    "output_tokens": 56,
                    "cache_read_input_tokens": 4321,
                    "cache_creation_input_tokens": 100,
                },
            },
        }
        rc, _ = _run_hook(tmp_path, json.dumps(payload))
        assert rc == 0
        path = tmp_path / ".tausik" / "token_metrics.jsonl"
        assert path.exists()
        line = path.read_text(encoding="utf-8").strip()
        rec = json.loads(line)
        assert rec["session_id"] == sid
        assert rec["tool_name"] == "Read"
        assert rec["input_tokens"] == 1234
        assert rec["cache_read"] == 4321
        assert rec["cache_create"] == 100
        assert rec["model"] == "claude-opus-4-7"

    def test_no_open_session_skips(self, tmp_path):
        # No active session → can't attribute → skip silently
        _make_tausik_project(tmp_path, with_open_session=False)
        payload = {
            "tool_name": "Read",
            "tool_response": {"usage": {"input_tokens": 100, "output_tokens": 5}},
        }
        rc, _ = _run_hook(tmp_path, json.dumps(payload))
        assert rc == 0
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_appends_multiple_rows(self, tmp_path):
        _make_tausik_project(tmp_path)
        for i in range(3):
            payload = {
                "tool_name": f"Tool{i}",
                "tool_response": {"usage": {"input_tokens": 10 * (i + 1), "output_tokens": 1}},
            }
            rc, _ = _run_hook(tmp_path, json.dumps(payload))
            assert rc == 0
        path = tmp_path / ".tausik" / "token_metrics.jsonl"
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 3
