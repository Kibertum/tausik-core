"""Perform a redaction and record the trace that makes it legitimate.

Decision #258. Two halves, and neither is optional:

  1. The sensitive substring leaves the database. Not moved, not shadowed, not
     kept "just in case" — gone. A redaction that stores the original somewhere
     has relocated the leak, not removed it, and the row it now sits in is one
     nobody thinks to scan.

  2. The FACT of the redaction stays, naming the entity, the field, the CLASS of
     what went, the reason, the count and the instant. An append-only journal is
     evidence because a row cannot be quietly rewritten; once rewriting becomes
     possible, only the trace keeps the journal worth believing.

Consequence, stated rather than discovered later: this is not undoable by
reverting code. The rollback plan for a redaction is a database backup taken
beforehand, and the command says so before it writes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import redact_scope
from tausik_utils import utcnow_iso


@dataclass(frozen=True)
class RedactionRequest:
    """What to strike out, what to call it, and on what grounds.

    ``label`` names the CLASS ("internal-host", "third-party-project"); it is
    what the marker and the trace will carry forever, so it is chosen for a
    reader who arrives years later with no memory of this session.

    ``reason`` is required and unvalidated on purpose: a mandatory field that
    accepts anything still forces the writer to type a justification, while a
    validated vocabulary would invite picking the nearest allowed word.
    """

    pattern: str
    label: str
    reason: str
    regex: bool = False


@dataclass(frozen=True)
class Hit:
    """One column of one row that the pattern matches."""

    entity_type: str
    entity_id: int
    field: str
    occurrences: int


@dataclass(frozen=True)
class RedactionResult:
    """What a run did, in a form that separates the three outcomes.

    ``matched`` exists so "found nothing" cannot be mistaken for "did the work":
    a caller who believes a leak is there and gets a clean exit learns nothing
    about a mistyped pattern. Same conflation the gates carry, in a command that
    writes.
    """

    matched: bool
    occurrences: int
    rows: int
    summary: str


def _compiled(req: RedactionRequest) -> re.Pattern[str]:
    return re.compile(req.pattern if req.regex else re.escape(req.pattern))


def _tables(svc: Any) -> dict[str, tuple[str, ...]]:
    """The declared map, filtered to tables this database actually has.

    A projection carried by an older schema simply has fewer tables; asking for
    a missing one would abort the whole run over a table that holds nothing.
    """
    present = {
        r[0]
        for r in svc.be._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    return {t: c for t, c in redact_scope.REDACTABLE_COLUMNS.items() if t in present}


def plan_redaction(svc: Any, req: RedactionRequest) -> list[Hit]:
    """Every (row, column) the pattern touches. Reads only — writes nothing.

    This is what a bare invocation runs: the irreversible half must be asked for
    explicitly, never reached by default.
    """
    rx = _compiled(req)
    hits: list[Hit] = []
    for table, columns in _tables(svc).items():
        for column in columns:
            rows = svc.be._conn.execute(
                f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL"  # noqa: S608
            ).fetchall()
            for row_id, value in rows:
                n = len(rx.findall(value or ""))
                if n:
                    hits.append(Hit(table, int(row_id), column, n))
    return hits


def apply_redaction(svc: Any, req: RedactionRequest) -> RedactionResult:
    """Overwrite every match with the marker and record one trace row per hit.

    The whole run is a single transaction: a redaction that half-applied would
    leave some columns clean, some leaking, and a trace claiming both.
    """
    ensure_redactions_table(svc)
    hits = plan_redaction(svc, req)
    if not hits:
        return RedactionResult(
            matched=False,
            occurrences=0,
            rows=0,
            summary=(
                f"no match for {req.pattern!r} in any redactable column — "
                f"nothing was written. If you expected a match, the pattern is "
                f"wrong, not the data."
            ),
        )

    rx = _compiled(req)
    replacement = redact_scope.marker(req.label)
    stamp = utcnow_iso()
    total = 0
    conn = svc.be._conn
    with conn:
        for hit in hits:
            current = conn.execute(
                f"SELECT {hit.field} FROM {hit.entity_type} WHERE id = ?",  # noqa: S608
                (hit.entity_id,),
            ).fetchone()[0]
            conn.execute(
                f"UPDATE {hit.entity_type} SET {hit.field} = ? WHERE id = ?",  # noqa: S608
                (rx.sub(replacement, current or ""), hit.entity_id),
            )
            conn.execute(
                "INSERT INTO redactions (entity_type, entity_id, field, label, "
                "reason, occurrences, redacted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    hit.entity_type,
                    hit.entity_id,
                    hit.field,
                    req.label,
                    req.reason,
                    hit.occurrences,
                    stamp,
                ),
            )
            total += hit.occurrences
    return RedactionResult(
        matched=True,
        occurrences=total,
        rows=len(hits),
        summary=(
            f"redacted {total} occurrence(s) across {len(hits)} column(s) as "
            f"{req.label!r}; the original is gone and cannot be restored from "
            f"this database"
        ),
    )


def ensure_redactions_table(svc: Any) -> None:
    """Create the trace table when an older database predates it.

    Additive and idempotent, so a project that never redacts anything pays a
    single ``CREATE TABLE IF NOT EXISTS`` and carries an empty table.
    """
    svc.be._conn.execute(REDACTIONS_DDL)


REDACTIONS_DDL = """
CREATE TABLE IF NOT EXISTS redactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    field TEXT NOT NULL,
    -- The CLASS of what was struck out, never its value: a trace quoting the
    -- secret would put the leak back into the database it was removed from.
    label TEXT NOT NULL,
    reason TEXT NOT NULL,
    occurrences INTEGER NOT NULL,
    redacted_at TEXT NOT NULL
)
"""
