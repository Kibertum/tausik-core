"""Regex set for detecting project-specific markers in text.

Used by the PostToolUse memory-audit hook to flag auto-memory writes that
look like project knowledge rather than cross-project user preferences.

Patterns are tuned for precision: literal path/slug/command shapes are
strong signals, generic technology names (python, pytest, React) are NOT
flagged to keep false positives low.

Stdlib-only — importable from hooks and from the brain scrubbing pipeline
(epic brain-tausik-integration) without dependency churn.
"""

from __future__ import annotations

import re
from typing import NamedTuple


class Match(NamedTuple):
    kind: str
    match: str
    span: tuple[int, int]


_ABS_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/](?:Work|Projects|Users|src|home|opt|tmp)[\\/][\w\-./\\]+)"
    r"|"
    r"(?:/(?:Users|home|opt|srv|var|workspace|projects)/[\w\-./]+)",
)

_SLUG_RE = re.compile(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+){1,}\b")

_TAUSIK_CMD_RE = re.compile(
    r"\.tausik[\\/]tausik(?:\.cmd)?"
    r"|tausik_(?:task|memory|decide|explore|session|skill|audit|dead_end|epic|story|gate)_[a-z_]+"
)

_SRC_FILE_RE = re.compile(
    r"\b(?:scripts|tests|src|app|lib|bootstrap|agents|components|pages|api)"
    r"/[\w\-./]+\.(?:py|ts|tsx|jsx|js|go|rs|rb|php|md|sql|sh|yml|yaml|toml)\b",
    re.IGNORECASE,
)


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("abs_path", _ABS_PATH_RE),
    ("src_file", _SRC_FILE_RE),
    ("tausik_cmd", _TAUSIK_CMD_RE),
    ("slug", _SLUG_RE),
]


def detect_markers(text: str) -> list[Match]:
    """Scan text for project-specific markers.

    Returns unique matches sorted by position. An empty list means the text
    looks like a plausible cross-project preference.

    2-segment slugs (`my-app`, `brain-init`, `kebab-case`) are structurally
    indistinguishable from English kebab compounds. They are kept only when
    corroborated — either another higher-precision detector fired
    (abs_path / src_file / tausik_cmd), or a 3+ segment slug is present in
    the same text. Standalone 2-seg slugs are dropped to keep audit signal
    high.
    """
    if not text:
        return []
    seen: set[tuple[str, str]] = set()
    results: list[Match] = []
    for kind, pattern in PATTERNS:
        for m in pattern.finditer(text):
            matched = m.group(0)
            key = (kind, matched)
            if key in seen:
                continue
            seen.add(key)
            results.append(Match(kind=kind, match=matched, span=m.span()))

    has_strong = any(m.kind != "slug" or m.match.count("-") >= 2 for m in results)
    if not has_strong:
        return []
    results.sort(key=lambda r: r.span[0])
    return results
