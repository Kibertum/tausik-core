"""Uniformity guards: shipped text may not make a claim the project retired.

The project keeps two retired claims out by TEST, not by one-off sweeps. A
sweep fixes the instances; a guard fixes the form, because the next file
quoting an old doc or skill would otherwise reintroduce the dead rule by
drift.

Guard 1 — the L3 selector describes evidence (decision #212). No shipped text
may call it a risk verdict: the backtest in
docs/ru/research/risk-model-backtest-2026-07.md measured AUC 0.4820 over 374
closures, i.e. the composite does not separate closures a defect escaped from
those it did not. The reframing reached the gate message, the compliance
matrix and part of `agent-contract`, and stopped there — eight other places
went on calling the same closure "high-risk", which is precisely the claim the
measurement refuted.

Guard 2 — one model family per environment (1.11.6). Until 1.11.6 SENAR Rule
4 required the L3 reviewer to run on a DIFFERENT model family, and
unavailability of one stopped the ship ("stop; never downgrade"). That
boundary is inverted: the reviewer runs on the host's own model in an
isolated read-only context, and pulling another family is refused.

SOURCES ONLY. `.claude/`, `.cursor/` and friends are bootstrap COPIES — they
are regenerated from these files, so flagging them would report one defect
many times and be "fixed" by a rebuild rather than by an edit.
"""

from __future__ import annotations

import os
import re

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Both guards sweep the whole tree, so no filename maps them to any one module
# and the resolver would leave them out of every scoped verify — see
# `verify-certifies-a-run-that-touched-no-test-of-the-subject`. Declared
# against the modules that actually CARRY the claims, so a change to any of
# them runs the guards rather than merely hoping the full suite does.
CROSSCUTTING_SCOPE = [
    "scripts/risk_l3_trigger.py",
    "scripts/risk_metrics.py",
    "scripts/config_trust.py",
    "scripts/external_reviewer.py",
    "scripts/review_separation.py",
    "scripts/review_routing.py",
    "scripts/project_parser_review.py",
    "docs/",
    "harness/",
    "README.md",
    "README.ru.md",
]

# Phrases that frame the selector as a prediction about danger rather than a
# description of evidence. Russian spellings are here for the same reason the
# mirrors exist: a claim is no less false for being made in the other language.
_FRAMING_FORBIDDEN = (
    re.compile(r"high[- ]risk\s+clos", re.IGNORECASE),
    re.compile(r"high[- ]risk\s+task", re.IGNORECASE),
    re.compile(r"Recent high-risk"),
    re.compile(r"high-risk\s+закрыти", re.IGNORECASE),
    re.compile(r"при\s+high-risk", re.IGNORECASE),
    re.compile(r"закрыти\w*\s+высокого\s+риска", re.IGNORECASE),
)

# Phrases that demand or describe the pre-1.11.6 cross-model review boundary.
# The legacy DB token 'different-model' is NOT here: code must keep reading
# historical records that carry it.
_FAMILY_FORBIDDEN = (
    re.compile(r"different\s+model\s+family", re.IGNORECASE),
    re.compile(r"different-family\s+reviewer", re.IGNORECASE),
    re.compile(r"a\s+different\s+model\s+(than|from)", re.IGNORECASE),
    re.compile(r"requires?\s+a\s+different\s+model", re.IGNORECASE),
    re.compile(r"never\s+downgrade(?![a-z])", re.IGNORECASE),
    re.compile(r"ревью\s+на\s+другой\s+модели", re.IGNORECASE),
    re.compile(r"другой\s+модел\w+,?\s+чем\s+у\s+автора", re.IGNORECASE),
)

# One entry per retired claim: (id, forbidden patterns, samples that must fire,
# replacement samples that must NOT be flagged, refusal message).
_RETIRED_CLAIMS = [
    (
        "risk-framing",
        _FRAMING_FORBIDDEN,
        (
            "blocks a high-risk closure until",
            "close a high-risk task",
            "Recent high-risk: a, b",
            "блокирует high-risk закрытие до записи",
            "| Hard (при high-risk) |",
            "требование внешнего L3-ревью при закрытии высокого риска",
        ),
        (
            "blocks an under-evidenced closure until an L3 review is recorded",
            "close an under-evidenced task",
            "Recent under-evidenced: a, b",
            "блокирует закрытие с тонким доказательством до записи L3-ревью",
            "| Hard (при тонком доказательстве) |",
            "требование внешнего L3-ревью при закрытии с тонким доказательством",
        ),
        "These call the L3 selector a risk verdict. The composite was measured "
        "and does NOT discriminate (AUC 0.4820, decision #212) — it describes "
        "how thin the evidence is. Say 'under-evidenced closure' (EN) or "
        "'закрытие с тонким доказательством' (RU).",
    ),
    (
        "one-family",
        _FAMILY_FORBIDDEN,
        (
            "one external reviewer on a different model family via",
            "review on a different model than the author",
            "L3 requires a different model from the author's",
            "If a different model is unavailable, stop; never downgrade.",
            "требует ревью на другой модели",
            "другой моделью, чем у автора",
        ),
        (
            "one external reviewer on the SAME model family (the host's own model)",
            "pulling another family for review is prohibited",
            "a reviewer from ANOTHER model family than the author's is refused",
            "запрещено дергать другое семейство для ревью",
            "reviewer_context TEXT NOT NULL CHECK(reviewer_context IN "
            "('external', 'different-model'))",
        ),
        "These demand or describe the pre-1.11.6 cross-model review boundary. "
        "Since 1.11.6 one model family runs per environment: the reviewer is "
        "the host's own model in an isolated read-only context, and pulling "
        "another family is prohibited.",
    ),
]

