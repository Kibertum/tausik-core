"""Semantic universality detector — FTS5 nearest-neighbor over brain mirror.

Catches synonyms the regex layer misses (e.g. "access control" → rbac,
"token bucket" → rate-limit) by querying the local brain mirror for
existing entries whose tags overlap a known universal topic. The
existing brain entries serve as the ground truth — once a user promotes
something to a brain artifact tagged 'rbac', new content describing the
same concept in different words will trigger the suggestion.

Pure stdlib. Reuses scripts/brain_search.py FTS5 infrastructure. Never
raises. No-op when brain disabled, mirror missing, or content empty.

Activation:
    cfg["enabled"] is True  AND
    cfg.get("semantic_universality_enabled", True) is True  AND
    mirror file exists on disk

Public API:
    find_similar_universal(content, conn, *, threshold, limit)
        -> list[tuple[topic, best_bm25_score]]
    emit_semantic_universality_hint(text, *, cfg) -> None
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
from typing import Any, Final

# bm25 score: lower = more relevant. Empirically chosen — strong matches
# against a populated brain mirror typically score 1-6; weak matches 9+.
DEFAULT_BM25_THRESHOLD: Final[float] = 8.0
# Cap on FTS searches per content blob (one search per token).
DEFAULT_TOKEN_LIMIT: Final[int] = 8
# Rows returned per token query.
DEFAULT_PER_TOKEN_LIMIT: Final[int] = 5
# Minimum token length to be considered distinctive.
_MIN_TOKEN_LEN: Final[int] = 4
# Cap on content prefix scanned for tokens — large blobs would over-search.
_MAX_CONTENT_CHARS: Final[int] = 4000

# Generic English stopwords — too common to be discriminative against brain
# entries. Kept short on purpose; over-filtering hurts recall.
_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "have",
        "into",
        "your",
        "their",
        "will",
        "would",
        "could",
        "should",
        "about",
        "than",
        "then",
        "there",
        "where",
        "which",
        "what",
        "when",
        "while",
        "very",
        "also",
        "only",
        "more",
        "most",
        "some",
        "such",
        "each",
        "other",
        "these",
        "those",
        "after",
        "before",
        "during",
        "between",
        "across",
        "needs",
        "need",
        "used",
        "using",
        "make",
        "made",
        "must",
        "case",
        "data",
        "thing",
        "things",
        "code",
        "file",
        "files",
        "user",
        "users",
    }
)

# Token = ASCII alpha-start, then alnum/underscore/hyphen. Excludes pure
# numbers and punctuation. Cyrillic etc. are skipped — brain entries are
# expected in English per docs/en/memory-merge-guidelines.md.
_WORD_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")


def _extract_tokens(content: str, *, limit: int = DEFAULT_TOKEN_LIMIT) -> list[str]:
    """Return up to ``limit`` distinctive lowercased tokens, in first-seen order.

    Tokens shorter than ``_MIN_TOKEN_LEN`` and stopwords are dropped. Empty
    / non-string input returns ``[]``. Never raises.
    """
    if not isinstance(content, str):
        return []
    text = content[:_MAX_CONTENT_CHARS].lower()
    seen: set[str] = set()
    out: list[str] = []
    for match in _WORD_RE.finditer(text):
        tok = match.group(0)
        if len(tok) < _MIN_TOKEN_LEN:
            continue
        if tok in _STOPWORDS:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
        if len(out) >= limit:
            break
    return out


def find_similar_universal(
    content: str,
    conn: sqlite3.Connection,
    *,
    threshold: float = DEFAULT_BM25_THRESHOLD,
    limit: int = DEFAULT_PER_TOKEN_LIMIT,
) -> list[tuple[str, float]]:
    """Return ``[(topic, best_bm25), ...]`` sorted ascending by score.

    For each distinctive token in ``content``, run a local FTS5 search via
    :func:`brain_search.search_local`. For every hit whose tags include
    a KNOWN_UNIVERSAL_TOPICS entry AND whose bm25 score is ≤ ``threshold``,
    record the topic. Return the best (lowest) score per topic.

    Empty content / closed conn / missing FTS tables / search_local raise
    → ``[]``. Never raises.
    """
    tokens = _extract_tokens(content)
    if not tokens:
        return []
    try:
        from brain_search import search_local
        from brain_universality import KNOWN_UNIVERSAL_TOPICS
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return []

    # Dedupe rows across token searches by (category, notion_page_id) — same
    # row may match multiple tokens; keep the best (lowest) bm25.
    best_per_row: dict[tuple[str, str], dict[str, Any]] = {}
    for token in tokens:
        try:
            rows = search_local(conn, token, limit=limit)
        except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
            continue
        for row in rows:
            key = (
                str(row.get("category", "")),
                str(row.get("notion_page_id", "")),
            )
            score = float(row.get("score") or 0.0)
            existing = best_per_row.get(key)
            if existing is None or score < float(existing.get("score") or 0.0):
                best_per_row[key] = row

    best_per_topic: dict[str, float] = {}
    for row in best_per_row.values():
        score = float(row.get("score") or 0.0)
        if score > threshold:
            continue
        tags = row.get("tags") or []
        if not isinstance(tags, list):
            continue
        for tag in tags:
            t = str(tag).strip().lower()
            if t in KNOWN_UNIVERSAL_TOPICS:
                prev = best_per_topic.get(t)
                if prev is None or score < prev:
                    best_per_topic[t] = score

    return sorted(best_per_topic.items(), key=lambda x: x[1])


def format_semantic_hint(topics: list[str]) -> str:
    """Format topics for stderr emission. Returns ``""`` when empty."""
    if not topics:
        return ""
    joined = ", ".join(topics)
    return (
        f"Semantic universality hint: {joined} — "
        f"new content resembles existing brain entries on these topics "
        f"(consider promoting via `brain_draft_artifact`)."
    )


def _resolve_brain_cfg(cfg: dict | None) -> dict | None:
    """Return merged brain dict (with semantic gate honored) or None."""
    try:
        from brain_config import load_brain
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return None
    try:
        merged = cfg if cfg is not None else load_brain()
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return None
    if not isinstance(merged, dict):
        return None
    if not merged.get("enabled"):
        return None
    if not merged.get("semantic_universality_enabled", True):
        return None
    return merged


def emit_semantic_universality_hint(text: str, *, cfg: dict | None = None) -> None:
    """Emit semantic-layer hint to stderr; silent when disabled / unavailable.

    Gates: ``brain.enabled`` AND ``brain.semantic_universality_enabled``
    (default True), AND mirror file must exist. Topics already caught by
    the regex layer are deduped so users see only NEW signal.

    Never raises, never blocks.
    """
    if not isinstance(text, str) or not text.strip():
        return
    merged = _resolve_brain_cfg(cfg)
    if merged is None:
        return
    try:
        from brain_config import get_brain_mirror_path
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return
    try:
        path = get_brain_mirror_path(merged)
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return
    if not path or not os.path.isfile(path):
        return
    try:
        conn = sqlite3.connect(path)
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return
    results: list[tuple[str, float]] = []
    try:
        conn.row_factory = sqlite3.Row
        results = find_similar_universal(text, conn)
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        results = []
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
            pass
    if not results:
        return
    try:
        from brain_universality import detect_universal_patterns

        already = set(detect_universal_patterns(text))
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        already = set()
    new_topics = [t for t, _ in results if t not in already]
    if not new_topics:
        return
    hint = format_semantic_hint(new_topics)
    if not hint:
        return
    try:
        print(hint, file=sys.stderr)
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        pass
