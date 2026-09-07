"""Tokenizer-era classification + compaction-aware token accounting.

Two corrections the cost telemetry needs to count tokens honestly across the
model generations this project runs on (l26-tokenizer-calibration):

1. TOKENIZER ERA. Opus 4.7+, Fable 5, Mythos 5 and Sonnet 5 use a NEW tokenizer
   that emits roughly 30% more tokens for the same text than the prior one
   (Sonnet 4.6 / Opus 4.6 / Haiku 4.5 and older). A token or dollar comparison
   that straddles this boundary is invalid without a correction; a comparison
   inside one era is exact and must be left untouched. `tokenizer_era` places a
   model id on one side or the other (or UNKNOWN, when a bare rank alias or a
   foreign family gives no fixed answer — we never guess a correction), and
   `normalized_token_count` / `era_normalized_total` express counts on a common
   era's scale so cross-era totals become comparable.

   Scope note: the DB calibration signal (`backend_tier_metrics.calibration_drift`)
   is computed over `call_budget` / `call_actual` — TOOL-CALL COUNTS, which are
   integers independent of any tokenizer. The ~30% correction here therefore
   does NOT touch that signal; it applies only where TOKENS or DOLLARS are
   compared across the boundary (usage rollups, token budgets). See that
   module's docstring for the recorded calibration re-check.

2. SERVER-SIDE COMPACTION. The API bills compaction passes separately, under
   `usage.iterations[*]`; the top-level `input_tokens` / `output_tokens` do NOT
   include them. Summing only the top level understates the real (billed) count.
   `sum_usage_tokens` folds the iterations back in.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Era labels. Strings (not an Enum) so they cross the JSON/DB boundary and land
# in usage-row dicts without a serialization step.
NEW_ERA = "new"
OLD_ERA = "old"
UNKNOWN_ERA = "unknown"

# The new tokenizer emits ~30% more tokens for the same text. A multiplicative
# factor applied only across the era boundary; documented as an estimate, not a
# measured-per-model constant (there is no public per-model ratio). Kept as one
# named constant so a future measured value has exactly one place to change.
NEW_TOKENIZER_INFLATION = 1.30

#: Last session recorded by the DOUBLE-COUNTING arithmetic `sum_usage_tokens`
#: used before it was corrected. Every `session_usage_metrics` row at or below
#: this id was written by the old rule and is inflated by the measured 1.9999x
#: wherever the API reported `usage.iterations`; every row above it is right.
#:
#: This is a fact about the data, captured once, not a calendar date — the value
#: is `MAX(session_id)` at the moment of the fix, and sessions only go forward,
#: so it cannot rot the way a date-based threshold does (that is exactly how
#: Sonnet 5 was billed at another model's rate for months).
#:
#: The old rows are NOT rewritten. Transcripts survive for only 65 of the 227
#: sessions, so the correct value is unknowable for the rest; and the inflation
#: is not uniform — a session whose messages predate the `iterations` field was
#: never doubled at all, and without its transcript there is no way to tell
#: which is which. Halving blindly would corrupt the rows that were already
#: right, and correcting only the recoverable ones would put a THIRD scale in
#: the same column. The series is therefore left as it is and the report says
#: so; see `render_metrics._usage_lines`.
LAST_SESSION_ON_SUPERSEDED_TOKEN_ARITHMETIC = 227

# Family -> the minimum (major, minor) version that uses the NEW tokenizer. A
# model at or above the bound is NEW; strictly below is OLD. `None` means the
# family has no known new-tokenizer release yet — every shipped version is OLD.
# Haiku is None: only 4.5 has shipped and it predates the boundary; encoding a
# speculative future bound would invent a fact, so we classify what exists.
_NEW_TOKENIZER_MIN: dict[str, tuple[int, int] | None] = {
    "fable": (5, 0),
    "mythos": (5, 0),
    "sonnet": (5, 0),
    "opus": (4, 7),
    "haiku": None,
}

# `claude-opus-4-7`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`, with an
# optional leading `claude-`, an optional 1-2 digit `-<minor>`, and any trailing
# suffix (`[1m]`, a release date, etc.) ignored. A bare rank alias like `opus`
# has no digits and deliberately does not match — era is unknowable without a
# version. The minor group is capped at 1-2 digits AND guarded by `(?!\d)` so a
# bare-major dated id like `claude-opus-4-20250514` does NOT read its 8-digit
# date as the minor (that misparse flipped a real Opus-4 id to the NEW era —
# s146 review). Such an id parses as major-only → (4, 0) → OLD, correctly.
_FAMILY_VERSION_RE = re.compile(
    r"^(?:claude-)?(fable|mythos|opus|sonnet|haiku)-(\d+)(?:-(\d{1,2})(?!\d))?"
)


def tokenizer_era(model_id: str | None) -> str:
    """Classify a model id as NEW_ERA, OLD_ERA, or UNKNOWN_ERA.

    Case- and whitespace-insensitive. Returns UNKNOWN_ERA for a missing id, a
    bare rank alias (`opus`), or any family/version we cannot place — callers
    treat UNKNOWN as "apply no correction" rather than a guess.
    """
    m = _FAMILY_VERSION_RE.match(str(model_id or "").strip().lower())
    if not m:
        return UNKNOWN_ERA
    family, major, minor = m.group(1), int(m.group(2)), int(m.group(3) or 0)
    bound = _NEW_TOKENIZER_MIN.get(family)
    if bound is None:
        # `family` is always one of the regex's five alternatives, all keys of
        # _NEW_TOKENIZER_MIN — so bound is None ONLY for haiku (no new-tokenizer
        # release yet): every haiku version is OLD.
        return OLD_ERA
    return NEW_ERA if (major, minor) >= bound else OLD_ERA


def normalized_token_count(
    tokens: float, model_id: str | None, *, target_era: str = NEW_ERA
) -> float:
    """Express `tokens` (measured under `model_id`) on `target_era`'s scale.

    Same era, or an unknown model, returns the count unchanged — the correction
    is applied ONLY across a known boundary, so within-era comparisons stay
    exact. Old→new scales up by NEW_TOKENIZER_INFLATION; new→old scales down.
    """
    era = tokenizer_era(model_id)
    if era == UNKNOWN_ERA or target_era == UNKNOWN_ERA or era == target_era:
        return float(tokens)
    if era == OLD_ERA and target_era == NEW_ERA:
        return float(tokens) * NEW_TOKENIZER_INFLATION
    if era == NEW_ERA and target_era == OLD_ERA:
        return float(tokens) / NEW_TOKENIZER_INFLATION
    # Any other target (shouldn't happen) → no correction.
    return float(tokens)


def era_normalized_total(
    rows: Iterable[dict[str, Any]],
    *,
    target_era: str = NEW_ERA,
    model_key: str = "model_id",
    token_key: str = "tokens_total",
) -> float:
    """Sum a set of usage rows with each row normalized to `target_era`.

    The honest way to compare or trend token totals that span the tokenizer
    boundary: a single-era set returns exactly the naive sum (no distortion),
    a mixed set applies the ~30% correction to the off-era rows only.
    """
    total = 0.0
    for r in rows:
        try:
            tokens = float(r.get(token_key) or 0)
        except (TypeError, ValueError):
            tokens = 0.0
        total += normalized_token_count(tokens, r.get(model_key), target_era=target_era)
    return total


def label_usage_rows(
    rows: Iterable[dict[str, Any]], *, model_key: str = "model_id"
) -> list[dict[str, Any]]:
    """Return copies of `rows` each carrying a derived `tokenizer_era` label.

    "Marking" historical records without a schema column: the era is a pure
    function of the already-stored `model_id`, so it is derived on read rather
    than persisted (a stored copy could only drift from the classifier). Input
    rows are not mutated.
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        copy = dict(r)
        copy["tokenizer_era"] = tokenizer_era(r.get(model_key))
        out.append(copy)
    return out


