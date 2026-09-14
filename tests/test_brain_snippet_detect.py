"""Tests for scripts/brain_snippet_detect.py — heuristic snippet classifier."""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_snippet_detect as bsd  # noqa: E402


# --- Empty / non-dict / no-text inputs (never raises) ----------------------


def test_empty_dict_returns_none():
    assert bsd.detect_artifact_kind({}) is None


def test_non_dict_returns_none():
    assert bsd.detect_artifact_kind(None) is None  # type: ignore[arg-type]
    assert bsd.detect_artifact_kind("not a dict") is None  # type: ignore[arg-type]


def test_blank_text_returns_none():
    assert bsd.detect_artifact_kind({"description": "   \n\t "}) is None


# --- Snippet positives (per cue) -------------------------------------------


def test_fenced_short_code_is_snippet():
    fields = {"example": "```python\ndef add(a, b):\n    return a + b\n```"}
    assert bsd.detect_artifact_kind(fields) == "snippet"


def test_yaml_config_is_snippet():
    fields = {"example": "port: 8080\nhost: localhost\ntimeout: 30"}
    assert bsd.detect_artifact_kind(fields) == "snippet"


def test_json_config_is_snippet():
    fields = {"example": '{"retries": 3, "backoff": "exponential"}'}
    assert bsd.detect_artifact_kind(fields) == "snippet"


def test_cli_with_flag_is_snippet():
    fields = {"example": "docker run -p 8080:8080 myimage\nkubectl get pods -n prod"}
    assert bsd.detect_artifact_kind(fields) == "snippet"


def test_shell_prompt_is_snippet():
    fields = {"example": "$ pip install requests\n$ python app.py"}
    assert bsd.detect_artifact_kind(fields) == "snippet"


# --- False-positive guards -------------------------------------------------


def test_plain_prose_is_none():
    fields = {
        "name": "Cache invalidation",
        "description": "Always invalidate the cache when the underlying record "
        "changes, otherwise stale reads leak across requests.",
    }
    assert bsd.detect_artifact_kind(fields) is None


def test_prose_with_colon_lines_is_not_snippet():
    """'Problem:'/'Solution:' prose lines must not read as YAML cues."""
    fields = {
        "description": "Problem: the cache fails under load.\n"
        "Solution: add a distributed lock around the write path."
    }
    assert bsd.detect_artifact_kind(fields) is None


def test_sentence_starting_with_tool_name_is_not_snippet():
    fields = {"description": "git is great for collaboration and history."}
    assert bsd.detect_artifact_kind(fields) is None


def test_long_fenced_code_is_pattern_not_snippet():
    body = "\n".join(f"    line_{i} = {i}" for i in range(25))
    fields = {"example": f"```python\n{body}\n```"}
    assert bsd.detect_artifact_kind(fields) == "pattern"


def test_single_yaml_line_is_not_cue():
    """Exactly one genuine `key: token` line must not count as a YAML config."""
    fields = {"description": "retries: 3\nThis is plain prose with no YAML structure at all."}
    assert bsd.detect_artifact_kind(fields) is None


def test_two_bare_word_metadata_lines_are_not_snippet():
    """Two `word: word` prose-metadata lines (no config-ish value) must not fire."""
    fields = {"description": "scope: global\nauthor: john"}
    assert bsd.detect_artifact_kind(fields) is None


def test_two_yaml_lines_with_numeric_value_is_snippet():
    """Exactly two lines fire only when at least one value is config-ish (numeric)."""
    fields = {"example": "port: 8080\nhost: localhost"}
    assert bsd.detect_artifact_kind(fields) == "snippet"


# --- maybe_autofill_snippet_kind (the store_record wire) -------------------


def _snippet_fields():
    return {"name": "retry config", "example": "max_retries: 5\nbackoff: exponential\njitter: true"}


def test_autofill_sets_snippet():
    work = _snippet_fields()
    cfg = {"auto_detect_snippet_kind": True}
    assert bsd.maybe_autofill_snippet_kind("patterns", work, cfg) == "snippet"
    assert work["artifact_taxonomy_kind"] == "snippet"


def test_autofill_does_not_overwrite_caller_value():
    work = _snippet_fields()
    work["artifact_taxonomy_kind"] = "artifact"
    out = bsd.maybe_autofill_snippet_kind("patterns", work, {"auto_detect_snippet_kind": True})
    assert out is None
    assert work["artifact_taxonomy_kind"] == "artifact"  # untouched


def test_autofill_disabled_by_knob():
    work = _snippet_fields()
    out = bsd.maybe_autofill_snippet_kind("patterns", work, {"auto_detect_snippet_kind": False})
    assert out is None
    assert "artifact_taxonomy_kind" not in work


def test_autofill_skips_non_taxonomy_category():
    work = _snippet_fields()
    out = bsd.maybe_autofill_snippet_kind("decisions", work, {"auto_detect_snippet_kind": True})
    assert out is None
    assert "artifact_taxonomy_kind" not in work


def test_autofill_skips_plain_prose():
    work = {"name": "x", "description": "Plain prose with no code at all here."}
    out = bsd.maybe_autofill_snippet_kind("patterns", work, {"auto_detect_snippet_kind": True})
    assert out is None
    assert "artifact_taxonomy_kind" not in work


def test_autofill_defaults_knob_on_when_absent():
    work = _snippet_fields()
    assert bsd.maybe_autofill_snippet_kind("patterns", work, {}) == "snippet"


# --- draft_artifact_publish integration ------------------------------------
