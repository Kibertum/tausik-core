"""An obligation with no subject here is DECLARED, and the declaration is bounded.

Three things have to hold at once, and each has broken somewhere in this project
before:

* the declaration reaches every SPEC it should, WITHOUT naming any of them — a
  written-out list of slugs is right only until the next SPEC exists;
* it does not become a claim of compliance — the sub-check it explains stays red;
* its premise ("no ТЗ exists here") is watched, because it is a statement about
  the world and the world is not obliged to stay that way.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import renar_normative_inapplicability as ni  # noqa: E402
from renar_clause_reactive_adapt import SPEC_PROVENANCE_FIELDS  # noqa: E402


def _specs_db(tmp_path, *, slugs=(), provenance_columns=(), tz_values=None):
    """A substrate holding exactly the SPEC facts a case is about."""
    conn = sqlite3.connect(str(tmp_path / "ni.db"))
    cols = "".join(f", {c} TEXT" for c in provenance_columns)
    conn.execute(f"CREATE TABLE specs (id INTEGER PRIMARY KEY, slug TEXT{cols})")
    for slug in slugs:
        conn.execute("INSERT INTO specs (slug) VALUES (?)", (slug,))
    for slug, value in (tz_values or {}).items():
        conn.execute(
            f"UPDATE specs SET {ni.TZ_PROVENANCE_FIELD}=? WHERE slug=?",
            (value, slug),
        )
    conn.commit()
    return conn


class TestTheDeclarationItself:
    def test_the_watched_field_is_one_the_clause_actually_looks_for(self):
        """A declaration about a field nothing reads would watch nothing.

        Asserted here rather than by an `assert` in the module: the mistake is a
        developer's, and a runtime check would fire at import in production.
        """
        assert ni.TZ_PROVENANCE_FIELD in SPEC_PROVENANCE_FIELDS

    def test_every_declaration_names_its_premise_and_its_exit(self):
        """A declaration without a stated exit is a permanent excuse."""
        required = {
            "clause",
            "obligation",
            "inapplicable-because",
            "decided-by",
            "evidence-ref",
            "not-a-claim-of-compliance",
            "premise-watched-by",
        }
        assert ni.DECLARATIONS, "an empty registry must go through the emptiness rule below"
        for d in ni.DECLARATIONS:
            assert required <= set(d), f"declaration missing {sorted(required - set(d))}"

    def test_emptiness_must_be_declared_not_merely_reached(self):
        """NEGATIVE SCENARIO: "nothing to disclose" must not look like silence.

        The registry is allowed to empty — the world can change — but only with
        a note saying what made it unnecessary. Without the rule, deleting the
        last entry and forgetting to write one render identically.
        """
        if not ni.DECLARATIONS:
            assert ni.REGISTRY_EMPTIED_BY, "the registry is empty and nothing says what emptied it"
        else:
            assert ni.REGISTRY_EMPTIED_BY is None, (
                "a non-empty registry must not also claim to have been emptied"
            )


class TestReachIsDerivedNotEnumerated:
    @pytest.mark.parametrize("provenance_columns", [(), (ni.TZ_PROVENANCE_FIELD,)])
    def test_a_fourth_spec_is_covered_the_day_it_appears(self, tmp_path, provenance_columns):
        """The reach follows the store; nobody has to remember to edit a list.

        BOTH branches, on purpose. `covered_specs` answers by a different query
        depending on whether the substrate can hold provenance at all, and the
        live project is on the no-column branch — so a single case would have
        left the other one able to enumerate. A declared mutation that capped
        the result SURVIVED for exactly that reason before this became
        parametrized.
        """
        conn = _specs_db(
            tmp_path, slugs=("a-spec", "b-spec", "c-spec"), provenance_columns=provenance_columns
        )
        try:
            assert ni.covered_specs(conn) == ("a-spec", "b-spec", "c-spec")
            conn.execute("INSERT INTO specs (slug) VALUES ('d-spec')")
            assert ni.covered_specs(conn) == ("a-spec", "b-spec", "c-spec", "d-spec")
        finally:
            conn.close()

    def test_a_spec_that_gains_provenance_leaves_the_reach(self, tmp_path):
        """NEGATIVE SCENARIO: the declaration must not keep covering what it no longer explains."""
        conn = _specs_db(
            tmp_path,
            slugs=("bare", "sourced"),
            provenance_columns=(ni.TZ_PROVENANCE_FIELD,),
            tz_values={"sourced": "TZ-2026-001 §4"},
        )
        try:
            assert ni.covered_specs(conn) == ("bare",)
        finally:
            conn.close()

    def test_no_specs_table_reaches_nothing(self, tmp_path):
        """NEGATIVE SCENARIO: a substrate without the class must not raise."""
        conn = sqlite3.connect(str(tmp_path / "empty.db"))
        try:
            assert ni.covered_specs(conn) == ()
            assert ni.premise_broken(conn) == ()
            assert ni.section(conn)["declarations"][0]["applies-to"] == []
        finally:
            conn.close()


class TestThePremiseIsWatched:
    def test_an_arriving_tz_reference_breaks_the_premise(self, tmp_path):
        """The ratchet: a ТЗ appearing is what ends this declaration.

        Proved on SYNTHETIC state, not by breaking the guarded artifact — the
        live store must not be mutated to show that a guard has teeth.
        """
        conn = _specs_db(
            tmp_path,
            slugs=("renar-adoption",),
            provenance_columns=(ni.TZ_PROVENANCE_FIELD,),
            tz_values={"renar-adoption": "TZ-2026-001 §1"},
        )
        try:
            assert ni.premise_broken(conn) == ("renar-adoption",)
        finally:
            conn.close()

    def test_each_declaration_names_a_watcher_this_module_actually_has(self):
        """A watcher named but not present is a promise nothing keeps.

        Both declarations rest on different premises and must therefore name
        DIFFERENT watchers — the first was written pointing at the other one's,
        which would have left the gate half unwatched while claiming otherwise.
        """
        named = [d["premise-watched-by"] for d in ni.DECLARATIONS]
        assert len(set(named)) == len(named), "two premises sharing one watcher"
        for full in named:
            module, _, func = full.rpartition(".")
            assert module == "renar_normative_inapplicability", full
            assert callable(getattr(ni, func, None)), f"{full} is not a function here"

    def test_a_source_adapt_column_appearing_gives_the_gate_a_spec_side_subject(self, tmp_path):
        """The second ratchet: a COLUMN, not a row, is what ends that declaration."""
        os.makedirs(tmp_path / "no-col", exist_ok=True)
        os.makedirs(tmp_path / "col", exist_ok=True)
        without = _specs_db(tmp_path / "no-col", slugs=("x",))
        with_col = _specs_db(tmp_path / "col", slugs=("x",), provenance_columns=("source_adapt",))
        try:
            assert ni.spec_adapt_reference_possible(without) is False
            assert ni.spec_adapt_reference_possible(with_col) is True
        finally:
            without.close()
            with_col.close()

    def test_no_specs_table_cannot_hold_a_spec_side_reference(self, tmp_path):
        """NEGATIVE SCENARIO: absence of the class is not a subject either."""
        conn = sqlite3.connect(str(tmp_path / "bare.db"))
        try:
            assert ni.spec_adapt_reference_possible(conn) is False
        finally:
            conn.close()

    def test_an_empty_or_absent_column_is_the_premise_holding(self, tmp_path):
        """NEGATIVE SCENARIO: neither a missing column nor an empty string is a ТЗ."""
        os.makedirs(tmp_path / "a", exist_ok=True)
        os.makedirs(tmp_path / "b", exist_ok=True)
        no_column = _specs_db(tmp_path / "a", slugs=("x",))
        empty_value = _specs_db(
            tmp_path / "b",
            slugs=("x",),
            provenance_columns=(ni.TZ_PROVENANCE_FIELD,),
            tz_values={"x": ""},
        )
        try:
            assert ni.premise_broken(no_column) == ()
            assert ni.premise_broken(empty_value) == ()
        finally:
            no_column.close()
            empty_value.close()

    def test_the_live_project_still_holds_the_premise(self):
        """The declaration is about THIS database; check it against THIS database.

        `premise_broken` compares against our own ruling, so it is meaningless
        on a fixture's database — the same reasoning `renar_tc_premise.classes_appeared`
        carries. Its one honest consumer is a guard run against the live store.
        """
        db = os.path.join(os.path.dirname(__file__), "..", ".tausik", "tausik.db")
        if not os.path.isfile(db):
            pytest.skip("no live project database in this tree")
        conn = sqlite3.connect(f"file:{os.path.abspath(db)}?mode=ro", uri=True)
        try:
            # A database that exists but holds no SPEC is a fresh clone's
            # (CI bootstraps one, session #253): there is no ruling to hold
            # the premise against, and "reach lost" would be a false verdict
            # about an empty store, not about the declaration.
            if not _has_rows(conn, "specs"):
                pytest.skip("the live database carries no SPEC — nothing to hold the premise against")
            broken = ni.premise_broken(conn)
            assert broken == (), (
                f"a ТЗ reference appeared on {list(broken)} — decision #307 must be "
                "re-decided by its owner, not quietly widened"
            )
            assert ni.covered_specs(conn), "the declaration covers no live SPEC — reach lost"
        finally:
            conn.close()


def _has_rows(conn: sqlite3.Connection, table: str) -> bool:
    try:
        return conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None
    except sqlite3.Error:
        return False


class TestADeclarationIsNotCompliance:
    def test_the_section_says_so_in_the_artifact(self, tmp_path):
        conn = _specs_db(tmp_path, slugs=("one",))
        try:
            block = ni.section(conn)
        finally:
            conn.close()
        assert "NOT compliance" in block["disclaimer"]
        entry = block["declarations"][0]
        assert "RED" in entry["not-a-claim-of-compliance"]
        assert entry["applies-to"] == ["one"]

    def test_an_empty_registry_publishes_no_section_at_all(self, tmp_path, monkeypatch):
        """NEGATIVE SCENARIO: an empty block would read as searched-and-found-none.

        A bare `normative-inapplicability: {}` is a stronger claim than an empty
        registry supports, so the key is dropped instead.
        """
        monkeypatch.setattr(ni, "DECLARATIONS", [])
        conn = _specs_db(tmp_path, slugs=("one",))
        try:
            assert ni.section(conn) == {}
        finally:
            conn.close()
