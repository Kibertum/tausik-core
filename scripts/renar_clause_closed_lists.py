"""§13.3.4 and §13.3.7 — closed lists MEASURED against the substrate, not written.

Both clauses were confirmed by a literal ``True`` whose evidence string named
``len(SPEC_TYPES)`` and ``len(FINDING_CATEGORIES)`` — a count, read as if a
check had run. Measured in session #213 by planting violating states: a
``specs.type`` CHECK admitting a local type ``FOO`` with a row of that type,
a CHECK one short of the standard's list, an ``adapt_findings.category``
CHECK admitting an eighth category with a finding in it, an ``adapts.status``
CHECK admitting a local status — every one left the clause ``true``. A
confirmation that cannot go red on the violations its clause names is the
degeneracy ADR-021 describes.

WHAT THE CLAUSES REQUIRE. §13.3.4: the SPEC type belongs to the standard's
closed list and a project may not add types locally. §13.3.7: the backward
finding categories are closed (§7.4.4), the SPEC types again (§13.3.4), and
the artifact lifecycle states are not extended locally. The substrate's own
enforcement of a closed list is the CHECK constraint on the column, so the
measurable question is: does the CHECK admit exactly the declared list, and
does every row sit inside it? The first reddens on a local extension or a
shortfall; the second on data written under an older or missing CHECK.

WHAT THE DECLARED LISTS ARE. ``SPEC_TYPES``, ``FINDING_CATEGORIES`` and
``ADAPT_STATUSES`` are the project's literal declarations of the standard's
lists; that they match the standard is pinned by their own guard tests
(``test_spec_types_closed_list``, the ADAPT guards). This module derives from
those declarations and enumerates nothing itself — a second literal copy is
the defect ``LIST_RE`` exists to catch.

THE CHECK PARSER IS THE PRIMITIVE. ``check_domain`` reads the values a
column's CHECK admits out of the DDL SQLite stores; ``renar_clause_reactive_adapt``
had a private cut of the same read keyed on one literal marker, and delegates
to this one now rather than keeping a copy.

Read-only: every function queries, none writes.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from renar_clause_reactive_adapt import Subcheck
from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES
from service_specs import SPEC_TYPES

CLAUSE_13_3_4 = "§13.3.4 (SPEC type list closed, no local types)"
CLAUSE_13_3_7 = "§13.3.7 (backward findings, SPEC types, lifecycle states closed)"


def check_domain(conn: sqlite3.Connection, table: str, column: str) -> tuple[str, ...] | None:
    """Values ``<column>``'s ``CHECK(<column> IN (...))`` admits, from the stored DDL.

    ``None`` when the table is absent or the column carries no such CHECK —
    which for a closed list is itself the finding: the substrate holds the
    list open. Parsed from ``sqlite_master`` because SQLite exposes no
    catalogue of CHECK constraints; the DDL text is the only carrier.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not row or not row[0]:
        return None
    col = re.escape(column)
    ddl = str(row[0])
    m = re.search(rf"\b{col}\s+TEXT\b[^,]*?CHECK\s*\(\s*{col}\s+IN\s*\(", ddl, re.S)
    if not m:
        return None
    return _values_until_close(ddl, m.end())


def _values_until_close(ddl: str, start: int) -> tuple[str, ...] | None:
    """Quoted values of an ``IN (...)`` list opened at *start*; ``None`` if unparseable.

    A regex is not enough and the shortcut cost two review findings: ``[^)]*``
    stops at a parenthesis INSIDE a value (``'FOO(BAR)'`` truncated the list to
    nothing and returned an empty tuple, which reads as "the CHECK admits no
    value" — a fact, where the truth was "this could not be read"), and
    ``'([^']*)'`` splits SQL's doubled-quote escape (``'isn''t'`` became two
    values). Both are latent today — no declared list holds either character —
    but this parser is billed as the primitive every closed list reuses, and a
    primitive that degrades quietly is the defect the clauses above exist to
    remove. So: scan, tracking the string state, and answer ``None`` for
    anything that does not close cleanly or yields no value.
    """
    values: list[str] = []
    buf: list[str] = []
    i, depth, in_string = start, 1, False
    while i < len(ddl):
        ch = ddl[i]
        # COMMENTS ARE NOT CODE, and reading them as code was a FALSE PASS, not
        # a crash: `CHECK(type IN ('A','B' /* note ) */, 'FAKE'))` is admitted
        # by SQLite with 'FAKE' in it, while the scan stopped at the `)` inside
        # the comment and reported a list that matched the declaration exactly
        # (external review #40, reproduced with a live INSERT). A guard that
        # goes green on the violation it exists to catch is the degeneracy this
        # module was written to remove. Skipped only OUTSIDE a string: `--` and
        # `/*` inside a quoted value are ordinary characters.
        if not in_string and ddl.startswith("--", i):
            nl = ddl.find("\n", i)
            if nl < 0:
                return None  # a line comment that never ends cannot close the list
            i = nl + 1
            continue
        if not in_string and ddl.startswith("/*", i):
            end = ddl.find("*/", i + 2)
            if end < 0:
                return None  # unterminated block comment — unreadable, not empty
            i = end + 2
            continue
        if in_string:
            if ch == "'":
                if i + 1 < len(ddl) and ddl[i + 1] == "'":
                    buf.append("'")  # SQL's escape for a literal quote
                    i += 2
                    continue
                in_string = False
                values.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        elif ch == "'":
            in_string = True
            buf = []
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return tuple(values) or None
        i += 1
    return None  # ran off the end: unterminated string or unbalanced parentheses


