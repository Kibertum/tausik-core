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

# The value TAUSIK reports for gen_ai.system — this framework is the producer.
GEN_AI_SYSTEM_VALUE = "tausik"
GEN_AI_OPERATION_VALUE = "session"


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
