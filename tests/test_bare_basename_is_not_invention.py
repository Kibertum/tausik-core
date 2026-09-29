"""A citation written without its directory is not an accusation of fabrication.

THE DEFECT. The evidence audit resolved a citation LITERALLY, so a reference written as
`test_brain_config.py` instead of `tests/test_brain_config.py` matched no path in history and
earned the verdict NEVER_EXISTED — which says a past closure INVENTED its evidence. Measured:
of 39 such findings, 27 named files git had.

WHY THIS DIRECTION OF ERROR IS THE EXPENSIVE ONE. An undeserved charge of fabrication devalues
the whole register, and a reader who has been wrong-footed once starts skimming all of it —
the very mechanism that already forced this project to declare a remainder rather than carry a
standing HIGH. Missing one real invention costs less than losing the register.

WHAT THE MEASUREMENT DECIDED. 718 bare occurrences across 276 tasks against 6682 with a
directory. At that spread the resolver is what is wrong, not the citations; and the journal is
append-only, so rewriting them was never available. Hence the widening below — with the two
refusals that keep it from becoming divination.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]

# These cases read THIS repository's own history as their fixture (a file deleted long
# ago, conftest.py in six directories). A shallow CI clone does not have it, so they run
# where the history is: a full local checkout.
import subprocess  # noqa: E402

_SHALLOW = (
    subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        stdin=subprocess.DEVNULL,
    ).stdout.strip()
    == "true"
)
needs_history = pytest.mark.skipif(
    _SHALLOW, reason="shallow clone: this fixture is the repo's own history"
)
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

from audit_closure_evidence import (  # noqa: E402
    AMBIGUOUS_NAME,
    NEVER_EXISTED,
    ROTTED,
    UNKNOWN_HISTORY,
    _history_verdict,
    git_dirs_that_ever_held,
)


def _no_literal_match(repo_root: str, rel: str, name: str | None) -> bool | None:
    """A probe that finds nothing, which is the state the bug lived in."""
    return False


#: One row per citation shape, with the verdict it must earn and why. A table rather than a
#: test apiece: all three read one verdict and compare it, which is the same shape three times
#: — the dedupe ratchet counts that, and it is right to.
_SHAPES = (
    (
        "test_brain_config.py",
        ROTTED,
        "AC-2: written without its directory, but git HAD it under tests/ and deleted it — "
        "that is rot, not invention",
    ),
    (
        "test_this_was_never_written_anywhere.py",
        NEVER_EXISTED,
        "AC-3, THE ONE THAT MATTERS: a widening that resolved everything would read as a clean "
        "register and check nothing, which is the failure this module was written against",
    ),
    (
        "tests/test_brain_config.py",
        NEVER_EXISTED,
        "a path written out in full is checked LITERALLY on purpose: resolving it by its "
        "basename would erase the difference between a wrong directory and a missing file",
    ),
)


@needs_history
@pytest.mark.parametrize("citation,expected,why", _SHAPES, ids=lambda v: str(v)[:40])
def test_the_verdict_matches_the_shape_of_the_citation(citation, expected, why):
    assert _history_verdict(_no_literal_match, str(_REPO), citation, None) == expected, why


@needs_history
def test_a_name_from_several_directories_is_ambiguous_not_a_match():
    """AC-4: two directories mean the citation is unresolved, not resolved to a guess.

    `conftest.py` has lived in six directories in this repository's history. Picking one
    would print a confirmed citation the reader cannot check — "something similar was found"
    dressed as "this matched".
    """
    dirs = git_dirs_that_ever_held(str(_REPO), "conftest.py")
    assert dirs is not None and len(dirs) > 1, dirs
    assert _history_verdict(_no_literal_match, str(_REPO), "conftest.py", None) == AMBIGUOUS_NAME


def test_a_path_with_a_directory_is_never_widened():
    """The widening applies ONLY to a bare name: a written-out path was checked literally
    on purpose, and resolving `tests/nope.py` by its basename would erase the distinction
    between a wrong directory and a missing file."""
    assert (
        _history_verdict(_no_literal_match, str(_REPO), "tests/test_brain_config.py", None)
        == NEVER_EXISTED
    )


def test_git_failing_is_unknown_not_a_verdict():
    """An unanswerable question is not an answer — the project's rule since decision #157."""

    def broken(repo_root: str, rel: str, name: str | None) -> bool | None:
        return None

    assert _history_verdict(broken, str(_REPO), "test_brain_config.py", None) == UNKNOWN_HISTORY
    assert _history_verdict(None, str(_REPO), "whatever.py", None) == UNKNOWN_HISTORY


@needs_history
@pytest.mark.parametrize(
    "name,expect_empty",
    [("test_brain_config.py", False), ("test_absolutely_not_a_real_file_xyz.py", True)],
)
def test_the_resolver_can_both_find_and_not_find(name, expect_empty):
    """The premise. A resolver that always returned [] would make every test above pass
    while calling every bare citation an invention again."""
    dirs = git_dirs_that_ever_held(str(_REPO), name)
    assert dirs is not None
    assert (dirs == []) is expect_empty, dirs
