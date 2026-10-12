"""Native Codex replay, restart, fork and incomplete-record behavior."""

import json
import sqlite3

import pytest

from conftest import canonical_ddl

from usage_codex import read_incremental, summarize
from usage_codex_report import report


def event(kind, payload):
    return {"type": kind, "timestamp": "2026-10-01T00:00:00Z", "payload": payload}


def meta(root, thread="thread"):
    return event(
        "session_meta",
        {"cwd": str(root), "id": thread, "model_provider": "openai", "cli_version": "test"},
    )


def usage(count=100):
    return {
        "input_tokens": count,
        "cached_input_tokens": count // 2,
        "output_tokens": 10,
        "reasoning_output_tokens": 2,
    }


def response(count=100, response_id="r", thread="thread"):
    return event(
        "token_usage_record",
        {"response_id": response_id, "thread_id": thread, "usage": usage(count)},
    )


def tool_call(command, call_id="call"):
    return event(
        "response_item",
        {"type": "custom_tool_call", "name": "exec", "input": command, "call_id": call_id},
    )


def tool_output(text, call_id="call"):
    return event(
        "response_item", {"type": "custom_tool_call_output", "output": text, "call_id": call_id}
    )


def cumulative(count=100):
    return event("event_msg", {"type": "token_count", "info": {"total_token_usage": usage(count)}})


def write(path, rows, mode="w"):
    with path.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def test_native_and_cumulative_are_not_added_replay_and_fork(tmp_path):
    path = tmp_path / "log.jsonl"
    write(
        path,
        [
            meta(tmp_path),
            event("turn_context", {"model": "gpt-test", "effort": "high"}),
            response(),
            cumulative(),
            response(),
        ],
    )
    state = read_incremental(path, tmp_path)
    result = summarize([state, state])
    assert result["responses"] == 1 and result["tokens"]["input"] == 100
    assert result["cumulative_fallback"] == []
    assert result["task_attribution"] == "unknown"
    again = read_incremental(path, tmp_path, state)
    assert again["bytes_read"] == 0
    fork = tmp_path / "fork.jsonl"
    write(fork, [meta(tmp_path, "child"), response(), response(30, "child-r", "child")])
    result = summarize([state, read_incremental(fork, tmp_path)])
    assert result["responses"] == 2 and result["tokens"]["input"] == 130


def test_partial_line_retry_invalid_complete_line_and_truncation(tmp_path):
    path = tmp_path / "log.jsonl"
    write(path, [meta(tmp_path)])
    raw = json.dumps(response()).encode()
    with path.open("ab") as f:
        f.write(raw[:20])
    state = read_incremental(path, tmp_path)
    assert not state["rows"] and state["malformed"] == 0
    with path.open("ab") as f:
        f.write(raw[20:] + b"\nBAD\n")
    state = read_incremental(path, tmp_path, state)
    assert len(state["rows"]) == 1 and state["malformed"] == 1
    write(path, [meta(tmp_path), response(20)])
    state = read_incremental(path, tmp_path, state)
    assert summarize([state])["tokens"]["input"] == 20


@pytest.mark.parametrize(
    "counts,expected,resets", [([100, 100, 150], 150, 0), ([100, 20, 40], 140, 1)]
)
def test_cumulative_fallback_resets_are_visible_and_unattributed(
    tmp_path, counts, expected, resets
):
    path = tmp_path / "log.jsonl"
    write(path, [meta(tmp_path)] + [cumulative(n) for n in counts])
    result = summarize([read_incremental(path, tmp_path)])
    assert result["tokens"]["input"] is None
    assert result["cumulative_fallback"][0]["tokens"]["input"] == expected
    assert result["coverage"]["counter_resets"] == resets


def test_project_filter_conflict_and_quota_freshness(tmp_path):
    path = tmp_path / "log.jsonl"
    quota = event(
        "event_msg",
        {
            "type": "token_count",
            "rate_limits": {
                "primary": {"used_percent": 42, "window_minutes": 10080, "resets_at": 1791453780}
            },
        },
    )
    write(path, [meta(tmp_path / "another"), response(), quota])
    result = summarize([read_incremental(path, tmp_path)])
    assert result["responses"] == 0 and result["tokens"]["input"] is None
    assert result["account_quota"]["primary"]["observed_at"] == quota["timestamp"]
    assert result["coverage"]["unattributed_responses"] == 1
    write(path, [meta(tmp_path), response(), response(110)])
    result = summarize([read_incremental(path, tmp_path)])
    assert result["coverage"]["conflicts"] == 1 and result["savings_claim"] is False


