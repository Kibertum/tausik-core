"""Every MCP tool a skill tells the agent to call must actually exist.

`harness/skills/task/SKILL.md` instructed the agent to call
`tausik_memory_quick` — a plausible sibling of the real `tausik_task_quick`,
and a name that has never existed. The instruction sat there through writing
and review because it *looked* right; the brain-suggestion suppression it was
meant to drive therefore never worked, while appearing to.

SCOPE, stated so nobody mistakes it for more: this checks that a referenced
tool NAME EXISTS. It does not check that the surrounding instruction is
sensible, correct, or benign. It is a guard against dead references, NOT a
defence against a hostile skill — SKILL.md content is otherwise unvalidated
(no size limit, no invisible-Unicode normalisation, no injection heuristics).

Reads the CANONICAL harness/skills tree, never the generated .claude/skills
mirror: a mirror is written by bootstrap and can be edited afterwards, so
verifying it would certify the copy instead of the source.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SKILLS = os.path.join(_ROOT, "harness", "skills")
_MCP_PROJECT = os.path.join(_ROOT, "harness", "claude", "mcp", "project")

if _MCP_PROJECT not in sys.path:
    sys.path.insert(0, _MCP_PROJECT)

# Bare `tausik_<name>` occurrences, with or without the client-side
# `mcp__tausik-project__` prefix. Trailing `(` or backtick is not part of it.
#
# Not `\b` after the optional prefix: `_` is a word character, so there is no
# boundary between `mcp__tausik-project__` and `tausik_…` and the prefixed form
# matched nothing at all. Either the literal prefix precedes the name, or the
# name starts a fresh identifier — which also keeps `my_tausik_thing` out.
_TOOL_REF = re.compile(r"(?:mcp__tausik-project__|(?<![a-z0-9_]))(tausik_[a-z0-9_]+)")

# Words that read like a tool name but are prose or CLI, not MCP tools.
# Kept explicit so an addition here is a visible decision, not a silent pass.
_NOT_TOOLS = {
    "tausik_dir",
    "tausik_db",
    "tausik_utils",
    "tausik_version",
}


def _tool_names() -> set[str]:
    from tools import TOOLS

    return {t["name"] for t in TOOLS}


def _skill_files() -> list[str]:
    found = []
    for dirpath, _dirnames, filenames in os.walk(_SKILLS):
        for fn in filenames:
            if fn.endswith(".md"):
                found.append(os.path.join(dirpath, fn))
    return sorted(found)


def _referenced(path: str) -> set[str]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return {m for m in _TOOL_REF.findall(text) if m not in _NOT_TOOLS}


class TestSkillToolReferences:
    def test_skill_tree_is_present(self):
        """Guard the guard: a moved tree must fail loudly, not vacuously pass."""
        files = _skill_files()
        assert files, f"no skill markdown found under {_SKILLS}"

    def test_tools_registry_loads(self):
        names = _tool_names()
        assert len(names) > 50
        assert "tausik_memory_add" in names

    def test_every_referenced_tool_exists(self):
        known = _tool_names()
        dangling: dict[str, set[str]] = {}
        for path in _skill_files():
            missing = _referenced(path) - known
            if missing:
                dangling[os.path.relpath(path, _ROOT)] = missing
        assert not dangling, "skills reference MCP tools that do not exist: " + "; ".join(
            f"{p} -> {sorted(m)}" for p, m in sorted(dangling.items())
        )

    def test_the_dead_reference_is_gone(self):
        """Named explicitly so the original defect cannot silently return."""
        assert "tausik_memory_quick" not in _tool_names()
        for path in _skill_files():
            assert "tausik_memory_quick" not in _referenced(path)


class TestExtractorPrecision:
    """The check is only worth its exit code if it does not cry wolf."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("call `tausik_memory_add(...)` now", {"tausik_memory_add"}),
            ("mcp__tausik-project__tausik_task_done fires", {"tausik_task_done"}),
            ("see tausik_status in prose", {"tausik_status"}),
            ("path scripts/tausik_utils.py", set()),
            ("no tools mentioned here at all", set()),
        ],
    )
    def test_extraction(self, text, expected, tmp_path):
        f = tmp_path / "s.md"
        f.write_text(text, encoding="utf-8")
        assert _referenced(str(f)) == expected
