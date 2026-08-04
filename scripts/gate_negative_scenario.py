"""QG-0 negative-scenario detection (v1.3.4 med-batch-2-qg #1).

Old detector did `kw in ac_text` substring match — "Works without errors"
satisfied the gate because "error" substring was present. This module
provides a boundary-aware replacement that splits AC into per-criterion
lines (handling inline `1. ... 2. ...` numbering), redacts negation
phrases ("no", "without", "never", "нет", "без", "не должно") plus their
~60-char span, then looks for surviving NEGATIVE_SCENARIO_KEYWORDS
matches at word boundaries.

Lives separately from `service_gates.py` for filesize-gate compliance.
"""

from __future__ import annotations

import re


NEGATIVE_SCENARIO_KEYWORDS = (
    "error",
    "fail",
    "invalid",
    "reject",
    "401",
    "403",
    "404",
    "422",
    "500",
    "ошибк",
    "невалидн",
    "отказ",
    "некорректн",
    "пуст",
    "отсутств",
    "not found",
    "denied",
    "unauthorized",
    "timeout",
    "empty",
    "missing",
    "negative",
    "не должн",
    "не может",
    "запрещ",
    "блокир",
    "exceed",
    "overflow",
    "refuse",
    "forbid",
    "block",
    "deny",
    "break",
    "crash",
    "exception",
    # Russian parity (qg0-negative-detector-russian-parity, convention #170): the
    # working language is Russian, but several English markers above had no
    # Russian counterpart, so a criterion that named its negative case in Russian
    # ("НЕГАТИВ: ...") failed QG-0. Each of these mirrors an English keyword
    # already in the list — additive, no new failure mode.
    "негатив",  # negative
    "таймаут",  # timeout
    "исключени",  # exception (исключение/исключения)
    "паден",  # crash (падение/упал)
    "крах",  # crash
    "превыш",  # exceed (превышение/превышен)
    "переполн",  # overflow (переполнение)
    # qg0-negative-detector-does-not-know-the-word-negative (#301): the
    # task-done evidence detector `ac_evidence_detectors.NEGATIVE_RE` matches the
    # negative-WORD family `negative | негативн | отрицательн`, but QG-0 knew only
    # the first two — so a criterion naming its negative case as "отрицательный"
    # passed the evidence check yet was BLOCKED at start. The two are pinned to
    # agree by `test_negative_word_parity_with_evidence_detector`; keep this stem
    # here (and add any new NEGATIVE_RE form) so they never diverge again.
    "отрицательн",  # negative (отрицательный/отрицательное)
)


_NEG_KW_RE = re.compile(
    r"(?<![\w])(?:" + "|".join(re.escape(k) for k in NEGATIVE_SCENARIO_KEYWORDS) + r")",
    re.IGNORECASE,
)
# Negation prefix that *cancels* a negative keyword on the same line. The
# match consumes up to the next sentence boundary (.,;\n) or 60 non-sentence
# chars so the keyword the negation governs gets redacted along with it.
# "Works without any errors expected" → fully consumed, leaving "Works".
_NEG_NEGATION_RE = re.compile(
    r"\b(?:no|without|never|нет|без|никогда|не\s+должно?\s+быть)\b[^.;\n]{0,60}",
    re.IGNORECASE,
)


def _split_ac_into_criteria(ac_text: str) -> list[str]:
    """Split AC into per-criterion lines.

    Two separators recognized:
      - newlines (most natural)
      - inline numbering "1." "2." "3." etc. (single-line ACs the user
        wrote without breaks: "AC: 1.Works 2.Errors handled")
    """
    if not ac_text:
        return []
    normalized = re.sub(r"\s*(?:^|[^.\d])(\d+)[.)]\s+", r"\n\1. ", ac_text)
    return [ln.strip() for ln in normalized.splitlines() if ln.strip()]


def has_negative_scenario(ac_text: str) -> bool:
    """True iff AC articulates at least one negative scenario.

    Per-line scan: a line counts iff it contains a NEGATIVE_SCENARIO_KEYWORDS
    keyword with word-boundary AND that keyword is NOT immediately preceded
    by a negation phrase on the same line.

    Empty AC returns False (caller decides whether to error or warn).
    """
    if not ac_text:
        return False
    for line in _split_ac_into_criteria(ac_text):
        stripped = _NEG_NEGATION_RE.sub(" ", line)
        if _NEG_KW_RE.search(stripped):
            return True
    return False
