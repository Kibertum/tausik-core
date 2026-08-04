"""The L3 selector describes evidence. No shipped text may call it a risk verdict.

Decision #212 measured the composite and found it does not discriminate (AUC
0.4820), so the escalation was reframed: the number says how THIN the evidence
for a closure is, not how likely a defect is to escape. The reframing reached
the gate message, the compliance matrix and part of `agent-contract`, and stopped
there — eight other places went on calling the same closure "high-risk", which is
precisely the claim the measurement refuted.

That is why this is a TEST and not a one-off sweep. Decision #206 was itself
about a number presented as a verdict being read as a verdict; fixing the wording
by hand leaves the ninth occurrence to be written next week by someone reading
the eighth. A sweep fixes the instances, a guard fixes the form.

SOURCES ONLY. `.claude/`, `.cursor/` and friends are bootstrap COPIES — they are
regenerated from these files, so flagging them would report one defect many
times and be "fixed" by a rebuild rather than by an edit.
"""

from __future__ import annotations

import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# This guard sweeps the whole tree, so no filename maps it to any one module and
# the resolver would leave it out of every scoped verify — see
# `verify-certifies-a-run-that-touched-no-test-of-the-subject`. Declared against
# the modules that actually PRINT the framing, so a change to any of them runs
# the guard rather than merely hoping the full suite does.
CROSSCUTTING_SCOPE = [
    "scripts/risk_l3_trigger.py",
    "scripts/risk_metrics.py",
    "scripts/config_trust.py",
    "scripts/external_reviewer.py",
    "docs/",
    "harness/",
    "README.md",
    "README.ru.md",
]

# Phrases that frame the selector as a prediction about danger rather than a
# description of evidence. Russian spellings are here for the same reason the
# mirrors exist: a claim is no less false for being made in the other language.
_FORBIDDEN = (
    re.compile(r"high[- ]risk\s+clos", re.IGNORECASE),
    re.compile(r"high[- ]risk\s+task", re.IGNORECASE),
    re.compile(r"Recent high-risk"),
    re.compile(r"high-risk\s+закрыти", re.IGNORECASE),
    re.compile(r"при\s+high-risk", re.IGNORECASE),
    re.compile(r"закрыти\w*\s+высокого\s+риска", re.IGNORECASE),
)

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


def _offenders() -> list[str]:
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
            for pattern in _FORBIDDEN:
                if pattern.search(line):
                    hits.append(f"{os.path.relpath(path, REPO)}:{number}: {line.strip()[:120]}")
                    break
    return hits


def test_no_shipped_text_calls_an_under_evidenced_closure_high_risk():
    offenders = _offenders()
    assert not offenders, (
        "These call the L3 selector a risk verdict. The composite was measured and "
        "does NOT discriminate (AUC 0.4820, decision #212) — it describes how thin "
        "the evidence is. Say 'under-evidenced closure' (EN) or 'закрытие с тонким "
        "доказательством' (RU).\n" + "\n".join(offenders)
    )


def test_the_guard_actually_scans_something():
    """A guard whose file list is empty passes forever and proves nothing."""
    files = _candidate_files()
    assert len(files) > 100, f"the sweep found only {len(files)} files to check"
    rel = {os.path.relpath(p, REPO).replace("\\", "/") for p in files}
    for expected in (
        "scripts/risk_l3_trigger.py",
        "scripts/risk_metrics.py",
        "docs/en/senar.md",
        "docs/ru/senar.md",
        "README.md",
        "harness/claude/subagents/tausik-external-reviewer.md",
    ):
        assert expected in rel, f"{expected} is not in the swept set"


def test_the_patterns_would_actually_fire():
    """The other half: patterns that match nothing would also pass forever."""
    for sample in (
        "blocks a high-risk closure until",
        "close a high-risk task",
        "Recent high-risk: a, b",
        "блокирует high-risk закрытие до записи",
        "| Hard (при high-risk) |",
        "требование внешнего L3-ревью при закрытии высокого риска",
    ):
        assert any(p.search(sample) for p in _FORBIDDEN), f"nothing matched: {sample}"


def test_the_replacement_wording_is_not_itself_flagged():
    """A guard that rejects the fix would make the fix unlandable."""
    for sample in (
        "blocks an under-evidenced closure until an L3 review is recorded",
        "close an under-evidenced task",
        "Recent under-evidenced: a, b",
        "блокирует закрытие с тонким доказательством до записи L3-ревью",
        "| Hard (при тонком доказательстве) |",
        "требование внешнего L3-ревью при закрытии с тонким доказательством",
    ):
        assert not any(p.search(sample) for p in _FORBIDDEN), f"wrongly flagged: {sample}"
