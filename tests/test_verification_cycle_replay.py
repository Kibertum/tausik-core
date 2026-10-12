from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verification_cycle_replay import evaluate_replay

_FIXTURE = Path(__file__).parent / "fixtures" / "verification_cycle_replay.json"


def _replay():
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_actual_release_111_pair_refuses_an_evidence_losing_reduction():
    replay = _replay()

    verdict = evaluate_replay(replay)

    assert replay["topology"]["occurrences"] == 111
    assert replay["pair"]["rounds"] == [18, 19]
    assert verdict["claim_reduction"] is False
    assert verdict["missing_result_ids"] == ["preflight"]
    assert verdict["before_model_returns"] == 2
    assert verdict["after_model_returns"] == 1


def test_an_exact_independent_replay_can_remove_one_model_return():
    replay = _replay()
    replay["pair"]["compound_preserves"] = copy.deepcopy(replay["pair"]["before"])

    verdict = evaluate_replay(replay)

    assert verdict == {
        "eligible": True,
        "claim_reduction": True,
        "before_model_returns": 2,
        "after_model_returns": 1,
        "missing_result_ids": [],
        "mismatched_result_ids": [],
        "reasons": [],
    }


@pytest.mark.parametrize("relationship", ["adaptive", "dependent"])
def test_a_non_independent_pair_is_rejected_even_with_exact_outputs(relationship):
    replay = _replay()
    replay["pair"]["relationship"] = relationship
    replay["pair"]["compound_preserves"] = copy.deepcopy(replay["pair"]["before"])

    verdict = evaluate_replay(replay)

    assert verdict["claim_reduction"] is False
    assert any(relationship in reason for reason in verdict["reasons"])


@pytest.mark.parametrize("field", ["verdict", "counts", "failures", "evidence"])
def test_every_observable_must_match(field):
    replay = _replay()
    replay["pair"]["compound_preserves"] = copy.deepcopy(replay["pair"]["before"])
    replay["pair"]["compound_preserves"][0][field] = "changed"

    verdict = evaluate_replay(replay)

    assert verdict["claim_reduction"] is False
    assert verdict["mismatched_result_ids"] == ["preflight"]


@pytest.mark.parametrize(
    ("rounds", "sequence"),
    [([18, 20], ["verification", "verification"]), ([18, 19], ["edit", "verification"])],
)
def test_only_an_observed_adjacent_verification_pair_is_eligible(rounds, sequence):
    replay = _replay()
    replay["pair"]["rounds"] = rounds
    replay["topology"]["sequence"] = sequence
    replay["pair"]["compound_preserves"] = copy.deepcopy(replay["pair"]["before"])

    assert evaluate_replay(replay)["claim_reduction"] is False
