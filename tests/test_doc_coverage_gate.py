"""One coverage gate, and the two halves that make it worth having.

MEASURED WHEN IT LANDED (session #235): of the 53 commands the parser declares,
14 were named nowhere in `docs/ru/cli.md` and 14 nowhere in `docs/en/cli.md`.
Two of them — `graph` and `symbol` — had been shipped by this very release WITH
their own documentation pages, and still never reached the command reference.

WHAT THIS FILE ASSERTS, in the order that matters:
  * the gate goes RED on a real omission, naming what and where;
  * it stays GREEN on the live tree, because a gate red on day one is a gate
    switched off;
  * it does NOT fire on the shapes that make a coverage gate noise — a
    substring, a word in prose, an intentional historical mention.

WHY THERE IS ONE GATE AND NOT A TEST PER KIND. Before this, `doctor` had its own
hand-written coverage test, and every other kind of shipped name had none. Each
such test re-derives the same idea and each can go blind on its own — the doctor
one did, the day the optional checks moved into another module. The registry in
`gate_doc_coverage.COVERED` is now the place a new kind is added.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import gate_doc_coverage as gate  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "docs/"]


class TestTheGateGoesRedOnARealOmission:
    """The red proof. A gate that has forgotten how to fail passes its whole
    happy path and certifies nothing."""

    def test_a_command_missing_from_the_reference_is_refused(self, tmp_path, monkeypatch):
        (tmp_path / "docs" / "ru").mkdir(parents=True)
        (tmp_path / "docs" / "en").mkdir(parents=True)
        for lang in ("ru", "en"):
            (tmp_path / "docs" / lang / "cli.md").write_text(
                "# CLI\n\n```bash\nstatus\n```\n", encoding="utf-8"
            )
            (tmp_path / "docs" / lang / "doctor.md").write_text("# doctor\n", encoding="utf-8")
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status", "graph"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: [])

        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert "graph" in message, "the refusal must name WHAT is missing"
        assert "docs/ru/cli.md" in message, "and WHERE to write it"
        assert "status" not in message.split("cli.md")[1], "a documented command must not appear"

    def test_a_missing_document_is_itself_a_gap(self, tmp_path, monkeypatch):
        """A document that does not exist covers nothing, and silence about it
        would read exactly like full coverage."""
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: [])
        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert "cli.md" in message


class TestTheGateIsGreenOnTheLiveTree:
    """A gate red the day it lands gets switched off, and then it protects
    nothing while looking like it does."""

    def test_the_repository_passes(self):
        ok, message = gate.check(str(_REPO))
        assert ok, message


class TestItDoesNotFireOnTheShapesThatWouldMakeItNoise:
    """The half that decides whether anyone leaves it enabled."""

    @pytest.mark.parametrize(
        "document,name",
        [
            pytest.param("Use the database for storage.\n", "db", id="substring_of_a_word"),
            pytest.param("Look at the roadmap.\n", "at", id="a_common_short_word"),
            pytest.param("The configuration is read once.\n", "config", id="prose_form"),
        ],
    )
    def test_a_mere_substring_does_not_count_as_documentation(self, document, name):
        assert gate._mentions(document, name) is False, (
            f"{name!r} was 'found' inside prose — a coverage gate satisfied by "
            "substrings is green while covering nothing"
        )

    @pytest.mark.parametrize(
        "document",
        [
            pytest.param("```bash\ndb prune\n```\n", id="in_a_code_block"),
            pytest.param("Run `tausik db prune` to trim backups.\n", id="after_the_wrapper"),
            pytest.param("db prune            # trim backups\n", id="at_a_line_start"),
        ],
    )
    def test_a_real_mention_does_count(self, document):
        assert gate._mentions(document, "db") is True

    def test_a_doctor_label_is_matched_as_a_phrase_not_as_a_command(self):
        """Two styles on purpose: a line-anchored matcher would never find
        'Commit hooks' inside a sentence, and a substring matcher would let
        `db` pass on 'database'. One matcher for both is wrong somewhere."""
        text = "The doctor reports Commit hooks among its checks.\n"
        assert gate._named(text, "Commit hooks", "phrase") is True
        assert gate._named(text, "Commit hooks", "command") is False


class TestTheRegistryCannotGoBlind:
    """Each hand-written coverage test could stop seeing its own subject without
    anyone noticing. The doctor one did. These premises fail loudly instead."""

    def test_the_command_list_is_not_empty(self):
        commands = gate.cli_commands()
        assert len(commands) >= 40, f"suspiciously few commands parsed: {commands}"

    def test_the_doctor_labels_are_not_empty_and_include_ones_outside_the_handler(self):
        labels = set(gate.doctor_checks())
        # 20 until decision #358 retired the two brain labels (MCP server (brain), Brain config).
        assert len(labels) >= 18, f"suspiciously few labels parsed: {sorted(labels)}"
        for moved in ("Commit hooks", "Enforcement coverage", "Session model"):
            assert moved in labels, (
                f"{moved} is printed by doctor from OUTSIDE project_cli_doctor.py — "
                "the discovery must follow the code, not a path"
            )

    def test_an_unreadable_registry_reports_absence_rather_than_no_gaps(self, monkeypatch):
        """Decision #334. A registry we could not read says nothing about the
        documentation, so reporting 'everything is documented' would be a lie of
        exactly the kind this gate exists to catch."""
        monkeypatch.setattr(gate, "cli_commands", lambda: [])
        monkeypatch.setattr(gate, "doctor_checks", lambda: [])
        ok, _message = gate.check(str(_REPO))
        assert ok is True, "an empty registry must not be reported as a failure either"
        assert gate.find_gaps(str(_REPO)) == []


class TestTheDocsDoNotRestateACountByHand:
    """Kept from the test this gate replaced, because it is NOT coverage: the
    doctor docs said 'nine checks' for months while the command had eighteen
    labels. Some checks are conditional, so no fixed number is even correct."""

    _FORBIDDEN = re.compile(
        r"\b(nine|ten|eleven|twelve|девять|десять|одиннадцать|двенадцать)\s+"
        r"(checks|проверок|проверки)\b",
        re.IGNORECASE,
    )

    @pytest.mark.parametrize("lang", ["en", "ru"])
    def test_no_hand_written_check_count(self, lang):
        text = (_REPO / "docs" / lang / "doctor.md").read_text(encoding="utf-8")
        hit = self._FORBIDDEN.search(text)
        assert not hit, (
            f"doctor.md ({lang}) states a hand-written check count ({hit.group(0)!r}); "
            "list the checks instead — some are conditional, so no fixed number is right"
        )
