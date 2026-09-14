"""Optional OTLP/JSON trace export — an ADDITIONAL output over internal events.

TAUSIK's internal events remain the source of truth (l26-otel-export, AC1). This
exporter is opt-in and OFF by default; when disabled it is never called, so the
event path is unchanged. It is stdlib-only: it emits OTLP/JSON (the JSON
encoding of the OTLP trace protobuf), which any OTLP receiver ingests, rather
than depend on the OpenTelemetry SDK.

All GenAI attribute names come from `otel_semconv` — this file deliberately
holds NO `gen_ai.*` string literal, so a churn in the unstable GenAI conventions
touches only the mapper (AC2).
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from otel_semconv import (
    GEN_AI_OPERATION_EXECUTE_TOOL,
    GEN_AI_OPERATION_VALUE,
    SERVICE_NAME,
    genai_attributes,
    tool_attributes,
)

_TRACE_ID_RE = re.compile(r"\A[0-9a-f]{32}\Z")
_SPAN_ID_RE = re.compile(r"\A[0-9a-f]{16}\Z")
_TRUTHY_ENV = {"1", "true", "yes", "on"}


_FALSY_ENV = {"0", "false", "no", "off"}


def export_enabled(config: Any, env: dict[str, str] | None = None) -> bool:
    """True when OTLP export is turned on, via config or environment.

    Off by default — export is an extra output nobody pays for unless they ask.
    Precedence: an EXPLICIT `TAUSIK_OTEL_EXPORT` overrides config in BOTH
    directions — a truthy value forces on, a falsy value (`0`/`false`/`no`/`off`)
    forces off even when config enables it (an ops kill switch, s146 review).
    With the env var unset, `config['otel_export']['enabled']` decides. A
    malformed config is treated as "off", never as an error.
    """
    if env is None:
        env = dict(os.environ)
    raw = str(env.get("TAUSIK_OTEL_EXPORT", "")).strip().lower()
    if raw in _TRUTHY_ENV:
        return True
    if raw in _FALSY_ENV:
        return False
    if isinstance(config, dict):
        section = config.get("otel_export")
        if isinstance(section, dict) and bool(section.get("enabled")):
            return True
    return False


def _attribute(key: str, value: Any) -> dict[str, Any]:
    """One OTLP/JSON KeyValue. int64 is string-encoded per the OTLP/JSON spec."""
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    return {"key": key, "value": {"stringValue": str(value)}}


def build_otlp_trace(
    metrics: Any,
    *,
    trace_id: str,
    span_id: str,
    start_unix_nano: int,
    end_unix_nano: int,
    service_name: str = "tausik",
    scope_version: str = "",
    tool_calls: Any = None,
) -> dict[str, Any]:
    """Build one OTLP/JSON ResourceSpans document from a session-metrics dict.

    Deterministic given the injected ids and timestamps, so it is testable
    against a golden sample. Returns ``{}`` — never raises — for empty/None
    metrics or a malformed trace/span id (AC5): a bad id must not silently emit
    an OTLP span a collector would reject.

    ``tool_calls`` are recorded `usage_events` rows, emitted as CHILD spans of
    the session's ``invoke_agent`` — the nesting the conventions describe, and
    the half this project had not built: one span per session said what we
    spent and nothing about what we DID. A row that is not a tool call, or
    whose timestamps do not fit inside the parent, yields no span rather than a
    guess; the parent is emitted either way.
    """
    if not isinstance(metrics, dict) or not metrics:
        return {}
    if not (isinstance(trace_id, str) and _TRACE_ID_RE.match(trace_id)):
        return {}
    if not (isinstance(span_id, str) and _SPAN_ID_RE.match(span_id)):
        return {}
    start, end = int(start_unix_nano), int(end_unix_nano)
    if end < start:
        # A backwards span (start after end) is invalid OTLP — a collector would
        # reject it. Symmetric with the id guards above: never emit a bad span
        # (s146 review — a negative duration_sec could otherwise produce one).
        return {}

    attributes = [_attribute(k, v) for k, v in genai_attributes(metrics).items()]
    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": GEN_AI_OPERATION_VALUE,
        "kind": 1,  # SPAN_KIND_INTERNAL
        # uint64 nanos exceed JSON's safe integer range → string per OTLP/JSON.
        "startTimeUnixNano": str(start),
        "endTimeUnixNano": str(end),
        "attributes": attributes,
    }
    spans = [span, *_tool_spans(tool_calls, trace_id, span_id, start, end)]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [_attribute(SERVICE_NAME, service_name)],
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "tausik", "version": scope_version},
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def child_span_id(parent_span_id: str, row: Any) -> str:
    """A stable 8-byte span id for one recorded tool call.

    DERIVED, not random: the same row under the same parent yields the same id
    on every export, so a document can be regenerated and compared — and a
    receipt could one day cite one. Salted with the parent so the same row
    under two sessions does not collide.
    """
    key = f"{parent_span_id}:{row.get('id')}:{row.get('recorded_at')}:{row.get('tool_name')}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _tool_spans(
    rows: Any, trace_id: str, parent_span_id: str, start: int, end: int
) -> list[dict[str, Any]]:
    """Child `execute_tool` spans for the rows we can map honestly.

    A row is skipped — never guessed at — when it carries no tool name, when
    its own window does not lie inside the parent's, or when it is not a dict.
    Rows without their own timestamps inherit the parent's window: that is the
    truthful statement "this happened during the session", not a fabricated
    duration.
    """
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        attrs = tool_attributes(row)
        if not attrs:
            continue
        child_start = _nano(row.get("start_unix_nano"), start)
        child_end = _nano(row.get("end_unix_nano"), end)
        if child_end < child_start or child_start < start or child_end > end:
            continue
        out.append(
            {
                "traceId": trace_id,
                "spanId": child_span_id(parent_span_id, row),
                "parentSpanId": parent_span_id,
                "name": GEN_AI_OPERATION_EXECUTE_TOOL,
                "kind": 1,  # SPAN_KIND_INTERNAL
                "startTimeUnixNano": str(child_start),
                "endTimeUnixNano": str(child_end),
                "attributes": [_attribute(k, v) for k, v in attrs.items()],
            }
        )
    return out


def _nano(raw: Any, fallback: int) -> int:
    """An injected nanosecond timestamp, or the parent's when we do not have one."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def session_otlp_document(
    metrics: Any,
    config: Any = None,
    *,
    now_ns: int | None = None,
    duration_ns: int | None = None,
    rand_hex: str | None = None,
    tool_calls: Any = None,
) -> dict[str, Any]:
    """OTLP/JSON trace document for a whole session — or ``{}`` when disabled.

    The opt-in entry point the SessionEnd metrics hook calls: when export is off
    (the default) this returns ``{}`` and the hook writes nothing, so the events
    path is untouched (AC1). Trace/span ids and timestamps are injectable so the
    wiring is testable; defaults use os.urandom + the wall clock.

    ``tool_calls`` — recorded tool calls, when the caller has them — becomes the
    child `execute_tool` spans. A PARAMETER, not a new key inside ``metrics``:
    that dict is also written to disk and recorded to the database, and a
    telemetry extension has no business changing the shape of either. This
    module never opens a database itself, and a caller with no rows still gets
    the session span it always got.
    """
    if not isinstance(metrics, dict) or not export_enabled(config):
        return {}
    if rand_hex is None:
        rand_hex = os.urandom(24).hex()  # 48 hex → 32-char trace + 16-char span
    if now_ns is None:
        import time

        now_ns = time.time_ns()
    if duration_ns is None:
        try:
            duration_ns = int(metrics.get("duration_sec") or 0) * 1_000_000_000
        except (TypeError, ValueError):
            duration_ns = 0
    # A transcript can yield a negative duration_sec (out-of-order or
    # clock-skewed timestamps); clamp so start never lands after end (s146).
    duration_ns = max(0, duration_ns)
    return build_otlp_trace(
        metrics,
        trace_id=rand_hex[:32],
        span_id=rand_hex[32:48],
        start_unix_nano=now_ns - duration_ns,
        end_unix_nano=now_ns,
        tool_calls=tool_calls,
    )
