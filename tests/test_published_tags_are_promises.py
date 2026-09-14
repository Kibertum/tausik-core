"""A published tag is a promise, and this is where the promise is checked.

tags-diverged-between-the-public-and-the-private-line. Measured in session #233
by asking both remotes rather than recalling #181:

    public (github)  9 tags     private (origin) 17     local 22
    only on origin   9          only on github    1
    names on BOTH    8 — and ALL EIGHT point at different objects. None agree.

`v1.8.0` is `623fb4ee` on the public line and `3866702f` on the private one. The
README tells consumers to add this repository as a git submodule, and a submodule
is pinned by SHA or by tag; so the same release name addresses two different
trees depending on which remote a consumer used.

THE QUESTION THE TASK REQUIRED BE ANSWERED FIRST — is a tag a promise to a
consumer or an internal bookmark — is answered by the README and by git itself: a
submodule pins against it, `git fetch --tags` refuses to clobber it, and this
project's firewall already refuses force-push on the same reasoning. It is a
promise. So published tags are never moved, the thirteen missing ones are not
backfilled, and the divergence is DECLARED and held here.

WHAT THIS FILE DOES NOT DO is repair the past. Eight names will keep addressing
two trees; that is recorded in docs/{ru,en}/publishing.md so a consumer can find
out, rather than being silently corrected into a different tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import publication_scope as ps  # noqa: E402

CROSSCUTTING_SCOPE = ["tausik/published_tags.json", "scripts/publication_scope.py"]

_SNAPSHOT = _REPO / "tausik" / "published_tags.json"
_PUBLIC_REMOTE = "github"


def _baseline() -> dict[str, str]:
    doc = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    return dict(doc["tags"])


class TestTheSnapshotIsUsable:
    """PREMISE. An empty or malformed baseline would pass every comparison."""

    def test_it_exists_and_names_how_it_was_taken(self):
        assert _SNAPSHOT.is_file(), f"{_SNAPSHOT} is missing — 'no tag moved' is unprovable"
        doc = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
        assert doc.get("_how_taken"), "a snapshot without its method cannot be re-taken"
        assert doc.get("_taken_at"), "a snapshot without a date cannot be aged"
        assert doc.get("_remote"), "a snapshot must say which line it describes"

    def test_it_holds_the_published_tags(self):
        tags = _baseline()
        assert len(tags) >= 9, f"only {len(tags)} tags in the baseline"
        for name, sha in tags.items():
            assert name.startswith("v"), name
            assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha), (name, sha)


class TestNoPublishedTagHasMoved:
    """AC3 and AC5. Compared against the remote, not against intention."""

    def test_the_public_line_still_names_the_same_objects(self):
        try:
            live = ps.remote_tag_map(_PUBLIC_REMOTE)
        except ps.RemoteUnreachable as exc:
            pytest.skip(
                f"the public remote could not be asked ({exc}). SKIPPED, not passed: "
                "a check that goes green without reaching the remote asserts "
                "something it never measured (decision #334)."
            )
        ok, message = ps.tags_unmoved(_baseline(), live)
        assert ok, (
            f"{message}\n\nA published tag is a pin in somebody's submodule. Moving, "
            "deleting or adding one changes what a consumer checks out without "
            "telling them. If a tag was published deliberately, re-take the "
            "snapshot in tausik/published_tags.json in the same commit."
        )


class TestAnUnreachableRemoteIsNotAGreen:
    """AC4. The failure mode this whole release is about, in one check."""

    def test_it_skips_rather_than_passes(self, monkeypatch):
        def _unreachable(remote, timeout=30):
            raise ps.RemoteUnreachable("simulated")

        monkeypatch.setattr(ps, "remote_tag_map", _unreachable)
        with pytest.raises(BaseException) as excinfo:
            TestNoPublishedTagHasMoved().test_the_public_line_still_names_the_same_objects()
        assert excinfo.typename == "Skipped", (
            "an unreachable remote produced something other than a skip — if it "
            "produced a pass, the check reports a promise it did not verify"
        )

    def test_an_empty_answer_is_not_treated_as_agreement(self):
        """The trap the exception exists to close: `{}` compares equal to `{}`,
        so a remote that answered nothing would read as 'nothing moved'."""
        ok, message = ps.tags_unmoved(_baseline(), {})
        assert not ok and "vanished" in message


class TestMovementIsDetectedInAllThreeDirections:
    """`tags_unmoved` already says so; this pins it against THIS baseline."""

    def test_a_changed_object_is_movement(self):
        live = _baseline()
        name = sorted(live)[0]
        live[name] = "0" * 40
        ok, message = ps.tags_unmoved(_baseline(), live)
        assert not ok and name in message

    def test_a_vanished_tag_is_movement(self):
        live = _baseline()
        name = sorted(live)[-1]
        del live[name]
        ok, message = ps.tags_unmoved(_baseline(), live)
        assert not ok and "vanished" in message

    def test_a_new_tag_is_movement_too(self):
        """Not an error to publish one — but it must be recorded in the snapshot
        in the same commit, or the baseline stops describing the public line."""
        live = _baseline()
        live["v9.9.9"] = "f" * 40
        ok, message = ps.tags_unmoved(_baseline(), live)
        assert not ok and "appeared" in message


class TestTheDivergenceIsDeclaredWhereAConsumerWouldLook:
    def test_both_language_pages_state_the_rule_and_the_numbers(self):
        for rel in ("docs/ru/publishing.md", "docs/en/publishing.md"):
            text = (_REPO / rel).read_text(encoding="utf-8")
            assert "v1.8.0" in text, f"{rel} does not show the divergence by example"
            assert "623fb4ee" in text and "3866702f" in text, (
                f"{rel} names the tag but not the two objects it resolves to — the "
                "example is what makes the problem checkable by a reader"
            )
            assert "published_tags.json" in text, (
                f"{rel} does not point at the snapshot that holds the promise"
            )
