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
"""

from __future__ import annotations

import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS = os.path.join(_ROOT, "tests")
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gate_test_resolver import read_crosscutting_scope  # noqa: E402

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


def _test_files() -> list[str]:
    return [f for f in os.listdir(_TESTS) if f.startswith("test_") and f.endswith(".py")]


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
