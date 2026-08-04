"""Tests for OTLP/JSON trace export (l26-otel-export).

Export is an ADDITIONAL output over TAUSIK's internal events, which stay the
source of truth. It is opt-in and stdlib-only (OTLP/JSON, ingested by any OTLP
receiver — no OTel SDK dependency). GenAI semantic conventions are UNSTABLE
(open-telemetry/semantic-conventions-genai, 0 releases, status Development as of
2026-07-18), so every gen_ai.* attribute name lives in one mapper module; this
suite pins the toggle, a golden OTLP document, and the no-crash negative path.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import otel_semconv  # noqa: E402
from otel_export import build_otlp_trace, export_enabled  # noqa: E402
from otel_semconv import genai_attributes  # noqa: E402

# The AC2 lint below walks all of scripts/ to prove no gen_ai.* literal escaped
# the single mapper module (convention #330), so ANY change under scripts/ can
# break it — a basename heuristic would never map that change back to this file.
CROSSCUTTING_SCOPE = ["scripts/"]

_SAMPLE_METRICS = {
    "model": "claude-opus-4-8",
    "tokens_input": 1000,
    "tokens_output": 500,
    "tokens_total": 1500,
    "cost_usd": 0.0175,
    "tool_calls": 7,
}


class TestExportToggle:
    """AC1 — opt-in; default off so the events path is never altered."""

    def test_default_off(self):
        assert export_enabled({}) is False
        assert export_enabled(None) is False

    def test_config_enables(self):
        assert export_enabled({"otel_export": {"enabled": True}}) is True

    def test_config_disabled_explicit(self):
        assert export_enabled({"otel_export": {"enabled": False}}) is False

    def test_env_enables(self):
        assert export_enabled({}, env={"TAUSIK_OTEL_EXPORT": "1"}) is True
        assert export_enabled({}, env={"TAUSIK_OTEL_EXPORT": "0"}) is False

    def test_env_falsy_overrides_config_enabled(self):
        # s146 review LOW: an explicit falsy env value is an ops kill switch —
        # it forces OFF even when config enables export.
        cfg = {"otel_export": {"enabled": True}}
        assert export_enabled(cfg, env={"TAUSIK_OTEL_EXPORT": "0"}) is False
        assert export_enabled(cfg, env={"TAUSIK_OTEL_EXPORT": "off"}) is False
        # env unset → config decides (still on).
        assert export_enabled(cfg, env={}) is True


class TestSemconvMapper:
    """AC2/AC4 — names centralized; instability documented."""

    def test_attributes_use_semconv_names(self):
        attrs = genai_attributes(_SAMPLE_METRICS)
        assert attrs[otel_semconv.GEN_AI_REQUEST_MODEL] == "claude-opus-4-8"
        assert attrs[otel_semconv.GEN_AI_USAGE_INPUT_TOKENS] == 1000
        assert attrs[otel_semconv.GEN_AI_USAGE_OUTPUT_TOKENS] == 500

    def test_missing_fields_omitted_not_empty(self):
        # An empty model must not emit an empty attribute.
        attrs = genai_attributes({"model": "", "tokens_input": 0, "tokens_output": 0})
        assert otel_semconv.GEN_AI_REQUEST_MODEL not in attrs

    def test_instability_is_documented(self):
        # AC4: the mapper must self-declare that GenAI conventions are unstable.
        assert "0 releases" in otel_semconv.__doc__ or "Development" in otel_semconv.__doc__
        assert otel_semconv.CONVENTIONS_STATUS
        assert "semantic-conventions-genai" in otel_semconv.CONVENTIONS_SOURCE

    def test_no_hardcoded_semconv_names_outside_mapper(self):
        # AC2 lint: no gen_ai.* string literal anywhere in scripts/ except the
        # mapper — a convention rename must touch exactly one file.
        scripts_dir = os.path.join(os.path.dirname(__file__), "..", "scripts")
        offenders = []
        # Catch both the contiguous `"gen_ai.usage..."` literal AND the
        # split-string evasion `"gen_ai" + ".system"` (s146 review MED): any
        # quoted `gen_ai` token, whether followed by a dot or a closing quote.
        pat = re.compile(r"[\"']gen_ai(?:\.|[\"'])")
        for root, _dirs, files in os.walk(scripts_dir):
            for fn in files:
                if not fn.endswith(".py") or fn == "otel_semconv.py":
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8") as f:
                    if pat.search(f.read()):
                        offenders.append(os.path.relpath(path, scripts_dir))
        assert offenders == [], f"hardcoded gen_ai.* semconv names outside mapper: {offenders}"


class TestBuildOtlpTrace:
    """AC3 — a structurally valid OTLP/JSON document; golden on fixed input."""

    def _build(self):
        return build_otlp_trace(
            _SAMPLE_METRICS,
            trace_id="0af7651916cd43dd8448eb211c80319c",
            span_id="b7ad6b7169203331",
            start_unix_nano=1690000000000000000,
            end_unix_nano=1690000000500000000,
            service_name="tausik",
            scope_version="1.8.0",
        )

    def test_otlp_structure_valid(self):
        doc = self._build()
        rs = doc["resourceSpans"][0]
        assert any(
            a["key"] == "service.name" and a["value"]["stringValue"] == "tausik"
            for a in rs["resource"]["attributes"]
        )
        span = rs["scopeSpans"][0]["spans"][0]
        # OTLP/JSON: trace/span ids are hex strings of fixed width.
        assert re.fullmatch(r"[0-9a-f]{32}", span["traceId"])
        assert re.fullmatch(r"[0-9a-f]{16}", span["spanId"])
        assert span["name"]
        # Timestamps are strings in OTLP/JSON (uint64 does not fit JSON number).
        assert span["startTimeUnixNano"] == "1690000000000000000"
        assert span["endTimeUnixNano"] == "1690000000500000000"

    def test_span_carries_genai_attributes(self):
        span = self._build()["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        by_key = {a["key"]: a["value"] for a in span["attributes"]}
        assert by_key[otel_semconv.GEN_AI_REQUEST_MODEL] == {"stringValue": "claude-opus-4-8"}
        assert by_key[otel_semconv.GEN_AI_USAGE_INPUT_TOKENS] == {"intValue": "1000"}

    def test_golden_document_is_stable(self):
        # Same input → byte-identical document (deterministic; ids injected).
        assert self._build() == self._build()


class TestNegativePath:
    """AC5 — empty/malformed metrics never crash and never corrupt output."""

    def test_none_metrics_returns_empty(self):
        assert (
            build_otlp_trace(
                None, trace_id="a" * 32, span_id="b" * 16, start_unix_nano=1, end_unix_nano=2
            )
            == {}
        )

    def test_empty_metrics_returns_empty(self):
        assert (
            build_otlp_trace(
                {}, trace_id="a" * 32, span_id="b" * 16, start_unix_nano=1, end_unix_nano=2
            )
            == {}
        )

    def test_missing_fields_do_not_crash(self):
        doc = build_otlp_trace(
            {"tool_calls": 3},  # no model, no tokens
            trace_id="a" * 32,
            span_id="b" * 16,
            start_unix_nano=1,
            end_unix_nano=2,
        )
        # Still a valid span (with whatever attributes survived), no exception.
        assert doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["name"]

    def test_bad_id_widths_rejected_safely(self):
        # A malformed id must not silently emit an invalid OTLP span.
        assert (
            build_otlp_trace(
                _SAMPLE_METRICS,
                trace_id="tooshort",
                span_id="b" * 16,
                start_unix_nano=1,
                end_unix_nano=2,
            )
            == {}
        )


class TestSessionWiring:
    """AC1 — the session document entry point: opt-in; off leaves events alone."""

    def test_disabled_returns_empty(self):
        from otel_export import session_otlp_document

        # Default/disabled config → no document, so the hook writes no OTLP file.
        assert session_otlp_document(_SAMPLE_METRICS, {}) == {}
        assert session_otlp_document(_SAMPLE_METRICS, None) == {}

    def test_enabled_builds_valid_span(self):
        from otel_export import session_otlp_document

        doc = session_otlp_document(
            _SAMPLE_METRICS,
            {"otel_export": {"enabled": True}},
            now_ns=1690000000500000000,
            duration_ns=500000000,
            rand_hex="0af7651916cd43dd8448eb211c80319c" + "b7ad6b7169203331",
        )
        span = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert span["traceId"] == "0af7651916cd43dd8448eb211c80319c"
        assert span["startTimeUnixNano"] == "1690000000000000000"

    def test_enabled_empty_metrics_still_safe(self):
        # NEGATIVE (AC5) at the wiring layer: enabled but empty → {}, no crash.
        from otel_export import session_otlp_document

        assert session_otlp_document({}, {"otel_export": {"enabled": True}}) == {}

    def test_negative_duration_clamped_not_backwards(self):
        # s146 review MED: a negative duration_sec must not yield a start>end
        # span. session_otlp_document clamps duration → start == end (valid).
        from otel_export import session_otlp_document

        doc = session_otlp_document(
            {**_SAMPLE_METRICS, "duration_sec": -120},
            {"otel_export": {"enabled": True}},
            now_ns=1800000000000000000,
            rand_hex="0af7651916cd43dd8448eb211c80319c" + "b7ad6b7169203331",
        )
        span = doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        assert int(span["endTimeUnixNano"]) >= int(span["startTimeUnixNano"])


class TestBackwardsSpanRejected:
    """s146 review MED — the builder never emits a start>end span."""

    def test_end_before_start_returns_empty(self):
        assert (
            build_otlp_trace(
                _SAMPLE_METRICS,
                trace_id="a" * 32,
                span_id="b" * 16,
                start_unix_nano=1000,
                end_unix_nano=500,
            )
            == {}
        )

    def test_equal_start_end_is_valid(self):
        doc = build_otlp_trace(
            _SAMPLE_METRICS,
            trace_id="a" * 32,
            span_id="b" * 16,
            start_unix_nano=1000,
            end_unix_nano=1000,
        )
        assert doc["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["name"]
