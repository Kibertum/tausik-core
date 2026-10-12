"""Incremental native Codex reader. Persist counters, never conversation bodies."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from usage_observation import (
    normalize_usage,
    observation,
    quota_snapshot,
    summarize_accepted_tasks,
)

COUNTERS = ("input", "cached_input", "cache_write", "output", "reasoning_output")
_TASK_START = re.compile(r"\btask\s+start\s+([a-z0-9][a-z0-9-]*)")
_TASK_DONE = re.compile(r"\btask\s+done\s+([a-z0-9][a-z0-9-]*)")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _anchor(stream, offset: int) -> str:
    stream.seek(max(0, offset - 256))
    return _digest(stream.read(min(offset, 256)))


def _new_state() -> dict:
    return {
        "version": 7,
        "offset": 0,
        "anchor": _digest(b""),
        "identity": {"host": "codex"},
        "thread": None,
        "project": None,
        "rows": {},
        "quota": {},
        "last_total": None,
        "fallback": [],
        "resets": 0,
        "malformed": 0,
        "conflicts": 0,
        "inherited": 0,
        "bytes_read": 0,
        "active_task": None,
        "pending_event": None,
        "window_conflicts": 0,
    }


def read_incremental(path: Path, project: Path, previous: dict | None = None) -> dict:
    """Replay only appended complete lines, replacing state after truncation/rewrite.

    A partial final line is left unread until complete. An invalid *complete*
    record is counted and skipped, never relabelled as zero usage.
    """
    state = previous if previous and previous.get("version") == 7 else _new_state()
    with path.open("rb") as stream:
        stream.seek(0, 2)
        if stream.tell() < state["offset"] or _anchor(stream, state["offset"]) != state["anchor"]:
            state = _new_state()
        stream.seek(state["offset"])
        start = state["offset"]
        while True:
            position = stream.tell()
            line = stream.readline()
            if not line or not line.endswith(b"\n"):
                stream.seek(position)
                break
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("Non-object event")
                _consume(state, record, project)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
                state["malformed"] += 1
        state["offset"] = stream.tell()
        state["bytes_read"] = state["offset"] - start
        state["anchor"] = _anchor(stream, state["offset"])
    return state


def _consume(state: dict, record: dict, project: Path) -> None:
    kind, payload = record.get("type"), record.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("Invalid payload")
    timestamp = record.get("timestamp")
    if kind == "session_meta":
        if state["thread"] is not None:
            return
        state["thread"] = payload.get("id") or payload.get("session_id")
        cwd = payload.get("cwd")
        matches = isinstance(cwd, str) and Path(cwd).resolve() == project.resolve()
        state["project"] = _digest(str(project.resolve()).casefold().encode()) if matches else None
        state["identity"].update(
            {"host_version": payload.get("cli_version"), "provider": payload.get("model_provider")}
        )
    elif kind == "turn_context":
        realtime = payload.get("realtime_active")
        state["identity"].update(
            {
                "model": payload.get("model"),
                "reasoning": payload.get("effort"),
                "speed": (
                    "realtime" if realtime is True else "standard" if realtime is False else None
                ),
            }
        )
    elif kind == "response_item" and payload.get("type") in {
        "custom_tool_call",
        "function_call",
    }:
        event = _task_event(payload)
        if event:
            action, slug = event
            current = state.get("active_task")
            if action == "start" and current and current != slug:
                state["window_conflicts"] += 1
                state["active_task"] = None
                event = None
            elif action == "done" and current != slug:
                state["window_conflicts"] += 1
                event = None
        state["pending_event"] = (
            {"action": event[0], "task": event[1], "call": payload.get("call_id")}
            if event
            else None
        )
    elif kind == "token_usage_record":
        response = payload.get("response_id")
        if not response:
            raise ValueError("Native response has no ID")
        thread = payload.get("thread_id") or state["thread"]
        inherited = thread != state["thread"]
        pending = state.get("pending_event") or {}
        task = pending.get("task") or state.get("active_task")
        # A start call is not authoritative until its tool result says it started.
        exact = bool(
            task and pending.get("action") != "start" and state["project"] and not inherited
        )
        row = observation(
            payload.get("usage"),
            "codex",
            observed=state["identity"],
            source={
                "timestamp": timestamp,
                "source_version": "token_usage_record/v1",
                "thread": thread,
                "response": response,
                "project": None if inherited else state["project"],
                "task": task if exact else None,
            },
            attribution=(
                "exact" if exact else "project" if state["project"] and not inherited else "unknown"
            ),
        )
        old = state["rows"].get(response)
        if old is not None and old["tokens"] != row["tokens"]:
            state["conflicts"] += 1
        else:
            state["rows"][response] = row
        if inherited and old is None:
            state["inherited"] += 1
        if pending:
            pending["response"] = response
            pending["inherited"] = inherited
            state["pending_event"] = pending
    elif kind == "response_item" and payload.get("type") in {
        "custom_tool_call_output",
        "function_call_output",
    }:
        pending = state.get("pending_event") or {}
        if pending and pending.get("call") == payload.get("call_id"):
            _finish_task_event(state, pending, payload.get("output"))
            state["pending_event"] = None
    elif kind == "event_msg" and payload.get("type") == "token_count":
        info = payload.get("info") or {}
        raw = info.get("total_token_usage")
        if raw is not None:
            total = normalize_usage(raw, "codex")
            old = state["last_total"]
            reset = old and any(
                total[k] is not None and old[k] is not None and total[k] < old[k] for k in COUNTERS
            )
            if reset:
                state["fallback"].append(old)
                state["resets"] += 1
            state["last_total"] = total
        limits = payload.get("rate_limits") or {}
        for name in ("primary", "secondary"):
            limit = limits.get(name)
            if not isinstance(limit, dict) or not timestamp:
                continue
            reset = limit.get("resets_at")
            reset_iso = datetime.fromtimestamp(reset, timezone.utc).isoformat() if reset else None
            state["quota"][name] = quota_snapshot(
                account="codex-local-account",
                observed_at=timestamp,
                window=str(limit.get("window_minutes", name)),
                used_percent=limit.get("used_percent"),
                resets_at=reset_iso,
            )


def _task_event(payload: dict) -> tuple[str, str] | None:
    """Extract only a task boundary; never retain the command or arguments."""
    name = str(payload.get("name") or "")
    raw = (
        payload.get("input")
        if payload.get("type") == "custom_tool_call"
        else payload.get("arguments")
    )
    source = raw if isinstance(raw, str) else json.dumps(raw or {})
    for action, pattern in (("done", _TASK_DONE), ("start", _TASK_START)):
        match = pattern.search(source)
        if match:
            return action, match.group(1)
    if name.endswith(("task_start", "task_done")):
        try:
            args = json.loads(source) if isinstance(source, str) else {}
        except ValueError:
            return None
        slug = args.get("slug") if isinstance(args, dict) else None
        if isinstance(slug, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            return ("start" if name.endswith("task_start") else "done"), slug
    return None


def _finish_task_event(state: dict, pending: dict, output: object) -> None:
    """Commit a boundary only after its tool result proves success."""
    if pending.get("inherited"):
        return
    slug = str(pending.get("task") or "")
    text = _output_text(output)
    if pending.get("action") == "start":
        success = (
            f"Task '{slug}' started" in text
            or "already active (resumed)" in text
            or (slug in text and ('"started":true' in text or '"started": true' in text))
        )
        response = pending.get("response")
        row = state["rows"].get(response)
        if success:
            state["active_task"] = slug
            if row and row["source"].get("project"):
                row["source"]["task"] = slug
                row["attribution"] = "exact"
        elif row:
            row["source"]["task"] = None
            row["attribution"] = "project" if row["source"].get("project") else "unknown"
    elif pending.get("action") == "done" and f"Task '{slug}' completed" in text:
        state["active_task"] = None


def _output_text(value: object) -> str:
    """Flatten an ephemeral tool result for a success marker; persist none of it."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_output_text(item) for item in value)
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
        return "\n".join(_output_text(item) for item in value.values())
    return ""


