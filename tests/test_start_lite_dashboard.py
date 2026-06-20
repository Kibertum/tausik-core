"""Tests for /start --lite Mode (v14b-start-lite-tool-truncation, AC #1 + #4).

Lite mode is a SKILL.md instruction shift, not a code path — so the test
pins the contract by inspecting the SKILL.md content:

- The Lite Mode section exists and is documented.
- The trigger argument is `--lite` (or bare `lite`).
- Lite mode promises ≤ 50 lines output.
- Default `/start` flow is preserved (no breaking change).
"""

from __future__ import annotations

import os
import re

REPO = os.path.join(os.path.dirname(__file__), "..")
START_SKILL = os.path.join(REPO, "harness", "skills", "start", "SKILL.md")


def test_start_skill_exists():
    assert os.path.isfile(START_SKILL)


def test_lite_mode_section_documented():
    text = open(START_SKILL, encoding="utf-8").read()
    assert "Lite mode" in text or "lite mode" in text.lower(), (
        "/start SKILL.md must document Lite mode (AC #1)"
    )


def test_lite_mode_trigger_is_lite_flag():
    text = open(START_SKILL, encoding="utf-8").read()
    # Either the `--lite` flag or bare `lite` arg must be the trigger.
    has_flag = "--lite" in text or "/start --lite" in text
    has_bare = re.search(r"`/start lite`|`lite`", text) is not None
    assert has_flag or has_bare, (
        "/start SKILL.md must specify the Lite mode trigger (--lite or `lite` arg)"
    )


def test_lite_mode_documents_50_line_cap():
    text = open(START_SKILL, encoding="utf-8").read()
    # AC #4: lite mode output ≤ 50 lines on a real session.
    assert "50 lines" in text or "≤ 50" in text or "<= 50" in text, (
        "Lite mode contract must state the ≤ 50-line cap (AC #4)"
    )


def test_default_dashboard_section_preserved():
    """Regression: AC #1 says default /start is unchanged."""
    text = open(START_SKILL, encoding="utf-8").read()
    # The default Phase 3 dashboard listing (6 numbered render steps) must remain.
    assert "Phase 3 — Present Dashboard" in text
    # The default render contract still mentions the 6 ordered sections.
    for keyword in ("MCP Health", "Session", "Active tasks", "Blocked tasks"):
        assert keyword in text, f"Default dashboard section '{keyword}' was removed"
