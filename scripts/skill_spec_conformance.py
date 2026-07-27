"""Validate SKILL.md against the canonical agentskills.io specification.

The SKILL.md format left Anthropic and became cross-vendor: the canon is now
agentskills.io/specification (OpenAI, Google, Microsoft, Cursor, JetBrains,
Mistral, AWS and others implement it). A reference CLI `skills-ref validate`
exists but is not a dependency here; this module enforces the same MACHINE-
checkable constraints in-process so a malformed skill is caught by our own gate:

  - `name`: 1-64 chars, `[a-z0-9]` and single hyphens only, no leading/trailing
    hyphen and NO doubled hyphen (`--`), and it MUST equal the parent directory
    name. Under progressive disclosure the name is the ~100-token metadata loaded
    for every skill at startup; a bad one breaks dispatch for all vendors.
  - `description`: 1-1024 chars.
  - `compatibility` (optional): <=500 chars when present.

SECURITY CAVEAT (agentskills.io): the spec is NOT versioned and contains NO
security provisions whatsoever — it says nothing about trust, sandboxing, or
tool permissions. Conformance here is a HYGIENE check (names/sizes that keep
progressive disclosure working), NEVER a trust signal. Do not gate trust on it.

Directories whose basename starts with `_` or `.` are local scaffolds / non-
deployed references (e.g. `_profile-demo`), not published skills, and are skipped
— matching how a publisher would only validate what it ships.
"""

from __future__ import annotations

import os
import re

MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500

# name = lowercase alnum segments joined by SINGLE hyphens; no leading/trailing
# hyphen, no doubled hyphen (the latter is not expressible as a single class so
# it is checked separately below).
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_publishable_skill_dir(skill_dir: str) -> bool:
    """A directory we validate: has a SKILL.md and is not a `_`/`.` scaffold."""
    base = os.path.basename(os.path.normpath(skill_dir))
    if base.startswith(("_", ".")):
        return False
    return os.path.isfile(os.path.join(skill_dir, "SKILL.md"))


def _read_frontmatter(text: str) -> dict[str, str]:
    """Lenient scalar frontmatter reader — MUST NOT raise on a malformed skill
    (validating broken skills is the whole point). Returns {} when no `---`
    block is present; pulls top-level `key: value` scalars, unquoting the value.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line or line[0] in " \t" or ":" not in line:
            continue  # nested/indented/list lines are not top-level scalars
        key, _, val = line.partition(":")
        val = val.strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        out[key.strip()] = val
    return out


def validate_skill_fields(name: str, description: str, dir_name: str) -> list[str]:
    """The pure name/description rules, decoupled from disk for direct testing."""
    problems: list[str] = []
    if not name:
        problems.append("name: missing or empty")
    else:
        if len(name) > MAX_NAME:
            problems.append(f"name: {len(name)} chars exceeds {MAX_NAME}")
        if "--" in name:
            problems.append("name: contains a doubled hyphen '--'")
        if not _NAME_RE.match(name):
            problems.append(
                "name: must be lowercase a-z0-9 with single hyphens, no leading/trailing hyphen"
            )
        if name != dir_name:
            problems.append(f"name: {name!r} must equal parent directory {dir_name!r}")
    if not description:
        problems.append("description: missing or empty")
    elif len(description) > MAX_DESCRIPTION:
        problems.append(f"description: {len(description)} chars exceeds {MAX_DESCRIPTION}")
    return problems


def validate_skill(skill_dir: str) -> list[str]:
    """Conformance problems for one skill directory; empty list = conformant.

    Never raises: an unreadable SKILL.md is itself a problem, reported as one.
    """
    skill_md = os.path.join(skill_dir, "SKILL.md")
    try:
        with open(skill_md, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        return [f"SKILL.md unreadable: {e}"]
    fm = _read_frontmatter(text)
    dir_name = os.path.basename(os.path.normpath(skill_dir))
    problems = validate_skill_fields(fm.get("name", ""), fm.get("description", ""), dir_name)
    compat = fm.get("compatibility", "")
    if compat and len(compat) > MAX_COMPATIBILITY:
        problems.append(f"compatibility: {len(compat)} chars exceeds {MAX_COMPATIBILITY}")
    return problems


def scan_skills(root: str) -> dict[str, list[str]]:
    """`{skill_name: problems}` for every publishable skill under `root`."""
    report: dict[str, list[str]] = {}
    if not os.path.isdir(root):
        return report
    for entry in sorted(os.listdir(root)):
        skill_dir = os.path.join(root, entry)
        if os.path.isdir(skill_dir) and is_publishable_skill_dir(skill_dir):
            report[entry] = validate_skill(skill_dir)
    return report


def run_skill_conformance_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Scoped gate: fail a close when a changed SKILL.md violates the canon.

    Inert unless a `SKILL.md` is among `files` — a change that touches no skill
    has nothing to check. The spec carries no security weight (see module
    docstring); this only guards progressive-disclosure hygiene.
    """
    # Normalize separators ONCE and use the normalized path for BOTH the basename
    # check and dirname: os.path.dirname on POSIX does not split on '\\', so a
    # backslash path would otherwise yield '' and validate the wrong directory.
    norm = [f.replace("\\", "/") for f in files]
    skill_dirs = [os.path.dirname(p) for p in norm if os.path.basename(p) == "SKILL.md"]
    if not skill_dirs:
        return True, "No SKILL.md changed — skill-conformance check skipped."
    violations: list[str] = []
    for skill_dir in skill_dirs:
        for problem in validate_skill(skill_dir or "."):
            violations.append(f"{skill_dir or '.'}: {problem}")
    if violations:
        return False, "Skill spec violations (agentskills.io):\n  " + "\n  ".join(violations)
    return True, f"{len(skill_dirs)} changed skill(s) conform to agentskills.io."
