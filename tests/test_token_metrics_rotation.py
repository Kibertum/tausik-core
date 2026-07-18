"""token_metrics.jsonl must stay idempotent and bounded.

Two defects motivated this: `extract_token_rows` re-derives a session's COMPLETE
row set from the transcript on every call, and the writer appended it — so every
re-run of the SessionEnd hook duplicated every row. There was also no size cap.
Together they took the file to 191 MB on this project.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from session_metrics import append_token_rows


def _rows(session_id: int, n: int = 3) -> list[dict]:
    return [
        {
            "ts": f"2026-07-18T00:00:0{i}Z",
            "session_id": session_id,
            "tool_name": f"Tool{i}",
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read": 0,
            "cache_create": 0,
            "model": "claude-opus-4-8",
        }
        for i in range(n)
    ]


def _read(tmp_path) -> list[dict]:
    p = tmp_path / ".tausik" / "token_metrics.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _proj(tmp_path):
    (tmp_path / ".tausik").mkdir()
    return str(tmp_path)


class TestIdempotence:
    def test_rerunning_same_session_does_not_duplicate(self, tmp_path):
        """The bug: the SessionEnd hook re-parses the transcript from byte 0 and
        re-emits every row, so appending multiplied the session on each run."""
        proj = _proj(tmp_path)
        append_token_rows(_rows(1), project_dir=proj)
        append_token_rows(_rows(1), project_dir=proj)
        append_token_rows(_rows(1), project_dir=proj)
        assert len(_read(tmp_path)) == 3

    def test_other_sessions_are_preserved(self, tmp_path):
        proj = _proj(tmp_path)
        append_token_rows(_rows(1), project_dir=proj)
        append_token_rows(_rows(2), project_dir=proj)
        append_token_rows(_rows(1), project_dir=proj)  # replaces session 1 only
        got = _read(tmp_path)
        assert sorted({r["session_id"] for r in got}) == [1, 2]
        assert len(got) == 6

    def test_replacement_uses_the_newest_content(self, tmp_path):
        proj = _proj(tmp_path)
        append_token_rows(_rows(1, n=5), project_dir=proj)
        append_token_rows(_rows(1, n=2), project_dir=proj)
        assert len(_read(tmp_path)) == 2


class TestRotation:
    def test_file_stays_under_cap_and_keeps_newest(self, tmp_path):
        proj = _proj(tmp_path)
        for sid in range(1, 40):
            append_token_rows(_rows(sid, n=5), project_dir=proj, max_bytes=4096)
        path = tmp_path / ".tausik" / "token_metrics.jsonl"
        assert path.stat().st_size <= 4096
        seen = {r["session_id"] for r in _read(tmp_path)}
        assert 39 in seen, "newest session must survive rotation"
        assert 1 not in seen, "oldest session must be dropped first"


class TestDegradation:
    def test_unparseable_line_is_skipped_not_fatal(self, tmp_path):
        """Negative: one malformed metrics row must not cost the whole file."""
        proj = _proj(tmp_path)
        path = tmp_path / ".tausik" / "token_metrics.jsonl"
        path.write_text(
            json.dumps(_rows(7)[0]) + "\n" + "{not json at all\n",
            encoding="utf-8",
        )
        assert append_token_rows(_rows(9), project_dir=proj) is not None
        got = _read(tmp_path)
        assert {r["session_id"] for r in got} == {7, 9}

    def test_empty_rows_is_a_noop(self, tmp_path):
        """Negative: nothing to record must not create or truncate the file."""
        proj = _proj(tmp_path)
        assert append_token_rows([], project_dir=proj) is None
        assert not (tmp_path / ".tausik" / "token_metrics.jsonl").exists()

    def test_missing_tausik_dir_is_a_noop(self, tmp_path):
        assert append_token_rows(_rows(1), project_dir=str(tmp_path)) is None

    def test_no_temp_file_left_behind(self, tmp_path):
        proj = _proj(tmp_path)
        append_token_rows(_rows(1), project_dir=proj)
        assert not list((tmp_path / ".tausik").glob("*.tmp"))
