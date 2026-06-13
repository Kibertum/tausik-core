"""Memory hygiene primitives — duration parsing + dedupe similarity.

Helpers used by ``KnowledgeMixin.memory_archive`` and
``KnowledgeMixin.memory_dedupe``. Kept separate so the service module
stays under the filesize gate.

Duration grammar accepted by ``parse_duration_to_days``:

    <int><unit>     where unit ∈ {d, w, m, y}
                    d=1 day, w=7 days, m=30 days, y=365 days

Anything else (negative, zero, mixed grammar like ``1d2h``) is a
``ValueError`` — caller surfaces a friendly CLI message.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([dwmy])\s*$", re.IGNORECASE)
_UNIT_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


def parse_duration_to_days(raw: str) -> int:
    """Parse ``"90d"`` / ``"12w"`` / ``"2m"`` / ``"1y"`` into integer days."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Invalid duration: {raw!r}. Use forms like '90d', '12w', '2m', '1y'.")
    m = _DURATION_RE.match(raw)
    if not m:
        raise ValueError(
            f"Invalid duration {raw!r}. Use <int><unit> where unit is d/w/m/y "
            "(e.g. '90d', '12w', '2m', '1y')."
        )
    n = int(m.group(1))
    if n <= 0:
        raise ValueError(f"Duration must be > 0, got {raw!r}.")
    unit = m.group(2).lower()
    return n * _UNIT_DAYS[unit]


def _similarity(a: str, b: str) -> float:
    """Normalised SequenceMatcher ratio over title+content concatenation."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def find_dedupe_candidates(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    """Pairwise similarity over memory rows; return suggestions above threshold.

    ``rows`` is the output of ``memory_list`` (each dict has at least
    ``id``, ``type``, ``title``, ``content``). Pairs of the SAME ``type``
    are compared on ``title || ' ' || content``; mismatched types are
    skipped to avoid suggesting a ``pattern`` merge into a ``gotcha``.
    The lower id is reported as ``id_a`` for stable ordering.
    """
    if not (0.0 < threshold <= 1.0):
        raise ValueError(f"threshold must be in (0, 1], got {threshold!r}")
    out: list[dict[str, Any]] = []
    n = len(rows)
    for i in range(n):
        ra = rows[i]
        ta = (ra.get("title") or "") + " " + (ra.get("content") or "")
        for j in range(i + 1, n):
            rb = rows[j]
            if ra.get("type") != rb.get("type"):
                continue
            tb = (rb.get("title") or "") + " " + (rb.get("content") or "")
            score = _similarity(ta, tb)
            if score >= threshold:
                lo, hi = sorted([ra, rb], key=lambda r: int(r.get("id") or 0))
                out.append(
                    {
                        "id_a": int(lo["id"]),
                        "id_b": int(hi["id"]),
                        "ratio": round(score, 4),
                        "type": ra.get("type"),
                        "title_a": lo.get("title") or "",
                        "title_b": hi.get("title") or "",
                    }
                )
    out.sort(key=lambda r: (-r["ratio"], r["id_a"], r["id_b"]))
    return out


# --- memory lint (v15p-memory-lint) ---------------------------------------
# Karpathy "second brain" hygiene: cheap deterministic linting instead of a
# heavy RAG pass. Three detectors run over the active memory set:
#   - contradicts: a `contradicts` graph edge between two live memories.
#   - superseded:  a live memory that a `supersedes` edge marks as outdated.
#   - stale_file:  content references a repo-relative path that no longer exists.
# Version staleness is intentionally NOT a heuristic here — memories legitimately
# cite both past and future versions ("deferred to v2.0"), so any pure rule is
# noisy; that judgement is left to the optional LLM pass (llm_check seam).

# A repo-relative path token: one-or-more slash segments ending in `.ext`.
_PATH_RE = re.compile(r"(?<![\w./\\])((?:[\w.\-]+/)+[\w.\-]+\.[A-Za-z0-9]{1,6})\b")


def _extract_paths(content: str) -> list[str]:
    """Return unique repo-relative path-like tokens mentioned in ``content``."""
    seen: dict[str, None] = {}
    for m in _PATH_RE.finditer(content or ""):
        token = m.group(1).strip("`'\"")
        seen.setdefault(token, None)
    return list(seen)


def find_lint_candidates(
    rows: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    file_exists: Any,
) -> list[dict[str, Any]]:
    """Deterministic memory-lint findings over the ACTIVE memory set.

    ``rows`` = unarchived ``memory_list`` output (id/type/title/content).
    ``edges`` = ``memory_edges`` rows (source/target type+id, relation).
    ``file_exists(path) -> bool`` resolves a repo-relative path.

    Returns findings ``{id, title, kind, reason, suggestion}`` sorted by id.
    Edges that point at non-active / non-memory nodes are skipped silently.
    """
    active = {int(r["id"]): (r.get("title") or "") for r in rows if r.get("id") is not None}
    findings: list[dict[str, Any]] = []

    def _is_mem(edge: dict[str, Any], side: str) -> bool:
        return (edge.get(f"{side}_type") or "memory") == "memory"

    for edge in edges:
        relation = edge.get("relation")
        if relation not in ("contradicts", "supersedes"):
            continue
        if not (_is_mem(edge, "source") and _is_mem(edge, "target")):
            continue
        try:
            src, tgt = int(edge["source_id"]), int(edge["target_id"])
        except (KeyError, TypeError, ValueError):
            continue
        if relation == "supersedes" and tgt in active:
            findings.append(
                {
                    "id": tgt,
                    "title": active[tgt],
                    "kind": "superseded",
                    "reason": f"superseded by memory #{src}",
                    "suggestion": "archive",
                }
            )
        elif relation == "contradicts":
            for a, b in ((src, tgt), (tgt, src)):
                if a in active:
                    findings.append(
                        {
                            "id": a,
                            "title": active[a],
                            "kind": "contradicts",
                            "reason": f"contradicts memory #{b}",
                            "suggestion": "review both; archive the outdated one",
                        }
                    )

    for r in rows:
        rid = r.get("id")
        if rid is None:
            continue
        for path in _extract_paths(r.get("content") or ""):
            if not file_exists(path):
                findings.append(
                    {
                        "id": int(rid),
                        "title": r.get("title") or "",
                        "kind": "stale_file",
                        "reason": f"references missing path '{path}'",
                        "suggestion": "update or archive — file no longer exists",
                    }
                )

    findings.sort(key=lambda f: (int(f["id"]), f["kind"]))
    return findings
