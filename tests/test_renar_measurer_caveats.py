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
import sys

import pytest

yaml = pytest.importorskip("yaml")

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from conftest import (  # noqa: E402
    DORMANT_ON_PUBLIC_SNAPSHOT,
    IS_PUBLIC_SNAPSHOT,
    projected_task_status,
)

from renar_measurer_caveats import (  # noqa: E402
    DISCLAIMER,
    MEASURER_CAVEATS,
    REGISTRY_EMPTIED_BY,
    caveated_clauses,
    caveats_section,
    header_lines,
)

# Reads the caveat registry, the committed manifest and the project DB; no
# import edge would otherwise select this test from a change to any of them.
CROSSCUTTING_SCOPE = ["scripts/", "RENAR-CONFORMANCE.yaml"]

MANIFEST = os.path.join(_ROOT, "RENAR-CONFORMANCE.yaml")
# No PROJECT_DB here any more. Both ratchets in this file read task status
# from the git-tracked `tausik/` projection, so they run in a bare checkout —
# which is where the manifest's disclosure ratchet has to hold.
REQUIRED_KEYS = {"clause", "measured-as", "why-degenerate", "open-task"}


def _manifest() -> dict:
    with open(MANIFEST, encoding="utf-8", newline="") as fh:
        return yaml.safe_load(fh)


def test_registry_is_either_populated_or_declared_empty():
    """An empty registry must be a PROVEN state, never a default.

    Every other check in this file is satisfied vacuously by an empty list, so
    emptiness is the one condition that cannot be left to speak for itself:
    "nothing disclosed" and "nothing to disclose" render identically in the
    manifest, and deleting the last entry is a one-line edit.

    Both original entries were retired by repairs, not by deletion — §13.3.3
    (renar_clause_reactive_adapt replaced the ADAPT row count) and §13.3.4 (the
    closed list reached the standard's eleven). So the registry is empty today,
    and REGISTRY_EMPTIED_BY must name the task that emptied it.
    """
    if MEASURER_CAVEATS:
        assert caveats_section(), "a non-empty registry must produce a section"
        assert REGISTRY_EMPTIED_BY is None, (
            "REGISTRY_EMPTIED_BY names the repair that emptied the registry; "
            "the registry is not empty, so it must be None"
        )
        return
    assert REGISTRY_EMPTIED_BY, (
        "the registry is empty and nothing says why. Emptying it is only "
        "legitimate as the result of a repair — name that task in "
        "REGISTRY_EMPTIED_BY, or restore the entry that was removed"
    )
    assert not caveats_section(), "an empty registry must produce no section"


def test_the_task_that_emptied_the_registry_is_real_and_underway():
    """The mirror of the ratchet on entries, and the half that gives it teeth.

    An entry must name a task that is still OPEN; the emptiness declaration must
    name one that is real and at least UNDERWAY. Without this half,
    REGISTRY_EMPTIED_BY could be any string and "a repair emptied it" would be
    as cheap as the deletion it exists to justify.

    Why `active` is accepted and not `done` alone: the change that empties the
    registry is the same change that closes the task, and it has to be GREEN
    before `task done` will run. Demanding `done` here makes the assertion
    unsatisfiable at exactly the moment it matters and green only afterwards —
    a test that can never be red for the change it governs. `planning` is
    refused: a task nobody has started has repaired nothing.
    """
    if MEASURER_CAVEATS:
        pytest.skip("registry is not empty")
    if IS_PUBLIC_SNAPSHOT:
        pytest.skip(DORMANT_ON_PUBLIC_SNAPSHOT)
    status = projected_task_status(REGISTRY_EMPTIED_BY)
    assert status is not None, (
        f"REGISTRY_EMPTIED_BY names task {REGISTRY_EMPTIED_BY!r}, which does not exist"
    )
    assert status in ("active", "done"), (
        f"task {REGISTRY_EMPTIED_BY!r} is {status!r} — the registry may not be "
        "emptied by a repair nobody has started"
    )


@pytest.mark.parametrize("caveat", MEASURER_CAVEATS, ids=lambda c: c["clause"])
def test_every_caveat_is_fully_stated(caveat):
    assert set(caveat) == REQUIRED_KEYS, f"unexpected/missing keys: {set(caveat) ^ REQUIRED_KEYS}"
    for key, value in caveat.items():
        assert value.strip(), f"{key} is empty — a caveat that says nothing discloses nothing"


@pytest.mark.parametrize("caveat", MEASURER_CAVEATS, ids=lambda c: c["clause"])
def test_named_task_exists_and_is_still_open(caveat):
    """The ratchet: a caveat may only stand while its fix is outstanding.

    Without this, `measurer-caveats` becomes the cheapest place in the codebase
    to park a defect forever — "disclosed" quietly replacing "fixed".
    """
    status = projected_task_status(caveat["open-task"])
    assert status is not None, (
        f"caveat for {caveat['clause']!r} names task {caveat['open-task']!r}, "
        "which does not exist — a disclosure pointing at nothing is not a disclosure"
    )
    assert status != "done", (
        f"task {caveat['open-task']!r} is closed — remove the caveat for "
        f"{caveat['clause']!r} in the same change that fixed its measurer"
    )


def test_header_paragraph_matches_the_registry_state():
    """The GENERATED header, not the committed file.

    The committed-manifest assertions further down read an artifact that was
    regenerated by hand, so a header that had stopped matching the registry
    would still look right there. Mutation testing proved it: forcing the
    "not every true is earned" branch on while the registry is empty left every
    file-reading assertion green. This calls the producer instead.
    """
    text = header_lines()
    lowered = text.lower()
    if MEASURER_CAVEATS:
        assert "not every `true`" in lowered
        assert "measurer-caveats" in lowered
    else:
        assert "not every `true`" not in lowered, (
            "the registry is empty, so the header must not claim unearned "
            "confirmations that no longer exist"
        )
        assert "is earned" in lowered
        # And it must not let "no caveats" be read as a conformance claim.
        assert "not a claim of" in lowered
        assert "conformance-declaration" in lowered


def test_disclaimer_refuses_to_be_mistaken_for_a_repair():
    lowered = DISCLAIMER.lower()
    assert "not a repair" in lowered
    assert "does not substitute" in lowered


class TestPublishedManifest:
    def test_section_matches_the_registry_including_when_it_is_empty(self):
        """The published section says exactly what the registry holds.

        An empty registry must publish NO section rather than an empty one: a
        `measurer-caveats:` key with nothing under it reads as "we looked and
        found none", which is a stronger claim than the data supports.
        """
        manifest = _manifest()
        section = manifest.get("measurer-caveats") or {}
        if not caveated_clauses():
            assert "measurer-caveats" not in manifest, (
                "the registry is empty, so the KEY must be absent, not present "
                f"and empty; found {section!r}"
            )
            return
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
        lowered = header.lower()
        if caveated_clauses():
            assert "not every `true`" in lowered
        else:
            # The empty state must not silently keep claiming unearned
            # confirmations, and must not let "no caveats" read as "conformant".
            assert "not every `true`" not in lowered
            assert "is earned" in lowered
            assert "not a claim of" in lowered
