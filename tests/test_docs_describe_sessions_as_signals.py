"""Docs do not promise a refusal where 1.10 gives advice (story E, decision #376).

Before this task 38 lines across docs, skills, CLAUDE.md and the consumer
template described the session limit as "hard block after 180 minutes", the
capacity gate as refusing a start, and checkpoints as "every 30–50 calls".
Since 1.10 time, capacity and the checkpoint are signals.
"""

from __future__ import annotations

from pathlib import Path

import glob
import os
import re

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROSSCUTTING_SCOPE = ["docs/", "harness/skills/", "CLAUDE.md", "bootstrap/bootstrap_templates.py"]

_BLOCK = re.compile(
    r"(\bblocks?\b|\bblocked\b|hard block|блокиру|жёсткая блокировка|отказывает)", re.I
)
_SESSION = re.compile(r"(session limit|лимит сессии|capacity|ёмкост|180[ -]?(min|мин))", re.I)
_NEGATED = re.compile(
    r"(не отказывает|never refuses|refuses nothing|not a refusal|no refusal|без отказа|не отказ|never blocks)",
    re.I,
)


def _pages() -> list[str]:
    pages = glob.glob(os.path.join(_ROOT, "docs", "ru", "*.md")) + glob.glob(
        os.path.join(_ROOT, "docs", "en", "*.md")
    )
    return [p for p in pages if "whats-new" not in p]


def test_no_page_promises_a_session_refusal():
    offenders = []
    for page in _pages():
        for n, line in enumerate(Path(page).read_text(encoding="utf-8").splitlines(), 1):
            if _BLOCK.search(line) and _SESSION.search(line) and not _NEGATED.search(line):
                offenders.append(f"{os.path.relpath(page, _ROOT)}:{n}: {line.strip()[:120]}")
    assert not offenders, "\n".join(offenders)


def test_the_detector_would_catch_the_old_wording():
    """NEGATIVE: the scan is not vacuous — the pre-1.10 sentence is caught."""
    old = "| Rule 9.2 | Session time limit | Hard block after 180 minutes |"
    assert _BLOCK.search(old) and _SESSION.search(old) and not _NEGATED.search(old)


def test_no_hand_typed_checkpoint_interval_remains():
    targets = _pages() + glob.glob(os.path.join(_ROOT, "harness", "skills", "*", "SKILL.md"))
    targets += [
        os.path.join(_ROOT, "CLAUDE.md"),
        os.path.join(_ROOT, "bootstrap", "bootstrap_templates.py"),
    ]
    hits = [
        os.path.relpath(p, _ROOT)
        for p in targets
        if re.search(r"30[-–]50 (tool )?(calls|вызов)", Path(p).read_text(encoding="utf-8"))
    ]
    assert not hits, hits
