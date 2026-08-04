"""The risk backtest must report whether the score separates anything.

It used to print two group averages. On this project's own 374 scored closures
those read as "escaped is slightly lower, so the score is inverted" — and the
inversion is not significant (permutation p=0.3848). The real finding is duller
and worse: AUC 0.4820, the composite separates nothing, while complexity alone —
a field the model ignores — scores 0.6327. Two averages cannot express that, so
they invited a wrong reading of a number consumed as evidence at every closure.

Full measurement: docs/ru/research/risk-model-backtest-2026-07.md
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backend_defect_escape import _auc, defect_escape_metrics  # noqa: E402


def test_auc_reports_perfect_separation():
    assert _auc([0.9, 0.8], [0.1, 0.2]) == 1.0


def test_auc_reports_a_perfectly_inverted_score():
    """Below 0.5 means the score points the WRONG way — the case two averages
    can only hint at."""
    assert _auc([0.1, 0.2], [0.9, 0.8]) == 0.0


def test_auc_of_identical_populations_is_a_coin_flip():
    assert _auc([0.5, 0.5], [0.5, 0.5]) == 0.5


def test_auc_is_undefined_not_neutral_when_a_side_is_empty():
    """None, not 0.5: an absent comparison must not read as 'no signal', which
    is a claim about data that does not exist."""
    assert _auc([], [0.3]) is None
    assert _auc([0.3], []) is None


class _FakeQuery:
    """Stands in for the backend query fn with a fixed set of done closures."""

    def __init__(self, rows):
        self._rows = rows

    def __call__(self, _sql, *_a, **_kw):
        return self._rows


def _row(slug, escaped, score, complexity="medium"):
    return {
        "slug": slug,
        "complexity": complexity,
        "role": "developer",
        "tier": "moderate",
        "risk_score": score,
        "escaped": escaped,
        "verified": 1,
    }


def test_backtest_exposes_auc_alongside_the_averages():
    q = _FakeQuery(
        [
            _row("a", 1, 0.9),
            _row("b", 1, 0.8),
            _row("c", 0, 0.1),
            _row("d", 0, 0.2),
        ]
    )
    bt = defect_escape_metrics(q)["risk_backtest"]
    assert bt["auc"] == 1.0
    assert bt["escaped_n"] == 2 and bt["clean_n"] == 2


def test_backtest_detects_a_score_that_points_the_wrong_way():
    q = _FakeQuery([_row("a", 1, 0.1), _row("b", 1, 0.2), _row("c", 0, 0.9), _row("d", 0, 0.8)])
    assert defect_escape_metrics(q)["risk_backtest"]["auc"] == 0.0


def test_complexity_auc_uses_the_same_population_as_the_composite():
    """The two AUCs print side by side, so they must be built from the same rows.

    Here the unscored closure would flip complexity's verdict if it were counted:
    it is `complex` and clean, which drags complexity's AUC down. The composite
    cannot see that row at all, so counting it on one side of the comparison and
    not the other would put two numbers from different populations on one line.
    """
    q = _FakeQuery(
        [
            _row("a", 1, 0.5, "complex"),
            _row("b", 0, 0.5, "simple"),
            _row("unscored", 0, None, "complex"),
        ]
    )
    bt = defect_escape_metrics(q)["risk_backtest"]
    assert bt["complexity_auc"] == 1.0  # scored rows only: complex escaped > simple clean
    assert bt["escaped_n"] == 1 and bt["clean_n"] == 1


def test_backtest_is_safe_on_an_empty_project():
    bt = defect_escape_metrics(_FakeQuery([]))["risk_backtest"]
    assert bt["auc"] is None and bt["complexity_auc"] is None
    assert bt["escaped_avg_risk"] is None and bt["clean_avg_risk"] is None
