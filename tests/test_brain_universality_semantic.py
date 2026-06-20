"""Tests for scripts/brain_universality_semantic.py — FTS5 nearest-neighbor.

Covers token extraction, find_similar_universal aggregation, and
emit_semantic_universality_hint config gating + dedup against regex layer.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_universality as bu  # noqa: E402
import brain_universality_semantic as bus  # noqa: E402
from brain_schema import apply_schema  # noqa: E402


# ---- _extract_tokens -----------------------------------------------------


class TestExtractTokens:
    def test_empty_string_returns_empty(self):
        assert bus._extract_tokens("") == []

    def test_whitespace_only_returns_empty(self):
        assert bus._extract_tokens("   \n\t  ") == []

    def test_non_string_returns_empty(self):
        assert bus._extract_tokens(None) == []  # type: ignore[arg-type]
        assert bus._extract_tokens(123) == []  # type: ignore[arg-type]

    def test_lowercases_tokens(self):
        out = bus._extract_tokens("Webhook RBAC OAuth")
        assert "webhook" in out
        assert "rbac" in out
        assert "oauth" in out

    def test_drops_short_tokens(self):
        # 'is', 'in', 'a' shorter than _MIN_TOKEN_LEN.
        out = bus._extract_tokens("a in is going")
        assert "a" not in out
        assert "in" not in out
        assert "is" not in out
        assert "going" in out

    def test_drops_stopwords(self):
        out = bus._extract_tokens("the and where there which")
        assert out == []

    def test_dedupes_first_seen_order(self):
        out = bus._extract_tokens("retry policy retry policy retry")
        assert out == ["retry", "policy"]

    def test_caps_at_limit(self):
        text = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
        out = bus._extract_tokens(text, limit=3)
        assert len(out) == 3
        assert out == ["alpha", "beta", "gamma"]

    def test_skips_pure_numbers(self):
        out = bus._extract_tokens("1234 5678 alpha")
        assert out == ["alpha"]

    def test_handles_hyphenated_tokens(self):
        out = bus._extract_tokens("rate-limit feature-flag")
        # Hyphens are part of the token regex.
        assert "rate-limit" in out or "feature-flag" in out


# ---- find_similar_universal ---------------------------------------------


@pytest.fixture
def mirror_conn(tmp_path):
    """Brain mirror with FTS5 schema, one decision + one pattern row pre-loaded."""
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    # Decision tagged 'rbac' — describes access control.
    c.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-rbac-1",
            "Use access control for editor scope",
            "Editors should only access their own posts and drafts",
            "Adopt role-based permissions across the API surface",
            "Reduces blast radius on credential leak",
            json.dumps(["rbac", "auth"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    # Pattern tagged 'rate-limit' — describes throttling.
    c.execute(
        """INSERT INTO brain_patterns(
            notion_page_id, name, description, when_to_use, example,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-throttle-1",
            "Token bucket throttling for incoming traffic",
            "Token bucket throttling smooths bursty client traffic",
            "When upstream APIs reject excessive request volumes",
            "bucket = TokenBucket(rate=100)",
            json.dumps(["rate-limit"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    c.commit()
    yield c
    c.close()


def test_find_similar_empty_content_returns_empty(mirror_conn):
    assert bus.find_similar_universal("", mirror_conn) == []


def test_find_similar_non_string_returns_empty(mirror_conn):
    assert bus.find_similar_universal(None, mirror_conn) == []  # type: ignore[arg-type]


def test_find_similar_no_match_returns_empty(mirror_conn):
    """Content with no token overlap → no FTS5 hits → empty."""
    assert bus.find_similar_universal("zzzzz qqqqq xxxxx", mirror_conn) == []


def test_find_similar_synonym_for_rbac_topic(mirror_conn):
    """'access control' (regex misses) should match brain_decisions row tagged 'rbac'."""
    results = bus.find_similar_universal(
        "We need access control over editor permissions",
        mirror_conn,
    )
    topics = [t for t, _ in results]
    assert "rbac" in topics


def test_find_similar_synonym_for_rate_limit_topic(mirror_conn):
    """'token bucket throttling' (regex catches throttling, this row is also 'rate-limit')."""
    results = bus.find_similar_universal(
        "Apply token bucket throttling on the gateway",
        mirror_conn,
    )
    topics = [t for t, _ in results]
    assert "rate-limit" in topics


def test_find_similar_tight_threshold_filters_weak_matches(mirror_conn):
    """bm25 lower = better; threshold caps the upper bound. Very negative
    threshold rejects all real-world matches."""
    results = bus.find_similar_universal(
        "We need access control over editor permissions",
        mirror_conn,
        threshold=-1000.0,
    )
    assert results == []


def test_find_similar_returns_sorted_ascending_by_score(mirror_conn):
    results = bus.find_similar_universal(
        "access control with throttling and bucket scope",
        mirror_conn,
    )
    if len(results) > 1:
        scores = [s for _, s in results]
        assert scores == sorted(scores)


def test_find_similar_empty_mirror_returns_empty(tmp_path):
    """Empty FTS5 mirror — graceful no-op."""
    path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    apply_schema(conn)
    try:
        results = bus.find_similar_universal("access control", conn)
    finally:
        conn.close()
    assert results == []


def test_find_similar_handles_search_local_exception(mirror_conn, monkeypatch):
    """search_local raising → no crash, returns []."""

    def boom(*_a, **_kw):
        raise RuntimeError("search broken")

    monkeypatch.setattr("brain_search.search_local", boom)
    assert bus.find_similar_universal("access control", mirror_conn) == []


def test_find_similar_ignores_tags_outside_known_universe(tmp_path):
    """Row tagged with non-universal label must not pollute results."""
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    c.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-x",
            "access control project notes",
            "Editors should only access their own posts",
            "Use a custom flag in db schema",
            "Lower risk",
            json.dumps(["custom-tag", "internal"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    c.commit()
    try:
        results = bus.find_similar_universal("access control over editors", c)
    finally:
        c.close()
    assert results == []


# ---- format_semantic_hint ------------------------------------------------


def test_format_semantic_hint_empty_returns_empty():
    assert bus.format_semantic_hint([]) == ""


def test_format_semantic_hint_includes_topics():
    hint = bus.format_semantic_hint(["rbac", "rate-limit"])
    assert "rbac" in hint
    assert "rate-limit" in hint
    assert "Semantic universality hint" in hint
    assert "brain_draft_artifact" in hint


def test_format_semantic_hint_is_single_line():
    hint = bus.format_semantic_hint(["rbac", "rate-limit", "webhook"])
    assert "\n" not in hint


# ---- emit_semantic_universality_hint -------------------------------------


def test_emit_silent_when_brain_disabled(capsys, mirror_conn, monkeypatch):
    """brain.enabled is False → no output."""
    monkeypatch.setattr("brain_config.load_brain", lambda: {"enabled": False})
    bus.emit_semantic_universality_hint("access control across services")
    err = capsys.readouterr().err
    assert "Semantic" not in err


def test_emit_silent_when_semantic_disabled(capsys, mirror_conn, monkeypatch, tmp_path):
    """brain.semantic_universality_enabled is False → no output."""
    db = tmp_path / "brain.db"
    # mirror_conn's path is in tmp_path / "brain.db" too — close+reuse.
    cfg = {
        "enabled": True,
        "semantic_universality_enabled": False,
        "local_mirror_path": str(db),
    }
    bus.emit_semantic_universality_hint("access control across services", cfg=cfg)
    err = capsys.readouterr().err
    assert "Semantic" not in err


def test_emit_silent_when_mirror_missing(capsys, tmp_path):
    """Mirror path doesn't exist on disk → no output."""
    cfg = {
        "enabled": True,
        "local_mirror_path": str(tmp_path / "missing.db"),
    }
    bus.emit_semantic_universality_hint("access control", cfg=cfg)
    err = capsys.readouterr().err
    assert "Semantic" not in err


def test_emit_silent_when_text_empty(capsys):
    bus.emit_semantic_universality_hint("", cfg={"enabled": True})
    bus.emit_semantic_universality_hint("   ", cfg={"enabled": True})
    err = capsys.readouterr().err
    assert err == ""


def test_emit_dedupes_against_regex_layer(capsys, tmp_path):
    """Topic already caught by regex is not re-emitted by semantic."""
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    # Brain row tagged 'rbac' that mentions both access and rbac literally —
    # so search_local matches AND regex layer catches 'rbac' too.
    c.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-1",
            "rbac and access control rules",
            "rbac scopes editor reads",
            "Adopt role-based permissions",
            "Lower blast radius",
            json.dumps(["rbac"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    c.commit()
    c.close()
    cfg = {
        "enabled": True,
        "semantic_universality_enabled": True,
        "local_mirror_path": str(path),
    }
    # 'rbac' literal triggers regex layer — semantic must NOT re-emit it.
    bus.emit_semantic_universality_hint("Use rbac for editor access", cfg=cfg)
    err = capsys.readouterr().err
    assert "Semantic universality hint" not in err


def test_emit_writes_hint_when_new_topic_found(capsys, tmp_path):
    """Semantic catches a topic regex misses → stderr emission."""
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    c.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-1",
            "Editors should only access their own posts",
            "Editors should only access their own posts and drafts",
            "Adopt role-based permissions across the API surface",
            "Reduces blast radius on credential leak",
            json.dumps(["rbac"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    c.commit()
    c.close()
    cfg = {
        "enabled": True,
        "semantic_universality_enabled": True,
        "local_mirror_path": str(path),
    }
    # No 'rbac' literal in input — regex misses, semantic must catch.
    bus.emit_semantic_universality_hint(
        "Editors should only access their own drafts and posts", cfg=cfg
    )
    err = capsys.readouterr().err
    assert "Semantic universality hint" in err
    assert "rbac" in err


def test_emit_never_raises_on_pathological_input(capsys):
    weird = "\x00" * 1000 + "​" * 500
    bus.emit_semantic_universality_hint(weird, cfg={"enabled": True})
    # No crash; output may be silent.
    capsys.readouterr()


# ---- emit_universality_hint integration (regex + semantic combined) ------


def test_emit_universality_hint_triggers_both_layers_when_brain_enabled(
    capsys, tmp_path, monkeypatch
):
    """emit_universality_hint() (the public API) must invoke semantic layer."""
    path = tmp_path / "brain.db"
    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    apply_schema(c)
    c.execute(
        """INSERT INTO brain_decisions(
            notion_page_id, name, context, decision, rationale,
            tags, stack, source_project_hash, last_edited_time, created_time
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            "page-1",
            "Editors should only access their own posts",
            "Editors should only access their own posts",
            "Use role-based permissions",
            "Lower blast radius",
            json.dumps(["rbac"]),
            json.dumps(["python"]),
            "ph",
            "2026-04-01T00:00:00Z",
            "2026-04-01T00:00:00Z",
        ),
    )
    c.commit()
    c.close()
    cfg = {
        "enabled": True,
        "semantic_universality_enabled": True,
        "local_mirror_path": str(path),
    }
    # Patch load_brain so the semantic layer reads our cfg without hitting
    # the user's real brain config.
    monkeypatch.setattr("brain_config.load_brain", lambda *_a, **_kw: cfg)
    monkeypatch.setattr("brain_config.get_brain_mirror_path", lambda *_a, **_kw: str(path))
    # Input has no regex topic but semantic should catch 'rbac'.
    bu.emit_universality_hint("Editors should only access their own posts")
    err = capsys.readouterr().err
    assert "Semantic universality hint" in err
    assert "rbac" in err


def test_emit_universality_hint_no_semantic_when_brain_disabled(capsys, monkeypatch):
    """No brain config → semantic is silent; regex layer still works."""
    monkeypatch.setattr("brain_config.load_brain", lambda *_a, **_kw: {"enabled": False})
    bu.emit_universality_hint("Use JWT for stateless auth")
    err = capsys.readouterr().err
    # Regex hint still emits.
    assert "Universal pattern(s) detected" in err
    assert "jwt" in err
    # Semantic does not.
    assert "Semantic universality hint" not in err
