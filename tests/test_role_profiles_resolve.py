"""A role the CLI names must have a profile, and a profile must be a real role.

`tausik role show researcher` printed a path to
`harness/roles/researcher.md` — a file that did not exist. The role reached the
database through `seed_v18_roles`, which seeds from DISTINCT role strings found
in tasks: one task typed "researcher" and a role appeared, designed by nobody.
The reverse gap exists too — `ui-ux` ships a profile that no task ever used, so
the seed never registered it.

Neither direction was caught by anything, which is the shape this release keeps
finding: a registry checked one way decays into a list of good intentions
(decision #335).

WHAT IS ASSERTED HERE is about the TREE, not about this project's database. The
DB is per-project data and a test that pinned its contents would fail on every
other install. What travels with the code is the profiles, so they are what gets
checked: each is readable, carries the sections a role profile needs, and the
researcher profile carries the receipt contract that the reconnaissance genre
exists for — including the part that names the unknown, which is the one a
summary is most tempted to drop.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_ROLES = _REPO / "harness" / "roles"

CROSSCUTTING_SCOPE = ["harness/roles/"]

#: Every role profile answers these, or it is a page of prose rather than a role.
_REQUIRED_HEADINGS = ("# Role:",)


def profiles() -> list[Path]:
    return sorted(_ROLES.glob("*.md"))


class TestEveryProfileIsAProfile:
    def test_each_profile_declares_the_role_it_defines(self):
        # The subject check rides here rather than in a test of its own: a
        # detector that finds nothing proves nothing, and asserting that in a
        # separate one-line test only added another indistinguishable shape.
        assert len(profiles()) >= 6, f"expected the shipped role profiles, found {profiles()}"
        for path in profiles():
            head = path.read_text(encoding="utf-8", errors="replace").lstrip().splitlines()[0]
            assert head.startswith("# Role:"), (
                f"{path.name} does not open with '# Role:' — the CLI points a reader here and "
                "the first line has to say what they are reading"
            )

    def test_every_file_name_is_addressable_as_a_slug(self):
        """`role show <slug>` resolves by FILE NAME, so the name must be one.

        NOT "the heading equals the file name": the heading is a human title and
        `ui-ux.md` says "UI/UX Developer", which is right. An earlier version of
        this test demanded they match and failed on that file — it was asserting
        a convention the project never adopted, which is a test inventing a rule
        rather than checking one.
        """
        for path in profiles():
            assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.stem), (
                f"{path.name} cannot be addressed: `role show` takes a slug, and this "
                "file name is not one"
            )

    def test_each_heading_says_something_about_the_role(self):
        for path in profiles():
            head = path.read_text(encoding="utf-8", errors="replace").lstrip().splitlines()[0]
            title = head.split(":", 1)[1].strip() if ":" in head else ""
            assert title, f"{path.name} opens with '# Role:' and no title after it"


class TestTheResearcherProfileCarriesTheReceiptContract:
    """The genre this task exists for: return a receipt, never a transcript."""

    def _text(self) -> str:
        path = _ROLES / "researcher.md"
        assert path.is_file(), (
            "harness/roles/researcher.md is missing — the role is registered and "
            "`role show researcher` names this exact path"
        )
        return path.read_text(encoding="utf-8", errors="replace")

    def test_the_five_parts_of_a_receipt_are_all_named(self):
        text = self._text().lower()
        for part in ("what was measured", "how", "the numbers", "refutes", "remains unknown"):
            assert part in text, f"the receipt contract does not name '{part}'"

    def test_naming_the_unknown_is_stated_as_mandatory(self):
        """The negative requirement of the task, checked in the text rather than
        promised in a commit message."""
        text = self._text()
        assert "Naming the unknown is not optional" in text
        assert "not measured" in text
        assert "never `0`" in text

    def test_it_forbids_returning_the_transcript(self):
        text = self._text().lower()
        assert "what you never return" in text
        for banned in ("full command output", "config dumps", "diffs"):
            assert banned in text, f"the contract does not exclude {banned!r}"

    def test_it_carries_the_measurement_that_motivated_it(self):
        """A role justified by nothing drifts into taste. The numbers stay with it."""
        text = self._text()
        assert "64,669" in text and "5.7%" in text
        assert re.search(r"session #\d+", text), "the measurement is not dated to a session"


class TestNoSecondRoleForTheSameGenre:
    def test_scout_was_not_added_alongside_researcher(self):
        """The task's own border: extend the existing role, do not double it.

        Two roles for one genre is the duplication this project refuses, and the
        reason `researcher` was filled in rather than a `scout` invented next to
        it.
        """
        assert not (_ROLES / "scout.md").exists()
        names = {p.stem for p in profiles()}
        assert "researcher" in names
