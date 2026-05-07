"""Tests for scripts/brain_universality.py — universal pattern detector."""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_universality as bu  # noqa: E402


# --- Empty / non-string inputs --------------------------------------------


def test_empty_string_returns_empty_list():
    assert bu.detect_universal_patterns("") == []


def test_whitespace_only_returns_empty_list():
    assert bu.detect_universal_patterns("   \n\t  ") == []


def test_non_string_returns_empty_list():
    assert bu.detect_universal_patterns(None) == []  # type: ignore[arg-type]
    assert bu.detect_universal_patterns(123) == []  # type: ignore[arg-type]
    assert bu.detect_universal_patterns(["jwt"]) == []  # type: ignore[arg-type]


# --- Per-topic positive cases (8+ topics covered) ------------------------


@pytest.mark.parametrize(
    "text,expected_topic",
    [
        ("Use RBAC to scope reads", "rbac"),
        ("Role-based access control for editors", "rbac"),
        ("Validate JWT in middleware", "jwt"),
        ("JSON Web Tokens expire after 1h", "jwt"),
        ("Switch to OAuth2 for SSO", "oauth"),
        ("Stick with OAuth flow only", "oauth"),
        ("Use exponential backoff for rate-limited APIs", "rate-limit"),
        ("Add a throttler at the edge", "rate-limit"),
        ("Cursor pagination beats offset", "pagination"),
        ("Paginate the result set", "pagination"),
        ("Always retry idempotent calls", "retry"),
        ("Use exponential backoff", "retry"),
        ("Make the endpoint idempotent", "idempotency"),
        ("Send an Idempotency-Key header", "idempotency"),
        ("Receive a webhook callback", "webhook"),
        ("Webhooks must be signed", "webhook"),
        ("Add a CSRF token to forms", "csrf"),
        ("XSRF protection via double-submit cookie", "csrf"),
        ("Cross-Site Request Forgery mitigation", "csrf"),
        ("Migrate the API to GraphQL", "graphql"),
        ("Write a gql query for the dashboard", "graphql"),
        ("Wrap calls in a feature flag", "feature-flag"),
        ("Feature-toggles for canary release", "feature-flag"),
        ("Open the circuit breaker on 5xx", "circuit-breaker"),
        ("Apply the bulkhead pattern", "circuit-breaker"),
    ],
)
def test_each_topic_detected(text: str, expected_topic: str):
    topics = bu.detect_universal_patterns(text)
    assert expected_topic in topics, f"{expected_topic!r} missing from {topics!r}"


# --- Negative / project-specific text ------------------------------------


def test_project_specific_text_no_match():
    text = "Refactor scripts/service_knowledge.py to extract helpers"
    assert bu.detect_universal_patterns(text) == []


def test_pure_natural_language_no_match():
    text = "This is just a regular sentence about lunch and weather."
    assert bu.detect_universal_patterns(text) == []


# --- False-positive guards (word boundary) -------------------------------


def test_rate_inside_aggregate_does_not_match_rate_limit():
    """Critical guard: 'aggregate' contains 'rate' — must NOT trigger rate-limit."""
    assert "rate-limit" not in bu.detect_universal_patterns("Aggregate the data")
    assert "rate-limit" not in bu.detect_universal_patterns("separately iterate")


def test_jwt_substring_in_other_word_does_not_match():
    """'ajwtb' is not a JWT mention."""
    assert "jwt" not in bu.detect_universal_patterns("xjwtx pseudo-token mojwt")


def test_oauth_substring_in_other_word_does_not_match():
    assert "oauth" not in bu.detect_universal_patterns("oauthorization-like word")


def test_retry_substring_does_not_match():
    """'pretrying' / 'retrying' — only 'retrying' should match."""
    assert bu.detect_universal_patterns("retrying the request") == ["retry"]
    # 'untrying' does not contain 'retry' as a word
    assert "retry" not in bu.detect_universal_patterns("the untrying spirit")


# --- New topic false-positive guards (csrf, graphql, feature-flag, circuit-breaker) -----


def test_csrf_substring_in_other_word_does_not_match():
    assert "csrf" not in bu.detect_universal_patterns("xcsrfx not a token")


def test_graphql_does_not_match_inside_unrelated_word():
    """'photographqlike' style — only standalone 'graphql' should match."""
    assert "graphql" not in bu.detect_universal_patterns("photographqlike artifact")


def test_gql_alone_without_query_keyword_does_not_match():
    """Bare 'gql' without query/mutation/etc. context — not enough signal."""
    assert "graphql" not in bu.detect_universal_patterns("the gql library version")


def test_feature_without_flag_does_not_match():
    """'feature' alone is too generic — must be 'feature flag/toggle'."""
    assert "feature-flag" not in bu.detect_universal_patterns("Add a new feature")


def test_circuit_without_breaker_does_not_match():
    """'circuit' alone (e.g. electrical) — must be 'circuit breaker'."""
    assert "circuit-breaker" not in bu.detect_universal_patterns("electrical circuit diagram")


def test_new_topics_count_in_universe():
    """Sanity: known topic universe contains the 4 new entries."""
    universe = bu.KNOWN_UNIVERSAL_TOPICS
    for topic in ("csrf", "graphql", "feature-flag", "circuit-breaker"):
        assert topic in universe


# --- Multi-topic + dedupe + sort ------------------------------------------


def test_multi_topic_sorted_and_unique():
    text = "JWT auth with rate-limit and retry on webhook delivery"
    topics = bu.detect_universal_patterns(text)
    assert topics == sorted(topics)
    assert len(topics) == len(set(topics))
    assert set(topics) == {"jwt", "rate-limit", "retry", "webhook"}


def test_repeated_mentions_dedupe():
    text = "JWT JWT JWT and more JWT"
    assert bu.detect_universal_patterns(text) == ["jwt"]


def test_case_insensitive():
    assert bu.detect_universal_patterns("RBAC") == ["rbac"]
    assert bu.detect_universal_patterns("rbac") == ["rbac"]
    assert bu.detect_universal_patterns("RbAc") == ["rbac"]


# --- format_universality_hint ---------------------------------------------


def test_format_empty_returns_empty_string():
    assert bu.format_universality_hint([]) == ""


def test_format_single_topic():
    hint = bu.format_universality_hint(["jwt"])
    assert "jwt" in hint
    assert "brain_draft_artifact" in hint
    assert "cross-project" in hint


def test_format_multi_topic_joins_comma():
    hint = bu.format_universality_hint(["jwt", "rate-limit"])
    assert "jwt, rate-limit" in hint


def test_format_is_single_line():
    hint = bu.format_universality_hint(["rbac", "jwt", "webhook"])
    assert "\n" not in hint


# --- AC #11: never blocks --------------------------------------------------


def test_detect_never_raises_on_pathological_input():
    # Massive string, weird unicode, control chars — must not crash.
    weird = "\x00" * 1000 + "JWT" + "​" * 500
    topics = bu.detect_universal_patterns(weird)
    assert "jwt" in topics
