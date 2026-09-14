"""No control may quietly stop running because a checkout has no database.

WHAT THIS EXISTS TO PREVENT, MEASURED IN SESSION #203. `.tausik/` is gitignored
and `bootstrap.py` — CI's only preparation step — does not create the project
database; both verified by running the CI steps in a clean `git worktree`. Every
control that opened `.tausik/tausik.db` therefore skipped in CI, and skipped
SILENTLY: eleven test instances across four files, among them the very ratchet
that `RENAR-CONFORMANCE.yaml` names as the reason a published `true` is safe.

It was not even consistent. Some test in the suite creates that database in the
repository root as it runs, so a gated control ran or skipped depending on
whether it happened to be scheduled before or after — under `-n auto` and random
order, a coin toss. A ratchet that sometimes measures nothing and always reports
green is worse than one switched off, because the green gets believed.

Three of the four files were moved onto git-tracked sources and now run
everywhere. What is left is the genuinely working-copy family: controls whose
SUBJECT is the live copy, which a bare checkout does not have. Those are allowed
to be dormant — and must say so, in the roster below, in the words of one shared
constant.

WHY THE SCAN IS SYNTACTIC AND NOT A GREP. The claudemd group hid for exactly the
length of a grep: it worded its skip differently from the renar group, so a
search for one phrase found three sites and missed seven. This walks the AST and
asks a structural question — does this skip's condition mention the project
database — which no rewording changes.
"""

from __future__ import annotations

import ast
import os

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

#: This file's subject is the tests/ tree itself — it imports no product module
#: and shares a basename with none, so change-based selection would never reach
#: it. Declared rather than left implicit: a roster nobody runs is the same
#: silence it exists to end, which the crosscutting registry ratchet said out
#: loud the first time this file was added.
CROSSCUTTING_SCOPE = ["tests/"]

#: Markers that identify a condition as "does the project database exist".
#: Deliberately about the SUBJECT, not about any one spelling of it.
_DB_MARKERS = ("tausik.db", "PROJECT_DB")

#: The name every dormant-allowed site must cite as its reason.
_REASON_NAME = "DORMANT_WITHOUT_LIVE_DB"

#: The roster: controls whose subject IS the live working copy, so a bare
#: checkout has nothing for them to measure. Each entry is a standing claim that
#: the control CANNOT be moved onto git — not that moving it was inconvenient.
#: A new gated control fails this test until someone puts it here on purpose.
ALLOWED_DORMANT: dict[str, set[str]] = {
    # Compares the COMMITTED manifest against what the live database yields.
    # There is no git-side answer: the question is whether this working copy has
    # drifted from its own artifact.
    "test_renar_manifest_artifact.py": {"test_committed_manifest_is_not_stale"},
    # End-to-end runs of the CLAUDE.md state gate against THIS repository. The
    # gate reads the live database by design; a synthetic one would test the
    # fixture. Their unit-level siblings in the same file are not gated and do
    # run in CI.
    "test_claudemd_state_gate.py": {
        # `test_no_database_skips` is deliberately NOT here. It reads as gated —
        # its body names the database — but it asserts on the gate's MESSAGE and
        # never stands down. The mirror duty below caught it in this roster on
        # the first run, which is the whole argument for keeping that duty.
        "test_the_gate_is_green_end_to_end_on_this_repository",
        "test_no_claudemd_skips",
        "test_an_empty_knowledge_base_owes_no_tail",
        "test_an_internal_fault_does_not_escape",
        "test_an_internal_fault_is_recorded_as_non_execution_not_as_a_pass",
        "test_an_honest_skip_does_not_block_and_says_which_one",
    },
    # SPEC bodies live in the project database; the control pins what the LIVE
    # repository reports, which is what its name says. There is no git-side
    # answer — the committed registry is a different control in the same file
    # (`test_the_committed_registry_is_valid_json_with_a_reach_note`) and that
    # one is not gated and does run in a bare checkout. Added after this test
    # was found FAILING rather than dormant there
    # (four-tests-fail-in-a-bare-checkout).
    "test_spec_completeness.py": {"test_the_live_repository_reports_exactly_the_gap_it_has"},
}


def _mentions_db(src: str, node: ast.AST) -> bool:
    """Does this node's own source mention the project database?

    Applied to a CONDITION, never to a whole function. The first version of this
    scan read the function's entire text and flagged twenty tests — tests that
    merely build a `tausik.db` under `tmp_path`, tests whose subject IS skipping,
    and, best of all, the very test this task had just repaired, because the
    COMMENT explaining the repair mentioned both words. Text near code is not
    code.
    """
    segment = ast.get_source_segment(src, node) or ""
    return any(m in segment for m in _DB_MARKERS)


