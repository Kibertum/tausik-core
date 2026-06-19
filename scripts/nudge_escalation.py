"""Escalating nudges — silent → hint → warning → strong (v15p-escalating-nudges).

Soft invariants (journaling, checkpoint cadence, session-limit approach) used to
fire a single fixed reminder every time, which the agent learns to tune out.
This module replaces that with a per-invariant violation counter: the more an
invariant is breached without being satisfied, the louder the nudge. Compliance
resets the counter to silence. Hard blocks (commit / task done / push) are NOT
nudges and stay enforced elsewhere.

Design is decoupled: the pure core (:func:`level_for_count`, :func:`render_nudge`,
:func:`resolve_thresholds`) needs no DB; the stateful helpers (:func:`bump`,
:func:`peek`, :func:`reset`, :func:`escalate`) persist the counter in the
``meta`` table under ``nudge:<invariant>``. Every stateful helper is best-effort
and never raises — a nudge must never break the call site it advises.
"""

from __future__ import annotations

import sqlite3
from typing import Any

# Escalation levels, ordered. SILENT emits nothing.
SILENT = 0
HINT = 1
WARNING = 2
STRONG = 3

_LEVEL_NAMES = {SILENT: "silent", HINT: "hint", WARNING: "warning", STRONG: "strong"}

# Default count thresholds: how many breaches before each level kicks in.
# count < hint → silent; >= hint → hint; >= warning → warning; >= strong → strong.
DEFAULT_THRESHOLDS: dict[str, int] = {"hint": 1, "warning": 3, "strong": 5}

# Per-level presentation. {count} / {message} are substituted in render_nudge.
_LEVEL_FORMAT = {
    HINT: "ⓘ {message}",
    WARNING: "⚠ {message} (reminder #{count})",
    STRONG: "‼ {message} — please address now (reminded {count}×)",
}

_META_PREFIX = "nudge:"


def _meta_key(invariant: str) -> str:
    return f"{_META_PREFIX}{invariant}"


def resolve_thresholds(invariant: str, config: dict[str, Any] | None) -> dict[str, int]:
    """Return {hint,warning,strong} thresholds for an invariant.

    Looks up ``config['nudge']['thresholds'][invariant]`` then
    ``config['nudge']['thresholds']['default']``, falling back to
    :data:`DEFAULT_THRESHOLDS`. A malformed config silently yields defaults —
    a nudge threshold must never raise. Only positive ints override; partial
    overrides merge over the defaults.
    """
    merged = dict(DEFAULT_THRESHOLDS)
    try:
        thresholds = ((config or {}).get("nudge") or {}).get("thresholds") or {}
        for source_key in ("default", invariant):  # specific overrides default
            block = thresholds.get(source_key)
            if isinstance(block, dict):
                for level in ("hint", "warning", "strong"):
                    val = block.get(level)
                    if isinstance(val, int) and not isinstance(val, bool) and val > 0:
                        merged[level] = val
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return dict(DEFAULT_THRESHOLDS)
    return merged


def level_for_count(count: int, thresholds: dict[str, int] | None = None) -> int:
    """Map a breach count to an escalation level (SILENT..STRONG)."""
    t = thresholds or DEFAULT_THRESHOLDS
    if count >= t.get("strong", DEFAULT_THRESHOLDS["strong"]):
        return STRONG
    if count >= t.get("warning", DEFAULT_THRESHOLDS["warning"]):
        return WARNING
    if count >= t.get("hint", DEFAULT_THRESHOLDS["hint"]):
        return HINT
    return SILENT


def level_name(level: int) -> str:
    """Human-readable level name (silent/hint/warning/strong)."""
    return _LEVEL_NAMES.get(level, "silent")


def render_nudge(message: str, level: int, count: int) -> str:
    """Render a level-appropriate nudge string. SILENT → empty string."""
    fmt = _LEVEL_FORMAT.get(level)
    if fmt is None:
        return ""
    return fmt.format(message=message, count=count)


def peek(conn: sqlite3.Connection, invariant: str) -> int:
    """Current breach count for an invariant (0 when unseen). Never raises."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_meta_key(invariant),)
        ).fetchone()
        if row is None:
            return 0
        return int(row[0])
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return 0


def bump(conn: sqlite3.Connection, invariant: str) -> int:
    """Increment and return the breach count for an invariant. Never raises."""
    try:
        new_count = peek(conn, invariant) + 1
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (_meta_key(invariant), str(new_count), str(new_count)),
        )
        conn.commit()
        return new_count
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return peek(conn, invariant)


def reset(conn: sqlite3.Connection, invariant: str) -> None:
    """Clear the breach counter — the invariant was satisfied. Never raises."""
    try:
        conn.execute("DELETE FROM meta WHERE key = ?", (_meta_key(invariant),))
        conn.commit()
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass


def escalate(
    conn: sqlite3.Connection,
    invariant: str,
    message: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Record a breach and return the escalated nudge text (``""`` if silent).

    One-call integration for a soft invariant: bump the counter, resolve the
    configured thresholds, and render the level-appropriate message.
    """
    count = bump(conn, invariant)
    thresholds = resolve_thresholds(invariant, config)
    level = level_for_count(count, thresholds)
    return render_nudge(message, level, count)
