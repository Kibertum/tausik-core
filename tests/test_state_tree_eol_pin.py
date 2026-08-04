"""The git-native state tree must survive a checkout unchanged.

`state_serialize.write_tree` emits LF only and `check_tree` reads the tree back
with universal-newline translation OFF, so anything that rewrites those files
with CRLF reads as corruption. On Windows `core.autocrlf=true` is the default,
and a checkout IS such a rewrite: without a `.gitattributes` pin every fresh
clone starts with a red `state export --check`.

The sibling `renar/` tree already carries that pin, with a comment naming this
exact failure. This module is what keeps the two from drifting apart again --
and, more to the point, what makes a SIXTH projected entity kind fail loudly
instead of silently landing outside the rule: the directories under test are
derived from the exporter's own registry (`state_serialize.ENTITY_DIRS`) and
from the resolver that picks the tree root (`project_cli_state._resolve_out_dir`),
never from a list retyped here.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_cli_state import _resolve_out_dir  # noqa: E402
from project_config import find_tausik_dir  # noqa: E402
from state_serialize import ENTITY_DIRS  # noqa: E402

_TIMEOUT = 60


def _git(cwd, *args):
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_TIMEOUT,
    )


def _project_root() -> str:
    return os.path.dirname(find_tausik_dir())


def _tree_rel_root() -> str:
    """`tausik`, asked of the resolver the CLI uses -- not spelled here."""
    return os.path.relpath(_resolve_out_dir(None), _project_root()).replace("\\", "/")


def _eol_attr(root: str, path: str) -> str:
    """The `eol` attribute git resolves for `path`, or "" when unset.

    `check-attr` answers for paths that need not exist, which is what lets this
    assert the rule covers a kind whose directory is still empty.
    """
    out = _git(root, "check-attr", "eol", "--", path).stdout.strip()
    # "<path>: eol: lf" -- the value is the last colon-separated field.
    return out.rsplit(":", 1)[-1].strip() if out else ""


def _pinned_paths() -> list[str]:
    """One representative file per directory the exporter claims as its own."""
    rel = _tree_rel_root()
    return [f"{rel}/README.md"] + [f"{rel}/{kind}/probe.md" for kind in ENTITY_DIRS]


@pytest.mark.skipif(not _git(".", "--version").stdout, reason="git unavailable")
class TestTreeIsPinned:
    def test_every_projected_directory_resolves_to_lf(self):
        """AC-1/AC-2: coverage is asserted over the REGISTRY, not a retyped list.

        A sixth entry in `ENTITY_DIRS` with no matching rule fails here, which is
        the whole point: the previous two derived trees each drifted because the
        thing that had to be updated was a hand-kept list somewhere else.
        """
        root = _project_root()
        unpinned = [p for p in _pinned_paths() if _eol_attr(root, p) != "lf"]
        assert not unpinned, (
            f"not pinned to LF in .gitattributes: {unpinned}. Every directory the "
            f"state export owns must be pinned, or a Windows checkout corrupts it."
        )

    def test_registry_is_non_empty(self):
        """Guards the guard: an empty registry would make the sweep vacuous."""
        assert ENTITY_DIRS, "ENTITY_DIRS empty -- the coverage sweep would assert nothing"
        assert len(_pinned_paths()) == len(ENTITY_DIRS) + 1

    def test_pin_does_not_reach_outside_the_tree(self):
        """AC-4 boundary: the rule must not reformat unrelated tracked files.

        `renar-tree-gitattributes-lf` refused a blanket `* eol=lf` for this
        reason; the same refusal has to stay verifiable.
        """
        root = _project_root()
        for outside in ("CHANGELOG.md", "README.md", "scripts/state_serialize.py"):
            assert _eol_attr(root, outside) != "lf", (
                f"{outside} picked up an eol=lf pin -- the rule leaked outside the "
                f"derived tree and will reformat files it does not own."
            )


@pytest.mark.skipif(not _git(".", "--version").stdout, reason="git unavailable")
class TestPinSurvivesACheckout:
    """AC-3: proven against real git, not against the attribute string.

    `check-attr` says what git *intends*; only a checkout says what git *does*.
    Both branches live in one test on purpose -- the control file establishes
    that this sandbox really does convert, so a green result cannot come from a
    sandbox where `autocrlf` never fired.
    """

    def _origin(self, tmp_path):
        origin = tmp_path / "origin"
        rel = _tree_rel_root()
        (origin / rel / "tasks").mkdir(parents=True)
        # The REAL rule, copied byte-for-byte -- a retyped rule would test itself.
        shipped = os.path.join(_project_root(), ".gitattributes")
        with open(shipped, "rb") as fh:
            (origin / ".gitattributes").write_bytes(fh.read())
        (origin / rel / "tasks" / "probe.md").write_bytes(b"---\nslug: probe\n---\n\nbody\n")
        (origin / "control.md").write_bytes(b"# control\n\nbody\n")
        _git(origin, "init", "-q", "-b", "main")
        _git(origin, "config", "user.email", "a@b.c")
        _git(origin, "config", "user.name", "t")
        _git(origin, "config", "core.autocrlf", "false")
        _git(origin, "add", "-A")
        _git(origin, "commit", "-qm", "seed")
        return origin

    def test_tree_stays_lf_while_an_unpinned_file_converts(self, tmp_path):
        origin = self._origin(tmp_path)
        dst = tmp_path / "clone"
        subprocess.run(
            ["git", "-c", "core.autocrlf=true", "clone", "-q", origin.as_uri(), str(dst)],
            capture_output=True,
            timeout=120,
        )
        rel = _tree_rel_root()
        with open(dst / rel / "tasks" / "probe.md", "rb") as fh:
            projected = fh.read()
        with open(dst / "control.md", "rb") as fh:
            control = fh.read()

        # PREMISE first: without it a broken pin would still pass, because a
        # sandbox that never converts anything makes the real assertion vacuous.
        assert b"\r\n" in control, (
            "control file did not become CRLF -- autocrlf never fired in this "
            "sandbox, so this test proves nothing about the pin"
        )
        assert b"\r\n" not in projected, (
            "a file in the state tree became CRLF on checkout -- the pin is not "
            "in effect, and `state export --check` will be red on a fresh clone"
        )
