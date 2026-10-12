"""Portable usage contract; legacy ledgers retain their original semantics.

Adapters must choose a known wire format, not infer it from a model name.
Counters measure tokens, never subscription quota or estimated API charges.
Only allowlisted scalar metadata and counters leave the source transcript.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

IDENTITY_FIELDS = ("host", "host_version", "provider", "model", "reasoning", "speed")
SOURCE_FIELDS = ("timestamp", "source_version", "project", "thread", "response", "task")
FORMATS = {"anthropic", "codex", "kilo-session", "openai-chat", "openai-responses"}


def _counter(values: Mapping, key: str) -> int | None:
    value = values.get(key)
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError(f"Invalid nonnegative integer counter: {key}")
    return value


def _details(values: Mapping, key: str) -> Mapping:
    value = values.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"Invalid counter details: {key}")
    return value


def normalize_usage(usage: Mapping | None, wire_format: str) -> dict:
    """Normalize known semantics; reject corrupt counters and unknown formats.

    Anthropic input/cache buckets are disjoint. OpenAI-compatible and native
    Codex cached input is a subset. Missing components stay unknown; in
    particular a partial Anthropic record cannot establish total input.
    """
    if wire_format not in FORMATS:
        raise ValueError(f"Unsupported usage format: {wire_format}")
    if usage is None:
        usage = {}
    if not isinstance(usage, Mapping):
        raise ValueError("Usage must be a mapping or null")
    cache_write = None
    if wire_format == "anthropic":
        buckets = [
            _counter(usage, k)
            for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        ]
        total_input = (
            sum(x for x in buckets if x is not None)
            if all(x is not None for x in buckets)
            else None
        )
        cached, cache_write = buckets[1:]
        output = _counter(usage, "output_tokens")
        reasoning = None
    elif wire_format == "codex":
        total_input = _counter(usage, "input_tokens")
        cached = _counter(usage, "cached_input_tokens")
        output = _counter(usage, "output_tokens")
        reasoning = _counter(usage, "reasoning_output_tokens")
    elif wire_format == "kilo-session":
        plain_input = _counter(usage, "input")
        plain_output = _counter(usage, "output")
        cache = _details(usage, "cache")
        cached = _counter(cache, "read")
        cache_write = _counter(cache, "write")
        reasoning = _counter(usage, "reasoning")
        if plain_input is None or cached is None or cache_write is None:
            total_input = None
        else:
            total_input = plain_input + cached + cache_write
        output = (
            plain_output + reasoning if plain_output is not None and reasoning is not None else None
        )
    else:
        chat = wire_format == "openai-chat"
        input_key, output_key = (
            ("prompt_tokens", "completion_tokens") if chat else ("input_tokens", "output_tokens")
        )
        total_input = _counter(usage, input_key)
        output = _counter(usage, output_key)
        cached = _counter(_details(usage, input_key + "_details"), "cached_tokens")
        reasoning = _counter(_details(usage, output_key + "_details"), "reasoning_tokens")
    for subset, whole, name in (
        (cached, total_input, "cached input"),
        (reasoning, output, "reasoning output"),
    ):
        if subset is not None and whole is not None and subset > whole:
            raise ValueError(f"{name} exceeds its total")
    return {
        "input": total_input,
        "cached_input": cached,
        "cache_write": cache_write,
        "output": output,
        "reasoning_output": reasoning,
    }


def observation(
    usage: Mapping | None,
    wire_format: str,
    *,
    observed: Mapping | None = None,
    configured: Mapping | None = None,
    source: Mapping | None = None,
    attribution: str = "unknown",
) -> dict:
    """Build versioned JSON-safe evidence, keeping identity provenance per field.

    ``source`` IDs must already be opaque identifiers, not paths/prompts/secrets.
    Quota snapshots are separate account observations, never task token records.
    """
    if attribution not in {"unknown", "project", "exact"}:
        raise ValueError("Invalid attribution confidence")
    observed, configured, source = observed or {}, configured or {}, source or {}
    identity = {}
    for key in IDENTITY_FIELDS:
        value = observed.get(key)
        basis = "observed"
        if value is None:
            value, basis = configured.get(key), "configured"
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"Invalid identity field: {key}")
        identity[key] = {"value": value, "basis": basis if value is not None else "unknown"}
    provenance = {key: source.get(key) for key in SOURCE_FIELDS}
    if any(
        v is not None and (not isinstance(v, str) or not v.strip()) for v in provenance.values()
    ):
        raise ValueError("Source metadata must be nonempty strings or null")
    if attribution == "exact" and not all(provenance[k] for k in ("project", "task", "response")):
        raise ValueError("Exact attribution requires project, task and response")
    if attribution == "project" and not provenance["project"]:
        raise ValueError("Project attribution requires project identity")
    return {
        "schema_version": 1,
        "format": wire_format,
        "identity": identity,
        "source": provenance,
        "attribution": attribution,
        "tokens": normalize_usage(usage, wire_format),
    }


def unique_observations(rows: list[dict]) -> list[dict]:
    """Deduplicate exact source responses; conflicting repeats fail closed.

    Records without sufficient identity are retained, never guessed identical.
    Consumers must report them as unattributed rather than cost per task.
    """
    seen: dict[tuple, dict] = {}
    result = []
    for row in rows:
        source = row["source"]
        key = (
            row["identity"]["host"]["value"],
            source["project"],
            source["thread"],
            source["response"],
        )
        if all(key):
            if key in seen:
                if seen[key] != row:
                    raise ValueError("Conflicting usage for the same response")
                continue
            seen[key] = row
        result.append(row)
    return result


def summarize_accepted_tasks(
    rows: list[dict],
    accepted_tasks: Iterable[str],
    *,
    attempts: Mapping[str, int] | None = None,
) -> dict:
    """Aggregate exact accepted-task responses without counting subsets twice."""
    accepted = {str(slug) for slug in accepted_tasks if str(slug)}
    grouped: dict[str, list[dict]] = {slug: [] for slug in sorted(accepted)}
    unique = unique_observations(rows)
    for row in unique:
        source = row.get("source", {})
        slug = source.get("task")
        if row.get("attribution") == "exact" and slug in grouped:
            grouped[slug].append(row)
    result = []
    for slug, task_rows in grouped.items():
        token_rows = [row.get("tokens", {}) for row in task_rows]
        measurable = bool(token_rows) and all(
            tokens.get("input") is not None and tokens.get("output") is not None
            for tokens in token_rows
        )
        attempt_count = attempts.get(slug) if attempts is not None else None
        if type(attempt_count) is not int or attempt_count < 1:
            attempt_count = None

        def _subset_total(key: str) -> int | None:
            if not token_rows or any(tokens.get(key) is None for tokens in token_rows):
                return None
            return sum(int(tokens[key]) for tokens in token_rows)

        result.append(
            {
                "task": slug,
                "responses": len(task_rows),
                "attempts": attempt_count,
                "retries": attempt_count - 1 if attempt_count is not None else None,
                "measurable": measurable,
                "tokens": {
                    "total": (
                        sum(tokens["input"] + tokens["output"] for tokens in token_rows)
                        if measurable
                        else None
                    ),
                    "input": _subset_total("input") if measurable else None,
                    "cached_input": _subset_total("cached_input"),
                    "cache_write": _subset_total("cache_write"),
                    "output": _subset_total("output") if measurable else None,
                    "reasoning_output": _subset_total("reasoning_output"),
                },
            }
        )
    attributed = sum(len(task_rows) for task_rows in grouped.values())
    return {"tasks": result, "unattributed_rows_excluded": len(unique) - attributed}


def quota_snapshot(
    *,
    account: str,
    observed_at: str,
    window: str,
    used_percent: float | None = None,
    resets_at: str | None = None,
) -> dict:
    """Keep account quota/freshness separate from attributed task consumption.

    Account is an opaque local identifier. No API-price or token conversion is
    meaningful here; consumers compute freshness from the observation timestamp.
    """
    if not all(isinstance(v, str) and v.strip() for v in (account, observed_at, window)):
        raise ValueError("Quota requires account, timestamp and window")
    if used_percent is not None and (
        type(used_percent) not in (int, float) or not 0 <= used_percent <= 100
    ):
        raise ValueError("Quota percentage must be between 0 and 100 or unknown")
    if resets_at is not None and (not isinstance(resets_at, str) or not resets_at.strip()):
        raise ValueError("Invalid reset timestamp")
    return {
        "schema_version": 1,
        "account": account,
        "observed_at": observed_at,
        "window": window,
        "used_percent": used_percent,
        "resets_at": resets_at,
    }