def _is_pytest_skip(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "skip"
    )


def _is_skipif(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "skipif"
    )


def _skip_sites() -> list[tuple[str, str, str]]:
    """`(file, test name, source of the gated skip)` for every DB-gated skip.

    Two structural shapes, and only these two:

    * ``@pytest.mark.skipif(<cond mentioning the project DB>, reason=…)``
    * ``if <cond mentioning the project DB>: … pytest.skip(…)``

    The database reference must be in the CONDITION. A test that opens a
    database it built itself is not standing down for want of one.
    """
    found: list[tuple[str, str, str]] = []
    for name in sorted(os.listdir(_TESTS_DIR)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        if name == os.path.basename(__file__):
            continue  # the roster names these on purpose; it is not a site
        path = os.path.join(_TESTS_DIR, name)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:  # pragma: no cover — a broken test file fails elsewhere
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test"):
                continue
            for dec in node.decorator_list:
                if _is_skipif(dec) and dec.args and _mentions_db(src, dec.args[0]):
                    found.append((name, node.name, ast.get_source_segment(src, dec) or ""))
            for inner in ast.walk(node):
                if not isinstance(inner, ast.If) or not _mentions_db(src, inner.test):
                    continue
                if any(_is_pytest_skip(c) for c in ast.walk(inner)):
                    found.append((name, node.name, ast.get_source_segment(src, inner) or ""))
    return found


def test_the_scan_finds_something_at_all():
    """A scan that silently matches nothing would pass every assertion below.

    The failure mode this guards is the one the whole file is about: a check
    that cannot fail because it never looks at anything.
    """
    sites = _skip_sites()
    assert sites, (
        "the AST scan found no DB-gated skip sites at all — either the markers "
        f"{_DB_MARKERS} no longer describe how the project database is named, "
        "or this scan is broken. Both mean this ratchet is measuring nothing."
    )


@pytest.mark.parametrize(
    "site", _skip_sites(), ids=lambda s: f"{s[0]}::{s[1]}" if isinstance(s, tuple) else str(s)
)
def test_every_db_gated_skip_is_rostered_and_loud(site):
    """Two duties, and they are separate on purpose.

    ROSTERED: someone decided this control cannot run from git. Without it, the
    cheapest way past a failing CI control is to gate it on a file CI lacks.

    LOUD: the skip cites the shared reason constant, so a reader of the run sees
    "DORMANT here, not passing" rather than a bare line in a skip count. Three
    of the four families that hid here worded their reason differently from each
    other; naming one constant is what makes the wording un-driftable.
    """
    filename, test_name, segment = site
    allowed = ALLOWED_DORMANT.get(filename, set())
    assert test_name in allowed, (
        f"{filename}::{test_name} stands down when .tausik/tausik.db is absent, "
        "which is every checkout and every CI run, and nothing says it may.\n"
        "Prefer moving it onto a git-tracked source — conftest.canonical_schema_db "
        "for 'what does this project declare', conftest.projected_task_status for "
        "'what is this task's state'. If its subject really is the live working "
        "copy, add it to ALLOWED_DORMANT here with the reason it cannot move."
    )
    assert _REASON_NAME in segment, (
        f"{filename}::{test_name} is rostered as dormant but does not cite "
        f"{_REASON_NAME}. A hand-written reason drifts from its siblings and "
        "stops being findable — which is exactly how seven of these hid."
    )


def test_the_roster_names_no_test_that_no_longer_exists():
    """The mirror duty, and the half that keeps the roster from rotting.

    Without it, a control that was fixed — moved onto git, so no longer gated —
    would leave its entry behind, and the roster would slowly become a list of
    permissions nobody needs, granting cover to any name that happened to match.
    """
    live = {(f, t) for f, t, _ in _skip_sites()}
    stale = sorted(
        f"{filename}::{name}"
        for filename, names in ALLOWED_DORMANT.items()
        for name in names
        if (filename, name) not in live
    )
    assert not stale, (
        "ALLOWED_DORMANT grants dormancy to controls that are no longer gated on "
        f"the project database: {', '.join(stale)}. Remove them — a permission "
        "nobody uses is one the next gated test inherits by accident."
    )
