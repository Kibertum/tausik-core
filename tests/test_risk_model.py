"""Tests for scripts/risk_model.py (v15-risk-model).

AC coverage: formula/weights/levels, normalizer clamps, error contract
(unknown/out-of-range/NaN -> ValueError, missing -> conservative 1.0),
monotonicity (raising any factor never lowers the score).
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import risk_model as rm  # noqa: E402

_ALL_SAFE = {name: 0.0 for name in rm.WEIGHTS}
_ALL_RISKY = {name: 1.0 for name in rm.WEIGHTS}


class TestComputeRisk:
    def test_weights_sum_to_one(self):
        assert abs(sum(rm.WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_safe_is_zero_low(self):
        r = rm.compute_risk(_ALL_SAFE)
        assert r["score"] == 0.0 and r["level"] == "low" and r["defaulted"] == []

    def test_all_risky_is_one_high(self):
        r = rm.compute_risk(_ALL_RISKY)
        assert r["score"] == 1.0 and r["level"] == "high"

    def test_score_is_weighted_sum(self):
        factors = dict(_ALL_SAFE, gate_coverage=1.0)
        assert rm.compute_risk(factors)["score"] == pytest.approx(0.25)

    @pytest.mark.parametrize(
        "score_factors,expected",
        [
            (dict(_ALL_SAFE), "low"),
            (dict(_ALL_SAFE, gate_coverage=1.0, code_churn=1.0), "medium"),  # 0.40
            (dict(_ALL_RISKY, code_churn=0.0), "high"),  # 0.85
        ],
    )
    def test_levels(self, score_factors, expected):
        assert rm.compute_risk(score_factors)["level"] == expected

    def test_boundaries_escalate_not_amnesty(self):
        # exactly 0.33 -> medium, exactly 0.66... construct via direct sums
        f = dict(_ALL_SAFE, gate_coverage=1.0, test_delta=0.4)  # 0.25+0.08=0.33
        assert rm.compute_risk(f)["level"] == "medium"

    def test_missing_factor_defaults_to_risky_and_reported(self):
        r = rm.compute_risk({"gate_coverage": 0.0})
        assert set(r["defaulted"]) == set(rm.WEIGHTS) - {"gate_coverage"}
        assert r["score"] == pytest.approx(0.75)

    def test_monotonic_in_every_factor(self):
        base = {name: 0.3 for name in rm.WEIGHTS}
        base_score = rm.compute_risk(base)["score"]
        for name in rm.WEIGHTS:
            raised = dict(base, **{name: 0.9})
            assert rm.compute_risk(raised)["score"] > base_score, name

    @pytest.mark.parametrize(
        "bad",
        [
            {"nonsense": 0.5},
            {"gate_coverage": -0.1},
            {"gate_coverage": 1.1},
            {"gate_coverage": float("nan")},
            {"gate_coverage": float("inf")},
            {"gate_coverage": "high"},
        ],
    )
    def test_invalid_input_raises(self, bad):
        with pytest.raises(ValueError):
            rm.compute_risk(bad)

    def test_non_dict_raises(self):
        with pytest.raises(ValueError):
            rm.compute_risk([0.1])  # type: ignore[arg-type]


class TestNormalizers:
    def test_gate_coverage(self):
        ran = {"name": "pytest", "passed": True}
        skipped = {"name": "hadolint", "skipped": True}
        assert rm.norm_gate_coverage([ran, ran]) == 0.0
        assert rm.norm_gate_coverage([ran, skipped]) == 0.5
        assert rm.norm_gate_coverage([skipped]) == 1.0
        assert rm.norm_gate_coverage([]) == 1.0

    def test_test_delta(self):
        assert rm.norm_test_delta(0, 0) == 0.0  # docs-only task
        assert rm.norm_test_delta(4, 0) == 1.0  # source w/o tests
        assert rm.norm_test_delta(2, 1) <= 0.2  # 1 test per 2 source = low
        assert rm.norm_test_delta(2, 2) == 0.0  # 1:1
        with pytest.raises(ValueError):
            rm.norm_test_delta(-1, 0)

    def test_ac_evidence(self):
        assert rm.norm_ac_evidence(0, 0) == 1.0  # no AC at all
        assert rm.norm_ac_evidence(4, 4) == 0.0
        assert rm.norm_ac_evidence(4, 2) == 0.5
        assert rm.norm_ac_evidence(4, 9) == 0.0  # over-report clamped
        with pytest.raises(ValueError):
            rm.norm_ac_evidence(4, -1)

    def test_code_churn_log_scale(self):
        assert rm.norm_code_churn(0) == 0.0
        assert 0.3 < rm.norm_code_churn(10) < 0.4
        assert 0.6 < rm.norm_code_churn(100) < 0.7
        assert rm.norm_code_churn(1000) == 1.0
        assert rm.norm_code_churn(50_000) == 1.0
        with pytest.raises(ValueError):
            rm.norm_code_churn(-5)

    def test_security_hits(self):
        assert rm.norm_security_hits([]) == 0.0
        assert rm.norm_security_hits(["docs/readme.md"]) == 0.0
        one_hit = rm.norm_security_hits(["src/auth.py", "docs/readme.md"])
        assert one_hit == 0.75  # floor 0.5 + 0.5 * 1/2
        assert rm.norm_security_hits(["src/auth.py"]) == 1.0

    def test_normalizer_outputs_feed_compute(self):
        r = rm.compute_risk(
            {
                "gate_coverage": rm.norm_gate_coverage([{"name": "pytest", "passed": True}]),
                "test_delta": rm.norm_test_delta(2, 2),
                "ac_evidence": rm.norm_ac_evidence(5, 5),
                "code_churn": rm.norm_code_churn(40),
                "security_hits": rm.norm_security_hits(["docs/x.md"]),
            }
        )
        assert r["level"] == "low" and r["defaulted"] == []
