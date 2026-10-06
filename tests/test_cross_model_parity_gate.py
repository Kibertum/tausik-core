"""A capability cannot go host-only without somebody saying so.

cross-model-parity-has-no-gate. The claude/qwen pair was already guarded — by a
test comparing SCRIPT BASENAMES. It reported 23 hooks on each side and passed,
while six of those hooks were registered on different MATCHERS: `task_done_verify`
fires on four tool patterns under Qwen and one under Claude, `task_call_counter`
counts every tool under Qwen and five under Claude. A parity check that cannot see
that passes while the hosts diverge, which is worse than no check, because it is
believed.

WHAT IS ASSERTED HERE IS THE FACT. The gate is run — on the real generators for
the live tree, and on synthetic tables for the shapes that do not exist yet — and
its verdict is read. Nothing asserts that a constant is present or that a function
is called.

The centre of the file is the mutation: take a hook away from one host and the
gate MUST turn red. A gate that survives its own subject being deleted is checking
nothing, whatever its docstring claims.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "bootstrap")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import gate_cross_model_parity as gate  # noqa: E402
import host_mechanisms as hm  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/", "scripts/hooks/", "scripts/host_mechanisms.py"]


def _undeclared_victim(caps: dict[str, str]) -> str:
    """A hook whose removal creates ONE difference and disturbs no declaration.

    Picking `sorted(...)[0]` chose `activity_event.py`, whose matcher difference
    IS declared — deleting it made that declaration stale and the test failed for
    a reason it was not about. The mutation has to be clean to prove anything.
    """
    for cap in sorted(caps):
        if not cap.startswith("hook:"):
            continue
        if any(cap in key for key in gate.DECLARED_DIFFERENCES):
            continue
        return cap
    raise AssertionError("every hook is named in a declaration; the mutation cannot be clean")


@pytest.fixture(scope="module")
def live_table() -> dict[str, dict[str, str]]:
    """The real generators, run once. Every test below reads the same tree."""
    return hm.matcher_table()


class TestTheTableIsDerivedFromTheGenerators:
    def test_each_mechanism_bearing_host_produced_something(self, live_table):
        assert set(live_table) == set(hm.MECHANISM_BUILDERS)
        for host, caps in live_table.items():
            assert caps, f"{host} produced no capabilities — its generator wrote nothing"
            assert not any(c.startswith("error:") for c in caps), f"{host}: {caps}"

    def test_the_capability_id_carries_the_event_not_only_the_file(self, live_table):
        """A hook moved between events is a different capability wearing the same
        file name, and an id built from the basename alone cannot say so."""
        hooks = [c for c in live_table["claude"] if c.startswith(hm.KIND_HOOK + ":")]
        assert hooks
        for cap in hooks:
            kind, event, script = cap.split(":", 2)
            assert kind == hm.KIND_HOOK
            assert event in {
                "PreToolUse",
                "PostToolUse",
                "SessionStart",
                "SessionEnd",
                "Stop",
                "UserPromptSubmit",
                "PreCompact",
                "Notification",
                "SubagentStop",
            }, f"unexpected event in {cap}"
            assert script.endswith(".py")

    def test_a_plugin_is_recorded_with_no_matcher_rather_than_a_made_up_one(self, live_table):
        for host in ("opencode", "kilo"):
            plugins = {c: m for c, m in live_table[host].items() if c.startswith("plugin:")}
            assert plugins, f"the {host} gate plugin did not land"
            assert set(plugins.values()) == {""}, (
                "a plugin has no matcher; inventing one would put a fact in the table "
                f"that no file supports: {host}: {plugins}"
            )

    def test_the_kilo_plugins_are_the_only_kilo_capabilities(self, live_table):
        """kilo-gate-plugin + provider-agnostic-model-observation: kilo joined
        the mechanism table with exactly its two plugins — the enforcement gate
        and the model observer. No hook commands were smuggled in alongside."""
        assert set(live_table["kilo"]) == {"plugin:tausik-gates.js", "plugin:tausik-observe.js"}

    def test_it_reads_a_clean_tree_not_the_repository_profiles(self, live_table):
        """The subject is what bootstrap WOULD deploy from the source as it
        stands. Reading `.claude/` here would let a stale deployed profile make a
        regression in the generator look settled."""
        assert live_table["claude"], "claude produced nothing"
        # The repo's own .claude is not consulted: prove it by asking for a table
        # with a lib_dir that is still the repo but from a different cwd-independent
        # path, and getting the same answer.
        again = hm.matcher_table(lib_dir=str(_REPO))
        assert again == live_table


class TestTheGateFindsRealDifferences:
    def test_the_matcher_differences_that_motivated_this_are_gone(self, live_table):
        """These four were why a basename-only comparison was not enough. Qwen
        built them from a hand-kept list; since 1.10 it builds from the shared
        declaration (decision #389), and they must not come back unnoticed."""
        found = gate.find_differences(live_table)
        for script in (
            "activity_event.py",
            "task_call_counter.py",
            "tool_output_truncation_nudge.py",
            "task_done_verify.py",
        ):
            assert f"matcher:hook:PostToolUse:{script}" not in found

    def test_every_live_difference_is_declared(self, live_table):
        found = set(gate.find_differences(live_table))
        undeclared = found - set(gate.DECLARED_DIFFERENCES)
        assert not undeclared, f"undeclared difference(s): {sorted(undeclared)}"

    def test_the_gate_passes_on_the_live_tree(self):
        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/bootstrap_hooks.py"])
        assert ok, msg

    def test_two_spellings_of_every_tool_are_not_a_difference(self):
        """Claude writes `""`, Qwen writes `*`. Reporting that as a divergence
        would bury the four real ones under a dozen false ones."""
        assert gate.normalise_matcher("") == gate.normalise_matcher("*")
        table = {
            "a": {"hook:PostToolUse:x.py": ""},
            "b": {"hook:PostToolUse:x.py": "*"},
        }
        assert gate.find_differences(table) == []


class TestTakingAHookAwayTurnsItRed:
    """The mutation. Without it every test above passes against a constant."""

    def test_a_hook_missing_from_one_host_is_an_undeclared_difference(self, live_table):
        mutated = {h: dict(c) for h, c in live_table.items()}
        victim = _undeclared_victim(mutated["qwen"])
        del mutated["qwen"][victim]

        found = gate.find_differences(mutated)
        assert f"missing:{victim}@qwen" in found, (
            "the gate did not notice a hook disappearing from one host — it is not "
            f"comparing anything. differences seen: {found}"
        )
        assert f"missing:{victim}@qwen" not in gate.DECLARED_DIFFERENCES

    def test_the_gate_blocks_when_that_happens(self, monkeypatch, live_table):
        mutated = {h: dict(c) for h, c in live_table.items()}
        victim = _undeclared_victim(mutated["claude"])
        del mutated["claude"][victim]
        monkeypatch.setattr(gate, "matcher_table", lambda *a, **k: mutated)

        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/x.py"])
        assert not ok
        assert victim in msg and "UNDECLARED" in msg

    def test_a_changed_matcher_alone_turns_it_red(self, monkeypatch, live_table):
        """The defect the old parity test could not see: same files, same events,
        different tools."""
        mutated = {h: dict(c) for h, c in live_table.items()}
        cap = "hook:PreToolUse:task_gate.py"
        assert cap in mutated["claude"] and cap in mutated["qwen"], cap
        mutated["qwen"][cap] = mutated["qwen"][cap] + "|SomethingElse"
        monkeypatch.setattr(gate, "matcher_table", lambda *a, **k: mutated)

        ok, msg = gate.run_cross_model_parity_gate({}, ["scripts/hooks/task_gate.py"])
        assert not ok
        assert f"matcher:{cap}" in msg


class TestADeclarationIsNotAFreePass:
    def test_a_declared_difference_passes(self, monkeypatch, live_table):
        """AC3: the gate must never demand sameness. Cursor has no extension
        point; there is nothing for it to be equal to."""
        mutated = {h: dict(c) for h, c in live_table.items()}
        victim = _undeclared_victim(mutated["qwen"])
        del mutated["qwen"][victim]
        monkeypatch.setattr(gate, "matcher_table", lambda *a, **k: mutated)
        monkeypatch.setitem(
            gate.DECLARED_DIFFERENCES, f"missing:{victim}@qwen", "declared for this test"
        )

        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/x.py"])
        assert ok, msg

    def test_a_declaration_without_a_reason_is_refused(self, monkeypatch):
        monkeypatch.setitem(gate.DECLARED_DIFFERENCES, "missing:hook:X:y.py@qwen", "   ")
        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/x.py"])
        assert not ok
        assert "no reason" in msg

    def test_a_declaration_matching_nothing_live_is_refused(self, monkeypatch):
        """Decision #335, the other direction. A note about the past presented as
        a statement about the present."""
        monkeypatch.setitem(
            gate.DECLARED_DIFFERENCES,
            "missing:hook:PostToolUse:long_gone.py@qwen",
            "a difference that was fixed three releases ago",
        )
        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/x.py"])
        assert not ok
        assert "no longer exist" in msg and "long_gone.py" in msg

    def test_every_shipped_declaration_carries_a_reason_with_substance(self):
        for key, why in gate.DECLARED_DIFFERENCES.items():
            assert len(why.strip()) > 80, f"{key}: the reason is too thin to check later"


class TestItIsNotATax:
    def test_a_change_outside_the_host_layer_skips_the_gate(self):
        ok, msg = gate.run_cross_model_parity_gate({}, ["scripts/service_at.py", "docs/ru/cli.md"])
        assert ok
        assert "not the host layer" in msg

    def test_a_change_inside_the_host_layer_runs_it(self):
        ok, msg = gate.run_cross_model_parity_gate({}, ["bootstrap/bootstrap_qwen.py"])
        assert "not the host layer" not in msg
        assert ok, msg

    def test_a_deployed_profile_path_also_counts_as_the_host_layer(self):
        """Bootstrap copies `scripts/hooks/` into every profile; an edit landing
        there is still an edit to the host layer."""
        assert gate._touches_host_layer([".claude/scripts/hooks/task_gate.py"])

    def test_no_files_at_all_means_run_it(self):
        """An empty file list is a whole-repo invocation, not an exemption."""
        ok, msg = gate.run_cross_model_parity_gate({}, [])
        assert "not the host layer" not in msg


class TestASingleBearerIsNotADifference:
    def test_plugin_names_differ_between_hosts_by_declaration_only(self, live_table):
        """AC7, updated by kilo-gate-plugin and provider-agnostic-model-
        observation. Two hosts now bear plugins, and the gate sees exactly the
        three file-name differences — each declared with a reason (the gates
        contract is shared and tested parametrized; the observer is a declared
        Kilo-only capability). Any plugin difference BEYOND those three is an
        undeclared divergence this test refuses to let pass."""
        found = gate.find_differences(live_table)
        plugin_diffs = sorted(d for d in found if "plugin:" in d)
        assert plugin_diffs == [
            "missing:plugin:tausik-gates.js@opencode",
            "missing:plugin:tausik-observe.js@opencode",
            "missing:plugin:tausik-qg0.js@kilo",
        ], plugin_diffs
        for d in plugin_diffs:
            assert d in gate.DECLARED_DIFFERENCES, f"declared or fix, not silence: {d}"

    def test_a_host_with_no_mechanism_is_absent_from_the_table_entirely(self, live_table):
        assert "cursor" not in live_table


class TestTheBuilderMapCannotGoStale:
    def test_the_disk_is_asked_whether_an_unbuilt_host_deploys_anything(self, tmp_path):
        """The guard on MECHANISM_BUILDERS: teach bootstrap to deploy hooks for
        Cursor, forget to add a builder, and the gate would go on calling Cursor
        mechanism-free — green, and wrong."""
        import json

        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursor" / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Write", "hooks": [{"command": "py hooks/task_gate.py"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        problems = hm.cross_check_against_disk(str(tmp_path))
        assert problems and "cursor" in problems[0]
        assert "MECHANISM_BUILDERS" in problems[0]

    def test_a_project_with_no_profiles_reports_nothing(self, tmp_path):
        """A consumer project deploys one host. 'The other four are missing' is
        not a finding, and a gate that says it teaches the reader to skip it."""
        assert hm.cross_check_against_disk(str(tmp_path)) == []

    def test_this_repository_is_clean(self):
        assert hm.cross_check_against_disk(str(_REPO)) == []


class TestHostRegistryDivergenceIsPinned:
    """AC8. The gate does not pretend there is one registry. Collapsing them is
    `four-ide-registries-collapse-into-one`; what is held here is that the
    remaining divergence does not WIDEN unnoticed while that waits."""

    def test_the_measured_divergence_is_exactly_what_was_recorded(self):
        from bootstrap_config import IDE_DIRS
        from ide_utils import IDE_REGISTRY
        from skill_profile_detect import VALID_IDES

        import providers

        assert set(IDE_DIRS) == set(IDE_REGISTRY), (
            "IDE_DIRS and IDE_REGISTRY agreed when this was measured; if they no "
            "longer do, the gate's host set has drifted from bootstrap's"
        )
        assert set(VALID_IDES) == {"claude", "codex", "cursor", "kilo", "qwen"}, (
            "the skill-profile registry changed. If a host was ADDED, good — move "
            "this pin. If one was removed, that is a regression."
        )
        assert set(providers.available()) == {"claude", "codex", "cursor", "kilo", "qwen"}

    def test_remaining_scaffolded_host_cannot_be_selected_as_a_profile(self):
        """Kilo is selectable in 1.11; opencode remains the measured gap."""
        from bootstrap_config import SCAFFOLD_IDES
        from skill_profile_detect import VALID_IDES

        unselectable = sorted(set(SCAFFOLD_IDES) - set(VALID_IDES))
        assert unselectable == ["opencode"], (
            f"the set of scaffolded-but-unselectable hosts changed to {unselectable}; "
            "update four-ide-registries-collapse-into-one and this pin together"
        )