def _rows_outside(
    conn: sqlite3.Connection, table: str, column: str, allowed: tuple[str, ...]
) -> int | None:
    """Rows whose value lies outside ``allowed``; ``None`` when the table cannot be read."""
    placeholders = ",".join("?" for _ in allowed)
    try:
        row = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({placeholders})", allowed
        ).fetchone()
    except sqlite3.Error:
        return None
    return int(row[0]) if row else 0


def closed_list_subchecks(
    conn: sqlite3.Connection,
    *,
    table: str,
    column: str,
    declared: tuple[str, ...],
    clause: str,
    label: str,
) -> list[Subcheck]:
    """Two named halves of one closed list: the substrate's CHECK, then the rows."""
    domain = check_domain(conn, table, column)
    if domain is None:
        substrate = Subcheck(
            f"{label}-substrate-closed",
            False,
            clause,
            f"{table}.{column} carries no CHECK constraint — the substrate holds the list open",
        )
    else:
        extra = sorted(set(domain) - set(declared))
        missing = sorted(set(declared) - set(domain))
        ok = not extra and not missing
        substrate = Subcheck(
            f"{label}-substrate-closed",
            ok,
            clause,
            (
                f"{table}.{column} CHECK admits exactly the declared {len(declared)} value(s)"
                if ok
                else f"{table}.{column} CHECK admits {extra or 'nothing'} beyond the declaration "
                f"and lacks {missing or 'nothing'} of it"
            ),
        )
    outside = _rows_outside(conn, table, column, declared)
    rows = Subcheck(
        f"{label}-rows-inside",
        outside == 0,
        clause,
        (
            f"every {table} row is inside the declared list"
            if outside == 0
            else f"{table} cannot be read"
            if outside is None
            else f"{outside} {table} row(s) carry a {column} outside the declared list"
        ),
    )
    return [substrate, rows]


def _verdict(subchecks: list[Subcheck], clause: str) -> dict[str, Any]:
    failed = [s.name for s in subchecks if not s.ok]
    return {
        "confirmed": not failed,
        "evidence": (
            f"{clause}: all {len(subchecks)} sub-checks hold"
            if not failed
            else f"{clause}: failed {failed}"
        ),
        "subchecks": [s.as_dict() for s in subchecks],
    }


def assess_spec_types(conn: sqlite3.Connection) -> dict[str, Any]:
    """§13.3.4: ``specs.type`` is closed at the declared list and every row is inside."""
    subchecks = closed_list_subchecks(
        conn,
        table="specs",
        column="type",
        declared=SPEC_TYPES,
        clause=CLAUSE_13_3_4,
        label="spec-types",
    )
    return _verdict(subchecks, CLAUSE_13_3_4)


def assess_closed_lists(conn: sqlite3.Connection) -> dict[str, Any]:
    """§13.3.7: backward-finding categories and ADAPT lifecycle statuses are closed.

    The SPEC type half of the clause is §13.3.4's own verdict and is not
    counted twice here. The lifecycle states measured are the ADAPT ones the
    project declares (``ADAPT_STATUSES``, §7.8.1, schema v50); the BR/SR/SPEC
    states of chapter 10 have no declared list in this project yet, and a
    sub-check over an undeclared list would be a guess (noted in the task
    journal for the owner, not built).
    """
    subchecks = closed_list_subchecks(
        conn,
        table="adapt_findings",
        column="category",
        declared=FINDING_CATEGORIES,
        clause=CLAUSE_13_3_7,
        label="backward-findings",
    ) + closed_list_subchecks(
        conn,
        table="adapts",
        column="status",
        declared=ADAPT_STATUSES,
        clause=CLAUSE_13_3_7,
        label="adapt-statuses",
    )
    return _verdict(subchecks, CLAUSE_13_3_7)
