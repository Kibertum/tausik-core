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

import json
import hashlib
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
    happy path and certifies nothing.

    The CLI reference is a GROUP of pages, and a group is exactly the shape that can make a
    coverage gate green by construction: enough pages, and some page mentions every word.
    So the group is what these tests attack — a command on none of them, a page missing from
    it, and one language documented while the other is not.
    """

    @staticmethod
    def _plant(root, *, ru, en, drop=()):
        """Write both groups, with `ru` / `en` the commands documented in each.

        Every page of the group is written, because a page left out is a DIFFERENT failure —
        the one `test_a_page_of_the_group_that_is_absent_is_a_gap` is about — and a test that
        confused the two would go green on either.
        """
        pages = {}
        for group, documented in ((gate.CLI_PAGES_RU, ru), (gate.CLI_PAGES_EN, en)):
            for rel in group:
                pages[rel] = "# CLI\n"
            pages[group[-1]] = "# CLI\n\n```bash\n" + "\n".join(documented) + "\n```\n"
        for lang in ("ru", "en"):
            pages[f"docs/{lang}/doctor.md"] = "# doctor\n\nCommit hooks\n"
        for rel in drop:
            pages.pop(rel)
        for rel, text in pages.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_a_command_on_no_page_of_the_group_is_refused(self, tmp_path, monkeypatch):
        self._plant(tmp_path, ru=["status"], en=["status"])
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status", "graph"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert "graph" in message, "the refusal must name WHAT is missing"
        assert "docs/ru/cli.md" in message, "and WHERE to write it"
        assert "status" not in message, "a documented command must not be reported missing"

    def test_a_command_documented_on_any_one_page_of_the_group_counts(self, tmp_path, monkeypatch):
        """The point of the group: `hygiene` lives on the maintenance page and nowhere else,
        and demanding it on all five would put every command back on every page — which is
        how the reference grew to 899 lines with a section named for what did not fit."""
        self._plant(tmp_path, ru=["hygiene"], en=["hygiene"])
        monkeypatch.setattr(gate, "cli_commands", lambda: ["hygiene"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.check(str(tmp_path))
        assert ok is True, message

    def test_a_page_of_the_group_that_is_absent_is_a_gap(self, tmp_path, monkeypatch):
        """Reading around a missing page would shrink the group in silence, and the gate
        would then certify coverage against whatever pages happened to survive."""
        gone = gate.CLI_PAGES_RU[1]
        self._plant(tmp_path, ru=["status"], en=["status"], drop=(gone,))
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert gone in message, "the refusal names the page that is not there"

    def test_the_two_languages_do_not_cover_for_each_other(self, tmp_path, monkeypatch):
        """Groups are joined WITHIN a language and never across one. A gate that pooled both
        would call a command documented once in Russian documented in English too, which is
        the drift a per-language check caught before."""
        self._plant(tmp_path, ru=["graph"], en=[])
        monkeypatch.setattr(gate, "cli_commands", lambda: ["graph"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert "docs/en/" in message
        assert "docs/ru/" not in message, "the language that documented it is not accused"

    def test_a_missing_document_outside_a_group_is_itself_a_gap(self, tmp_path, monkeypatch):
        """A document that does not exist covers nothing, and silence about it
        would read exactly like full coverage."""
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])
        ok, message = gate.check(str(tmp_path))
        assert ok is False
        assert "cli.md" in message


class TestTheGateIsGreenOnTheLiveTree:
    """A gate red the day it lands gets switched off, and then it protects
    nothing while looking like it does."""

    def test_the_repository_passes(self):
        ok, message = gate.check(str(_REPO))
        assert ok, message


class TestCodexConsumerProjectionIsNotTheFrameworkSourceTree:
    def test_deployed_codex_profile_does_not_require_undelivered_framework_docs(
        self, tmp_path, monkeypatch
    ):
        profile = tmp_path / ".codex"
        scripts = profile / "scripts"
        hooks = scripts / "hooks"
        hooks.mkdir(parents=True)
        adapters = {}
        for name in gate._CODEX_PROJECTION_ADAPTERS:
            payload = f"adapter:{name}".encode()
            (hooks / name).write_bytes(payload)
            adapters[name] = hashlib.sha256(payload).hexdigest()
        (profile / "tausik-capability.json").write_text(
            json.dumps(
                {
                    "capability_version": 5,
                    "adapters": adapters,
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(gate, "_HERE", str(scripts))

        ok, message = gate.run_doc_coverage_gate({}, [])

        assert ok is True
        assert "consumer Codex projection" in message

    def test_deployed_cursor_profile_does_not_require_undelivered_framework_docs(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.syspath_prepend(str(_REPO / "bootstrap"))
        from bootstrap_copy import copy_scripts
        from bootstrap_generate import generate_cursor_hooks_json

        profile = tmp_path / ".cursor"
        profile.mkdir()
        copy_scripts(str(_REPO), str(profile))
        generate_cursor_hooks_json(str(tmp_path), str(profile), venv_python=sys.executable)
        monkeypatch.setattr(gate, "_HERE", str(profile / "scripts"))

        ok, message = gate.run_doc_coverage_gate({}, [])

        assert ok is True
        assert "consumer Cursor projection" in message

    @pytest.mark.parametrize(
        "manifest",
        [
            {},
            {"capability_version": 5, "adapters": {}},
            {
                "capability_version": True,
                "adapters": {name: "0" * 64 for name in gate._CODEX_PROJECTION_ADAPTERS},
            },
            {
                "capability_version": 5,
                "adapters": {name: "0" * 64 for name in gate._CODEX_PROJECTION_ADAPTERS},
            },
        ],
    )
    def test_forged_or_incomplete_capability_does_not_bypass_gate(
        self, tmp_path, monkeypatch, manifest
    ):
        profile = tmp_path / ".codex"
        scripts = profile / "scripts"
        scripts.mkdir(parents=True)
        (profile / "tausik-capability.json").write_text(json.dumps(manifest), encoding="utf-8")
        monkeypatch.setattr(gate, "_HERE", str(scripts))
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.run_doc_coverage_gate({}, [])

        assert ok is False
        assert "docs/en/cli.md" in message

    def test_missing_source_docs_still_fail_when_no_projection_attestation(
        self, tmp_path, monkeypatch
    ):
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        monkeypatch.setattr(gate, "_HERE", str(scripts))
        monkeypatch.setattr(gate, "cli_commands", lambda: ["status"])
        monkeypatch.setattr(gate, "doctor_checks", lambda: ["Commit hooks"])

        ok, message = gate.run_doc_coverage_gate({}, [])

        assert ok is False
        assert "docs/en/cli.md" in message


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

    @pytest.mark.parametrize("missing", ["cli_commands", "doctor_checks"])
    def test_an_unreadable_registry_fails_closed(self, monkeypatch, missing):
        """Decision #334. A registry we could not read says nothing about the
        documentation, so reporting 'everything is documented' would be a lie of
        exactly the kind this gate exists to catch."""
        monkeypatch.setattr(gate, missing, lambda: [])

        ok, message = gate.check(str(_REPO))

        assert ok is False
        assert "<the registry itself>" in message
        assert missing in message


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
