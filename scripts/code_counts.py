"""Repo-state counts surfaced in `constants.json` — review agents, hooks, skills.

Shared with `gen_doc_constants.py`. Each helper is single-purpose and returns
an int derived directly from the filesystem so the marketing copy on the
landing can no longer drift from reality.
"""

from __future__ import annotations

import json
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


def count_official_skills(repo_root: Path) -> int | None:
    """Entries in ``skills-official/registry.json``, or None when unreadable.

    The opt-in catalogue is quoted as a bare number in three places (both
    READMEs, AGENTS.md) and was bound to nothing: AGENTS.md said "25+ official"
    while the registry held 20, and no check could disagree because no constant
    existed to disagree WITH. Reading the registry rather than the directory
    listing on purpose -- the directory also holds `README.md` and
    `bundles.json`, and a count that walks it answers a different question than
    the one the docs ask.

    NONE MEANS "THE SOURCE IS NOT HERE", AND THAT IS NOT THE SAME AS ZERO.
    ``skills-official/`` is a separate repository and is gitignored, so a clean
    clone -- every CI runner included -- has no registry at all. The first cut
    of this function returned 0 there, which made ``--check`` disagree with the
    committed constant and turned every CI run red (measured: `git archive HEAD`
    into an empty directory, then the literal CI command, exit 1). Worse, a
    merely corrupted registry would have fed 0 to ``write_cross_file_fixes``,
    which rewrites documents from constants: "20 official skills" would have
    become "0 official skills" in three files, silently and in writing. A count
    that cannot be taken is ABSENT; the caller decides what to do about it, and
    :func:`gen_doc_constants.build_constants_doc` keeps the previously recorded
    value exactly as it already does for ``test_count``.
    """
    registry = repo_root / "skills-official" / "registry.json"
    if not registry.is_file():
        return None
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    skills = data.get("skills") if isinstance(data, dict) else None
    return len(skills) if isinstance(skills, (list, dict)) else None


def count_stacks(repo_root: Path) -> int:
    """Count stack profile dirs under `stacks/` (excluding the schema file)."""
    stacks_dir = repo_root / "stacks"
    if not stacks_dir.is_dir():
        return 0
    return sum(1 for p in stacks_dir.iterdir() if p.is_dir())


def count_roles(repo_root: Path) -> int:
    """Count built-in role profiles under `harness/roles/*.md`.

    Each `.md` is one registered role (architect, developer, devops, qa,
    tech-writer, ui-ux). Docs quote this number ("6 roles"/"6 ролей"), so it is
    surfaced as a constant to make that copy fail the doc-drift check when a role
    is added or removed rather than drift silently — which it already did once
    (architecture.md kept "5 roles" after devops landed as the sixth).
    """
    roles_dir = repo_root / "harness" / "roles"
    if not roles_dir.is_dir():
        return 0
    return sum(1 for p in roles_dir.glob("*.md") if p.is_file())


def code_counts_flat(repo_root: Path) -> dict[str, int]:
    """Bundle for `gen_doc_constants` to merge into `constants.json`.

    ``skills_official_count`` is OMITTED rather than zeroed when its registry is
    unreadable -- see :func:`count_official_skills` for why absence and zero are
    different answers here.
    """
    counts = {
        "review_agents_count": count_review_agents(repo_root),
        "hooks_count": count_registered_hooks(repo_root),
        "skills_core_count": count_core_skills(repo_root),
        "stacks_count": count_stacks(repo_root),
        "roles_count": count_roles(repo_root),
    }
    official = count_official_skills(repo_root)
    if official is not None:
        counts["skills_official_count"] = official
    return counts