def _as_int(value: Any) -> int:
    """`int(value)` or 0 — a non-numeric field must never raise (zero-safe).

    A malformed token field (e.g. a stray `"N/A"` string somewhere in a
    transcript) must not crash the metrics hook, which parses per line with no
    surrounding guard. Falsy (None/0/"") already yields 0.
    """
    if not value:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _iter_tokens(entry: Any) -> tuple[int, int]:
    """(input, output) from an iteration entry, whether flat or nested `usage`."""
    if not isinstance(entry, dict):
        return 0, 0
    nested = entry.get("usage")
    src = nested if isinstance(nested, dict) else entry
    return _as_int(src.get("input_tokens")), _as_int(src.get("output_tokens"))


def sum_usage_tokens(usage: Any) -> tuple[int, int]:
    """(input, output) tokens INCLUDING separately-billed server-side compaction.

    `usage.iterations` is the COMPLETE list of passes the API billed for this
    message — the first pass included, not excluded. The top level is a VIEW of
    that list, not a separate quantity: with one iteration it equals it exactly,
    and with several it equals the FIRST one. So the total is the sum over
    `iterations` when the list is non-empty, and the top level when there is no
    list at all.

    This function used to ADD the two, on the assumption that `iterations` held
    only the extra compaction passes. Measured against every transcript this
    project has (session #227, 23,836 messages with usage): 23,818 of them
    — 99.92% — carry exactly one iteration whose fields equal the top level
    character for character, so the old rule returned exactly DOUBLE. The
    measured inflation was 1.9999x on the total, and it reached
    `tokens_input` / `tokens_output` / `cost_usd` in `session_usage_metrics`,
    which is what `tausik metrics` reports as this project's LLM spend.

    The original INTENT was right and is preserved: compaction passes are real
    and are billed separately. The 7 multi-iteration messages in that corpus
    contribute 2,247 tokens that the top level alone would miss (top 32/2905
    against an iteration sum of 64/3194) — this rule still counts them. What it
    stops doing is counting the first pass twice.

    Malformed input is zero-safe — telemetry must never raise (a non-numeric
    field yields 0, not a ValueError up into the hook).
    """
    if not isinstance(usage, dict):
        return 0, 0
    top = (_as_int(usage.get("input_tokens")), _as_int(usage.get("output_tokens")))
    iters = usage.get("iterations")
    if not isinstance(iters, list) or not iters:
        return top
    ti = to = 0
    for it in iters:
        iti, ito = _iter_tokens(it)
        ti += iti
        to += ito
    if (ti, to) == (0, 0) and top != (0, 0):
        # The list is present but unreadable — entries that are not dicts, or
        # whose counts are non-numeric. The top level is the FIRST pass, so it
        # is a lower bound on the truth; reporting it beats reporting zero for a
        # message we can plainly see was not free.
        return top
    return ti, to
