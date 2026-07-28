"""Tests for scripts/token_accounting.py — tokenizer-era + compaction accounting.

Two token-counting corrections the cost telemetry needs and this suite locks in:

1. Tokenizer era (l26-tokenizer-calibration). Opus 4.7+, Fable 5, Mythos 5 and
   Sonnet 5 emit ~30% more tokens for the same text than the prior tokenizer
   (Sonnet 4.6 / Opus 4.6 / Haiku 4.5 and older). Cross-boundary token/cost
   comparisons are invalid without a correction; same-era comparisons must stay
   byte-exact (the fails-then-passes pair below proves both directions).

2. Server-side compaction. The API bills compaction under usage.iterations[*];
   top-level input/output_tokens omit it, so a top-level-only sum understates
   the real (billed) token count.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from token_accounting import (  # noqa: E402
    NEW_ERA,
    NEW_TOKENIZER_INFLATION,
    OLD_ERA,
    UNKNOWN_ERA,
    era_normalized_total,
    label_usage_rows,
    normalized_token_count,
    sum_usage_tokens,
    tokenizer_era,
)


class TestTokenizerEraBoundary:
    """AC1 — historical records classified by the exact era boundary."""

    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-opus-4-7",
            "claude-opus-4-8",
            "claude-opus-4-8[1m]",
            "claude-fable-5",
            "claude-mythos-5",
            "claude-sonnet-5",
            "claude-sonnet-5[1m]",
            "  CLAUDE-OPUS-4-7  ",  # case + whitespace tolerated
        ],
    )
    def test_new_era_models(self, model_id):
        assert tokenizer_era(model_id) == NEW_ERA

    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-sonnet-4-6",
            "claude-sonnet-4-6[1m]",
            "claude-opus-4-6",
            "claude-opus-4-5",
            "claude-haiku-4-5",
            "claude-haiku-4-5-20251001",  # dated id still classifies
        ],
    )
    def test_old_era_models(self, model_id):
        assert tokenizer_era(model_id) == OLD_ERA

    def test_boundary_is_between_opus_4_6_and_4_7(self):
        # The whole point: 4.6 and 4.7 land on opposite sides.
        assert tokenizer_era("claude-opus-4-6") == OLD_ERA
        assert tokenizer_era("claude-opus-4-7") == NEW_ERA

    @pytest.mark.parametrize(
        "model_id",
        [
            "claude-opus-4-20250514",  # bare-major + release date (real id form)
            "claude-sonnet-4-20250514",
        ],
    )
    def test_bare_major_dated_id_is_old_not_new(self, model_id):
        # s146 review HIGH: an 8-digit date must NOT be read as the minor version
        # (that flipped a real Opus-4 id to NEW). Bare major → (major, 0) → OLD.
        assert tokenizer_era(model_id) == OLD_ERA

    def test_dated_id_with_explicit_minor_still_classifies(self):
        # A minor DOES parse when present; trailing date is ignored.
        assert tokenizer_era("claude-sonnet-4-5-20250929") == OLD_ERA
        assert tokenizer_era("claude-opus-4-7-20260101") == NEW_ERA

    @pytest.mark.parametrize(
        "model_id",
        [None, "", "opus", "sonnet", "gpt-4o", "claude-unknownfamily-9"],
    )
    def test_unknown_when_version_absent_or_foreign(self, model_id):
        # A bare rank alias ("opus") has no fixed era — honest UNKNOWN, never a
        # guessed correction. Non-Claude / unparseable ids are UNKNOWN too.
        assert tokenizer_era(model_id) == UNKNOWN_ERA


class TestNormalizedTokenCount:
    """AC2 — cross-era correction; same-era untouched."""

    def test_same_era_is_identity(self):
        # Within one era the count is exact — no factor applied.
        assert normalized_token_count(1000, "claude-opus-4-8", target_era=NEW_ERA) == 1000.0
        assert normalized_token_count(1000, "claude-sonnet-4-6", target_era=OLD_ERA) == 1000.0

    def test_old_measured_scaled_up_to_new(self):
        # Old-tokenizer count expressed on the new-tokenizer scale grows ~30%.
        got = normalized_token_count(1000, "claude-sonnet-4-6", target_era=NEW_ERA)
        assert got == pytest.approx(1000 * NEW_TOKENIZER_INFLATION)

    def test_new_measured_scaled_down_to_old(self):
        got = normalized_token_count(1300, "claude-opus-4-8", target_era=OLD_ERA)
        assert got == pytest.approx(1300 / NEW_TOKENIZER_INFLATION)

    def test_unknown_era_never_corrected(self):
        # Never fabricate a correction for a model we cannot place.
        assert normalized_token_count(1000, "opus", target_era=NEW_ERA) == 1000.0


class TestEraNormalizedTotal:
    """AC2 — the cross-era comparison surface: aggregate honestly."""

    def test_single_era_total_undistorted(self):
        rows = [
            {"model_id": "claude-opus-4-8", "tokens_total": 1000},
            {"model_id": "claude-sonnet-5", "tokens_total": 500},
        ]
        # All new-era → normalized total equals the naive sum exactly.
        assert era_normalized_total(rows, target_era=NEW_ERA) == pytest.approx(1500.0)

    def test_cross_era_total_corrected(self):
        rows = [
            {"model_id": "claude-opus-4-8", "tokens_total": 1000},  # new
            {"model_id": "claude-sonnet-4-6", "tokens_total": 1000},  # old → *1.30
        ]
        naive = 2000.0
        got = era_normalized_total(rows, target_era=NEW_ERA)
        assert got == pytest.approx(1000 + 1000 * NEW_TOKENIZER_INFLATION)
        assert got > naive  # the correction is visible, not a no-op

    def test_unknown_rows_pass_through_uncorrected(self):
        rows = [{"model_id": "opus", "tokens_total": 1000}]
        assert era_normalized_total(rows, target_era=NEW_ERA) == pytest.approx(1000.0)


class TestLabelUsageRows:
    """AC1 — records get a derived tokenizer_era label (no schema column)."""

    def test_rows_labelled_without_mutating_input(self):
        rows = [
            {"model_id": "claude-opus-4-8", "tokens_total": 10},
            {"model_id": "claude-sonnet-4-6", "tokens_total": 20},
        ]
        labelled = label_usage_rows(rows)
        assert [r["tokenizer_era"] for r in labelled] == [NEW_ERA, OLD_ERA]
        # Original rows untouched.
        assert "tokenizer_era" not in rows[0]


class TestSumUsageTokens:
    """AC4 — compaction billed under usage.iterations is not lost."""

    def test_top_level_only(self):
        assert sum_usage_tokens({"input_tokens": 100, "output_tokens": 50}) == (100, 50)

    def test_iterations_added_to_top_level(self):
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "iterations": [
                {"input_tokens": 30, "output_tokens": 10},
                {"input_tokens": 5, "output_tokens": 2},
            ],
        }
        # Naive top-level-only sum would report (100, 50); compaction adds 35/12.
        assert sum_usage_tokens(usage) == (135, 62)

    def test_iterations_nested_under_usage_key(self):
        # Defensive: an iteration may carry its counts under a nested `usage`.
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "iterations": [{"usage": {"input_tokens": 40, "output_tokens": 20}}],
        }
        assert sum_usage_tokens(usage) == (140, 70)

    def test_malformed_inputs_are_zero_safe(self):
        assert sum_usage_tokens(None) == (0, 0)
        assert sum_usage_tokens({}) == (0, 0)
        assert sum_usage_tokens({"iterations": "not-a-list"}) == (0, 0)
        assert sum_usage_tokens({"input_tokens": None, "output_tokens": None}) == (0, 0)

    def test_non_numeric_field_does_not_raise(self):
        # s146 review HIGH: a stray non-numeric token value must yield 0, not a
        # ValueError up into the metrics hook (which parses per line, unguarded).
        assert sum_usage_tokens({"input_tokens": "N/A", "output_tokens": 5}) == (0, 5)
        assert sum_usage_tokens(
            {"input_tokens": 10, "output_tokens": 20, "iterations": [{"input_tokens": "oops"}]}
        ) == (10, 20)
