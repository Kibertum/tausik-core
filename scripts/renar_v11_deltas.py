"""The twenty changes of RENAR 1.1, each one done, declared or deferred — never silent.

`guide/12-migration-v11.md` of the RENAR corpus lists the wave in one table (rows
numbered 1–18, 21 and 20: there is no row 19). §13.7.3 makes a minor release an
immediate trigger for re-assessing a claim, and a delta nobody mentions reads the
same as one that was adopted. So every row gets exactly one status here:

* ``implemented`` — a mechanism in this repository does it; ``mechanism`` names
  it as ``module:function`` and a test imports it. A row marked implemented
  without a resolvable mechanism is a red test, not a claim.
* ``inapplicable`` — the obligation has no subject here; ``premise`` says why
  and ``premise_check`` names a function over the live database that returns a
  non-empty tuple the day the subject appears. The manifest publishes these.
* ``deferred`` — owed, not done; ``to`` names the release and ``decided_by`` the
  decision that moved it.
* ``no-action`` — the guide itself says the row needs none.

The count of rows is not typed anywhere: the test reads it from the guide.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

GUIDE_RELPATH = os.path.join("guide", "12-migration-v11.md")
STATUSES = ("implemented", "inapplicable", "deferred", "no-action")
_DEFER_SET = "decision #382 — the description-set model is a schema rewrite, moved to 2.0"

DELTAS: list[dict[str, Any]] = [
    {
        "row": 1,
        "change": "description set; BR/SR/SPEC/TC without status/version; set-version N.M",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 2,
        "change": "QG-0/1/2 objects: set version / TC implementation / version on product",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 3,
        "change": "§13.3.5 TC pair coverage checked at QG-0 of the set (coverage-presence)",
        "status": "implemented",
        "mechanism": "renar_mandatory_clauses:eval_mandatory_clauses",
        "note": "per artifact, not per set version — the set itself is row 1",
    },
    {
        "row": 4,
        "change": "manifest: set-version, confirmation first-party|second-party",
        "status": "deferred",
        "to": "2.0 (set-version); 1.11 (confirmation, first-party §1.4.4)",
        "decided_by": _DEFER_SET + "; decision #377 puts first-party confirmation in 1.11",
    },
    {
        "row": 5,
        "change": "SPEC-UC, the twelfth SPEC type",
        "status": "implemented",
        "mechanism": "spec_uc:check_uc_body",
    },
    {
        "row": 6,
        "change": "MW — manual walkthrough record",
        "status": "inapplicable",
        "premise_check": "renar_v11_deltas:manual_walkthrough_carriers",
        "premise": "every test case here is automated and no manual pass is run, so there is "
        "nothing for an MW record to hold; a manual-walkthrough class appearing ends this",
    },
    {
        "row": 7,
        "change": "first-party confirmation §1.4.4",
        "status": "deferred",
        "to": "1.11",
        "decided_by": "decision #377 (story B of 1.11)",
    },
    {
        "row": 8,
        "change": "reusable component: own tree, assumptions[], applies-to, uses[]",
        "status": "inapplicable",
        "premise_check": "renar_v11_deltas:component_carriers",
        "premise": "TAUSIK is described as one system; no artifact class can hold a uses[] edge",
    },
    {
        "row": 9,
        "change": "implements[] — mandatory clause §13.3.8",
        "status": "implemented",
        "mechanism": "renar_br_premise:implements_edge_clause",
    },
    {
        "row": 10,
        "change": "screen registry in SPEC-ARCH, screens[] in SPEC-UI",
        "status": "inapplicable",
        "premise_check": "renar_v11_deltas:screen_carriers",
        "premise": "the product has no interface of screens (CLI, MCP, hooks); no SPEC-UI exists",
    },
    {
        "row": 11,
        "change": "coverage completeness of the mandatory SPEC body",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 12,
        "change": "SPEC-ARCH and SPEC-SEC mandatory and non-empty at system level",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
        "note": "both exist (renar-adoption, sec-config-trust-tiers); nothing enforces them yet",
    },
    {
        "row": 13,
        "change": "controlled form of an SR statement (recommendation)",
        "status": "deferred",
        "to": "not adopted (SHOULD)",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 14,
        "change": "description language, chapter 15 — mandatory from RENAR-2",
        "status": "inapplicable",
        "premise_check": "renar_v11_deltas:level_at_least_two",
        "premise": "mandatory from RENAR-2; the manifest's level is null (§1.5.4 declaration)",
    },
    {
        "row": 15,
        "change": "automation.status: automated | manual-pending with deadline and reason",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 16,
        "change": "AR records the primary agent's model; ai-provenance by the canon",
        "status": "inapplicable",
        "premise_check": "renar_v11_deltas:ar_carriers",
        "premise": "no artifact class has the AR shape (renar_clause_reactive_adapt reads it), so "
        "there is no AR to carry primary.*; ai-provenance is mandatory from RENAR-4",
    },
    {
        "row": 17,
        "change": "metric threshold calibration by data sufficiency",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 18,
        "change": "non-degeneracy measurer for a new mandatory control §13.9.4",
        "status": "implemented",
        "mechanism": "renar_measurer_caveats:caveats_section",
    },
    {
        "row": 21,
        "change": "statement address <id>#n in TC verifies[] and step refs",
        "status": "deferred",
        "to": "2.0",
        "decided_by": _DEFER_SET,
    },
    {
        "row": 20,
        "change": "norm and process: the standard norms artifacts, not the order of work",
        "status": "no-action",
        "note": "the guide: 'Строка 20 действий не требует'",
    },
]


def guide_rows(corpus_dir: str) -> list[int]:
    """Row numbers of the change table in guide/12, read from the corpus."""
    path = os.path.join(corpus_dir, GUIDE_RELPATH)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    table = text.split("## 1.", 1)[1].split("\n## ", 1)[0]
    return [int(m.group(1)) for m in re.finditer(r"^\|\s*(\d+)\s*\|", table, re.M)]


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {str(r[0]) for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in conn.execute(f"PRAGMA table_info({table})")}


def manual_walkthrough_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(sorted(t for t in _tables(conn) if re.search(r"(^mw$|manual_walk)", t)))


def component_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(sorted(t for t in _tables(conn) if {"uses", "applies_to"} & _cols(conn, t)))


def screen_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    found = [t for t in _tables(conn) if "screens" in _cols(conn, t)]
    if "specs" in _tables(conn) and "type" in _cols(conn, "specs"):
        found += [f"specs:{r[0]}" for r in conn.execute("SELECT slug FROM specs WHERE type='UI'")]
    return tuple(sorted(found))


def ar_carriers(conn: sqlite3.Connection) -> tuple[str, ...]:
    from renar_clause_reactive_adapt import collect_state

    return tuple(collect_state(conn).ar_tables)


def level_at_least_two(conn: sqlite3.Connection) -> tuple[str, ...]:
    from renar_conformance import current_level

    level = current_level(conn).get("level")
    return (f"level {level}",) if level and str(level) not in ("RENAR-0", "RENAR-1") else ()


def section() -> dict[str, Any]:
    """The manifest block: every inapplicable and deferred row, with its reason."""
    return {
        "source": "RENAR corpus " + GUIDE_RELPATH.replace(os.sep, "/"),
        "declared-inapplicable": [
            {
                "row": d["row"],
                "change": d["change"],
                "premise": d["premise"],
                "premise-watched-by": d["premise_check"],
            }
            for d in DELTAS
            if d["status"] == "inapplicable"
        ],
        "deferred": [
            {"row": d["row"], "change": d["change"], "to": d["to"], "decided-by": d["decided_by"]}
            for d in DELTAS
            if d["status"] == "deferred"
        ],
    }


def _resolves(ref: str) -> bool:
    import importlib

    module, _, func = str(ref).partition(":")
    try:
        return callable(getattr(importlib.import_module(module), func, None))
    except ImportError:
        return False


def validate(deltas: list[dict[str, Any]]) -> list[str]:
    """Problems with the registry; empty when every row says what backs it."""
    problems: list[str] = []
    for d in deltas:
        row, status = d.get("row"), d.get("status")
        if status not in STATUSES:
            problems.append(f"row {row}: status {status!r} is not one of {STATUSES}")
        elif status == "implemented":
            if not d.get("mechanism"):
                problems.append(f"row {row}: implemented without a mechanism")
            elif not _resolves(d["mechanism"]):
                problems.append(f"row {row}: mechanism {d['mechanism']} does not resolve")
        elif status == "inapplicable":
            if not d.get("premise") or not _resolves(d.get("premise_check", "")):
                problems.append(f"row {row}: inapplicable without a premise and its check")
        elif status == "deferred" and not (d.get("to") and d.get("decided_by")):
            problems.append(f"row {row}: deferred without a release and a decision")
    return problems
