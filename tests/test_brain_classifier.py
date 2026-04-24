"""Tests for scripts/brain_classifier.py."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_classifier as bc  # noqa: E402
import brain_project_registry as bpr  # noqa: E402


# --- API shape -------------------------------------------------------------


def test_classify_returns_decision_for_each_valid_category():
    for cat in ("decision", "pattern", "gotcha", "web_cache"):
        d = bc.classify("plain generic text about testing", cat)
        assert isinstance(d, bc.Decision)
        assert d.target in ("local", "brain")
        assert isinstance(d.reason, str) and d.reason
        assert isinstance(d.markers, list)
        assert d.blocklist_hit is None or isinstance(d.blocklist_hit, str)


def test_classify_rejects_unknown_category():
    with pytest.raises(ValueError):
        bc.classify("some text", "random")


def test_classify_rejects_non_string_content():
    for bad in (None, 42, 3.14, b"bytes", ["a", "b"], {"k": "v"}):
        with pytest.raises(TypeError):
            bc.classify(bad, "decision")  # type: ignore[arg-type]


# --- Empty / whitespace ----------------------------------------------------


def test_empty_content_routed_local():
    d = bc.classify("", "decision")
    assert d.target == "local"
    assert d.reason == "empty content"
    assert d.markers == []
    assert d.blocklist_hit is None


def test_whitespace_only_content_routed_local():
    d = bc.classify("   \n\t  ", "pattern")
    assert d.target == "local"
    assert d.reason == "empty content"


# --- Markers detection (AC2) -----------------------------------------------


def test_abs_path_marker_routes_local():
    content = "Bug found in D:\\Work\\Personal\\claude\\scripts\\foo.py"
    d = bc.classify(content, "pattern")
    assert d.target == "local"
    assert "abs_path" in d.reason or "src_file" in d.reason
    assert d.markers
    assert d.blocklist_hit is None


def test_src_file_marker_routes_local():
    d = bc.classify("See scripts/brain_classifier.py for details", "decision")
    assert d.target == "local"
    assert "src_file" in d.reason
    assert any(m.kind == "src_file" for m in d.markers)


def test_tausik_cmd_marker_routes_local():
    d = bc.classify("Use tausik_task_start to activate", "gotcha")
    assert d.target == "local"
    assert "tausik_cmd" in d.reason
    assert any(m.kind == "tausik_cmd" for m in d.markers)


def test_slug_marker_routes_local_for_non_web_cache():
    d = bc.classify("Task brain-mcp-path-fix was closed", "decision")
    assert d.target == "local"
    assert "slug" in d.reason
    assert any(m.kind == "slug" for m in d.markers)


def test_marker_reason_includes_exact_match():
    d = bc.classify("See scripts/brain_classifier.py here", "decision")
    assert "scripts/brain_classifier.py" in d.reason


# --- Web cache category bias (AC5) ----------------------------------------


def test_web_cache_suppresses_slug_markers():
    """AC5: slug-like forms in URL query strings should not fight web_cache."""
    d = bc.classify(
        "Fetched https://api.stripe.com/v1/payment-intents-list", "web_cache"
    )
    assert d.target == "brain"
    assert d.reason == "no project-specific markers detected"


def test_web_cache_still_blocks_on_abs_path():
    """Bias only suppresses slug — other markers still force local."""
    d = bc.classify(
        "Response cached at /home/dev/repo/cache.json from https://api.x.com",
        "web_cache",
    )
    assert d.target == "local"
    assert any(m.kind == "abs_path" for m in d.markers)


def test_web_cache_still_blocks_on_src_file():
    d = bc.classify("See scripts/fetcher.py for the WebFetch call", "web_cache")
    assert d.target == "local"
    assert any(m.kind == "src_file" for m in d.markers)


def test_web_cache_still_blocks_on_tausik_cmd():
    d = bc.classify("Run .tausik/tausik to refresh cache", "web_cache")
    assert d.target == "local"
    assert any(m.kind == "tausik_cmd" for m in d.markers)


def test_decision_category_keeps_slug_signal():
    """Strict categories must NOT suppress slugs — opposite of web_cache."""
    d = bc.classify("See task my-weird-project-slug for reasoning", "decision")
    assert d.target == "local"
    assert any(m.kind == "slug" for m in d.markers)


# --- Blocklist (AC3) -------------------------------------------------------


def test_blocklist_from_cfg_routes_local():
    d = bc.classify(
        "Pattern: always mock the Kareta API in tests",
        "pattern",
        cfg={"project_names": ["Kareta"]},
    )
    assert d.target == "local"
    assert d.blocklist_hit == "Kareta"
    assert "blocklist" in d.reason


def test_blocklist_is_case_insensitive():
    d = bc.classify(
        "pattern mentioning kareta in lowercase",
        "pattern",
        cfg={"project_names": ["Kareta"]},
    )
    assert d.target == "local"
    assert d.blocklist_hit == "Kareta"


def test_blocklist_no_hit_routes_brain():
    d = bc.classify(
        "A pure generic tip about retry logic in HTTP clients",
        "pattern",
        cfg={"project_names": ["Princess", "Kareta"]},
    )
    assert d.target == "brain"
    assert d.reason == "no project-specific markers detected"


def test_blocklist_union_with_registry(tmp_path, monkeypatch):
    """AC3: registry names must be merged with cfg['project_names']."""
    reg = tmp_path / "projects.json"
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(reg))
    bpr.register_project("princess", "/projects/princess")
    d = bc.classify(
        "Yet another thought about princess deployments",
        "pattern",
        cfg=None,
    )
    assert d.target == "local"
    assert d.blocklist_hit == "princess"


def test_blocklist_ignores_non_string_names():
    d = bc.classify(
        "pattern about retries",
        "pattern",
        cfg={"project_names": [None, 42, "", "   ", "kareta"]},
    )
    # kareta not in content → brain. No crash on bad inputs.
    assert d.target == "brain"


# --- Brain default path (AC4) ----------------------------------------------


def test_clean_content_routes_brain():
    d = bc.classify(
        "HTTP/2 is negotiated via ALPN during TLS handshake",
        "pattern",
    )
    assert d.target == "brain"
    assert d.reason == "no project-specific markers detected"
    assert d.markers == []
    assert d.blocklist_hit is None


def test_clean_content_all_categories_route_brain():
    generic = "Use exponential backoff for rate-limited APIs"
    for cat in ("decision", "pattern", "gotcha", "web_cache"):
        d = bc.classify(generic, cat)
        assert d.target == "brain", f"category {cat} unexpectedly routed local"


# --- Precedence ------------------------------------------------------------


def test_markers_beat_blocklist_in_reason_order():
    """When both markers and blocklist would match, markers come first."""
    d = bc.classify(
        "scripts/foo.py references kareta",
        "pattern",
        cfg={"project_names": ["Kareta"]},
    )
    assert d.target == "local"
    # Marker path wins: reason mentions src_file, blocklist_hit is None.
    assert "src_file" in d.reason
    assert d.blocklist_hit is None
