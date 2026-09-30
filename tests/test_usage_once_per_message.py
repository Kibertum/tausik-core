"""A message's usage is counted once, however many content blocks carry it
(session-metrics-sums-usage-once-per-content-block)."""

from __future__ import annotations

from pathlib import Path

import hashlib
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from session_metrics import parse_transcript  # noqa: E402
from token_rows import extract_token_rows  # noqa: E402

USAGE = {"input_tokens": 10, "output_tokens": 300, "cache_read_input_tokens": 90}


def _entry(mid, block, usage=USAGE, ts="2026-09-23T10:00:00Z"):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {"id": mid, "model": "claude-opus-5", "usage": usage, "content": [block]},
    }


def _write(tmp_path, entries):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return str(p)


THREE_BLOCKS = [
    _entry("msg_1", {"type": "thinking", "thinking": "..."}),
    _entry("msg_1", {"type": "text", "text": "reading"}),
    _entry("msg_1", {"type": "tool_use", "name": "Read", "input": {}}),
]


def test_one_three_block_message_is_counted_once(tmp_path):
    m = parse_transcript(_write(tmp_path, THREE_BLOCKS))
    assert (m["tokens_input"], m["tokens_output"]) == (10, 300)


def test_two_different_messages_of_the_same_shape_both_count(tmp_path):
    second = [dict(e, message=dict(e["message"], id="msg_2")) for e in THREE_BLOCKS]
    m = parse_transcript(_write(tmp_path, THREE_BLOCKS + second))
    assert (m["tokens_input"], m["tokens_output"]) == (20, 600)


def test_the_last_usage_of_a_message_wins(tmp_path):
    grown = dict(USAGE, output_tokens=450)
    entries = THREE_BLOCKS[:2] + [_entry("msg_1", {"type": "tool_use", "name": "Read"}, grown)]
    assert parse_transcript(_write(tmp_path, entries))["tokens_output"] == 450


def test_tool_rows_split_one_message_usage_across_its_tool_uses(tmp_path):
    entries = [
        _entry("msg_9", {"type": "tool_use", "name": "Read"}),
        _entry("msg_9", {"type": "tool_use", "name": "Grep"}),
    ]
    rows = extract_token_rows(_write(tmp_path, entries), 1)
    assert [r["tool_name"] for r in rows] == ["Read", "Grep"]
    assert sum(r["output_tokens"] for r in rows) == 300
    assert sum(r["input_tokens"] for r in rows) == 10


_B = os.path.join(_ROOT, "docs", "ru", "research", "_internal", "rag-replay", "2026-09-14", "B")


def test_the_replay_transcript_of_session_263_meters_the_deduplicated_sum():
    """The recorded replay, when this machine is the one that recorded it.

    The guard used to sit one step too late: it checked for the transcript and opened
    the MANIFEST that names it without checking anything. `docs/ru/research/_internal`
    is untracked by design, so in CI the open raised FileNotFoundError instead of
    skipping, and this failure was one of nine that kept the release branch red — and
    a red test stage never lets the full-battery stage start, so it also hid every
    slow-marked test behind it.

    Skipping here is honest rather than convenient: the assertion is about one
    specific transcript's bytes, which exist on one machine. What is NOT acceptable is
    an error that reads as a broken suite.
    """
    manifest = os.path.join(_B, "transcript.sha256")
    usage_path = os.path.join(_B, "usage.json")
    for needed in (manifest, usage_path):
        if not os.path.isfile(needed):
            pytest.skip(
                f"{os.path.basename(needed)} is absent — `_internal` is untracked by design"
            )
    sha_line = Path(manifest).read_text(encoding="utf-8").split()
    usage = json.loads(Path(usage_path).read_text(encoding="utf-8"))
    name = sha_line[1]
    path = None
    base = os.path.expanduser("~/.claude/projects")
    if os.path.isdir(base):
        for d in os.listdir(base):
            cand = os.path.join(base, d, name)
            if os.path.isfile(cand):
                path = cand
                break
    if path is None:
        pytest.skip(f"replay transcript {name} is not on this machine")
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha_line[0]
    lo, hi = usage["window"]
    m = parse_transcript(
        path, session_resolver=lambda ts: 263 if ts and lo <= ts <= hi else None, session_id=263
    )
    dedup = usage["deduplicated_by_message_id"]
    assert m["tokens_total"] == dedup["input_tokens"] + dedup["output_tokens"] == 31613
