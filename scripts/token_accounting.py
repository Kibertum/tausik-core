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

    Top-level `input_tokens` / `output_tokens` omit compaction passes, which the
    API reports under `usage.iterations[*]` (each entry carrying its own counts,
    flat or under a nested `usage`). Summing only the top level understates the
    real token count. Malformed input is zero-safe — telemetry must never raise
    (a non-numeric field yields 0, not a ValueError up into the hook).
    """
    if not isinstance(usage, dict):
        return 0, 0
    ti = _as_int(usage.get("input_tokens"))
    to = _as_int(usage.get("output_tokens"))
    iters = usage.get("iterations")
    if isinstance(iters, list):
        for it in iters:
            iti, ito = _iter_tokens(it)
            ti += iti
            to += ito
    return ti, to
