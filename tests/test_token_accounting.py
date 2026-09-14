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
    """`usage.iterations` is the COMPLETE pass list, not the extra passes.

    These fixtures used to encode the opposite — `{100, iterations:[35]}` was
    asserted to be 135 — and the assumption was never checked against a real
    response. It is wrong: the top level is a VIEW of the list (equal to it at
    n=1, equal to its FIRST entry at n>1), so adding them double-counted the
    first pass. Measured over every transcript this project has, session #227:
    23,818 of 23,836 messages with usage (99.92%) carry exactly one iteration
    equal to the top level, and the old rule inflated the total by 1.9999x —
    straight into the LLM spend `tausik metrics` reports.

    Every fixture below is now the SHAPE OF A REAL RESPONSE, not an invented one.
    """

    def test_no_iterations_key_uses_the_top_level(self):
        assert sum_usage_tokens({"input_tokens": 100, "output_tokens": 50}) == (100, 50)

    def test_the_single_iteration_case_is_not_doubled(self):
        """THE defect, in the exact shape that covers 99.92% of messages.

        Taken verbatim from a live transcript: `input_tokens` is 2 because
        prompt caching moved the context into cache_read/cache_create, and the
        lone iteration repeats the same numbers.
        """
        usage = {
            "input_tokens": 2,
            "output_tokens": 72,
            "cache_read_input_tokens": 29855,
            "cache_creation_input_tokens": 20632,
            "iterations": [
                {
                    "input_tokens": 2,
                    "output_tokens": 72,
                    "cache_read_input_tokens": 29855,
                    "cache_creation_input_tokens": 20632,
                    "type": "message",
                }
            ],
        }
        assert sum_usage_tokens(usage) == (2, 72)
        assert sum_usage_tokens(usage) != (4, 144)  # what the old rule returned

    def test_compaction_is_still_counted_at_more_than_one_iteration(self):
        """The intent the old rule was written for, preserved.

        Real numbers from the 7 multi-iteration messages in the corpus: the top
        level reads 32/2905 and the two passes together are 64/3194. The extra
        pass is genuinely billed and must not be lost — but the total is the
        SUM OF THE PASSES, not the passes plus the first one again (96/6099).
        """
        usage = {
            "input_tokens": 32,
            "output_tokens": 2905,
            "iterations": [
                {"input_tokens": 32, "output_tokens": 2905},
                {"input_tokens": 32, "output_tokens": 289},
            ],
        }
        assert sum_usage_tokens(usage) == (64, 3194)

    def test_iterations_nested_under_usage_key(self):
        # Defensive: an iteration may carry its counts under a nested `usage`.
        usage = {
            "input_tokens": 40,
            "output_tokens": 20,
            "iterations": [{"usage": {"input_tokens": 40, "output_tokens": 20}}],
        }
        assert sum_usage_tokens(usage) == (40, 20)

    def test_empty_iterations_list_means_the_top_level(self):
        assert sum_usage_tokens({"input_tokens": 7, "output_tokens": 3, "iterations": []}) == (7, 3)

    def test_malformed_inputs_are_zero_safe(self):
        assert sum_usage_tokens(None) == (0, 0)
        assert sum_usage_tokens({}) == (0, 0)
        assert sum_usage_tokens({"iterations": "not-a-list"}) == (0, 0)
        assert sum_usage_tokens({"input_tokens": None, "output_tokens": None}) == (0, 0)
        assert sum_usage_tokens([1, 2, 3]) == (0, 0)

    def test_a_non_list_iterations_value_falls_back_to_the_top_level(self):
        for junk in ("not-a-list", 17, {"a": 1}, None):
            assert sum_usage_tokens(
                {"input_tokens": 11, "output_tokens": 5, "iterations": junk}
            ) == (11, 5)

    def test_non_numeric_field_does_not_raise(self):
        # s146 review HIGH: a stray non-numeric token value must yield 0, not a
        # ValueError up into the metrics hook (which parses per line, unguarded).
        assert sum_usage_tokens({"input_tokens": "N/A", "output_tokens": 5}) == (0, 5)

    def test_an_unreadable_iteration_list_reports_the_lower_bound_not_zero(self):
        """The top level is the first pass, so it is a floor, not a guess.

        A list we cannot read means we do not know the total; reporting 0 for a
        message we can plainly see was not free would be worse than reporting
        what we can read.
        """
        assert sum_usage_tokens(
            {"input_tokens": 10, "output_tokens": 20, "iterations": [{"input_tokens": "oops"}]}
        ) == (10, 20)
        assert sum_usage_tokens(
            {"input_tokens": 10, "output_tokens": 20, "iterations": ["not-a-dict", 5]}
        ) == (10, 20)

    def test_a_genuinely_free_message_stays_zero(self):
        assert sum_usage_tokens({"input_tokens": 0, "output_tokens": 0, "iterations": [{}]}) == (
            0,
            0,
        )

    def test_deeply_nested_junk_returns_ints_and_leaks_no_strings(self):
        """Transcript content is arbitrary user input; the result is numbers."""
        secret = "sk-ant-SUPERSECRET"
        got = sum_usage_tokens(
            {
                "input_tokens": {"nested": [secret]},
                "output_tokens": [secret],
                "iterations": [{"input_tokens": secret, "output_tokens": {"x": secret}}],
            }
        )
        assert got == (0, 0)
        assert all(isinstance(v, int) for v in got)
        assert secret not in repr(got)


