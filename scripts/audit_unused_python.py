"""Static unused-Python audit (v14-audit-unused-python).

Stdlib-only (TAUSIK convention #19: no external deps). Reports top-level
``def``/``class`` symbols inside ``scripts/`` whose name is never
referenced anywhere in the repo. Conservative on purpose:

  * dunder methods, ``main`` and CLI entry points are excluded.
  * Names whose module is in ``EXEMPT_MODULES`` are excluded (legacy
    shims, generated code, MCP handler dispatch tables).
  * Symbols used dynamically (``getattr``, MCP dispatch by string)
    surface as candidates — explicit human review required, never
    auto-delete.

Run::

    python scripts/audit_unused_python.py            # markdown report
    python scripts/audit_unused_python.py --json     # JSON output
    python scripts/audit_unused_python.py --check    # exit 1 on any candidate

Spec / motivation: docs/ru/research/tausik-1.4-epics-master-plan-2026-05-01.md
(epic ``v14-dead-code-audit``).
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
from pathlib import Path

SCAN_GLOBS: tuple[str, ...] = ("scripts/**/*.py",)

# Globs (relative, forward-slashed) excluded from the SOURCE side
# (we don't pull definitions from these to flag).
SOURCE_EXCLUDES: tuple[str, ...] = (
    "scripts/hooks/*",
    "scripts/hooks/**/*",
    "scripts/__pycache__/*",
    "scripts/__pycache__/**/*",
    "**/__pycache__/*",
)

# Modules whose symbols are never reported — legacy shims, MCP/CLI dispatch
# tables that are accessed by string lookup, generated code.
EXEMPT_MODULES: frozenset[str] = frozenset(
    {
        "verify_recent_lookup",  # compat shim
        "tausik_version",
        "gen_doc_constants",
    }
)

# Symbol names always considered referenced (entry points, conventions).
ALWAYS_REFERENCED_NAMES: frozenset[str] = frozenset(
    {
        "main",
        "__init__",
        "__enter__",
        "__exit__",
        "__repr__",
        "__str__",
        "__call__",
        "__hash__",
        "__eq__",
        "__lt__",
        "__iter__",
        "__next__",
        "__len__",
        "__contains__",
        "__getitem__",
        "__setitem__",
        "__delitem__",
    }
)

# Where references can come from — covers tests + agents + bootstrap +
# scripts + skill docs + root markdown / TOML.
REFERENCE_DIRS: tuple[str, ...] = (
    "scripts",
    "harness",
    "bootstrap",
    "tests",
)
REFERENCE_GLOBS: tuple[str, ...] = ("*.py", "*.json", "*.md", "*.toml", "*.yaml", "*.yml")
ROOT_REF_FILES: tuple[str, ...] = (
    "README.md",
    "README.ru.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "CHANGELOG.ru.md",
    "QWEN.md",
    "pyproject.toml",
)


def _is_excluded(rel: str, excludes: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in excludes)


def _module_name(rel: str) -> str:
    base = rel.split("/")[-1]
    return base[:-3] if base.endswith(".py") else base


def _toplevel_defs(path: Path) -> list[tuple[str, int]]:
    """Return ``(name, lineno)`` for every top-level def / class definition."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    out: list[tuple[str, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((node.name, node.lineno))
    return out


def _collect_references(repo_root: Path) -> str:
    chunks: list[str] = []
    seen: set[Path] = set()
    for fname in ROOT_REF_FILES:
        p = repo_root / fname
        if p.is_file() and p not in seen:
            seen.add(p)
            try:
                chunks.append(p.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
    for d in REFERENCE_DIRS:
        sub = repo_root / d
        if not sub.is_dir():
            continue
        for pattern in REFERENCE_GLOBS:
            for p in sub.rglob(pattern):
                if p in seen:
                    continue
                seen.add(p)
                try:
                    chunks.append(p.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, OSError):
                    continue
    return "\n".join(chunks)


def collect_unused(
    repo_root: Path,
    *,
    source_excludes: tuple[str, ...] = SOURCE_EXCLUDES,
    exempt_modules: frozenset[str] = EXEMPT_MODULES,
) -> list[dict[str, object]]:
    candidates: list[tuple[str, str, int]] = []  # (rel_path, name, lineno)
    for glob in SCAN_GLOBS:
        for p in repo_root.glob(glob):
            rel = p.relative_to(repo_root).as_posix()
            if _is_excluded(rel, source_excludes):
                continue
            if _module_name(rel) in exempt_modules:
                continue
            for name, lineno in _toplevel_defs(p):
                if name.startswith("_") and not name.startswith("__"):
                    # private helpers are commonly internal-only — skip noise
                    continue
                if name in ALWAYS_REFERENCED_NAMES:
                    continue
                candidates.append((rel, name, lineno))

    if not candidates:
        return []

    haystack = _collect_references(repo_root)
    unused: list[dict[str, object]] = []
    for rel, name, lineno in candidates:
        # A reference is any occurrence of the bare name as a word in any
        # tracked file. Conservative — false negatives preferred to false
        # positives in v1.
        # Count occurrences excluding this very definition file's `def NAME(`.
        ref_count = haystack.count(name)
        # Subtract the definition itself (`def NAME` or `class NAME`).
        if ref_count > 0:
            ref_count -= 1  # the def line in the source
        if ref_count <= 0:
            unused.append({"file": rel, "name": name, "lineno": lineno})
    unused.sort(key=lambda r: (r["file"], r["lineno"]))
    return unused


def render_markdown(rows: list[dict[str, object]]) -> str:
    lines = ["# Unused Python audit (`scripts/`)\n"]
    if not rows:
        lines.append("No unused top-level symbols detected. (OK)\n")
    else:
        lines.append(f"{len(rows)} candidate(s) — **manual review required**, never auto-delete.\n")
        lines.append("Symbols may be referenced via `getattr` / dispatch tables.\n")
        for r in rows:
            lines.append(f"- `{r['file']}:{r['lineno']}` — `{r['name']}`")
        lines.append("")
    lines.append("## Documented false positives\n")
    lines.append(
        "- Modules in `EXEMPT_MODULES` are skipped wholesale "
        "(legacy shims, generated code, MCP dispatch tables)."
    )
    lines.append(
        "- Private helpers (`_*`) are skipped — too noisy in v1; revisit when "
        "type-aware analysis lands."
    )
    lines.append(
        "- Tests and hooks are excluded from the SOURCE side: their entry points "
        "live outside the audit's scope (pytest collection / hook runner)."
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Static unused-symbol audit (scripts/)")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any unused symbol is found (useful for CI)",
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

    rows = collect_unused(root)
    if args.json:
        print(
            json.dumps(
                {
                    "unused": rows,
                    "exempt_modules": sorted(EXEMPT_MODULES),
                    "source_excludes": list(SOURCE_EXCLUDES),
                },
                indent=2,
            )
        )
    else:
        print(render_markdown(rows))

    if args.check and rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
