"""Universality heuristic for brain artifact suggestions.

Detects well-known cross-project patterns (RBAC, JWT, OAuth, rate-limit,
pagination, retry/backoff, idempotency, webhook, CSRF, GraphQL,
feature-flag, circuit-breaker) in memory/decision text. Hits suggest
promoting the entry to a shared brain artifact via ``brain_draft_artifact``.

Pure stdlib, zero deps. Never raises. Word-boundary aware to avoid the
classic 'rate' inside 'aggregate' false positive.

Public API:
    detect_universal_patterns(content: str) -> list[str]
    format_universality_hint(topics: list[str]) -> str
    emit_universality_hint(text: str) -> None
"""

from __future__ import annotations

import re
from typing import Final

# Each topic maps to a list of compiled regexes; ANY match flags the topic.
# Patterns use \b word boundaries (case-insensitive) so 'rate' inside
# 'aggregate' / 'separate' / 'rate' inside 'iteration' will not match.
_TOPIC_PATTERNS: Final[dict[str, list[re.Pattern[str]]]] = {
    "rbac": [
        re.compile(r"\brbac\b", re.IGNORECASE),
        re.compile(r"\brole[\s\-]based\s+access\b", re.IGNORECASE),
    ],
    "jwt": [
        re.compile(r"\bjwt\b", re.IGNORECASE),
        re.compile(r"\bjson\s+web\s+tokens?\b", re.IGNORECASE),
    ],
    "oauth": [
        re.compile(r"\boauth(?:1|2)?\b", re.IGNORECASE),
    ],
    "rate-limit": [
        re.compile(r"\brate[\s\-]?limit(?:s|ed|ing|er)?\b", re.IGNORECASE),
        re.compile(r"\bthrottl(?:e|ed|ing|er)\b", re.IGNORECASE),
    ],
    "pagination": [
        re.compile(r"\bpaginat(?:ion|e|ed|ing|or)\b", re.IGNORECASE),
        re.compile(r"\bcursor[\s\-]based\s+pag(?:ination|ing)\b", re.IGNORECASE),
    ],
    "retry": [
        re.compile(r"\bretr(?:y|ies|ied|ying)\b", re.IGNORECASE),
        re.compile(r"\b(?:exponential\s+)?backoff\b", re.IGNORECASE),
    ],
    "idempotency": [
        re.compile(r"\bidempoten(?:t|cy|ce|tly)\b", re.IGNORECASE),
        re.compile(r"\bidempotency[\s\-]key\b", re.IGNORECASE),
    ],
    "webhook": [
        re.compile(r"\bwebhooks?\b", re.IGNORECASE),
    ],
    "csrf": [
        re.compile(r"\bcsrf\b", re.IGNORECASE),
        re.compile(r"\bxsrf\b", re.IGNORECASE),
        re.compile(r"\bcross[\s\-]site\s+request\s+forgery\b", re.IGNORECASE),
    ],
    "graphql": [
        re.compile(r"\bgraphql\b", re.IGNORECASE),
        re.compile(r"\bgql\s+(?:query|mutation|subscription|schema|resolver)\b", re.IGNORECASE),
    ],
    "feature-flag": [
        re.compile(r"\bfeature[\s\-]flag(?:s|ged|ging)?\b", re.IGNORECASE),
        re.compile(r"\bfeature[\s\-]toggle(?:s|d|ing)?\b", re.IGNORECASE),
    ],
    "circuit-breaker": [
        re.compile(r"\bcircuit[\s\-]breaker(?:s)?\b", re.IGNORECASE),
        re.compile(r"\bbulkhead\s+pattern\b", re.IGNORECASE),
    ],
}

# Public — the catalogue is what the tests and the hint share.
KNOWN_UNIVERSAL_TOPICS: Final[frozenset[str]] = frozenset(_TOPIC_PATTERNS.keys())


def detect_universal_patterns(content: str) -> list[str]:
    """Return sorted unique topic slugs found in ``content``.

    Empty / whitespace-only input returns ``[]``. Order is alphabetical
    (sorted) for deterministic output. Non-string input is treated as
    empty — never raises.
    """
    if not isinstance(content, str):
        return []
    text = content.strip()
    if not text:
        return []
    found: set[str] = set()
    for topic, patterns in _TOPIC_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                found.add(topic)
                break
    return sorted(found)


def format_universality_hint(topics: list[str]) -> str:
    """Format detected topics as a single-line hint for stderr emission.

    Returns ``""`` for empty input so callers can guard with truthiness.
    The hint is advisory — never blocking.
    """
    if not topics:
        return ""
    joined = ", ".join(topics)
    return (
        f"Universal pattern(s) detected: {joined} — "
        f"consider `memory add --global` (or skip with `confirm: cross-project`)."
    )


def emit_universality_hint(text: str, *, cfg: dict | None = None) -> None:
    """Detect universal patterns in ``text`` and print hint to stderr.

    One layer, advisory and crash-safe: the regex catalogue of this module.
    The FTS5 semantic layer that used to follow it searched the Notion
    mirror and left with the transport (decision #358). ``cfg`` is accepted
    and ignored so call-sites keep their signature.

    Never raises, never blocks.
    """
    del cfg
    try:
        topics = detect_universal_patterns(text)
        hint = format_universality_hint(topics)
        if hint:
            import sys

            print(hint, file=sys.stderr)
    except Exception:  # noqa: BLE001 — best-effort: the hint is non-fatal to the local flow
        pass
