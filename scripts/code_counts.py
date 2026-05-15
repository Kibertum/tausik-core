"""Repo-state counts surfaced in `constants.json` — review agents, hooks, skills.

Shared with `gen_doc_constants.py`. Each helper is single-purpose and returns
an int derived directly from the filesystem so the marketing copy on the
landing can no longer drift from reality.
"""

from __future__ import annotations

import re
from pathlib import Path

_HOOK_CMD_RE = re.compile(r'hook_cmd\(\s*"([a-zA-Z0-9_]+)\.py"', re.MULTILINE)

# Skill directories under harness/skills/ excluded from the public "core skills"
# count. _profile-demo is a docs-only skeleton; review is invoked by other
# skills (not user-typed) and is counted separately as review_agents_count.
_NON_CORE_SKILL_DIRS: frozenset[str] = frozenset({"_profile-demo", "review"})


def count_review_agents(repo_root: Path) -> int:
    """Count `.md` files under `harness/skills/review/agents/`."""
    agents_dir = repo_root / "harness" / "skills" / "review" / "agents"
    if not agents_dir.is_dir():
        return 0
    return sum(1 for p in agents_dir.glob("*.md") if p.is_file())


def count_registered_hooks(repo_root: Path) -> int:
    """Count unique hooks registered via `bootstrap/bootstrap_hooks.py`.

    Two registration shapes coexist (`register_hook("name", ...)` and an inline
    `"command": ".../hooks/name.py"`). Both are deduped on the script basename
    so a hook listed in multiple lifecycle slots counts once.
    """
    hooks_module = repo_root / "bootstrap" / "bootstrap_hooks.py"
    if not hooks_module.is_file():
        return 0
    text = hooks_module.read_text(encoding="utf-8")
    return len(set(_HOOK_CMD_RE.findall(text)))


def count_core_skills(repo_root: Path) -> int:
    """Count user-facing skill dirs under `harness/skills/`.

    A directory qualifies if it contains a `SKILL.md` AND its name is not in
    `_NON_CORE_SKILL_DIRS`.
    """
    skills_dir = repo_root / "harness" / "skills"
    if not skills_dir.is_dir():
        return 0
    return sum(
        1
        for p in skills_dir.iterdir()
        if p.is_dir() and p.name not in _NON_CORE_SKILL_DIRS and (p / "SKILL.md").is_file()
    )


def count_stacks(repo_root: Path) -> int:
    """Count stack profile dirs under `stacks/` (excluding the schema file)."""
    stacks_dir = repo_root / "stacks"
    if not stacks_dir.is_dir():
        return 0
    return sum(1 for p in stacks_dir.iterdir() if p.is_dir())


def code_counts_flat(repo_root: Path) -> dict[str, int]:
    """Bundle for `gen_doc_constants` to merge into `constants.json`."""
    return {
        "review_agents_count": count_review_agents(repo_root),
        "hooks_count": count_registered_hooks(repo_root),
        "skills_core_count": count_core_skills(repo_root),
        "stacks_count": count_stacks(repo_root),
    }
