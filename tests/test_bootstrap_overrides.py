"""r14-overrides-integration: harness/overrides/{ide}/rules.md is wired
into the generated CLAUDE.md / .cursorrules / QWEN.md.

The audit found the override files exist on disk but no generator was
reading them — they were "documented but unused", a load-bearing-looking
extension point that silently no-ops. v1.4 wires `build_full_body` to
optionally append the IDE-specific block right before the DYNAMIC state
section, and the existing generators pass `ide=...` so each rendered
file carries its host's overrides.

These tests pin the contract:
1. `build_full_body(ide="claude")` includes the Claude override marker.
2. Same for cursor / qwen.
3. `ide=None` (used by AGENTS.md, which is meant to be host-agnostic)
    intentionally drops the override block.
4. Missing override file is non-fatal — no traceback, no garbage section
    header, just an empty append.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "bootstrap"))


@pytest.fixture
def build():
    from bootstrap_templates import build_full_body

    return build_full_body


@pytest.mark.parametrize("ide", ["claude", "cursor", "qwen"])
def test_overrides_block_present_for_known_ide(build, ide):
    body = build("p", ["python"], "agent", ".claude", ide=ide)
    assert f"## IDE-specific overrides ({ide})" in body, (
        f"override section missing for ide={ide}"
    )


def test_claude_override_carries_claude_specific_text(build):
    body = build("p", ["python"], "agent", ".claude", ide="claude")
    # Sanity: pull a short, stable phrase from harness/overrides/claude/rules.md
    # so we know the actual file content reached the rendered body, not just
    # the section header.
    assert "AskUserQuestion" in body or "dedicated tools" in body


def test_cursor_override_section_appears_before_dynamic_block(build):
    body = build("p", ["python"], "agent", ".cursor", ide="cursor")
    cursor_idx = body.find("## IDE-specific overrides (cursor)")
    dynamic_idx = body.find("<!-- DYNAMIC:START -->")
    assert cursor_idx > 0
    assert dynamic_idx > cursor_idx, (
        "override block must precede DYNAMIC state so doctor's drift "
        "checker still treats user-side state as the tail it can ignore"
    )


def test_no_override_block_when_ide_is_none(build):
    body = build("p", ["python"], "agent", ".claude", ide=None)
    assert "## IDE-specific overrides" not in body


def test_unknown_ide_yields_no_section(build):
    body = build("p", ["python"], "agent", ".claude", ide="totally-not-a-real-ide")
    assert "## IDE-specific overrides" not in body


def test_default_ide_arg_is_none_for_backward_compat(build):
    """Existing callers (e.g. AGENTS.md) that didn't pass `ide` keep working."""
    body = build("p", ["python"], "agent", ".claude")
    assert "## IDE-specific overrides" not in body
    assert "Hard Constraints" in body
