"""§13.3.8 is vacuous here, and this file is the ratchet the manifest names.

RENAR v1.1 made the subsystem `implements`-edge the eighth mandatory clause.
The manifest publishes it as `vacuous` (no BR class, no `level` column) and
names `renar_br_premise.premise_broken` as the watch. A watch nobody runs is a
promise nothing keeps, so the canonical schema — what `tausik init` creates,
from git, in CI — is read here on every run; the day it grows a BR carrier,
this goes red and the declaration must be re-decided, not widened.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import renar_br_premise as br  # noqa: E402
import renar_normative_inapplicability as ni  # noqa: E402
from conftest import canonical_schema_db  # noqa: E402

CROSSCUTTING_SCOPE: list[str] = []  # reads a schema, never the tree


@pytest.fixture
def db(tmp_path):
    """A project-shaped database with both harmless `implements` occurrences:
    the task→SPEC relation VALUE and nothing else."""
    conn = sqlite3.connect(str(tmp_path / "probe.db"))
    conn.execute("CREATE TABLE specs (id INTEGER PRIMARY KEY, type TEXT, title TEXT)")
    conn.execute(
        "CREATE TABLE task_specs (task_slug TEXT, spec_slug TEXT, "
        "relation TEXT NOT NULL DEFAULT 'implements' CHECK(relation IN ('implements','constrained_by')))"
    )
    conn.execute("CREATE VIRTUAL TABLE fts_specs USING fts5(title)")
    conn.commit()
    yield conn
    conn.close()


# --- the premise holds on a project-shaped database ------------------------------


def test_the_premise_holds_when_no_carrier_exists(db):
    """`implements` as a VALUE of task_specs.relation is not the edge (§13.3.8
    runs BR → BR); the ratchet must not mistake it for one."""
    assert br.level_carriers(db) == ()
    assert br.implements_edge_carriers(db) == ()
    assert br.premise_broken(db) == ()
    assert ni.implements_edge_carrier_exists(db) is False


def test_the_canonical_schema_holds_the_premise():
    """THE RATCHET. The declaration is about this project's schema, and this is
    that schema as `tausik init` creates it. Red here means a BR class, a
    subsystem level or an implements column arrived — re-assess §13.3.8 by
    measurement (decision #364 names the shape), do not edit the message."""
    conn = canonical_schema_db()
    try:
        broken = br.premise_broken(conn)
    finally:
        conn.close()
    assert not broken, (
        "the substrate now carries a §13.3.8 subject: "
        + ", ".join(broken)
        + " — the vacuous verdict `implements-edge-subsystem` and the §10.11.1 "
        "control-point declaration must be re-decided"
    )


# --- the premise breaks on every carrier kind ------------------------------------------


@pytest.mark.parametrize(
    ("ddl", "expect"),
    [
        (
            "CREATE TABLE business_requirements (id INTEGER PRIMARY KEY, title TEXT)",
            "table business_requirements (level/BR class)",
        ),
        (
            "CREATE TABLE product_reqs (id INTEGER PRIMARY KEY, "
            "level TEXT NOT NULL CHECK(level IN ('system','subsystem')))",
            "table product_reqs (level/BR class)",
        ),
        (
            "CREATE TABLE reqs (id INTEGER PRIMARY KEY, implements TEXT)",
            "table reqs (implements column)",
        ),
    ],
    ids=["br-named-table", "level-admitting-subsystem", "implements-column"],
)
def test_a_carrier_of_any_kind_breaks_the_premise(db, ddl, expect):
    db.execute(ddl)
    db.commit()
    assert expect in br.premise_broken(db), br.premise_broken(db)
    assert ni.implements_edge_carrier_exists(db) is True


def test_a_level_column_without_subsystem_is_not_a_carrier(db):
    """NEGATIVE: `level` is a common word. A severity level on a finding, or a
    log level, admits no `subsystem` and gives §13.3.8 no subject."""
    db.execute(
        "CREATE TABLE findings (id INTEGER PRIMARY KEY, level TEXT CHECK(level IN ('low','high')))"
    )
    db.commit()
    assert br.premise_broken(db) == ()


# --- what the manifest publishes ---------------------------------------------------------


def test_the_verdict_is_vacuous_true_and_names_its_watch():
    clause = br.implements_edge_clause()
    assert clause["confirmed"] is True
    assert "vacuous" in str(clause["evidence"]) and "§13.3.8" in str(clause["evidence"])
    assert "renar_br_premise.premise_broken" in br.BR_PREMISE_WATCH
    assert "tests/test_renar_br_premise.py" in br.BR_PREMISE_WATCH


def test_the_control_point_declaration_is_registered_and_watched():
    decl = [d for d in ni.DECLARATIONS if d is br.CONTROL_POINT_DECLARATION]
    assert len(decl) == 1, "the §10.11.1 half must be declared exactly once"
    _module, _, func = decl[0]["premise-watched-by"].rpartition(".")
    assert callable(getattr(ni, func))
    assert "decision #364" in decl[0]["decided-by"]