def test_report_incremental_restart_and_no_transcript_body_persisted(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    write(
        sessions / "log.jsonl",
        [
            meta(tmp_path),
            response(),
            event("response_item", {"content": "SECRET-PROMPT-DO-NOT-PERSIST"}),
        ],
    )
    first = report(str(tmp_path), sessions_dir=str(sessions))
    second = report(str(tmp_path), sessions_dir=str(sessions))
    assert first["tokens"] == second["tokens"] and second["bytes_read"] == 0
    assert b"SECRET-PROMPT" not in (tmp_path / ".tausik/usage-codex.sqlite").read_bytes()


def test_thread_report_uses_only_that_thread_and_exposes_latest_context(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    write(
        sessions / "rollout-thread-a.jsonl",
        [meta(tmp_path, "thread-a"), response(80, "a", "thread-a")],
    )
    write(
        sessions / "rollout-thread-b.jsonl",
        [meta(tmp_path, "thread-b"), response(130, "b", "thread-b")],
    )

    result = report(str(tmp_path), sessions_dir=str(sessions), thread_id="thread-b")

    assert result["responses"] == 1
    assert result["tokens"]["input"] == 130
    assert result["latest_context_tokens"] == 130


def test_exact_task_window_includes_failed_close_rework_and_successful_close(tmp_path):
    path = tmp_path / "log.jsonl"
    rows = [
        meta(tmp_path),
        event(
            "turn_context",
            {"model": "gpt-test", "effort": "medium", "realtime_active": False},
        ),
    ]
    rows += [
        tool_call(".tausik/tausik task start accepted", "start"),
        response(10, "r-start"),
        tool_output("Task 'accepted' started (attempt #1).", "start"),
        tool_call("rg -n needle scripts", "work"),
        response(20, "r-work"),
        tool_output("Script completed", "work"),
        tool_call(".tausik/tausik task done accepted --ac-verified", "done-red"),
        response(30, "r-done-red"),
        tool_output("Closure blocked by bootstrap_drift", "done-red"),
        tool_call("python -m pytest -q", "retry"),
        response(40, "r-retry"),
        tool_output("1 passed", "retry"),
        tool_call(".tausik/tausik task done accepted --ac-verified", "done-green"),
        response(50, "r-done-green"),
        tool_output("Task 'accepted' completed.", "done-green"),
        tool_call("rg -n outside docs", "after"),
        response(60, "r-after"),
        tool_output("Script completed", "after"),
    ]
    write(path, rows)
    result = summarize([read_incremental(path, tmp_path)], ["accepted"], attempts={"accepted": 2})
    task = result["accepted_task_cost"]["tasks"][0]
    assert task["responses"] == 5
    assert task["tokens"]["input"] == 150
    assert task["attempts"] == 2 and task["retries"] == 1
    assert task["identity"] == {
        "model": ["gpt-test"],
        "reasoning": ["medium"],
        "speed": ["standard"],
    }
    assert task["comparable_identity"] is True
    assert result["coverage"]["unattributed_task_responses"] == 1


def test_failed_start_and_nested_window_are_never_exact(tmp_path):
    path = tmp_path / "log.jsonl"
    write(
        path,
        [
            meta(tmp_path),
            tool_call(".tausik/tausik task start rejected", "rejected"),
            response(10, "r-rejected"),
            tool_output("QG-0 blocked", "rejected"),
            tool_call(".tausik/tausik task start outer", "outer"),
            response(20, "r-outer"),
            tool_output("Task 'outer' started (attempt #1).", "outer"),
            tool_call(".tausik/tausik task start nested", "nested"),
            response(30, "r-nested"),
            tool_output("Task 'nested' started (attempt #1).", "nested"),
        ],
    )
    result = summarize([read_incremental(path, tmp_path)], ["rejected", "outer", "nested"])
    by_task = {task["task"]: task for task in result["accepted_task_cost"]["tasks"]}
    assert by_task["outer"]["responses"] == 1
    assert by_task["rejected"]["responses"] == 0
    assert by_task["nested"]["responses"] == 0
    assert result["coverage"]["window_conflicts"] == 1


def test_inherited_fork_boundaries_do_not_open_a_child_task_window(tmp_path):
    path = tmp_path / "fork.jsonl"
    write(
        path,
        [
            meta(tmp_path, "child"),
            meta(tmp_path, "parent"),
            tool_call(".tausik/tausik task start parent-task", "parent-start"),
            response(10, "parent-response", "parent"),
            tool_output("Task 'parent-task' started (attempt #1).", "parent-start"),
            response(20, "child-response", "child"),
        ],
    )
    result = summarize([read_incremental(path, tmp_path)], ["parent-task"])
    task = result["accepted_task_cost"]["tasks"][0]
    assert task["responses"] == 0
    assert result["coverage"]["open_task_windows"] == 0


def test_report_accepts_only_db_done_tasks_and_persists_no_command(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    write(
        sessions / "log.jsonl",
        [
            meta(tmp_path),
            event("turn_context", {"model": "gpt-test", "effort": "medium"}),
            tool_call(".tausik/tausik task start accepted", "start"),
            response(10, "r-start"),
            tool_output(
                [{"type": "input_text", "text": '{"task":{"slug":"accepted"},"started":true}'}],
                "start",
            ),
            event("turn_context", {"model": "gpt-other", "effort": "medium"}),
            tool_call(".tausik/tausik task done accepted", "done"),
            response(20, "r-done"),
            tool_output("Task 'accepted' completed.", "done"),
        ],
    )
    db = tmp_path / ".tausik" / "tausik.db"
    db.parent.mkdir()
    with sqlite3.connect(db) as conn:
        conn.execute(canonical_ddl("tasks"))
        conn.execute(
            """INSERT INTO tasks(
                slug, title, status, attempts, created_at, updated_at
            ) VALUES ('accepted', 'Accepted', 'done', 2, '2026-10-01', '2026-10-01')"""
        )
    rate_card = {
        "unit": "credits_per_million_tokens",
        "source": "https://developers.openai.com/docs/pricing",
        "as_of": "2026-10-02",
        "models": {
            "gpt-test": {"input": 100, "cached_input": 10, "output": 500},
            "gpt-other": {"input": 200, "cached_input": 20, "output": 1000},
        },
    }
    (tmp_path / ".tausik" / "config.json").write_text(
        json.dumps({"codex_subscription_credit_rates": rate_card}), encoding="utf-8"
    )
    result = report(str(tmp_path), sessions_dir=str(sessions))
    task = result["accepted_task_cost"]["tasks"][0]
    assert task["responses"] == 2 and task["retries"] == 1
    assert task["tokens"]["cache_write"] is None
    assert task["subscription_credits"] == 0.01775
    assert task["subscription_credit_breakdown"]["tokens"] == {
        "input": 15,
        "cached_input": 15,
        "output": 20,
    }
    assert task["subscription_credit_breakdown"]["reasoning_output_is_subset"] is True
    assert task["subscription_credit_breakdown"]["models"] == ["gpt-other", "gpt-test"]
    assert result["subscription_credit_rate_card"]["credits_are_not_api_usd_or_remaining_quota"]

    rate_card["models"] = {"another-model": {"input": 1, "cached_input": 1, "output": 1}}
    (tmp_path / ".tausik" / "config.json").write_text(
        json.dumps({"codex_subscription_credit_rates": rate_card}), encoding="utf-8"
    )
    unknown = report(str(tmp_path), sessions_dir=str(sessions))
    unknown_task = unknown["accepted_task_cost"]["tasks"][0]
    assert unknown_task["subscription_credits"] is None
    assert unknown_task["subscription_credit_status"] == "unknown-model-rate"
    assert unknown_task["tokens"] == task["tokens"], "raw telemetry survives pricing failure"

    from usage_credit import parse_rate_card

    for invalid in (
        {"unit": "credits_per_million_tokens", "models": {}},
        {**rate_card, "as_of": ""},
        {**rate_card, "models": {"gpt": {"input": -1, "cached_input": 1, "output": 1}}},
        {
            **rate_card,
            "models": {"gpt": {"input": float("nan"), "cached_input": 1, "output": 1}},
        },
    ):
        assert parse_rate_card({"codex_subscription_credit_rates": invalid}) == (
            None,
            "rate-card-invalid",
        )
    cache = (tmp_path / ".tausik/usage-codex.sqlite").read_bytes()
    assert b"task start accepted" not in cache and b"task done accepted" not in cache


def test_cli_and_mcp_share_native_report(tmp_path, monkeypatch, capsys):
    from pathlib import Path
    from types import SimpleNamespace

    from project_cli_metrics import cmd_metrics
    from project_parser import build_parser

    monkeypatch.syspath_prepend(
        str(Path(__file__).resolve().parents[1] / "harness/claude/mcp/project")
    )
    from handlers_status import _handle_metrics

    sessions = tmp_path / "codex/sessions"
    sessions.mkdir(parents=True)
    write(sessions / "log.jsonl", [meta(tmp_path), response()])
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    svc = SimpleNamespace(tausik_dir=lambda: str(tmp_path / ".tausik"))
    cmd_metrics(svc, build_parser().parse_args(["metrics", "tokens", "--host", "codex", "--json"]))
    cli = json.loads(capsys.readouterr().out)
    mcp = json.loads(_handle_metrics(svc, {"host": "codex"}))
    assert cli["tokens"] == mcp["tokens"] and mcp["responses"] == 1
    assert mcp["bytes_read"] == 0
