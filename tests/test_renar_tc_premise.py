"""The premise "TAUSIK holds no TC artifacts" is measured once, and it can red.

Two declarations rest on that premise — the manifest's `tc-pos-neg-pairing`
(§13.3.5) and ADR-013's TC.environment-ref duty — and before
scripts/renar_tc_premise neither was measured. The manifest wrote `True` as a
literal, and the guard test matched two table names. A table `spec_tests` with
`assertion_ref`, `polarity` and `environment_ref` in it left both green.

So every test below is a MUTATION: it makes the premise false in one specific
way and requires the measure to notice. A test that only asserted the green case
would repeat the defect it exists to close.

The baseline is monkeypatched to the synthetic fixture's own class set. That is
not a loosening: the real `CLASSES_AT_DECLARATION` is exercised against the live
database by test_adr_013_conditional_obligations_are_still_vacuous, and pinning
it here would make these tests fail whenever a migration lands, which is a
different signal than the one they carry.

One test below does NOT monkeypatch, on purpose —
`test_a_smaller_database_is_not_a_new_class`. It pins what the full suite taught,
and the lesson was not the one first guessed. Eight tests went red because the
class ratchet was wired into the published clause, and that clause is evaluated
against ANY database — fixtures included, one of which creates tables by DDL on
purpose. Widening the witness from a count to a set did NOT fix them: the ratchet
simply does not belong to a measure that runs on databases the declaration was
never about. It moved to the repository's own guard test, and this test holds the
line that a smaller database is not an arrival.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import renar_tc_premise as premise  # noqa: E402


@pytest.fixture
def db(tmp_path):
    """A project-shaped database: two ordinary classes and one FTS index.

    The FTS index is not decoration. Its shadow tables are the reason
    `artifact_classes` cannot simply count rows in sqlite_master, and the reason
    it must not filter them by name either.
    """
    path = tmp_path / "probe.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE specs (id INTEGER PRIMARY KEY, type TEXT, title TEXT)")
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, slug TEXT)")
    conn.execute("CREATE VIRTUAL TABLE fts_specs USING fts5(title)")
    conn.commit()
    yield conn
    conn.close()


def _baseline(monkeypatch, conn):
    """Pin the witness to what this fixture currently holds, then mutate."""
    monkeypatch.setattr(
        premise, "CLASSES_AT_DECLARATION", frozenset(premise.artifact_classes(conn))
    )


def test_a_smaller_database_is_not_a_new_class(db):
    """A fixture is a SUBSET of the declaration, and a subset is not an arrival.

    No monkeypatch here: this runs against the real `CLASSES_AT_DECLARATION`, the
    way `eval_mandatory_clauses` does whenever a test builds a database of its
    own. The measure must stay silent — the clause is evaluated on many databases
    and only one of them is the one the declaration was made about.
    """
    classes = set(premise.artifact_classes(db))
    assert classes < set(premise.CLASSES_AT_DECLARATION), (
        "this fixture is no longer a strict subset of the declaration, so it "
        "cannot prove that subsets stay silent"
    )
    assert premise.tc_evidence(db) == []
    assert premise.pairing_clause(db)["confirmed"] is True


def test_fts_shadow_tables_are_not_artifact_classes(db):
    """The FTS index contributes ONE class, not the six tables SQLite made for it."""
    classes = premise.artifact_classes(db)
    assert classes == ["specs", "tasks"], classes
    raw = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert len(raw) > len(classes), (
        "the fixture created no shadow tables, so this test proves nothing about "
        "the exclusion it exists to check"
    )


def test_a_table_named_like_an_index_is_still_a_class(db, monkeypatch):
    """The exclusion is derived from the virtual table, NOT matched on `fts_`.

    This is the bypass a prefix filter would have opened: name the TC table
    `fts_test_cases` and it disappears from the measure. It is a shadow only if
    some virtual table owns it, and none owns this one.
    """
    _baseline(monkeypatch, db)
    db.execute("CREATE TABLE fts_test_cases (id INTEGER PRIMARY KEY, assertion_ref TEXT)")
    db.commit()

    assert "fts_test_cases" in premise.artifact_classes(db)
    assert premise.classes_appeared(db), (
        "a new class hiding behind an index-shaped name went unseen"
    )


def test_a_new_class_under_an_unguessable_name_reds(db, monkeypatch):
    """The mutation that survived the old cut. It must not survive this one.

    `spec_tests` matches no name the previous detector looked for, which is the
    whole point: the cut may not depend on having guessed the name.
    """
    _baseline(monkeypatch, db)
    db.execute("CREATE TABLE spec_tests (id INTEGER PRIMARY KEY, assertion_ref TEXT)")
    db.commit()

    appeared = premise.classes_appeared(db)
    assert appeared == ["spec_tests"], appeared


def test_a_spec_doc_artifact_reds_the_doc_lint_duty(db, monkeypatch):
    """The second conditional duty, and it has its own subject and its own row.

    No table appears here, so the class ratchet stays silent: this branch reds on
    data alone, which is exactly why both branches are needed.

    This test used to end by asserting that the same row reddened `pairing_clause`.
    That line encoded the defect rather than the behaviour — §13.3.5 is about TC
    pairing, and this row is ADR-013's doc-lint duty. What the clause does with a
    SPEC-DOC is now asserted, correctly, in
    `test_a_spec_doc_artifact_does_not_red_the_pairing_clause`.
    """
    _baseline(monkeypatch, db)
    db.execute("INSERT INTO specs (type, title) VALUES ('DOC', 'delivered handbook')")
    db.commit()

    evidence = premise.tc_evidence(db)
    assert evidence, "a SPEC-DOC artifact exists and the doc-lint duty stayed vacuous"
    assert "SPEC-DOC" in evidence[0], evidence
    assert "docs_lint" in evidence[0], "the finding must name the executor that does not exist"


def test_the_untouched_premise_is_green_for_the_right_reason(db, monkeypatch):
    """The green case, checked the way convention #491 requires.

    Green here must come from the protection under test and not from some other
    part of the measure, so the same call is made twice: once on the untouched
    fixture, once with ONLY the checked premise broken. If green did not move,
    it was never measuring this.
    """
    _baseline(monkeypatch, db)
    assert premise.classes_appeared(db) == []
    assert premise.pairing_clause(db)["confirmed"] is True

    db.execute("CREATE TABLE anything_at_all (id INTEGER PRIMARY KEY)")
    db.commit()
    assert premise.classes_appeared(db) != [], (
        "the green above was not produced by the class ratchet — removing the "
        "only thing it checks left it green"
    )


def test_a_spec_doc_artifact_does_not_red_the_pairing_clause(db, monkeypatch):
    """§13.3.5 is about TC pairing. A SPEC-DOC artifact is a different obligation.

    The regression this pins was live for one commit: `pairing_clause` derived its
    verdict from `tc_evidence`, whose only finding is a SPEC-DOC row. Adding a
    SPEC-DOC — legal since migration v49 — flipped a mandatory clause to `false`
    and drove `infer_level` to pre-adoption, telling an external tracker we
    violate a clause about test-case pairing because a document exists.

    The finding itself is NOT deleted: it still reaches the ADR-013 guard test,
    which is the duty it belongs to. Both halves are asserted here, so a "fix"
    that simply dropped the finding would fail this test too.
    """
    _baseline(monkeypatch, db)
    db.execute("INSERT INTO specs (type, title) VALUES ('DOC', 'delivered handbook')")
    db.commit()

    assert premise.pairing_clause(db)["confirmed"] is True, (
        "a SPEC-DOC artifact reddened §13.3.5, which is not its clause"
    )
    evidence = premise.tc_evidence(db)
    assert evidence and "SPEC-DOC" in evidence[0], (
        "the doc-lint duty stopped being watched at all — the finding must stay, "
        "it only must not drive this clause"
    )


def test_the_pairing_clause_is_disclosed_as_vacuous(db):
    """A constant `true` may be published only while the artifact says it is one.

    `pairing_clause` cannot go red on any database, by construction. Until
    session #213 the disclosure was a `measurer-caveats` entry; now every
    clause carries a basis, and this one's must be `vacuous` with the ratchet
    that watches the premise named — so the two must not drift apart.
    """
    from renar_mandatory_clauses import TC_PREMISE_WATCH, eval_mandatory_clauses

    assert premise.pairing_clause(db)["confirmed"] is True
    clause = eval_mandatory_clauses(
        {
            "signals": {"substrate_v1_v6": True},
            "clause_13_3_3": {"confirmed": False, "evidence": "-", "subchecks": []},
            "clause_13_3_4": {"confirmed": True, "evidence": "-", "subchecks": []},
            "clause_13_3_5": premise.pairing_clause(db),
            "clause_13_3_7": {"confirmed": True, "evidence": "-", "subchecks": []},
        }
    )["tc-pos-neg-pairing"]
    assert clause["basis"] == "vacuous", (
        "the clause returns a constant true and nothing discloses it; either "
        "publish it as vacuous or make the verdict measured"
    )
    assert clause["premise-watched-by"] == TC_PREMISE_WATCH
    assert "classes_appeared" in TC_PREMISE_WATCH
