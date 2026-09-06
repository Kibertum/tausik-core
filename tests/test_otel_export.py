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
from otel_export import build_otlp_trace, child_span_id, export_enabled  # noqa: E402
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

    def test_the_document_is_deterministic(self):
        # Same input → byte-identical document (deterministic; ids injected).
        # RENAMED from "golden_document_is_stable", which it never was: a
        # comparison of a build with ITSELF pins determinism and nothing else,
        # while the name promised a pinned reference. It could not notice that
        # the span reported an operation name the conventions do not define —
        # and did not, for a whole release.
        assert self._build() == self._build()

    def test_the_operation_name_is_one_the_conventions_define(self):
        """The half the name above promised and did not deliver.

        `gen_ai.operation.name` is an ENUMERATION in the conventions, and this
        project reported "session" — a word of ours inside a standard field,
        which is the vocabulary without the meaning. `assert span["name"]`
        (truthiness) let that stand; this pins the value.
        """
        span = self._build()["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        by_key = {a["key"]: a["value"] for a in span["attributes"]}
        assert span["name"] == otel_semconv.GEN_AI_OPERATION_INVOKE_AGENT
        assert by_key[otel_semconv.GEN_AI_OPERATION_NAME] == {"stringValue": "invoke_agent"}
        assert by_key[otel_semconv.GEN_AI_OPERATION_NAME]["stringValue"] in otel_semconv.OPERATIONS
        assert by_key[otel_semconv.GEN_AI_AGENT_NAME] == {"stringValue": "tausik"}

    def test_no_operation_value_of_our_own_invention_survives(self):
        """NEGATIVE SCENARIO: "session" must not reappear as an operation.

        Written because it WAS the value: a detector that only checked the
        field was present would have gone on passing.
        """
        doc = self._build()
        for scope_span in doc["resourceSpans"][0]["scopeSpans"]:
            for span in scope_span["spans"]:
                by_key = {a["key"]: a["value"] for a in span["attributes"]}
                value = by_key[otel_semconv.GEN_AI_OPERATION_NAME]["stringValue"]
                assert value in otel_semconv.OPERATIONS, f"{value!r} is not a defined operation"


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


class TestToolSpansNestUnderTheAgentRun:
    """The shape the conventions describe, and the half this project lacked.

    One span per session said what we SPENT and nothing about what we DID.
    Every case here is a recorded `usage_events` row: mapped when we can say
    something true about it, skipped when we cannot — never guessed at.
    """

    PARENT = "b7ad6b7169203331"
    TRACE = "0af7651916cd43dd8448eb211c80319c"
    START, END = 1690000000000000000, 1690000000500000000

    def _build(self, rows):
        return build_otlp_trace(
            _SAMPLE_METRICS,
            trace_id=self.TRACE,
            span_id=self.PARENT,
            start_unix_nano=self.START,
            end_unix_nano=self.END,
            tool_calls=rows,
        )

    def _spans(self, rows):
        return self._build(rows)["resourceSpans"][0]["scopeSpans"][0]["spans"]

    def test_a_tool_call_becomes_a_child_of_the_session(self):
        spans = self._spans([{"id": 1, "tool_name": "Read", "recorded_at": "2026-09-06T10:00:00Z"}])
        assert len(spans) == 2
        child = spans[1]
        assert child["parentSpanId"] == self.PARENT
        assert child["traceId"] == self.TRACE
        assert child["name"] == otel_semconv.GEN_AI_OPERATION_EXECUTE_TOOL
        by_key = {a["key"]: a["value"] for a in child["attributes"]}
        assert by_key[otel_semconv.GEN_AI_TOOL_NAME] == {"stringValue": "Read"}
        assert by_key[otel_semconv.GEN_AI_OPERATION_NAME] == {"stringValue": "execute_tool"}

    def test_child_ids_are_derived_and_distinct(self):
        rows = [
            {"id": 1, "tool_name": "Read", "recorded_at": "t1"},
            {"id": 2, "tool_name": "Read", "recorded_at": "t1"},
        ]
        first, second = self._spans(rows)[1:]
        assert first["spanId"] != second["spanId"], "two rows are two spans"
        assert re.fullmatch(r"[0-9a-f]{16}", first["spanId"])
        assert self._spans(rows) == self._spans(rows), "same rows → same ids"

    def test_the_same_row_under_another_parent_gets_another_id(self):
        """NEGATIVE SCENARIO: ids are salted with the parent, so one row
        exported from two sessions does not collide in a backend."""
        row = {"id": 1, "tool_name": "Read", "recorded_at": "t1"}
        assert child_span_id("b" * 16, row) != child_span_id("c" * 16, row)

    def test_a_row_with_no_tool_name_is_not_a_tool_call(self):
        assert len(self._spans([{"id": 1, "tokens_input": 5}])) == 1, "parent only"

    def test_a_row_outside_the_parents_window_is_skipped(self):
        """A child that starts before its parent or ends after it is invalid
        nesting; a collector would take it, and it would be a lie."""
        rows = [
            {"id": 1, "tool_name": "Read", "start_unix_nano": self.START - 1},
            {"id": 2, "tool_name": "Edit", "end_unix_nano": self.END + 1},
            {
                "id": 3,
                "tool_name": "Bash",
                "start_unix_nano": self.END,
                "end_unix_nano": self.START,
            },
        ]
        assert len(self._spans(rows)) == 1, "parent only — none of the three fits"

    def test_a_row_without_its_own_window_inherits_the_parents(self):
        """ "It happened during the session" is true; a made-up duration is not."""
        child = self._spans([{"id": 1, "tool_name": "Read"}])[1]
        assert child["startTimeUnixNano"] == str(self.START)
        assert child["endTimeUnixNano"] == str(self.END)

    def test_tokens_and_model_travel_when_present_and_are_omitted_when_not(self):
        row = {"id": 1, "tool_name": "Read", "model_id": "claude-opus-5", "tokens_input": 7}
        by_key = {a["key"]: a["value"] for a in self._spans([row])[1]["attributes"]}
        assert by_key[otel_semconv.GEN_AI_REQUEST_MODEL] == {"stringValue": "claude-opus-5"}
        assert by_key[otel_semconv.GEN_AI_USAGE_INPUT_TOKENS] == {"intValue": "7"}
        assert otel_semconv.GEN_AI_USAGE_OUTPUT_TOKENS not in by_key, "absent stays absent"

    def test_an_explicit_zero_is_omitted_not_reported(self):
        """NEGATIVE SCENARIO: a recorded 0 is "we measured nothing", and a
        backend reading `output_tokens: 0` would take it for a measurement.

        Written because a declared mutation SURVIVED: the case above passes a
        row with the key MISSING, and `if raw:` versus `if raw is not None:`
        behave identically there — the branch is only reachable with an
        explicit zero, which is the value our own rows actually carry.
        """
        row = {"id": 1, "tool_name": "Read", "tokens_input": 0, "tokens_output": 0}
        by_key = {a["key"]: a["value"] for a in self._spans([row])[1]["attributes"]}
        assert otel_semconv.GEN_AI_USAGE_INPUT_TOKENS not in by_key
        assert otel_semconv.GEN_AI_USAGE_OUTPUT_TOKENS not in by_key
        assert by_key[otel_semconv.GEN_AI_TOOL_NAME] == {"stringValue": "Read"}, (
            "the span itself is still emitted — only the empty measurement is not"
        )

    def test_no_tool_calls_leaves_the_document_exactly_as_before(self):
        """The extension is additive: an export with nothing to add is the
        document this project already emitted."""
        assert self._build(None) == self._build([]) == self._build([{"id": 1}])

    def test_a_kind_we_cannot_map_gets_no_operation_name_of_our_own(self):
        """`operation_for` answers None rather than inventing a word — the
        defect that put "session" into a standard field in the first place."""
        assert otel_semconv.operation_for("memory") is None
        assert otel_semconv.operation_for("session") in otel_semconv.OPERATIONS
        assert otel_semconv.operation_for("tool") in otel_semconv.OPERATIONS
