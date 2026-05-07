"""Tests for the tausik-reviewer Claude-native sub-agent (v14b-subagent-reviewer).

Covers:
- Sub-agent file exists at harness/claude/subagents/tausik-reviewer.md
- File size < 3KB (AC #4 — proves docs are read at runtime, not embedded)
- Frontmatter contract: name, model=sonnet, tools = Read+Grep+Bash (no Edit/Write/Agent)
- System prompt references the 3 runtime-loaded rubric docs
- bootstrap_copy.copy_subagents() deploys it to <target>/agents/ for Claude only
"""

from __future__ import annotations

import os
import re
import sys
import tempfile

import pytest

REPO = os.path.join(os.path.dirname(__file__), "..")
SUBAGENT_PATH = os.path.join(REPO, "harness", "claude", "subagents", "tausik-reviewer.md")
BOOTSTRAP_DIR = os.path.join(REPO, "bootstrap")

# AC #4: "verified by sub-agent file size < 3KB"
MAX_BYTES = 3 * 1024

# Forbidden tools — sub-agent must be read-only (no mutation, no nested Agent fork).
FORBIDDEN_TOOLS = {"Edit", "Write", "Agent", "NotebookEdit"}
# Required at minimum: Read (load files), Grep (locate symbols), Bash (run git diff).
REQUIRED_TOOLS = {"Read", "Grep", "Bash"}

# Runtime-loaded rubric docs the sub-agent MUST cite (the AC explicitly forbids embedding them).
EXPECTED_DOC_REFS = [
    "harness/skills/review/agents/quality.md",
    "docs/en/security.md",
    "docs/en/security-checklist.md",
]


# --- File-level checks -------------------------------------------------------


def test_subagent_file_exists():
    assert os.path.isfile(SUBAGENT_PATH), (
        f"Missing {SUBAGENT_PATH}: bootstrap cannot deploy what does not exist."
    )


def test_subagent_under_3kb():
    size = os.path.getsize(SUBAGENT_PATH)
    assert size < MAX_BYTES, (
        f"tausik-reviewer.md is {size} bytes, AC #4 requires < {MAX_BYTES}. "
        f"Trim prose or push more guidance into the runtime-loaded rubric docs."
    )


# --- Frontmatter contract ----------------------------------------------------


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML frontmatter parser — enough for name/description/tools/model."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "tausik-reviewer.md must start with --- frontmatter ---"
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def test_subagent_frontmatter_contract():
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "tausik-reviewer"
    assert fm.get("model") == "sonnet", (
        "AC #1 fixes model=sonnet — opus is overkill for read-only review."
    )
    tools_raw = fm.get("tools", "")
    tools = {t.strip() for t in tools_raw.split(",") if t.strip()}
    missing = REQUIRED_TOOLS - tools
    assert not missing, f"Missing required tools: {missing}"
    forbidden_present = FORBIDDEN_TOOLS & tools
    assert not forbidden_present, (
        f"AC #1 forbids these tools (sub-agent must be read-only): {forbidden_present}"
    )


# --- Runtime doc loading (anti-embed check) ----------------------------------


def test_subagent_cites_runtime_docs_not_embeds():
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    for path in EXPECTED_DOC_REFS:
        assert path in text, (
            f"Sub-agent must cite '{path}' (read-from-docs at runtime). "
            f"AC #4 forbids embedding these docs into the system prompt."
        )


def test_subagent_returns_structured_json():
    """AC #5: sub-agent returns {critical, high, medium, low} structured output."""
    text = open(SUBAGENT_PATH, encoding="utf-8").read()
    for sev in ("critical", "high", "medium", "low"):
        assert sev in text, f"JSON schema must define '{sev}' bucket"


# --- Bootstrap deployment ----------------------------------------------------


@pytest.fixture
def lib_dir_with_subagent(tmp_path):
    """Build a minimal lib_dir containing only what copy_subagents needs."""
    lib = tmp_path / "lib"
    sub_src = lib / "harness" / "claude" / "subagents"
    sub_src.mkdir(parents=True)
    (sub_src / "tausik-reviewer.md").write_text(
        "---\nname: tausik-reviewer\nmodel: sonnet\ntools: Read, Grep, Bash\n---\nbody",
        encoding="utf-8",
    )
    (sub_src / "non-md-file.txt").write_text("ignore me", encoding="utf-8")
    return str(lib)


def test_copy_subagents_for_claude_writes_to_agents_dir(lib_dir_with_subagent, tmp_path):
    sys.path.insert(0, BOOTSTRAP_DIR)
    from bootstrap_copy import copy_subagents

    target = tmp_path / "target"
    target.mkdir()
    n = copy_subagents(lib_dir_with_subagent, str(target), "claude")
    assert n == 1, "Only the .md file should be copied; .txt should be ignored"
    deployed = target / "agents" / "tausik-reviewer.md"
    assert deployed.is_file()
    body = deployed.read_text(encoding="utf-8")
    assert "name: tausik-reviewer" in body


def test_copy_subagents_skips_non_claude_ides(lib_dir_with_subagent, tmp_path):
    sys.path.insert(0, BOOTSTRAP_DIR)
    from bootstrap_copy import copy_subagents

    for ide in ("cursor", "qwen", "codex", "windsurf"):
        target = tmp_path / f"target_{ide}"
        target.mkdir()
        n = copy_subagents(lib_dir_with_subagent, str(target), ide)
        assert n == 0, f"copy_subagents must be a no-op for {ide!r} (Claude-only feature)"
        # And no agents/ dir should be created for non-claude IDEs.
        assert not (target / "agents").exists()


def test_copy_subagents_no_source_dir_returns_zero(tmp_path):
    sys.path.insert(0, BOOTSTRAP_DIR)
    from bootstrap_copy import copy_subagents

    lib = tmp_path / "lib"  # no harness/claude/subagents/ inside
    lib.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    n = copy_subagents(str(lib), str(target), "claude")
    assert n == 0
