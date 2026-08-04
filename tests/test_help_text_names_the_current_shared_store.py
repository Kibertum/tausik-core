"""Help text names the store the code actually uses — and history keeps its own.

Decision #222 moved the shared store out of `~/.tausik/`, because a directory of
that name in the user's home captured project discovery for every path beneath
it. The code moved. Four CLI help strings and four docstrings did not, and help
text is read as an INSTRUCTION: a person told `~/.tausik/knowledge.db` goes
there, finds nothing, and concludes their entries were never saved.

The interesting half of this file is the third class. A defect phrased as "the
old path appears in the source" invites a blind sweep, and a blind sweep is
wrong here: the comment explaining WHY the store moved has to name the old path,
or it stops explaining anything. So the tests pull in opposite directions on
purpose — one forbids the old spelling where it misleads, the other requires it
where it informs. A sweep that satisfies the first by breaking the second turns
this file red rather than green.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Iterator

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import project_parser  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_db.py", "scripts/project_parser.py"]

_LEGACY_DISPLAY = "~/.tausik/knowledge.db"


def _all_help_strings(parser: argparse.ArgumentParser) -> Iterator[tuple[str, str]]:
    """Every help string in the tree, paired with where it came from.

    Reaches through `_actions`/`choices` — argparse exposes no public walk, and
    the alternative is asserting against a hand-written list of the four sites
    we happen to know about, which would pass while a fifth one lied.
    """
    yield (parser.prog, parser.description or "")
    for action in parser._actions:
        yield (f"{parser.prog} {'/'.join(action.option_strings) or action.dest}", action.help or "")
        if isinstance(action, argparse._SubParsersAction):
            # `sub.add_parser("knowledge", help="...")` does NOT put that string on
            # the sub-parser or in `choices` — argparse parks it on a pseudo-action
            # used only when rendering the parent's command list. Walking `choices`
            # alone therefore misses every SUBCOMMAND SUMMARY, which is the first
            # help a person reads. A probe caught this: deleting the path from the
            # `knowledge` summary left both tests green.
            for pseudo in getattr(action, "_choices_actions", ()):
                yield (f"{parser.prog} {pseudo.dest}", pseudo.help or "")
            for sub in action.choices.values():
                yield from _all_help_strings(sub)


def _destination_options() -> Iterator[tuple[str, str]]:
    """The options that SEND something to the shared store, found by shape.

    These are where the location has to be stated, because they are where a
    person decides. Recognised by `dest="to_global"` (both `--global` flags) and
    by carrying `global` among their choices (`brain move --scope`) — never by a
    list of the four sites we know about today, which would go quietly stale the
    moment a fifth destination appears.
    """
    for prog, action in _all_actions(project_parser.build_parser()):
        if isinstance(action, argparse._SubParsersAction):
            continue
        choices = action.choices or ()
        if action.dest == "to_global" or "global" in choices:
            yield (f"{prog} {'/'.join(action.option_strings) or action.dest}", action.help or "")


def _all_actions(parser: argparse.ArgumentParser) -> Iterator[tuple[str, argparse.Action]]:
    for action in parser._actions:
        yield (parser.prog, action)
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                yield from _all_actions(sub)


class TestTheCliNeverNamesTheOldPath:
    def test_no_help_string_in_the_whole_tree_names_it(self):
        offenders = [
            where
            for where, text in _all_help_strings(project_parser.build_parser())
            if _LEGACY_DISPLAY in text
        ]
        assert not offenders, (
            "CLI help still sends people to the store's old address, where there is "
            f"nothing: {offenders}"
        )

    def test_the_tree_was_actually_walked(self):
        """Guards the guard: a broken walk would report zero offenders forever."""
        seen = list(_all_help_strings(project_parser.build_parser()))
        assert len(seen) > 100, f"the walk collected only {len(seen)} help strings"
        assert any(t.startswith("Shared knowledge store") for _, t in seen), (
            "the walk never reached SUBCOMMAND SUMMARIES — the `help=` given to "
            "`add_parser` lives on `_choices_actions`, not on the sub-parser, so a "
            "walk over `choices` alone inspects everything except the first line a "
            "person reads. This assertion once checked `'knowledge' in where`, "
            "which passed while those summaries were entirely invisible."
        )


class TestHelpAgreesWithTheCode:
    def test_the_displayed_default_expands_to_the_path_that_is_opened(self, monkeypatch):
        """The one comparison that matters: words against behaviour."""
        monkeypatch.delenv(knowledge_db._HOME_ENV, raising=False)
        shown = os.path.normcase(
            os.path.normpath(os.path.expanduser(knowledge_db.default_store_display_path()))
        )
        opened = os.path.normcase(os.path.normpath(knowledge_db.knowledge_db_path()))
        assert shown == opened

    def test_the_display_path_is_derived_from_the_constant_not_repeated(self, monkeypatch):
        """AC2, stated mechanically: move the constant, the help must follow.

        A test asserting the literal `~/.tausik-knowledge/knowledge.db` would pass
        just as well against a hand-typed copy — and a hand-typed copy is exactly
        the defect. So the constant is changed to something no one would type by
        accident, and the output has to change with it.
        """
        monkeypatch.setattr(knowledge_db, "_HOME_DIRNAME", ".tausik-moved-again")
        assert knowledge_db.default_store_display_path() == "~/.tausik-moved-again/knowledge.db"

    def test_every_option_that_writes_to_the_shared_store_says_where_that_is(self):
        """Deleting the path from help would satisfy the first test too.

        Twice rewritten under probes, and both rewrites are the point. It began
        as `>= 3 occurrences`, and removing the path from one of four sites left
        three — green while a command had gone silent. Widened to "every help
        string mentioning the store", it demanded the full path inside `export`,
        `restore` and `import-brain`, which is not a contract but noise: those
        say what they DO, and the group they sit under already says where.

        What survives is the narrow true statement. A person is owed the location
        at the moment they choose to send knowledge there — nowhere else.
        """
        current = knowledge_db.default_store_display_path()
        silent = [where for where, text in _destination_options() if current not in text]
        assert not silent, (
            "these options send knowledge to the shared store without saying where "
            f"it lands — which passes the 'no old path' check by saying nothing: {silent}"
        )

    def test_the_command_group_about_the_store_says_where_the_store_is(self):
        """`tausik knowledge` is the one summary whose subject IS the location."""
        current = knowledge_db.default_store_display_path()
        summaries = [
            text
            for where, text in _all_help_strings(project_parser.build_parser())
            if where.endswith(" knowledge")
        ]
        assert summaries, "the `knowledge` command summary was not found at all"
        assert any(current in t for t in summaries), (
            f"`tausik knowledge` no longer names the store's location: {summaries}"
        )


class TestHistoryKeepsTheOldPath:
    """The negative scenario. Red iff a blind sweep 'fixed' the explanation."""

    def test_the_incident_comment_still_names_the_address_that_caused_it(self):
        src = io.open(knowledge_db.__file__, encoding="utf-8").read()
        assert "Creating `~/.tausik/knowledge.db` did it" in src, (
            "the comment explaining WHY the store moved was rewritten to the new "
            "path — it now says the current address caused the incident, which is "
            "false, and the reason for the move is lost"
        )

    def test_the_legacy_constant_still_holds_the_old_directory(self):
        """Adoption of an existing store reads this; a sweep must not touch it."""
        assert knowledge_db._LEGACY_HOME_DIRNAME == ".tausik"
