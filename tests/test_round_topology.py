from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from round_topology import extract, report


def _write(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _call(call_id, command):
    return {
        "type": "response_item",
        "payload": {
            "type": "custom_tool_call",
            "name": "exec",
            "call_id": call_id,
            "input": command,
        },
    }


def _usage(response_id):
    return {"type": "token_usage_record", "payload": {"response_id": response_id}}


def _output(call_id, text):
    return {
        "type": "response_item",
        "payload": {"type": "custom_tool_call_output", "call_id": call_id, "output": text},
    }


def test_only_successful_accepted_windows_contribute_body_free_transitions(tmp_path):
    path = tmp_path / "native.jsonl"
    _write(
        path,
        [
            _call("s", ".tausik/tausik task start accepted"),
            _usage("r1"),
            _output("s", "Task 'accepted' started (attempt #1)."),
            _call("read1", "rg -n needle scripts"),
            _usage("r2"),
            _output("read1", "SECRET BODY"),
            _call("read2", "Get-Content tests/x.py"),
            _usage("r3"),
            _output("read2", "MORE SECRET"),
            _call("d", ".tausik/tausik task done accepted"),
            _usage("r4"),
            _output("d", "Task 'accepted' completed."),
            _call("x", ".tausik/tausik task start rejected"),
            _usage("r5"),
            _output("x", "QG-0 blocked"),
        ],
    )
    tasks, coverage = extract([str(path)], {"accepted"})
    result = report(tasks, coverage)
    assert tasks["accepted"] == ["task-start", "retrieval", "retrieval", "task-done"]
    assert result["coverage"] == {
        "transcripts": 1,
        "ambiguous_boundaries": 0,
        "inherited_responses_excluded": 0,
        "duplicate_responses_excluded": 0,
        "accepted_windows": 1,
        "accepted_response_rounds": 4,
    }
    assert result["transitions"][1]["sequence"] == ["retrieval", "retrieval"]
    assert "SECRET" not in json.dumps(result)


def test_failed_close_stays_inside_window_and_ambiguous_done_is_excluded(tmp_path):
    path = tmp_path / "native.jsonl"
    _write(
        path,
        [
            _call("s", ".tausik/tausik task start kept"),
            _usage("r1"),
            _output("s", "Task 'kept' started (attempt #1)."),
            _call("bad", ".tausik/tausik task done kept"),
            _usage("r2"),
            _output("bad", "verify red"),
            _call("v", "python -m pytest -q"),
            _usage("r3"),
            _output("v", "1 passed"),
            _call("wrong", ".tausik/tausik task done other"),
            _usage("r4"),
            _output("wrong", "Task 'other' completed."),
            _call("good", ".tausik/tausik task done kept"),
            _usage("r5"),
            _output("good", "Task 'kept' completed."),
        ],
    )
    tasks, coverage = extract([str(path)], {"kept", "other"})
    assert tasks["kept"] == [
        "task-start",
        "task-done-failed",
        "verification",
        "task-done",
    ]
    assert "other" not in tasks and coverage["ambiguous_boundaries"] == 1


def test_forked_duplicate_responses_are_not_counted_twice(tmp_path):
    rows = [
        _call("s", ".tausik/tausik task start once"),
        _usage("same-start"),
        _output("s", "Task 'once' started (attempt #1)."),
        _call("d", ".tausik/tausik task done once"),
        _usage("same-done"),
        _output("d", "Task 'once' completed."),
    ]
    first, fork = tmp_path / "first.jsonl", tmp_path / "fork.jsonl"
    _write(first, rows)
    _write(fork, rows)
    tasks, coverage = extract([str(first), str(fork)], {"once"})
    assert tasks["once"] == ["task-start", "task-done"]
    assert coverage["duplicate_responses_excluded"] == 2
