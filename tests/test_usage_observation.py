"""Behavior contracts shared by native Codex and provider adapters."""

import pytest

from usage_observation import (
    normalize_usage,
    observation,
    quota_snapshot,
    summarize_accepted_tasks,
    unique_observations,
)


@pytest.mark.parametrize(
    "wire,usage,expected",
    [
        (
            "anthropic",
            {
                "input_tokens": 2,
                "cache_read_input_tokens": 80,
                "cache_creation_input_tokens": 18,
                "output_tokens": 10,
            },
            (100, 80, 18, 10, None),
        ),
        (
            "codex",
            {
                "input_tokens": 100,
                "cached_input_tokens": 80,
                "output_tokens": 10,
                "reasoning_output_tokens": 4,
            },
            (100, 80, None, 10, 4),
        ),
        (
            "openai-chat",
            {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 80},
                "completion_tokens_details": {"reasoning_tokens": 4},
            },
            (100, 80, None, 10, 4),
        ),
        (
            "openai-responses",
            {
                "input_tokens": 100,
                "output_tokens": 10,
                "input_tokens_details": {"cached_tokens": 80},
            },
            (100, 80, None, 10, None),
        ),
        (
            "kilo-session",
            {
                "input": 10,
                "output": 3,
                "reasoning": 5,
                "cache": {"read": 20, "write": 2},
            },
            (32, 20, 2, 8, 5),
        ),
        ("anthropic", {"input_tokens": 2}, (None, None, None, None, None)),
        ("codex", None, (None, None, None, None, None)),
        ("codex", {"input_tokens": 0, "output_tokens": 0}, (0, None, None, 0, None)),
    ],
)
def test_wire_semantics(wire, usage, expected):
    result = normalize_usage(usage, wire)
    assert (
        tuple(
            result[k]
            for k in ("input", "cached_input", "cache_write", "output", "reasoning_output")
        )
        == expected
    )


@pytest.mark.parametrize(
    "usage,wire",
    [
        ({"input_tokens": -1}, "codex"),
        ({"input_tokens": True}, "codex"),
        ({"output_tokens": 1.5}, "codex"),
        ({"input_tokens": "100"}, "codex"),
        ({"input_tokens": 1, "cached_input_tokens": 2}, "codex"),
        ({"output_tokens": 1, "reasoning_output_tokens": 2}, "codex"),
        ({"prompt_tokens_details": []}, "openai-chat"),
        ({}, "unknown-provider"),
    ],
)
def test_corrupt_or_unsupported_usage_rejected(usage, wire):
    with pytest.raises(ValueError):
        normalize_usage(usage, wire)


@pytest.mark.parametrize(
    "host,provider,model",
    [
        ("codex", "openai", "gpt-model"),
        ("kilo", "z.ai", "glm-model"),
        ("cursor", "openrouter", "vendor/model"),
        ("claude-code", "anthropic", "claude-model"),
    ],
)
def test_identity_provenance_and_allowlist(host, provider, model):
    row = observation(
        {},
        "openai-chat",
        observed={"host": host, "model": model},
        configured={"provider": provider, "model": "wrong"},
        source={"timestamp": "2026-10-01T00:00:00Z", "prompt": "secret"},
    )
    assert row["identity"]["model"] == {"value": model, "basis": "observed"}
    assert row["identity"]["provider"] == {"value": provider, "basis": "configured"}
    assert row["identity"]["speed"] == {"value": None, "basis": "unknown"}
    assert "secret" not in str(row)
    assert row["tokens"]["input"] is None


def test_repeated_response_is_not_billed_twice_and_conflict_rejected():
    source = {"project": "p", "thread": "t", "response": "r", "task": "work"}
    row = observation(
        {"input_tokens": 10},
        "codex",
        observed={"host": "codex"},
        source=source,
        attribution="exact",
    )
    assert unique_observations([row, row]) == [row]
    conflict = observation(
        {"input_tokens": 11},
        "codex",
        observed={"host": "codex"},
        source=source,
        attribution="exact",
    )
    with pytest.raises(ValueError):
        unique_observations([row, conflict])
    unknown = observation(None, "codex")
    assert len(unique_observations([unknown, unknown])) == 2
    with pytest.raises(ValueError):
        observation({}, "codex", attribution="exact")


def test_accepted_task_cost_deduplicates_and_does_not_add_token_subsets_twice():
    row = observation(
        {
            "input_tokens": 100,
            "cached_input_tokens": 80,
            "output_tokens": 20,
            "reasoning_output_tokens": 5,
        },
        "codex",
        observed={"host": "codex", "model": "gpt-5.6-terra"},
        source={"project": "p", "thread": "t", "response": "r", "task": "accepted"},
        attribution="exact",
    )
    result = summarize_accepted_tasks([row, row], ["accepted"], attempts={"accepted": 2})
    task = result["tasks"][0]
    assert task["responses"] == 1
    assert task["attempts"] == 2 and task["retries"] == 1
    assert task["tokens"] == {
        "total": 120,
        "input": 100,
        "cached_input": 80,
        "cache_write": None,
        "output": 20,
        "reasoning_output": 5,
    }


def test_accepted_task_cost_keeps_missing_or_inexact_usage_unmeasured():
    exact_missing = observation(
        {"input_tokens": 10},
        "codex",
        source={"project": "p", "thread": "t", "response": "r", "task": "accepted"},
        attribution="exact",
    )
    inexact = observation({"input_tokens": 10, "output_tokens": 2}, "codex")
    result = summarize_accepted_tasks([exact_missing, inexact], ["accepted", "absent"])
    by_task = {row["task"]: row for row in result["tasks"]}
    assert by_task["accepted"]["measurable"] is False
    assert by_task["accepted"]["tokens"]["total"] is None
    assert by_task["absent"]["responses"] == 0
    assert result["unattributed_rows_excluded"] == 1


@pytest.mark.parametrize(
    "percent,valid",
    [
        (None, True),
        (0, True),
        (42.5, True),
        (-1, False),
        (101, False),
        (True, False),
        (float("nan"), False),
    ],
)
def test_quota_remains_separate_and_missing_is_unknown(percent, valid):
    args = {
        "account": "local-account",
        "observed_at": "2026-10-01T00:00:00Z",
        "window": "weekly",
        "used_percent": percent,
    }
    if not valid:
        with pytest.raises(ValueError):
            quota_snapshot(**args)
    else:
        result = quota_snapshot(**args)
        assert result["used_percent"] == percent
        assert result["resets_at"] is None
        assert "tokens" not in result and "task" not in result
