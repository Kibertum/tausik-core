"""No module in the CLI family is named after what would not fit elsewhere.

MEASURED before the split: the family held 33 modules and 31 were named after a command
or a domain. The two exceptions were `project_cli_ops.py` and `project_cli_extra.py`,
and the first one's own docstring admitted it — "NOT a domain. This module is the residue
of repeated bleeding to satisfy the filesize gate". Three other modules carried the same
confession in their headers: "extracted from project_cli_ops for filesize gate", "kept
out of project_cli_ops.py (400-line gate)", "extracted from project_cli_ops.py to keep it
under the filesize gate".

A residue drawer is not a naming problem. It is where the next command lands when nobody
has decided where it belongs, and it grows until a line limit pushes something out at
random. So the shape is checked rather than remembered, in two ways: the NAME must not be
a drawer word, and the first line of the docstring must name a home instead of listing
what is inside (convention #348 — a bad cut shows in the docstring, which enumerates
entities instead of naming the house they share).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"

#: The guarded prefix must be a real path, not a filename stem: the registry checks that
#: declared scopes still exist so a rename cannot leave a test guarding nothing. The
#: whole tree is the honest declaration here — this file reads EVERY `project_cli_*`
#: module, so any new one must pull it in.
CROSSCUTTING_SCOPE = ["scripts/"]

#: Words that name a leftover rather than a subject. `extra` and `ops` are here because
#: they WERE the two exceptions; the rest are the shapes the same habit takes next.
DRAWER_WORDS = frozenset(
    {"ops", "extra", "misc", "other", "others", "util", "utils", "helpers", "common", "stuff"}
)

#: A first docstring line that enumerates commands. Three or more comma-separated
#: fragments in one sentence is the signature of a list, not of a name.
_ENUMERATION = re.compile(r"^[^.]*?,[^.]*?,[^.]*?,")


def family() -> list[Path]:
    return sorted(p for p in _SCRIPTS.glob("project_cli_*.py") if p.is_file())


def test_the_family_is_not_empty():
    """A guard over an empty glob passes forever."""
    assert len(family()) >= 20, [p.name for p in family()]


@pytest.mark.parametrize("path", family(), ids=lambda p: p.stem)
def test_no_module_is_named_after_a_drawer(path):
    stem = path.stem.removeprefix("project_cli_")
    parts = set(stem.split("_"))
    offending = parts & DRAWER_WORDS
    assert not offending, (
        f"{path.name} is named after a leftover ({sorted(offending)}). A module named for "
        "what did not fit is where the next command lands when nobody decided where it "
        "belongs — name the subject instead."
    )


@pytest.mark.parametrize("path", family(), ids=lambda p: p.stem)
def test_the_docstring_names_a_home_not_a_list(path):
    """Convention #348: a bad cut is visible in the docstring before it is in the code."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc = ast.get_docstring(tree) or ""
    assert doc.strip(), f"{path.name} has no docstring, so it claims no subject at all"
    first = doc.splitlines()[0]
    assert not _ENUMERATION.match(first), (
        f"{path.name} opens by listing three or more things: {first!r}. Name the house they "
        "share; if they share none, they belong in different modules."
    )


class TestTheGuardWouldCatchARegression:
    """Mutation, because a rule that cannot fail is decoration.

    Both halves are provoked on throwaway text rather than on the tree, so proving the
    guard has teeth costs nothing and leaves nothing to undo.
    """

    @pytest.mark.parametrize("stem", ["project_cli_ops", "project_cli_extra", "project_cli_misc"])
    def test_a_drawer_name_is_recognised(self, stem):
        parts = set(stem.removeprefix("project_cli_").split("_"))
        assert parts & DRAWER_WORDS, stem

    def test_a_domain_name_is_not_recognised_as_a_drawer(self):
        """NEGATIVE: the real names must pass, or the rule is unusable."""
        for stem in ("project_cli_task", "project_cli_verify", "project_cli_knowledge"):
            assert not set(stem.removeprefix("project_cli_").split("_")) & DRAWER_WORDS, stem

    def test_an_enumerating_docstring_is_recognised(self):
        assert _ENUMERATION.match("TAUSIK CLI handlers — memory, gates, skill, fts, claudemd.")
        assert _ENUMERATION.match("Handlers with no module of their own — hud, search, doc, run.")

    def test_a_naming_docstring_is_not_recognised(self):
        """NEGATIVE: a sentence may contain commas and still name one subject."""
        for line in (
            "The current session: what it is, what it advises, and its numbers.",
            "Reading and writing what the project knows.",
            "Gate state: what is enabled and what it costs.",
        ):
            assert not _ENUMERATION.match(line), line
