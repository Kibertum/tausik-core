"""Visibility ratchet for cross-cutting tests (scoped-pytest-blind-to-crosscutting-tests).

A test that iterates a SOURCE TREE (every hook, every skill, every profile) is
relevant to any change inside that tree, but the basename heuristic can never map
a change TO it. `CROSSCUTTING_SCOPE` lets such a test opt in by path — but an
opt-in mechanism nobody remembers to use just reproduces the original blindness
silently.

So the absence of a declaration is made VISIBLE, not required-everywhere: this
gate detects tests that iterate a source tree and asserts each one either

  * declares `CROSSCUTTING_SCOPE = [...]` (the trees it guards), or
  * opts out with `CROSSCUTTING_SCOPE = []` ("reviewed, not cross-cutting"), or
  * is in the frozen `_GRANDFATHERED` baseline below.

`_GRANDFATHERED` is a RATCHET: it may only shrink. A NEW tree-iterating test that
is neither declared nor grandfathered reddens the gate (the absence is now
visible); and a baseline entry that later declares a scope must be removed, so the
list cannot rot into a forgotten registry. The 30 current entries are the
pre-existing tree-iterators, acknowledged once and left to be scoped over time —
not a blank cheque for new ones.

SECOND DETECTOR — INVISIBLE TO EVERY EDGE (invariant-guards-are-invisible-...).
The first detector asks a narrow question: does this test WALK a source tree? It
found real cases, and it also missed a whole other class. A guard that compares a
DDL with a fixture, a fresh schema with a migrated one, or a consumer's layout
with the expected one walks nothing at all — it imports two things and asserts
they agree. Such a test was invisible to the first detector, and the workaround
was a line in the shift handover telling humans to hand-mix five file names into
every scoped run. A rule that requires remembering five file names gets forgotten;
that is how it came to be written down in the first place.

So the second detector does not guess at a class of test. It asks the resolver the
only question that matters — "is there ANY change that would select you?" — using
the resolver's own three edges (basename, import, declared scope) rather than a
private copy of them. Measured when it was added: 200 of 408 test files were
unreachable by basename, the import edge revived 180, and the 18 that remain are
in `_INVISIBLE_BASELINE` below. Same ratchet contract as above: declare a scope,
opt out visibly, or be in the frozen list, which may only shrink.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS = os.path.join(_ROOT, "tests")
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from conftest import IS_PUBLIC_SNAPSHOT  # noqa: E402
from gate_test_resolver import (  # noqa: E402
    deferred_global_crosscutting_for_relevant,
    read_crosscutting_scope,
    resolve_test_files_for_relevant,
)
from publication_snapshot import is_excluded  # noqa: E402


def _dormant_here(prefix: str) -> bool:
    """On the public snapshot a prefix the filter leaves behind is not rot —
    its test is dormant there (decision #368), and the registry says so instead
    of reporting a dead binding for a file the snapshot never carried."""
    return IS_PUBLIC_SNAPSHOT and is_excluded(prefix.replace(os.sep, "/"))


# A test iterates a source tree if it walks/globs (ITER) a repo-root-anchored
# (ANCHOR) path that names a source directory (SRC). Conservative by design: the
# escape hatch is a one-line `CROSSCUTTING_SCOPE = []`, so a false positive costs
# a visible opt-out, never a silent miss.
_ITER = re.compile(r"os\.walk\(|glob\.i?glob\(|\.rglob\(|\.glob\(")
_ANCHOR = re.compile(r"parents\[1\]|dirname\([^)]*__file__[^)]*\)")
_SRC = re.compile(r"[\"'](scripts|bootstrap|harness|docs)[\"'/]|/(scripts|bootstrap|harness|docs)/")

# The detector is not its own subject: this file mentions the iteration idioms as
# regex text, which must not count as iterating a tree.
_SELF = {"test_crosscutting_registry.py"}

# Frozen baseline — the tree-iterators that predate the CROSSCUTTING_SCOPE
# mechanism. RATCHET: only ever remove entries (by declaring a scope on them);
# never add. A new tree-iterator belongs in a declaration, not here.
_GRANDFATHERED = {
    "test_audit_pytest_dedupe.py",
    "test_bootstrap_drift_gate.py",
    "test_bootstrap_non_destructive.py",
    "test_bootstrap_real.py",
    "test_caveman_output_mode.py",
    "test_cli_entrypoint_guard.py",
    "test_copy_symlinks_disabled.py",
    "test_docs_no_fake_npm_packages.py",
    "test_doctor_multi_ide.py",
    "test_external_flags_are_real.py",
    "test_gate_command_neutering.py",
    "test_gate_truncation_pipe.py",
    "test_ide_single_source.py",
    "test_mcp_answers_prompts_list.py",
    "test_mcp_no_deprecated_primitives.py",
    "test_migrations.py",
    "test_no_silent_subprocess.py",
    "test_risk_compute_stdin.py",
    "test_schema_upgrade_parity.py",
    "test_skill_repo_trust.py",
    "test_skill_tool_references.py",
    "test_skills_have_gotchas.py",
    "test_skills_no_boilerplate.py",
    "test_stack_gate_coverage.py",
    "test_state_export.py",
    "test_state_roundtrip_gate.py",
    "test_state_triggers.py",
    "test_tausik_utils.py",
    "test_token_metrics_rotation.py",
    "test_unicode_stdio.py",
}


# Frozen baseline for the SECOND detector — tests no change can select at all.
# RATCHET, same contract: entries leave by declaring a CROSSCUTTING_SCOPE (or by
# gaining an import of the code they guard), never by being added to. Every one of
# these reads files or config instead of importing product code, which is why the
# import edge cannot reach them.
_INVISIBLE_BASELINE = {
    "test_adversarial_review_mode.py",
    "test_ble001_enforced.py",
    "test_breaking_change_count_converges.py",
    "test_coverage_badge.py",
    "test_interview_skill.py",
    "test_mypy_clean.py",
    "test_no_silent_subprocess.py",
    "test_plan_skill_agent_aware.py",
    "test_pytest_hang_guard.py",
    "test_skill_descriptions_length.py",
    "test_start_lite_dashboard.py",
    "test_subagent_gate_fixer.py",
    "test_subagent_model_hints.py",
    "test_tausik_cli.py",
    "test_unicode_stdio.py",
}


def _test_files() -> list[str]:
    return [f for f in os.listdir(_TESTS) if f.startswith("test_") and f.endswith(".py")]


def _tracked_sources() -> list[str]:
    """Every git-tracked file outside tests/ — the universe of possible changes.

    Tracked, not walked. An IDE mirror under `.kilo/` or a gitignored artifact like
    `opencode.json` is not a file anyone changes on purpose, and counting it made
    15 tests look reachable when nothing a person edits would ever select them
    (convention #424: git history settles this, not a list of exclusions).

    A missing or failing git is a LOUD failure, never a silent narrowing: this gate
    would still pass while measuring the wrong universe.
    """
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "`git ls-files` failed, so the set of source files this gate reasons "
            f"about is unknown — that is not the same as 'nothing is invisible':\n{proc.stderr}"
        )
    # `tests/tools/` IS source, and is the one exception to "outside tests/".
    # Measured in #193: the audit hook lives at tests/tools/claudemd_audit/
    # sitecustomize.py by decision #279, and its test guards nothing else. With
    # the whole of tests/ struck from the universe, that test could NEVER be
    # selected by any change — so it read as invisible no matter what it
    # declared, and no CROSSCUTTING_SCOPE could rescue it. The gate was not
    # catching a gap; it was measuring the wrong universe (convention #444: a
    # check that does not match its own subject reports something else).
    #
    # This does NOT weaken the claim. Every test must still be reachable by some
    # edge; what changes is which files count as a possible change. Files under
    # tests/tools/ are hand-edited, tracked, and have tests of their own — they
    # are tools, not tests. Widening cost exactly one file and made exactly one
    # test visible (19 invisible -> 18); nothing became invisible, and no
    # _INVISIBLE_BASELINE entry went stale.
    files = [
        f
        for f in proc.stdout.splitlines()
        if f and (not f.startswith("tests/") or f.startswith("tests/tools/"))
    ]
    files = [f for f in files if "/tests/" not in f]
    if not files:
        raise RuntimeError("`git ls-files` returned no source files — the universe cannot be empty")
    return files


def _invisible_to_every_edge() -> set[str]:
    """Tests that NO change to any tracked source file would select.

    Asked as ONE call to the real resolver over the whole universe of sources,
    rather than by re-deriving its edges here. The first version of this function
    did re-derive them, and mutation testing caught it immediately: ripping the
    import edge out of `resolve_test_files_for_relevant` left this gate GREEN,
    because it was still computing imports on its own. A ratchet that models the
    thing it guards will always drift from it; this one asks it. Cost ~1.2 s.
    """
    sources = _tracked_sources()
    selectable = {os.path.basename(p) for p in resolve_test_files_for_relevant(sources, root=_ROOT)}
    # Whole-tree declarations are not evidence from an ordinary scoped receipt,
    # but are explicit full/release-lane obligations, not invisible tests.
    selectable |= {
        os.path.basename(p) for p in deferred_global_crosscutting_for_relevant(sources, root=_ROOT)
    }
    invisible = {fn for fn in _test_files() if fn not in selectable}
    if IS_PUBLIC_SNAPSHOT:
        # A test whose whole declared scope stayed on the development line is
        # dormant here, not invisible: nothing it guards is in this checkout.
        invisible = {
            fn
            for fn in invisible
            if not (
                (scope := read_crosscutting_scope(os.path.join(_TESTS, fn)))
                and all(_dormant_here(p) for p in scope)
            )
        }
    return invisible


def _iterates_source_tree(text: str) -> bool:
    return bool(_ITER.search(text) and _ANCHOR.search(text) and _SRC.search(text))


def _flagged_undeclared() -> set[str]:
    out: set[str] = set()
    for fn in _test_files():
        if fn in _SELF:
            continue
        path = os.path.join(_TESTS, fn)
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if _iterates_source_tree(text) and read_crosscutting_scope(path) is None:
            out.add(fn)
    return out


class TestCrosscuttingVisibility:
    def test_new_tree_iterator_must_declare_or_optout(self):
        """AC3: a tree-iterating test that neither declares a scope nor opts out
        must be caught — the whole point is that the gap can no longer hide."""
        new = _flagged_undeclared() - _GRANDFATHERED
        assert not new, (
            "these tests iterate a source tree but neither declare "
            "CROSSCUTTING_SCOPE = [<guarded path prefixes>] nor opt out with "
            "CROSSCUTTING_SCOPE = [] — the scoped-pytest gate is blind to them:\n  "
            + "\n  ".join(sorted(new))
        )

    def test_grandfather_baseline_only_shrinks(self):
        """The ratchet: a baseline entry that has since declared a scope (or stopped
        iterating a tree) is stale and must be removed, so the list keeps shrinking
        rather than rotting into a registry nobody prunes."""
        stale = _GRANDFATHERED - _flagged_undeclared()
        assert not stale, (
            "remove these from _GRANDFATHERED — they declared a scope or no longer "
            "iterate a source tree, and a ratchet that never shrinks is just a list:\n  "
            + "\n  ".join(sorted(stale))
        )


class TestDeclaredScopesDoNotRot:
    def test_every_declared_prefix_points_at_a_real_path(self):
        """AC4: a CROSSCUTTING_SCOPE prefix that names a path which no longer exists
        is a dead binding — the tree moved and the test now guards nothing."""
        offenders: list[str] = []
        for fn in _test_files():
            scope = read_crosscutting_scope(os.path.join(_TESTS, fn))
            if not scope:
                continue
            for prefix in scope:
                if _dormant_here(prefix):
                    continue
                if not os.path.exists(
                    os.path.join(_ROOT, prefix.replace("/", os.sep).rstrip(os.sep))
                ):
                    offenders.append(f"{fn}: '{prefix}'")
        assert not offenders, (
            "declared CROSSCUTTING_SCOPE prefixes that do not exist on disk:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_gate_is_not_hollow(self):
        """A detector that flags nothing would pass vacuously. At least the known
        tree-iterators must still register."""
        flagged_or_declared = _flagged_undeclared() | {
            fn for fn in _test_files() if read_crosscutting_scope(os.path.join(_TESTS, fn))
        }
        assert len(flagged_or_declared) >= 20, "detector went blind — heuristic likely broke"


class TestInvisibleToEveryEdge:
    """The second detector. Subject: a test NO change can select, by any edge."""

    def test_a_test_no_change_can_select_must_declare_or_be_baselined(self):
        """AC3. A new test that nothing selects is not a neutral fact — it is a
        gate that will pass every scoped run without ever executing, and its first
        real failure arrives on the full lane, days later and attached to the wrong
        change. One line of `CROSSCUTTING_SCOPE` decides which it is."""
        new = _invisible_to_every_edge() - _INVISIBLE_BASELINE
        assert not new, (
            "no change to any tracked source file would ever select these tests — "
            "they match no basename, import no product module, and declare no "
            "scoped or full/release CROSSCUTTING_SCOPE, so every lane silently skips them:\n  "
            + "\n  ".join(sorted(new))
        )

    def test_invisible_baseline_only_shrinks(self):
        """The ratchet. An entry that has since become selectable is stale, and a
        frozen list nobody prunes is just a list."""
        stale = _INVISIBLE_BASELINE - _invisible_to_every_edge()
        assert not stale, (
            "remove these from _INVISIBLE_BASELINE — a change can now select them, "
            "so the baseline must shrink by exactly that much:\n  " + "\n  ".join(sorted(stale))
        )

    def test_the_second_detector_is_not_hollow(self):
        """It must still be able to SEE. If the reachability computation silently
        started calling everything reachable, both tests above would pass forever
        while the blindness returned."""
        invisible = _invisible_to_every_edge()
        assert invisible, (
            "the invisibility detector found nothing at all — either every test is "
            "genuinely selectable (then empty the baseline deliberately) or the "
            "resolver's edges stopped being computed"
        )
        assert len(invisible) < len(_test_files()) // 2, (
            f"{len(invisible)} of {len(_test_files())} tests read as invisible — the "
            "detector is flagging wholesale, which means it broke rather than found"
        )
