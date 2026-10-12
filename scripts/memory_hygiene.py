"""Memory layers and the by-relevance tail (memory-tail-by-relevance-not-recency).

Kaeru-flavoured layering for the TAUSIK memory corpus. Layers are assigned by
ACCUMULATION — explicit reads (hit_count), pinning, age — never by schedule
and never by hand per record. The tail in CLAUDE.md keeps its recency order
until the project opts in via .tausik/config.json
(``{"memory_tail_by_relevance": true}``): kaeru ships hygiene opt-in too, and
the caution is deliberate — run the dry-run on a corpus you care about first.

Everything here works on the backend facade (`be`) the CLI/service already
hold; no new public backend members (the class-surface ratchet holds).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, cast

#: Rank used when ordering the tail; lower sorts first. Pinned beats all.
LAYER_RANK: dict[str | None, int] = {
    "core": 0,
    "hot": 1,
    "warm": 2,
    "cold": 3,
    "frozen": 4,
    None: 3,
}

#: A record is FROZEN at 0 hits only past this age (days); a fresh record has
#: not had the chance to be read and stays cold, not frozen.
FROZEN_AFTER_DAYS = 90

#: Layer thresholds on cumulative explicit reads. Derivation: the corpus has
#: 902 active records; a `show` costs a deliberate round trip, so 2 reads
#: already separate signal from noise (warm), 8 says a convention people
#: actually work by (hot), 20 makes it structural (core).
HOT_AT_HITS = 8
CORE_AT_HITS = 20


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def planned_layer(row: dict[str, Any], now: datetime | None = None) -> str:
    """The layer a record deserves, from its own accumulation. Pure.

    Pinned records report ``core`` — informational only: `apply_layers`
    never writes a layer for them, and the tail sorts pinned first anyway.
    """
    if row.get("pinned"):
        return "core"
    hits = row.get("hit_count") or 0
    if hits >= CORE_AT_HITS:
        return "core"
    if hits >= HOT_AT_HITS:
        return "hot"
    if hits >= 2:
        return "warm"
    if hits == 1:
        return "cold"
    updated = _parse_ts(row.get("updated_at"))
    if now is None:
        now = datetime.now(timezone.utc)
    if updated is not None and (now - updated).days >= FROZEN_AFTER_DAYS:
        return "frozen"
    return "cold"


def record_hit(be: Any, mid: int) -> None:
    """Bump hit_count/last_hit_at. Called on every explicit `memory show`."""
    be._conn.execute(
        "UPDATE memory SET hit_count = hit_count + 1, last_hit_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), mid),
    )
    be._conn.commit()


def set_pinned(be: Any, mid: int, pinned: bool) -> str:
    row = be._q1("SELECT id, title, pinned FROM memory WHERE id=?", (mid,))
    if not row:
        return f"Memory #{mid} not found."
    be._conn.execute("UPDATE memory SET pinned = ? WHERE id = ?", (1 if pinned else 0, mid))
    be._conn.commit()
    state = "pinned — never auto-demoted, always first in the tail" if pinned else "unpinned"
    return f"Memory #{mid} ({row['title'][:60]}) {state}."


def _all_rows(be: Any) -> list[dict[str, Any]]:
    return cast(
        "list[dict[str, Any]]",
        be._q(
            "SELECT id, type, title, hit_count, last_hit_at, layer, pinned, updated_at "
            "FROM memory WHERE archived_at IS NULL ORDER BY id"
        ),
    )


def report_lines(be: Any) -> list[str]:
    """DRY-RUN: what the next apply would do and why. Writes nothing (AC3)."""
    rows = _all_rows(be)
    if not rows:
        return [
            "Memory hygiene: corpus is empty — nothing to plan, nothing to move.",
            "The tail keeps its recency order; no headings are emitted for it.",
        ]
    now = datetime.now(timezone.utc)
    moves: list[tuple[int, str, str, str]] = []
    pinned = 0
    for r in rows:
        if r["pinned"]:
            pinned += 1
            continue
        want = planned_layer(r, now)
        if want != (r["layer"] or None):
            moves.append((r["id"], r["layer"] or "unset", want, r["title"][:50]))
    by_target: dict[str, int] = {}
    for _, _, want, _ in moves:
        by_target[want] = by_target.get(want, 0) + 1
    out = [
        "Memory hygiene plan (DRY-RUN — nothing written):",
        f"  corpus: {len(rows)} active record(s), {pinned} pinned (never moved)",
        f"  planned moves: {len(moves)}"
        + (f" — {', '.join(f'{k}: {v}' for k, v in sorted(by_target.items()))}" if moves else ""),
    ]
    for mid, prev, want, title in moves[:15]:
        out.append(f"    #{mid:<4} {prev:<5} -> {want:<6} {title}")
    if len(moves) > 15:
        out.append(f"    … and {len(moves) - 15} more")
    out.append("Apply with --yes (snapshotted; --revert undoes the last apply in one command).")
    return out


def apply_layers(be: Any) -> str:
    """Write planned layers, snapshotting previous values for `--revert` (AC4)."""
    rows = _all_rows(be)
    if not rows:
        return "Memory hygiene: corpus is empty — nothing applied."
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    run_row = be._q1("SELECT COALESCE(MAX(run_id), 0) + 1 AS rid FROM memory_hygiene_snapshots")
    run_id = int(run_row["rid"]) if run_row else 1
    moved = pinned = 0
    for r in rows:
        if r["pinned"]:
            pinned += 1  # AC5: pinned records are never auto-demoted, full stop
            continue
        want = planned_layer(r, now)
        if want == (r["layer"] or None):
            continue
        be._conn.execute(
            "INSERT INTO memory_hygiene_snapshots(run_id, memory_id, prev_layer, applied_at) "
            "VALUES(?,?,?,?)",
            (run_id, r["id"], r["layer"], stamp),
        )
        be._conn.execute("UPDATE memory SET layer = ? WHERE id = ?", (want, r["id"]))
        moved += 1
    be._conn.commit()
    return (
        f"Memory hygiene applied: {moved} record(s) re-layered, {pinned} pinned skipped. "
        f"Run #{run_id} snapshotted — `memory hygiene --revert` restores it."
    )


def revert_last(be: Any) -> str:
    """Undo the last apply, exactly, in one command (AC4). Nothing is deleted."""
    row = be._q1("SELECT run_id, applied_at FROM memory_hygiene_snapshots ORDER BY id DESC LIMIT 1")
    if not row:
        return "Memory hygiene: nothing to revert — no apply has ever run."
    run_id = int(row["run_id"])
    snaps = be._q(
        "SELECT memory_id, prev_layer FROM memory_hygiene_snapshots WHERE run_id=?", (run_id,)
    )
    for s in snaps:
        be._conn.execute(
            "UPDATE memory SET layer = ? WHERE id = ?", (s["prev_layer"], s["memory_id"])
        )
    be._conn.execute("DELETE FROM memory_hygiene_snapshots WHERE run_id=?", (run_id,))
    be._conn.commit()
    return f"Memory hygiene reverted run #{run_id}: {len(snaps)} record(s) restored."


def relevance_head(be: Any, mem_type: str, n: int) -> list[dict[str, Any]]:
    """Per-type head ordered by significance: pinned, then layer, then hits."""
    return cast(
        "list[dict[str, Any]]",
        be._q(
            "SELECT * FROM memory WHERE archived_at IS NULL AND type=? "
            "ORDER BY pinned DESC, "
            "CASE COALESCE(layer, 'cold') WHEN 'core' THEN 0 WHEN 'hot' THEN 1 "
            "WHEN 'warm' THEN 2 WHEN 'cold' THEN 3 ELSE 4 END, "
            "hit_count DESC, id DESC LIMIT ?",
            (mem_type, n),
        ),
    )


def tail_by_relevance_enabled(be: Any) -> bool:
    """The opt-in flag (AC7): absent/false keeps the recency tail byte-identical."""
    try:
        cfg_path = os.path.join(os.path.dirname(be.db_path), "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return (
                bool(data.get("memory_tail_by_relevance", False))
                if isinstance(data, dict)
                else False
            )
    except Exception:  # noqa: BLE001 — a broken flag must degrade to the default, not break /start
        return False
    return False
