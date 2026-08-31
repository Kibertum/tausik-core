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

from renar_conformance import generate  # noqa: E402

# Reads the committed manifest and the project DB — no import edge selects this.
CROSSCUTTING_SCOPE = ["scripts/", "RENAR-CONFORMANCE.yaml"]

MANIFEST = os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml")
PROJECT_DB = os.path.join(_ROOT, ".tausik", "tausik.db")

# Fields whose value is a function of WHEN the manifest was written, not of what
# the project is. Comparing them would make the test fail every day at midnight.
DATE_DEPENDENT = {"assessment-date", "manifest-id", "next-assessment-due",
                  "manifest-version", "assessor", "replaces", "assessment-evidence"}


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


@pytest.mark.skipif(not os.path.isfile(PROJECT_DB), reason="project DB absent")
def test_committed_manifest_is_not_stale():
    """Substantive fields must match what the live DB yields today.

    Scoped to the claim-bearing keys; the date-dependent ones move on their own
    and comparing them would make this fail with the calendar rather than with
    the project.
    """
    committed = _committed()
    conn = sqlite3.connect(f"file:{PROJECT_DB}?mode=ro", uri=True)
    try:
        fresh, _ = generate(conn, "test", committed["assessment-date"],
                            committed["manifest-version"])
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

    def test_later_versions_name_their_predecessor(self, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m2, _ = generate(conn, "a", "2026-08-31", manifest_version=2)
        m3, _ = generate(conn, "a", "2026-08-31", manifest_version=3)
        conn.close()
        # §13.4.2's own form: "<manifest-id>@v<N-1>".
        assert m2["replaces"] == f"{m2['manifest-id']}@v1"
        assert m3["replaces"] == f"{m3['manifest-id']}@v2"

    def test_replaces_is_not_the_unknown_state_sentinel(self, tmp_path):
        """`replaced-by` and `replaces` are different fields with different jobs.

        The standard overloads `replaced-by`: §13.4.1 uses it to point at the
        next manifest version, §13.8.2 uses it as the `<unknown-state>` sentinel.
        We are in the sentinel case, so it carries the sentinel — and `replaces`
        must keep pointing backwards regardless.
        """
        conn = sqlite3.connect(str(tmp_path / "c.db"))
        m, _ = generate(conn, "a", "2026-08-31", manifest_version=2)
        conn.close()
        assert m["replaced-by"] == "<unknown-state>"
        assert m["replaces"] != m["replaced-by"]
