"""The manifest must not publish a confirmation it knows is unearned.

Committing RENAR-CONFORMANCE.yaml to the repo root made
`mandatory-clauses-confirmed` a PUBLISHED statement — and two of its seven
`true`s are printed by measurers we measured, this same session, to be incapable
of going red on the violations they exist to catch. That is exactly the defect
the RENAR-1 withdrawal was about (decisions#292), only this time we are the ones
printing the unearned value.

`measurer-caveats` discloses it. These tests make sure the disclosure stays a
disclosure and does not decay into a parking space for defects: every entry must
name a task that exists AND is still open, so closing the fix is the only way to
remove the caveat honestly.
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

from renar_measurer_caveats import (  # noqa: E402
    DISCLAIMER,
    MEASURER_CAVEATS,
    caveated_clauses,
    caveats_section,
)

# Reads the caveat registry, the committed manifest and the project DB; no
# import edge would otherwise select this test from a change to any of them.
CROSSCUTTING_SCOPE = ["scripts/", "RENAR-CONFORMANCE.yaml"]

MANIFEST = os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml")
PROJECT_DB = os.path.join(_ROOT, ".tausik", "tausik.db")
REQUIRED_KEYS = {"clause", "measured-as", "why-degenerate", "open-task"}


def _manifest() -> dict:
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        return yaml.safe_load(fh)


def test_registry_is_not_empty():
    """Guards a vacuous pass: an empty registry would satisfy every check below.

    One known-unearned confirmation remains today (§13.3.4); §13.3.3 left the
    registry when its measurer was repaired, in that repair's own commit. If
    this ever legitimately drops to zero, the drop belongs in the same commit
    that closes the last task — not in a silent edit here.
    """
    assert len(MEASURER_CAVEATS) >= 1
    assert caveats_section(), "a non-empty registry must produce a section"


@pytest.mark.parametrize("caveat", MEASURER_CAVEATS, ids=lambda c: c["clause"])
def test_every_caveat_is_fully_stated(caveat):
    assert set(caveat) == REQUIRED_KEYS, f"unexpected/missing keys: {set(caveat) ^ REQUIRED_KEYS}"
    for key, value in caveat.items():
        assert value.strip(), f"{key} is empty — a caveat that says nothing discloses nothing"


@pytest.mark.skipif(not os.path.isfile(PROJECT_DB), reason="project DB absent")
@pytest.mark.parametrize("caveat", MEASURER_CAVEATS, ids=lambda c: c["clause"])
def test_named_task_exists_and_is_still_open(caveat):
    """The ratchet: a caveat may only stand while its fix is outstanding.

    Without this, `measurer-caveats` becomes the cheapest place in the codebase
    to park a defect forever — "disclosed" quietly replacing "fixed".
    """
    conn = sqlite3.connect(f"file:{PROJECT_DB}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT status FROM tasks WHERE slug = ?", (caveat["open-task"],)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, (
        f"caveat for {caveat['clause']!r} names task {caveat['open-task']!r}, "
        "which does not exist — a disclosure pointing at nothing is not a disclosure"
    )
    assert row[0] != "done", (
        f"task {caveat['open-task']!r} is closed — remove the caveat for "
        f"{caveat['clause']!r} in the same change that fixed its measurer"
    )


def test_disclaimer_refuses_to_be_mistaken_for_a_repair():
    lowered = DISCLAIMER.lower()
    assert "not a repair" in lowered
    assert "does not substitute" in lowered


class TestPublishedManifest:
    def test_section_is_present_and_matches_the_registry(self):
        section = _manifest().get("measurer-caveats") or {}
        assert section, "the committed manifest carries no measurer-caveats section"
        published = {c["clause"] for c in section["unearned-confirmations"]}
        assert published == caveated_clauses()

    def test_every_caveated_clause_is_one_the_manifest_actually_confirms(self):
        """A caveat about a clause the manifest does not print is noise.

        It also catches the reverse mistake — renaming a clause key and leaving
        the caveat pointing at the old name.
        """
        confirmed = _manifest()["mandatory-clauses-confirmed"]
        for clause in caveated_clauses():
            assert clause in confirmed, f"{clause!r} is not a clause this manifest prints"

    def test_header_points_the_reader_at_the_caveats(self):
        """A caveat below the block it qualifies is read second, or not at all.

        Same rule the non-conformance declaration follows (memory #475).
        """
        with open(MANIFEST, encoding="utf-8", newline="") as fh:
            header = "".join(line for line in fh if line.startswith("#"))
        assert "measurer-caveats" in header
        assert "not every `true`" in header.lower()
