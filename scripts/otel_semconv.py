"""GenAI OpenTelemetry semantic-convention attribute names — the SINGLE source.

⚠ UNSTABLE CONVENTIONS. GenAI semantic conventions live in
`open-telemetry/semantic-conventions-genai` with ZERO published releases —
status Development, verified against the source repository on 2026-07-18. Blog
claims of "stable OTel GenAI" conflate the semconv release train with GenAI
maturity; they are not the same. The names below WILL churn, and that is
expected — NOT a bug. Keeping every `gen_ai.*` name in this one module means a
convention rename touches exactly this file, never the exporter or the event
path (l26-otel-export, AC2/AC4).
"""

from __future__ import annotations

from typing import Any

# Where the conventions live and their maturity, surfaced as data so a report or
# doc can cite the instability rather than restating it (AC4).
CONVENTIONS_SOURCE = "open-telemetry/semantic-conventions-genai"
CONVENTIONS_STATUS = "unstable/development (0 releases as of 2026-07-18)"

# --- Resource-level (stable OTel, not GenAI) -------------------------------
SERVICE_NAME = "service.name"

# --- GenAI span attributes (UNSTABLE — see module docstring) ---------------
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

GEN_AI_TOOL_NAME = "gen_ai.tool.name"
GEN_AI_AGENT_NAME = "gen_ai.agent.name"

# The value TAUSIK reports for gen_ai.system — this framework is the producer.
GEN_AI_SYSTEM_VALUE = "tausik"

# THE OPERATION NAME IS NOT FREE TEXT, and ours was. `gen_ai.operation.name` is
# an enumeration in the conventions — `chat`, `execute_tool`, `invoke_agent`,
# and others — and until now this module reported "session", a word the
# conventions do not define. A span shaped like GenAI that declares an
# operation nobody can interpret speaks the vocabulary without the meaning,
# which is the same defect as publishing a closed list of our own invention.
#
# Session runs map to `invoke_agent`: an agent run that contains the rest. A
# tool call maps to `execute_tool`. Both are members of the conventions' own
# list; anything we cannot map honestly gets NO span rather than a made-up
# operation (see `operation_for`).
GEN_AI_OPERATION_INVOKE_AGENT = "invoke_agent"
GEN_AI_OPERATION_EXECUTE_TOOL = "execute_tool"
OPERATIONS = (GEN_AI_OPERATION_INVOKE_AGENT, GEN_AI_OPERATION_EXECUTE_TOOL)

# Kept for the session document's span name, now bound to the convention's
# value rather than to a word of ours.
GEN_AI_OPERATION_VALUE = GEN_AI_OPERATION_INVOKE_AGENT

# The agent name a session span reports. TAUSIK runs one agent per session; the
# name is the framework's, not the model's — the model travels in
# gen_ai.request.model.
GEN_AI_AGENT_NAME_VALUE = "tausik"


def operation_for(kind: str) -> str | None:
    """The convention's operation name for one of OUR event kinds, or None.

    ``None`` is the honest answer for anything we cannot map — a memory write,
    a knowledge search — and the caller emits no span for it. Inventing an
    operation name would put our vocabulary inside a standard field, which is
    the thing this module exists to stop.
    """
    return {
        "session": GEN_AI_OPERATION_INVOKE_AGENT,
        "tool": GEN_AI_OPERATION_EXECUTE_TOOL,
    }.get(kind)


def tool_attributes(row: Any) -> dict[str, Any]:
    """Map ONE recorded tool call (a `usage_events` row) to semconv attributes.

    Same discipline as :func:`genai_attributes`: a field we do not have is
    omitted, never emitted as an empty string or a zero that a backend would
    read as a measured value. A row with no tool name is not a tool call and
    yields ``{}`` — the caller then emits nothing.
    """
    if not isinstance(row, dict):
        return {}
    tool = str(row.get("tool_name") or "").strip()
    if not tool:
        return {}
    attrs: dict[str, Any] = {
        GEN_AI_SYSTEM: GEN_AI_SYSTEM_VALUE,
        GEN_AI_OPERATION_NAME: GEN_AI_OPERATION_EXECUTE_TOOL,
        GEN_AI_TOOL_NAME: tool,
    }
    model = str(row.get("model_id") or "").strip()
    if model:
        attrs[GEN_AI_REQUEST_MODEL] = model
    for field, name in (
        ("tokens_input", GEN_AI_USAGE_INPUT_TOKENS),
        ("tokens_output", GEN_AI_USAGE_OUTPUT_TOKENS),
    ):
        raw = row.get(field)
        if raw:
            try:
                attrs[name] = int(raw)
            except (TypeError, ValueError):
                continue
    return attrs


def genai_attributes(metrics: Any) -> dict[str, Any]:
    """Map a TAUSIK session-metrics dict to ``{semconv_name: value}``.

    Missing, empty, or None fields are OMITTED — never emitted as an empty or
    zero-value attribute that a backend would misread as a real measurement.
    Returns ``{}`` for a non-dict input (the negative path never raises).
    """
    if not isinstance(metrics, dict):
        return {}
    attrs: dict[str, Any] = {
        GEN_AI_SYSTEM: GEN_AI_SYSTEM_VALUE,
        GEN_AI_OPERATION_NAME: GEN_AI_OPERATION_VALUE,
        GEN_AI_AGENT_NAME: GEN_AI_AGENT_NAME_VALUE,
    }
    model = str(metrics.get("model") or "").strip()
    if model:
        attrs[GEN_AI_REQUEST_MODEL] = model
    for field, name in (
        ("tokens_input", GEN_AI_USAGE_INPUT_TOKENS),
        ("tokens_output", GEN_AI_USAGE_OUTPUT_TOKENS),
    ):
        raw = metrics.get(field)
        if raw:  # 0 / None / missing → omit; a real usage attribute is > 0
            try:
                attrs[name] = int(raw)
            except (TypeError, ValueError):
                continue
    return attrs
