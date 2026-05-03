"""Static pytest duplicate-scenario audit (v14-pytest-dedupe-audit).

Stdlib-only AST analyzer. Groups test functions whose **structure** is
identical (modulo names, strings, and numeric literals). Used to surface
copy-paste tests that don't exercise new behaviour — catching the
``testing-principles`` antipattern (see docs/{en,ru}/testing-principles.md).

Run::

    python scripts/audit_pytest_dedupe.py            # markdown report
    python scripts/audit_pytest_dedupe.py --json     # JSON output
    python scripts/audit_pytest_dedupe.py --check    # exit 1 on any group

Spec / motivation: docs/ru/research/tausik-1.4-epics-master-plan-2026-05-01.md
(epic ``v14-test-philosophy``).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

# Test scenarios that are *expected* to share structure (parametrized
# variants on the same path) — listed here so review can ignore them.
KNOWN_FALSE_POSITIVES: tuple[tuple[str, str], ...] = (
    # (test_file_basename, test_func_name) — explicit allowlist
    # (we don't actually skip them in the report, just annotate)
)


def _normalize_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Convert function body to a canonical structural string.

    Identifier names are replaced with ``ID``, strings with ``S``, numbers
    with ``N``. Keeps the AST shape so two functions with the same logic
    but different identifiers / values hash to the same signature.
    """
    parts: list[str] = []
    for child in ast.walk(node):
        # Skip the outer FunctionDef header itself
        if child is node:
            continue
        kind = type(child).__name__
        if isinstance(child, ast.Name):
            parts.append("Name:ID")
        elif isinstance(child, ast.Attribute):
            parts.append("Attr:ID")
        elif isinstance(child, ast.Constant):
            v = child.value
            if isinstance(v, str):
                parts.append("Const:S")
            elif isinstance(v, (int, float, complex)):
                parts.append("Const:N")
            elif isinstance(v, bool):
                parts.append("Const:B")
            elif v is None:
                parts.append("Const:None")
            else:
                parts.append("Const:OTHER")
        elif isinstance(child, ast.arg):
            parts.append("arg:ID")
        elif isinstance(child, ast.keyword):
            parts.append("kw:ID")
        else:
            parts.append(kind)
    return "|".join(parts)


def _signature(body_norm: str) -> str:
    return hashlib.sha1(body_norm.encode("utf-8")).hexdigest()[:16]


def _is_test_func(node: ast.AST) -> bool:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name.startswith("test_")
    return False


def _walk_tests(path: Path) -> list[tuple[str, int, ast.FunctionDef]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []
    out: list[tuple[str, int, ast.FunctionDef]] = []
    # Top-level test functions. _is_test_func narrows to FunctionDef|AsyncFunctionDef
    # but mypy can't track the predicate; cast the assignment site.
    for node in tree.body:
        if _is_test_func(node) and isinstance(node, ast.FunctionDef):
            out.append((node.name, node.lineno, node))
    # Methods on classes
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if _is_test_func(sub) and isinstance(sub, ast.FunctionDef):
                    qual = f"{node.name}.{sub.name}"
                    out.append((qual, sub.lineno, sub))
    return out


def collect_duplicates(repo_root: Path) -> list[dict[str, object]]:
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return []
    by_sig: dict[str, list[dict[str, object]]] = {}
    for p in sorted(tests_dir.rglob("test_*.py")):
        rel = p.relative_to(repo_root).as_posix()
        for name, lineno, node in _walk_tests(p):
            sig = _signature(_normalize_function(node))
            by_sig.setdefault(sig, []).append({"file": rel, "name": name, "lineno": lineno})

    groups: list[dict[str, object]] = []
    for sig, members in by_sig.items():
        if len(members) < 2:
            continue
        # Filter out obvious noise: single-line `pass` / TODO stubs
        groups.append({"signature": sig, "members": members})

    # Stable order: largest group first, then by file/name
    groups.sort(key=lambda g: (-len(g["members"]), g["members"][0]["file"]))  # type: ignore[index, arg-type]
    return groups


def render_markdown(groups: list[dict[str, object]]) -> str:
    lines = ["# pytest dedupe audit (`tests/`)\n"]
    if not groups:
        lines.append("No duplicate test scenarios detected. (OK)\n")
    else:
        total = sum(len(g["members"]) for g in groups)  # type: ignore[arg-type, misc]
        lines.append(
            f"{len(groups)} group(s) of structurally identical test functions "
            f"(total {total} tests). **Review only — do not auto-delete.**\n"
        )
        for i, g in enumerate(groups, 1):
            members = g["members"]
            lines.append(f"## Group {i} (sig `{g['signature']}`, {len(members)} tests)")  # type: ignore[arg-type]
            for m in members:  # type: ignore[attr-defined]
                lines.append(f"- `{m['file']}:{m['lineno']}` — `{m['name']}`")
            lines.append("")
    lines.append("## Documented false positives\n")
    lines.append(
        "- Tests that share AST shape because they exercise different inputs "
        "but the same code path are **not bugs** — they are explicit coverage "
        "of edge cases. Review each group manually."
    )
    lines.append(
        "- Identifier names, string literals, and numeric values are erased "
        "during normalisation. So two tests with different fixtures and "
        "assertions but identical control flow will hash the same."
    )
    lines.append(
        "- Parametrize candidates: groups whose members differ only in a "
        "single literal can usually collapse into one parametrised test."
    )
    if KNOWN_FALSE_POSITIVES:
        lines.append("- Allowlist (annotation only):")
        for f, n in KNOWN_FALSE_POSITIVES:
            lines.append(f"  - `{f}::{n}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Static pytest duplicate-scenario audit")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any duplicate group is found (useful for CI)",
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

    groups = collect_duplicates(root)
    if args.json:
        print(json.dumps({"groups": groups}, indent=2))
    else:
        print(render_markdown(groups))

    if args.check and groups:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