def summarize(
    states: list[dict],
    accepted_tasks: list[str] | None = None,
    *,
    attempts: dict[str, int] | None = None,
) -> dict:
    """Prefer response evidence; expose cumulative fallback separately, never add it.

    No task inference from the active task or timestamp. Cumulative-only history
    is useful as an explicitly unattributed estimate, not a response baseline.
    """
    rows: dict[str, dict] = {}
    conflicts = sum(s["conflicts"] for s in states)
    for state in states:
        for key, row in state["rows"].items():
            old = rows.get(key)
            if old and old["tokens"] != row["tokens"]:
                conflicts += 1
            elif old is None or (not old["source"]["project"] and row["source"]["project"]):
                rows[key] = row
    own = [r for r in rows.values() if r["source"]["project"]]
    exact = [r for r in own if r.get("attribution") == "exact"]
    task_cost = summarize_accepted_tasks(own, accepted_tasks or [], attempts=attempts)
    for task in task_cost["tasks"]:
        task_rows = [row for row in exact if row["source"].get("task") == task["task"]]
        identity = {
            key: sorted(
                {
                    row["identity"][key]["value"]
                    for row in task_rows
                    if row["identity"][key]["value"] is not None
                }
            )
            for key in ("model", "reasoning", "speed")
        }
        task["identity"] = identity
        task["comparable_identity"] = all(len(identity[key]) == 1 for key in identity)
    totals = {
        k: sum(r["tokens"][k] for r in own)
        if own and all(r["tokens"][k] is not None for r in own)
        else None
        for k in COUNTERS
    }
    fallback = []
    seen_threads = set()
    for state in states:
        if not state["project"] or state["rows"] or state["thread"] in seen_threads:
            continue
        seen_threads.add(state["thread"])
        segments = state["fallback"] + ([state["last_total"]] if state["last_total"] else [])
        if segments:
            fallback.append(
                {
                    "thread": state["thread"],
                    "attribution": "unknown",
                    "tokens": {
                        k: sum(s[k] for s in segments)
                        if all(s[k] is not None for s in segments)
                        else None
                        for k in COUNTERS
                    },
                }
            )
    quota: dict[str, dict] = {}
    for state in states:
        for key, value in state["quota"].items():
            if key not in quota or value["observed_at"] > quota[key]["observed_at"]:
                quota[key] = value
    return {
        "schema_version": 1,
        "host": "codex",
        "responses": len(own),
        "tokens": totals,
        "task_attribution": "exact-native-boundaries" if exact else "unknown",
        "response_rounds": len(own),
        "accepted_task_cost": task_cost,
        "cumulative_fallback": fallback,
        "account_quota": quota,
        "models": sorted(
            {r["identity"]["model"]["value"] for r in own if r["identity"]["model"]["value"]}
        ),
        "coverage": {
            "files": len(states),
            "native_files": sum(bool(s["rows"]) for s in states),
            "unattributed_responses": len(rows) - len(own),
            "counter_resets": sum(s["resets"] for s in states),
            "malformed": sum(s["malformed"] for s in states),
            "conflicts": conflicts,
            "exact_task_responses": len(exact),
            "unattributed_task_responses": len(own) - len(exact),
            "open_task_windows": sum(bool(s.get("active_task")) for s in states),
            "window_conflicts": sum(s.get("window_conflicts", 0) for s in states),
        },
        "bytes_read": sum(s["bytes_read"] for s in states),
        "savings_claim": False,
        "reliable_totals": conflicts == 0 and not any(s["malformed"] for s in states),
    }
