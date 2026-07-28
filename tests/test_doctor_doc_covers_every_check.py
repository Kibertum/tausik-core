"""Every check `doctor` can print must appear in the doctor docs.

The docs said "nine checks" and listed nine groups while the command had grown
to eighteen labels — and two checks that existed for months, `CLAUDE.md drift`
and `Config trust tier`, were documented nowhere at all. Nothing caught it,
because prose that restates a machine-readable fact drifts silently unless
something derives it (conventions #339, #340).

So the list is derived here rather than restated: the labels come out of the
source, and both language versions must mention each one. A new check that
nobody documents fails this test on the commit that adds it, which is the only
moment the omission is cheap to fix.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_DOCTOR_SRC = REPO / "scripts" / "project_cli_doctor.py"
_BACKLOG_SRC = REPO / "scripts" / "service_doctor_backlog.py"
_DOCS = (REPO / "docs" / "en" / "doctor.md", REPO / "docs" / "ru" / "doctor.md")

CROSSCUTTING_SCOPE = ["scripts/", "docs/"]

# Labels that are not user-facing checks: the transient/diagnostic lines.
_NOT_A_CHECK = {"caveman interop"}

# A label may be worded differently in prose than in the terminal. Map only
# where the doc legitimately says it another way; an empty mapping means the
# doc is expected to use the label verbatim.
_DOC_ALIASES = {
    "Kilo MCP config": ("Kilo",),
    "OpenCode config": ("OpenCode",),
    "Brain config": ("Brain",),
    "Verify-First profile": ("Verify-First",),
    "Config trust tier": ("Trust tier", "trust tier"),
    "MCP server (project)": ("MCP",),
    "MCP server (brain)": ("MCP",),
    "Project DB": ("DB",),
    "Python venv": ("venv",),
    "Config knobs": ("Knobs", "knobs"),
    "Quality gates": ("gates",),
}


def _labels() -> set[str]:
    """Check labels the doctor can print, read out of the source."""
    found: set[str] = set()
    pattern = re.compile(r"""_print_(?:ok|warn|fail)\(\s*["']([^"']+)["']""")
    for src in (_DOCTOR_SRC, _BACKLOG_SRC):
        found |= set(pattern.findall(src.read_text(encoding="utf-8")))
    # service_doctor_backlog hands its labels back as constants, not print calls.
    found |= set(
        re.findall(
            r"""^_\w*LABEL\s*=\s*["']([^"']+)["']""",
            _BACKLOG_SRC.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    return {label for label in found if label not in _NOT_A_CHECK}


def test_source_still_exposes_labels_to_read():
    """Guards the test itself: a refactor that renames the printer silently
    empties the label set and would make every assertion below vacuous."""
    assert len(_labels()) >= 12, f"suspiciously few labels parsed: {sorted(_labels())}"


def test_every_check_is_documented_in_both_languages():
    labels = _labels()
    missing: dict[str, list[str]] = {}
    for doc in _DOCS:
        text = doc.read_text(encoding="utf-8")
        for label in sorted(labels):
            candidates = (label, *_DOC_ALIASES.get(label, ()))
            if not any(c in text for c in candidates):
                missing.setdefault(doc.name, []).append(label)
    assert not missing, (
        "doctor can print these checks but the docs never mention them — "
        f"a reader cannot tell what the command verifies: {missing}"
    )


def test_docs_do_not_claim_a_fixed_number_of_checks():
    """The count was wrong for months precisely because it was written by hand.

    Some checks are conditional on what is installed, so no single number is
    even correct. Naming one invites the same drift back.
    """
    forbidden = re.compile(
        r"\b(nine|ten|eleven|twelve|девять|десять|одиннадцать|двенадцать)\s+"
        r"(checks|проверок|проверки)\b",
        re.IGNORECASE,
    )
    for doc in _DOCS:
        hit = forbidden.search(doc.read_text(encoding="utf-8"))
        assert not hit, (
            f"{doc.name} states a hand-written check count ({hit.group(0)!r}); "
            "list the checks instead — some are conditional, so no fixed number is right"
        )
