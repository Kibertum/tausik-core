"""Offline topology of native Codex response rounds; stores no transcript bodies."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable

_START = re.compile(r"\btask\s+start\s+([a-z0-9][a-z0-9-]*)")
_DONE = re.compile(r"\btask\s+done\s+([a-z0-9][a-z0-9-]*)")


def action(payload: dict) -> tuple[str, tuple[str, str] | None]:
    """Return a body-free action label and an optional task boundary."""
    raw = (
        payload.get("input")
        if payload.get("type") == "custom_tool_call"
        else payload.get("arguments")
    )
    source = raw if isinstance(raw, str) else json.dumps(raw or {})
    if match := _DONE.search(source):
        return "task-done", ("done", match.group(1))
    if match := _START.search(source):
        return "task-start", ("start", match.group(1))
    lowered = source.casefold()
    if "task show" in lowered or "task_show" in lowered or "--package" in lowered:
        return "task-context", None
    if "task log" in lowered or "task step" in lowered or "task_log" in lowered:
        return "task-progress", None
    if "tausik verify" in lowered or "pytest" in lowered or "ruff" in lowered or "mypy" in lowered:
        return "verification", None
    if "apply_patch" in lowered or '"write"' in lowered or "set-content" in lowered:
        return "edit", None
    if any(word in lowered for word in ("get-content", "rg -n", "read_mcp_resource", "view_image")):
        return "retrieval", None
    if "memory search" in lowered or "memory_list" in lowered or "memory_search" in lowered:
        return "memory", None
    return "other-tool", None


def _success(kind: str, slug: str, output: object) -> bool:
    text = output if isinstance(output, str) else json.dumps(output or {}, ensure_ascii=False)
    if kind == "start":
        return (
            f"Task '{slug}' started" in text
            or "already active (resumed)" in text
            or (slug in text and ('"started":true' in text or '"started": true' in text))
        )
    return f"Task '{slug}' completed" in text


def extract(paths: Iterable[str], accepted: set[str]) -> tuple[dict[str, list[str]], dict]:
    """Extract ordered response labels from successful, DB-accepted task windows."""
    tasks: dict[str, list[str]] = {}
    transcripts = 0
    ambiguous = 0
    inherited = 0
    duplicate_responses = 0
    seen_responses: set[str] = set()
    for filename in paths:
        transcripts += 1
        thread: str | None = None
        active: str | None = None
        rounds: dict[str, list[str]] = {}
        pending: dict[str, tuple[str, str, list[str]]] = {}
        valid_rounds: set[int] = set()
        current: list[str] = []
        current_response: str | None = None
        with open(filename, encoding="utf-8", errors="replace") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                payload = record.get("payload") or {}
                if record.get("type") == "session_meta" and thread is None:
                    thread = str(payload.get("id") or payload.get("session_id") or "") or None
                elif record.get("type") == "response_item" and payload.get("type") in {
                    "custom_tool_call",
                    "function_call",
                }:
                    label, boundary = action(payload)
                    current.append(label)
                    if boundary:
                        pending[str(payload.get("call_id"))] = (*boundary, current)
                elif record.get("type") == "token_usage_record":
                    current_response = str(payload.get("response_id") or "")
                    response_thread = payload.get("thread_id") or thread
                    if thread and response_thread != thread:
                        inherited += 1
                        current = []
                        continue
                    if current_response in seen_responses:
                        duplicate_responses += 1
                        current = []
                        continue
                    if current_response:
                        seen_responses.add(current_response)
                    if current_response and current:
                        rounds[current_response] = current
                        valid_rounds.add(id(current))
                    current = []
                elif record.get("type") == "response_item" and payload.get("type") in {
                    "custom_tool_call_output",
                    "function_call_output",
                }:
                    pending_boundary = pending.pop(str(payload.get("call_id")), None)
                    if not pending_boundary:
                        continue
                    kind, slug, boundary_round = pending_boundary
                    if id(boundary_round) not in valid_rounds:
                        continue
                    if not _success(kind, slug, payload.get("output")):
                        if kind == "done" and active == slug:
                            tasks.setdefault(slug, []).append("task-done-failed")
                        continue
                    if kind == "start":
                        if active and active != slug:
                            ambiguous += 1
                            active = None
                        elif slug in accepted:
                            active = slug
                            tasks.setdefault(slug, []).append(_label(boundary_round))
                    elif active == slug:
                        tasks.setdefault(slug, []).append(_label(boundary_round))
                        active = None
                    else:
                        ambiguous += 1
                if record.get("type") == "token_usage_record" and active and current_response:
                    labels = rounds.pop(current_response, None)
                    if labels and not any(x in {"task-start", "task-done"} for x in labels):
                        tasks.setdefault(active, []).append(_label(labels))
    tasks = {slug: rows for slug, rows in tasks.items() if slug in accepted and rows}
    return tasks, {
        "transcripts": transcripts,
        "ambiguous_boundaries": ambiguous,
        "inherited_responses_excluded": inherited,
        "duplicate_responses_excluded": duplicate_responses,
    }


def _label(actions: list[str]) -> str:
    return "+".join(dict.fromkeys(actions)) if actions else "message"


def report(tasks: dict[str, list[str]], coverage: dict) -> dict:
    pairs = Counter(
        (left, right) for rounds in tasks.values() for left, right in zip(rounds, rounds[1:])
    )
    ranked = [
        {"sequence": list(pair), "occurrences": count, "upper_bound_rounds_removed": count}
        for pair, count in pairs.most_common()
    ]
    return {
        "schema_version": 1,
        "coverage": {
            **coverage,
            "accepted_windows": len(tasks),
            "accepted_response_rounds": sum(map(len, tasks.values())),
        },
        "transitions": ranked,
        "limitations": [
            "Only successful native task boundaries whose slug is DB-accepted are included.",
            "Counts are deterministic upper bounds on removable round boundaries, not causal token savings.",
            "Transcript bodies, commands and tool outputs are not returned or persisted.",
        ],
    }
