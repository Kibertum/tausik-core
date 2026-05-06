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
