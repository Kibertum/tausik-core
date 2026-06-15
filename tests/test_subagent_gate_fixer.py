"""Tests for the tausik-gate-fixer Claude-native sub-agent (v14b-subagent-gate-fixer).

Covers:
- Sub-agent file exists at harness/claude/subagents/tausik-gate-fixer.md
- File size < 3KB (consistency with tausik-reviewer; proves docs are read at runtime)
- Frontmatter contract: name, model=sonnet, tools = Read+Grep+Bash (no Edit/Write/Agent)
- System prompt cites runtime-loaded docs (no embedded gate list)
- Plan-emission contract present (action vocabulary + 1-3 step cap)
- /debug SKILL.md mentions the auto-helper invocation pattern
"""

from __future__ import annotations

import os
import re

REPO = os.path.join(os.path.dirname(__file__), "..")
SUBAGENT_PATH = os.path.join(REPO, "harness", "claude", "subagents", "tausik-gate-fixer.md")
DEBUG_SKILL_PATH = os.path.join(REPO, "harness", "skills", "debug", "SKILL.md")

MAX_BYTES = 3 * 1024
FORBIDDEN_TOOLS = {"Edit", "Write", "Agent", "NotebookEdit"}
REQUIRED_TOOLS = {"Read", "Grep", "Bash"}

# AC #4: gate-fixer must read references AT RUNTIME, not embed them.
EXPECTED_DOC_REFS = [
    "docs/en/troubleshooting.md",
    "docs/en/architecture.md",
]


def test_gate_fixer_file_exists():
    assert os.path.isfile(SUBAGENT_PATH)


def test_gate_fixer_under_3kb():
    size = os.path.getsize(SUBAGENT_PATH)
    assert size < MAX_BYTES, (
        f"tausik-gate-fixer.md is {size} bytes, must be < {MAX_BYTES} for parity "
        f"with tausik-reviewer (read-from-docs invariant)."
    )


def _parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "tausik-gate-fixer.md must start with --- frontmatter ---"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def test_gate_fixer_frontmatter_contract():
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "tausik-gate-fixer"
    assert fm.get("model") == "sonnet"
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    assert REQUIRED_TOOLS <= tools, f"Missing required tools: {REQUIRED_TOOLS - tools}"
    forbidden = FORBIDDEN_TOOLS & tools
    assert not forbidden, (
        f"AC #1 forbids these tools (sub-agent must be read-only PLAN agent, "
        f"never apply edits): {forbidden}"
    )


def test_gate_fixer_cites_runtime_docs_not_embeds():
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    for path in EXPECTED_DOC_REFS:
        assert path in text, f"Sub-agent must cite '{path}' (read-at-runtime, no embed)."


def test_gate_fixer_emits_plan_with_action_vocabulary():
    """AC #3: returns 1-3 step fix plan with structured `action` field."""
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    # The action vocabulary must be present in the system prompt so the agent
    # picks one of the recognized verbs (avoids open-ended free-text actions).
    for action in ("edit", "extract_module", "add_test", "re_run_gate"):
        assert action in text, (
            f"action vocabulary item '{action}' missing — sub-agent must emit "
            f"one of the recognized verbs"
        )
    assert "1-3" in text or "three" in text.lower(), (
        "Plan length cap (1-3 steps) must be stated in the system prompt"
    )


def test_gate_fixer_returns_json_only():
    """Sub-agent must emit JSON, no prose — pin via prompt review."""
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    assert "JSON" in text or "json" in text
    # Must explicitly forbid prose around the JSON to keep main-context output clean.
    assert "no prose" in text.lower() or "nothing else" in text.lower(), (
        "Sub-agent must instruct 'no prose / nothing else' around JSON output"
    )


def test_debug_skill_mentions_gate_fixer_invocation():
    """AC #6: /debug skill SKILL.md updated to mention auto-helper."""
    text = open(DEBUG_SKILL_PATH, encoding="utf-8").read()
    assert "tausik-gate-fixer" in text, (
        "/debug SKILL.md must mention the tausik-gate-fixer auto-helper"
    )
    assert "subagent_type" in text, (
        "/debug SKILL.md must show the Agent invocation pattern with subagent_type"
    )
