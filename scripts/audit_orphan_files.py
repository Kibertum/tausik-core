"""Static orphan-file audit (v14-audit-orphan-files).

Reports Python source files inside ``scripts/`` that nothing inside the
TAUSIK repo imports — candidates for review (NOT for automatic delete).
Tests, generated assets, and known exclusions stay out of the report.

Run::

    python scripts/audit_orphan_files.py            # markdown report
    python scripts/audit_orphan_files.py --json     # JSON output
    python scripts/audit_orphan_files.py --check    # exit 1 on any orphan

Spec / motivation: docs/ru/research/tausik-1.4-epics-master-plan-2026-05-01.md
(epic ``v14-dead-code-audit``).
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
from pathlib import Path

# Excluded path globs (relative to repo root, forward-slashed).
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "tests/*",
    "tests/**/*",
    ".tausik/*",
    ".tausik/**/*",
    ".claude/*",
    ".claude/**/*",
    ".cursor/*",
    ".cursor/**/*",
    ".qwen/*",
    ".qwen/**/*",
    "docs/_generated/*",
    "docs/_generated/**/*",
    "harness/skills/_*/**/*",
    "bootstrap/*",
    "bootstrap/**/*",
    "scripts/project.py",
    "scripts/hooks/*",
    "scripts/hooks/**/*",
    "**/__pycache__/*",
    "**/__pycache__/**/*",
)

# Modules to look for as entry points (treated as "always referenced").
ENTRY_POINTS: tuple[str, ...] = (
    "project",
    "audit_orphan_files",
)


def _is_excluded(rel: str, excludes: tuple[str, ...]) -> bool:
    for pat in excludes:
        if fnmatch.fnmatch(rel, pat):
            return True
    return False


def _module_name(rel: str) -> str:
    """`scripts/foo_bar.py` → `foo_bar`. Used to compare with imports."""
    base = os.path.basename(rel)
    if base.endswith(".py"):
        base = base[:-3]
    return base


def _imports_in(path: Path) -> set[str]:
    """Top-level module names imported by the given file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split(".")[0])
    return out


def collect_orphans(repo_root: Path, excludes: tuple[str, ...] = DEFAULT_EXCLUDES) -> list[str]:
    """Return relative paths (forward-slashed) of orphan .py files in ``scripts/``."""
    scripts_dir = repo_root / "scripts"
    if not scripts_dir.is_dir():
        return []

    rel_paths: list[str] = []
    module_to_rel: dict[str, str] = {}
    for p in scripts_dir.rglob("*.py"):
        rel = p.relative_to(repo_root).as_posix()
        if _is_excluded(rel, excludes):
            continue
        rel_paths.append(rel)
        module_to_rel[_module_name(rel)] = rel

    # Build the set of imported module names from the entire repo
    # (scripts/, harness/**, bootstrap/**, tests/** — for completeness).
    referenced: set[str] = set(ENTRY_POINTS)
    for searched_dir in ("scripts", "harness", "bootstrap", "tests"):
        d = repo_root / searched_dir
        if not d.is_dir():
            continue
        for p in d.rglob("*.py"):
            referenced |= _imports_in(p)

    # Also count "soft" references in human-facing docs/skills — a script that
    # is documented as a CLI is not orphan even if no .py imports it.
    doc_referenced = _doc_referenced_modules(repo_root, list(module_to_rel.keys()))

    orphans: list[str] = []
    for mod, rel in module_to_rel.items():
        if mod in referenced or mod in doc_referenced:
            continue
        orphans.append(rel)
    orphans.sort()
    return orphans


def _doc_referenced_modules(repo_root: Path, module_names: list[str]) -> set[str]:
    """Modules whose ``<name>.py`` is mentioned anywhere under ``docs/`` or
    ``harness/skills/``. Picks up CLI scripts that nothing imports but the
    architecture docs / skill READMEs reference by file name.
    """
    needles = {f"{m}.py" for m in module_names}
    found: set[str] = set()
    for searched_dir in ("docs", "harness/skills", "harness/roles", "harness/stacks"):
        d = repo_root / searched_dir
        if not d.is_dir():
            continue
        for p in d.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for needle in needles:
                if needle in text:
                    found.add(needle[:-3])  # strip .py
        if found >= set(module_names):
            break
    return found


def render_markdown(orphans: list[str], excludes: tuple[str, ...]) -> str:
    lines = ["# Orphan-file audit (`scripts/`)\n"]
    if not orphans:
        lines.append("No orphan files detected. (OK)\n")
    else:
        lines.append(
            f"{len(orphans)} candidate(s) — **NOT auto-delete**, manual review required:\n"
        )
        for rel in orphans:
            lines.append(f"- `{rel}`")
        lines.append("")
    lines.append("## Excluded glob patterns\n")
    for pat in excludes:
        lines.append(f"- `{pat}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Static orphan-file audit (scripts/)")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any orphan is found (useful for CI)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (default: directory containing pyproject.toml)",
    )
    args = p.parse_args(argv)

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        here = Path.cwd().resolve()
        root = next(
            (q for q in [here, *here.parents] if (q / "pyproject.toml").is_file()),
            here,
        )

    orphans = collect_orphans(root)
    if args.json:
        print(json.dumps({"orphans": orphans, "excludes": list(DEFAULT_EXCLUDES)}, indent=2))
    else:
        print(render_markdown(orphans, DEFAULT_EXCLUDES))

    if args.check and orphans:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