_SEARCH_ROOTS = ("scripts", "docs", "harness", "bootstrap")
_SEARCH_FILES = ("README.md", "README.ru.md", "CLAUDE.md")
_EXTENSIONS = (".py", ".md", ".json", ".yaml", ".yml", ".toml")

# Directories whose text is a record of the past rather than a claim about the
# present. A research note reporting what the audit SAW is not made true or
# false by a later rename, and editing it would corrupt the record.
_HISTORICAL = (
    os.path.join("docs", "en", "research"),
    os.path.join("docs", "ru", "research"),
)

_SKIP_DIRS = {"__pycache__", "node_modules", ".git", "vendor"}


def _candidate_files() -> list[str]:
    found: list[str] = []
    for name in _SEARCH_FILES:
        path = os.path.join(REPO, name)
        if os.path.isfile(path):
            found.append(path)
    for root_name in _SEARCH_ROOTS:
        root = os.path.join(REPO, root_name)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            rel_dir = os.path.relpath(dirpath, REPO)
            if any(rel_dir.startswith(h) for h in _HISTORICAL):
                continue
            for filename in filenames:
                if filename.endswith(_EXTENSIONS):
                    found.append(os.path.join(dirpath, filename))
    return found


def _offenders(forbidden: tuple[re.Pattern[str], ...]) -> list[str]:
    hits: list[str] = []
    for path in _candidate_files():
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.readlines()
        except (OSError, UnicodeDecodeError):
            # Named, not skipped: a file this cannot read is a file this cannot
            # vouch for, and silently dropping it would narrow the guard's reach
            # without narrowing its claim.
            hits.append(f"{os.path.relpath(path, REPO)}: UNREADABLE")
            continue
        for number, line in enumerate(lines, 1):
            for pattern in forbidden:
                if pattern.search(line):
                    hits.append(f"{os.path.relpath(path, REPO)}:{number}: {line.strip()[:120]}")
                    break
    return hits


@pytest.mark.parametrize("claim", _RETIRED_CLAIMS, ids=[c[0] for c in _RETIRED_CLAIMS])
def test_no_shipped_text_makes_a_retired_claim(claim):
    _, forbidden, _, _, message = claim
    offenders = _offenders(forbidden)
    assert not offenders, f"{message}\n" + "\n".join(offenders)


def test_the_guard_actually_scans_something():
    """A guard whose file list is empty passes forever and proves nothing."""
    files = _candidate_files()
    assert len(files) > 100, f"the sweep found only {len(files)} files to check"
    rel = {os.path.relpath(p, REPO).replace("\\", "/") for p in files}
    for expected in (
        "scripts/risk_l3_trigger.py",
        "scripts/risk_metrics.py",
        "scripts/review_separation.py",
        "scripts/external_reviewer.py",
        "docs/en/senar.md",
        "docs/ru/senar.md",
        "docs/en/workflow.md",
        "README.md",
        "harness/claude/subagents/tausik-external-reviewer.md",
    ):
        assert expected in rel, f"{expected} is not in the swept set"


@pytest.mark.parametrize("claim", _RETIRED_CLAIMS, ids=[c[0] for c in _RETIRED_CLAIMS])
def test_the_patterns_would_actually_fire(claim):
    """The other half: patterns that match nothing would also pass forever."""
    _, forbidden, fire, _, _ = claim
    for sample in fire:
        assert any(p.search(sample) for p in forbidden), f"nothing matched: {sample}"


@pytest.mark.parametrize("claim", _RETIRED_CLAIMS, ids=[c[0] for c in _RETIRED_CLAIMS])
def test_the_replacement_wording_is_not_itself_flagged(claim):
    """A guard that rejects the fix would make the fix unlandable."""
    _, forbidden, _, safe, _ = claim
    for sample in safe:
        assert not any(p.search(sample) for p in forbidden), f"wrongly flagged: {sample}"