class TestIterationsShapeAgainstLiveTranscripts:
    """The fixture assumption, re-checked against the source that produces it.

    The old rule was green for months because its fixtures were invented. This
    class reads the project's OWN transcripts and asserts the shape those
    fixtures now claim. It skips loudly when no transcript is reachable — a
    skip says the live check did not run, which is not the same as passing.
    """

    def _messages_with_usage(self):
        import json
        import os
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
        from transcript_locator import project_transcripts

        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        found = []
        for path in project_transcripts(root)[-4:]:
            try:
                handle = open(path, encoding="utf-8", errors="replace")
            except OSError:
                continue
            with handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if entry.get("type") != "assistant":
                        continue
                    msg = entry.get("message") if isinstance(entry.get("message"), dict) else {}
                    usage = entry.get("usage") or msg.get("usage") or {}
                    if isinstance(usage, dict) and usage:
                        found.append(usage)
        return found

    def test_a_single_iteration_repeats_the_top_level(self):
        import pytest

        usages = self._messages_with_usage()
        if not usages:
            pytest.skip("no project transcript reachable — live shape check not run")
        singles = [u for u in usages if isinstance(u.get("iterations"), list) and len(u["iterations"]) == 1]
        if not singles:
            pytest.skip("no single-iteration message in the sampled transcripts")
        mismatched = [
            u
            for u in singles
            if (
                int(u["iterations"][0].get("input_tokens") or 0) != int(u.get("input_tokens") or 0)
                or int(u["iterations"][0].get("output_tokens") or 0)
                != int(u.get("output_tokens") or 0)
            )
        ]
        assert not mismatched, (
            f"{len(mismatched)} of {len(singles)} single-iteration messages no longer repeat the "
            "top level. The API changed shape; sum_usage_tokens' rule must be re-derived from it, "
            "not adjusted by guess."
        )

    def test_the_rule_does_not_double_the_live_corpus(self):
        """The whole point, on real data: no message is counted twice."""
        import pytest

        usages = self._messages_with_usage()
        if not usages:
            pytest.skip("no project transcript reachable — live shape check not run")
        for usage in usages:
            got_in, got_out = sum_usage_tokens(usage)
            iters = usage.get("iterations")
            if isinstance(iters, list) and iters:
                ceiling_in = int(usage.get("input_tokens") or 0) + sum(
                    int((it.get("usage") or it).get("input_tokens") or 0)
                    for it in iters
                    if isinstance(it, dict)
                )
                assert got_in < ceiling_in or ceiling_in == 0, (
                    "input equals the old top-plus-iterations sum — the double count is back"
                )
