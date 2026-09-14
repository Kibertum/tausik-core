"""The committed RENAR-CONFORMANCE.yaml, and the version chain behind it.

§13.4.1 puts the manifest at the root of the requirements substrate and calls it
immutable in the V1 sense: each claim makes a new version, and previous versions
are NOT deleted — they stay in the substrate as an audit journal.

We had neither. `tausik renar conformance` printed a manifest on demand and
`--write` overwrote the file, so `manifest-version` counted up while every
earlier version vanished. Nothing outside the repo could read our state at all,
which is exactly why ADR-020 §3 described our claim from stale data.

After decisions#292 the file's ABSENCE is no longer a violation — §1.5.4 allows
"the manifest either does not exist or explicitly declares non-conformance". It
exists by choice: a state nobody outside can read is a state that gets described
wrongly by whoever tries.

A stale committed manifest would be worse than none — a published false
statement rather than a missing one — so `test_committed_manifest_is_not_stale`
holds it to what the live DB says today.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

yaml = pytest.importorskip("yaml")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from conftest import DORMANT_WITHOUT_LIVE_DB  # noqa: E402

from renar_conformance import generate  # noqa: E402

# Reads the committed manifest and the project DB — no import edge selects this.
CROSSCUTTING_SCOPE = ["scripts/", "RENAR-CONFORMANCE.yaml"]

MANIFEST = os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml")
PROJECT_DB = os.path.join(_ROOT, ".tausik", "tausik.db")

# Fields whose value is a function of WHEN the manifest was written, not of what
# the project is. Comparing them would make the test fail every day at midnight.
DATE_DEPENDENT = {
    "assessment-date",
    "manifest-id",
    "next-assessment-due",
    "manifest-version",
    "assessor",
    "replaces",
    "assessment-evidence",
}


def _committed() -> dict:
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        return yaml.safe_load(fh)


def test_manifest_exists_at_the_substrate_root():
    assert os.path.isfile(MANIFEST), (
        "§13.4.1 puts RENAR-CONFORMANCE.yaml at the substrate root; it is absent"
    )


def test_manifest_declares_non_conformance():
    """The file a reader outside this repo opens must state our position."""
    m = _committed()
    assert m["level"] is None
    assert m["conformance-declaration"] == "non-conformant"
    assert m["scope-exclusion"]["clause"] == "§1.5.4"
    assert m["scope-exclusion"]["decided-in"] == "decisions#292"


def test_header_names_where_previous_versions_live():
    """§13.4.1's audit journal is git history — say so IN the artifact.

    A reader outside this repo cannot guess that the journal is the file's own
    history. An undocumented mechanism satisfies the clause for us and not for
    them, which is the same failure as having no journal.
    """
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        header = "".join(line for line in fh if line.startswith("#"))
    assert "§13.4.1" in header
    assert "git log --follow -p RENAR-CONFORMANCE.yaml" in header


@pytest.mark.skipif(
    not os.path.isfile(PROJECT_DB),
    reason=DORMANT_WITHOUT_LIVE_DB,
)
def test_committed_manifest_is_not_stale():
    """Substantive fields must match what the live DB yields today.

    Scoped to the claim-bearing keys; the date-dependent ones move on their own
    and comparing them would make this fail with the calendar rather than with
    the project.

    THE ONE CONTROL IN THIS FAMILY THAT CANNOT MOVE TO GIT, and the reason is in
    the sentence above: its subject IS the working copy. "Does the committed
    artifact still match what this database yields" has no answer where there is
    no database — unlike "which classes does this project declare" or "is the
    task this caveat names still open", both of which git answers and both of
    which were moved there in session #203. So this one stays dormant in CI and
    says so out loud, in the roster, instead of vanishing into the skip count.
    """
    committed = _committed()
    conn = sqlite3.connect(f"file:{PROJECT_DB}?mode=ro", uri=True)
    try:
        fresh, _ = generate(
            conn, "test", committed["assessment-date"], committed["manifest-version"]
        )
    finally:
        conn.close()
    drifted = {
        k: (committed.get(k), fresh.get(k))
        for k in set(committed) | set(fresh)
        if k not in DATE_DEPENDENT and committed.get(k) != fresh.get(k)
    }
    assert not drifted, (
        "committed manifest no longer matches live DB state — regenerate with "
        "`tausik renar conformance --write`:\n"
        + "\n".join(f"  {k}: committed={c!r} live={f!r}" for k, (c, f) in sorted(drifted.items()))
    )


class TestVersionChain:
    """§13.4.2's `replaces` is the back-link that makes the journal navigable."""

    def test_v1_replaces_nothing(self, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m, _ = generate(conn, "a", "2026-08-31", manifest_version=1)
        conn.close()
        assert m["replaces"] is None, "a chain has to start somewhere"

    def test_the_library_never_invents_the_back_link(self, tmp_path):
        """No caller-supplied link means `replaces: null`, at ANY version.

        This module cannot see the audit journal, so any link it composed would
        be a guess. It used to guess `<manifest-id>@v<N-1>` from the generation
        date and the counter, and the guess was wrong for 5 of the first 8
        versions — the counter advances on every `--write`, the journal records
        only commits, so v4, v5, v6, v8, v10 and v12 were named as predecessors
        without ever having existed. Silence is the honest default; the caller
        that can read the journal supplies the link.
        """
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m2, _ = generate(conn, "a", "2026-08-31", manifest_version=2)
        m9, _ = generate(conn, "a", "2026-08-31", manifest_version=9)
        conn.close()
        assert m2["replaces"] is None
        assert m9["replaces"] is None

    def test_the_supplied_link_is_carried_verbatim(self, tmp_path):
        """Whatever the journal-reading caller passes reaches the manifest as-is.

        Not re-derived, not reformatted, not overridden by the counter: a link
        naming a version far behind this one is exactly what an uncommitted
        `--write` leaves behind, and it must survive to the artifact.
        """
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m, text = generate(
            conn, "a", "2026-09-04", manifest_version=17, replaces="CFM-2026-08-31-tausik@v15"
        )
        conn.close()
        assert m["replaces"] == "CFM-2026-08-31-tausik@v15"
        assert "CFM-2026-08-31-tausik@v15" in text

    def test_replaces_is_not_the_unknown_state_sentinel(self, tmp_path):
        """`replaced-by` and `replaces` are different fields with different jobs.

        The standard overloads `replaced-by`: §13.4.1 uses it to point at the
        next manifest version, §13.8.2 uses it as the `<unknown-state>` sentinel.
        We are in the sentinel case, so it carries the sentinel — and `replaces`
        must keep pointing backwards regardless.

        The link is supplied explicitly: with `replaces` left to its default the
        comparison would pass on `None != "<unknown-state>"` alone and prove
        nothing about the two fields being kept apart.
        """
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m, _ = generate(
            conn, "a", "2026-08-31", manifest_version=2, replaces="CFM-2026-08-31-tausik@v1"
        )
        conn.close()
        assert m["replaced-by"] == "<unknown-state>"
        assert m["replaces"] == "CFM-2026-08-31-tausik@v1"
        assert m["replaces"] != m["replaced-by"]
