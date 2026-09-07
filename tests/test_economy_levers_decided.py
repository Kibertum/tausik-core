"""Every economy lever TAUSIK ships must be DECIDED on by TAUSIK itself.

The project claims "this framework is its own user" and shipped levers it had
decided on none of: `output_mode` unset, `read_ledger` unset, both output
thresholds unset, `context_tier` set to the value it already defaults to. That
divergence was found by reading a config field — which is exactly how it should
not be found. A discrepancy nobody can trip over survives.

WHAT IS ASSERTED IS NOT "EVERY LEVER IS ON". Most are correctly off here, with
numbers: caveman's ceiling on this corpus is 6.6% (output is 71.6% of context
growth, but only 9.2% of output is the prose it compresses — 90.6% is tool
arguments it exempts as byte-exact), and it could not reach a hand-written
CLAUDE.md anyway. The read ledger's ceiling is 0.49%. What is asserted is that a
decision EXISTS: a value, or a registry entry carrying the reason. A default
nobody chose is not a decision.

BOTH DIRECTIONS, because a registry checked one way decays into a list of good
intentions (decision #335): an entry naming a lever the code no longer has fails,
and a lever the code gained that nobody decided on fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))

import economy_levers as el  # noqa: E402

CROSSCUTTING_SCOPE = [
    "scripts/economy_levers.py",
    "bootstrap/bootstrap_templates.py",
    "scripts/hooks/tool_output_truncation_nudge.py",
    "scripts/hooks/read_ledger.py",
]


class TestThisProjectHasDecidedOnEveryLeverItShips:
    def test_no_lever_is_left_undecided(self):
        undecided = el.undecided_levers(str(_REPO), str(_REPO))
        assert not undecided, (
            f"these shipped economy levers have neither a value in .tausik/config.json nor "
            f"an entry in DELIBERATELY_UNSET: {undecided}. Shipping a lever the project "
            "itself never examined is the dogfooding claim failing quietly."
        )

    def test_no_registry_entry_names_a_lever_the_code_lost(self):
        stale = el.stale_registry_entries(str(_REPO))
        assert not stale, (
            f"DELIBERATELY_UNSET names levers that are no longer shipped: {stale}. "
            "An entry matching nothing live is a claim about code that is gone "
            "(decision #335)."
        )

    def test_every_reason_says_something_a_reader_can_check(self):
        """A reason is for a human, so 'not needed' does not count."""
        for lever, reason in el.DELIBERATELY_UNSET.items():
            assert len(reason) > 120, f"{lever}: the reason is too short to be a reason"
            assert any(ch.isdigit() for ch in reason), (
                f"{lever}: the reason carries no number. Every one of these decisions was "
                "made against a measurement, and a reason without one is a preference."
            )


class TestTheShippedProofIsReadNotImported:
    def test_each_lever_points_at_code_that_exists(self):
        for lever in el.SHIPPED_LEVERS:
            assert el.lever_is_shipped(str(_REPO), lever), (
                f"{lever} claims to be shipped but its proof symbol is not in the file"
            )

    def test_a_lever_whose_file_is_gone_reads_as_not_shipped(self, tmp_path):
        """The proof is a fact about the tree, not a name in a table."""
        assert not el.lever_is_shipped(str(tmp_path), "output_mode")


class TestTheDetectorGoesRedWhenItShould:
    """A guard nobody has seen fail is not evidence. Each branch is made to fail."""

    def test_an_invented_registry_entry_is_caught(self, monkeypatch):
        monkeypatch.setitem(el.DELIBERATELY_UNSET, "lever_that_never_existed", "x" * 200)
        assert "lever_that_never_existed" in el.stale_registry_entries(str(_REPO))

    def test_a_registry_entry_whose_code_vanished_is_caught(self, monkeypatch, tmp_path):
        """Same entry, tree without the code: the check follows the tree."""
        assert "output_mode" in el.stale_registry_entries(str(tmp_path))

    def test_a_new_lever_nobody_decided_on_is_caught(self, monkeypatch, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "config.json").write_text("{}", encoding="utf-8")
        monkeypatch.setitem(
            el.SHIPPED_LEVERS, "brand_new_lever", ("scripts/economy_levers.py", "SHIPPED_LEVERS")
        )
        undecided = el.undecided_levers(str(tmp_path), str(_REPO))
        assert "brand_new_lever" in undecided

    def test_a_missing_config_is_not_a_pass(self, tmp_path):
        """No config means no decisions — never mistake absence for agreement."""
        assert el.load_config(str(tmp_path)) is None
        assert el.undecided_levers(str(tmp_path), str(_REPO)) == sorted(el.SHIPPED_LEVERS)

    def test_a_malformed_config_is_not_a_pass_either(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "config.json").write_text("{not json", encoding="utf-8")
        assert el.load_config(str(tmp_path)) is None


class TestOurOwnConfigMatchesWhatWeDecided:
    def test_context_tier_is_present_but_recorded_as_inert(self):
        """Deleting it does not stick — bootstrap writes it back, and correctly.

        The first attempt here removed the key from our config as a "silent
        no-op". The next bootstrap put it straight back, which is right: the
        lever IS live for projects whose rules file the generator writes. So the
        honest state is not absence but an explicit note that the value is inert
        HERE, and the registry carries it.
        """
        cfg = json.loads((_REPO / ".tausik" / "config.json").read_text(encoding="utf-8"))
        assert cfg.get("context_tier") == "standard"
        assert "context_tier" in el.DELIBERATELY_UNSET
        assert "INERT" in el.DELIBERATELY_UNSET["context_tier"]

    def test_output_mode_is_not_quietly_enabled(self):
        cfg = json.loads((_REPO / ".tausik" / "config.json").read_text(encoding="utf-8"))
        assert cfg.get("output_mode") in (None, "off"), (
            "output_mode was enabled without moving it out of DELIBERATELY_UNSET — the "
            "decision and the config would then disagree, which is the state this file "
            "exists to make impossible"
        )
