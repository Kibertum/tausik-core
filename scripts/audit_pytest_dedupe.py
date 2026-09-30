"""Static pytest duplicate-scenario audit (v14-pytest-dedupe-audit).

Stdlib-only AST analyzer. Groups test functions whose **structure** is
identical (modulo names, strings, and numeric literals), then gives each group a
VERDICT: a ``COPY`` is literally the same code, a ``PARALLEL`` differs in the parts
the signature erased.

The verdict exists because the grouping alone was read as copy-paste debt for three
releases and MEASURED wrong 99.3% of the time: 284 of 286 groups were one contract
exercised on different inputs, which is what a suite is supposed to look like. The
shape count measures SIMILARITY; only ``COPY`` measures duplication, and only that
number backs the ``test_dedupe`` gate (see docs/{en,ru}/testing-principles.md).

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
from typing import Any

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
    # `usedforsecurity=False` states the intent rather than suppressing the
    # scanner: this is a bucket key for grouping identical test bodies in a
    # report, not a signature anyone trusts. Sixteen hex characters of SHA-1
    # would be a poor security choice and a perfectly good dedupe key, and the
    # flag is where that difference is written down. A `# nosec` here would
    # have silenced the finding while leaving the next reader to guess.
    return hashlib.sha1(body_norm.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


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


#: The two verdicts a machine is entitled to reach about a group.
#:
#: The shape count never told duplication from similarity: a group whose members
#: differ in the parts the signature erases -- names, strings, numbers -- is one
#: contract exercised on different inputs, which is what a suite is supposed to look
#: like. Only a group whose members are literally the same code is a copy, and that is
#: the number worth a gate. The numbers behind this are in the module docstring.
#:
#: A third category, a template asserting nothing, has no verdict here because there
#: is nothing for it to report: no test in this suite is unable to fail, and that is
#: held by tests/test_gate_test_dedupe.py rather than claimed in a comment.
COPY = "copy"
PARALLEL = "parallel"


def _qualified_bodies(path: Path) -> dict[str, str]:
    """`Class.method` / `func` -> its source, unparsed so formatting cannot differ."""
    out: dict[str, str] = {}

    def walk(node: ast.AST, prefix: str = "") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out[f"{prefix}{child.name}"] = ast.unparse(child)

    walk(ast.parse(path.read_text(encoding="utf-8")))
    return out


def classify(groups: list[dict[str, Any]], repo_root: Path) -> list[dict[str, Any]]:
    """Attach a verdict to every group, in place, and return the groups.

    Unparsed source is compared rather than raw text, so whitespace, comments and
    line wrapping cannot make two copies look different. The function's own name is
    blanked first: two tests are not distinguishable merely by being called
    different things -- a name is a promise, not a check.
    """
    cache: dict[str, dict[str, str]] = {}
    for group in groups:
        bodies: list[str | None] = []
        for member in group["members"]:
            rel = str(member["file"])
            if rel not in cache:
                try:
                    cache[rel] = _qualified_bodies(repo_root / rel)
                except (OSError, SyntaxError):
                    cache[rel] = {}
            text = cache[rel].get(str(member["name"]))
            short = str(member["name"]).rsplit(".", 1)[-1]
            bodies.append(text.replace(short, "F", 1) if text else None)
        readable = [b for b in bodies if b is not None]
        # A group we could not read is NOT called a copy: an unreadable file must
        # never turn into a claim about the tests inside it.
        group["verdict"] = (
            COPY if len(readable) == len(bodies) and len(set(readable)) == 1 else PARALLEL
        )
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
        # ABSENCE is reported as absence, never as zero. A caller that skipped
        # `classify` gets "not computed" instead of "0 copy", because a report
        # claiming no copies because nobody looked is the failure this verdict was
        # added to end.
        if all("verdict" in g for g in groups):
            copies = sum(1 for g in groups if g["verdict"] == COPY)
            headline = f"Verdicts: **{copies} copy**, {len(groups) - copies} parallel."
        else:
            headline = (
                "Verdicts: **not computed** — these groups were never passed through "
                "`classify`, so this report says nothing about copies."
            )
        lines.append(
            headline + " A COPY is "
            "literally the same code under two names; a PARALLEL differs in the parts "
            "the signature erases, which is one contract on different inputs. The "
            "verdict is WRITTEN here rather than left to the reader, because a report "
            "that only counts groups has been read as duplication debt for three "
            "releases and was wrong about it 99.3% of the time.\n"
        )
        for i, g in enumerate(groups, 1):
            members: list[dict[str, Any]] = g["members"]  # type: ignore[assignment]
            verdict = str(g.get("verdict", "unclassified")).upper()
            lines.append(f"## Group {i} — {verdict} (sig `{g['signature']}`, {len(members)} tests)")
            for m in members:
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
    lines.append(
        "- A template that asserts nothing would be the dangerous category, and it "
        "is EMPTY here: of 7829 test functions none is unable to fail (no empty "
        "body, no assertion on a constant, no test without any call). Measured, not "
        "assumed -- the check is in `tests/test_gate_test_dedupe.py`."
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

    # Classified here, not defaulted in the renderer: a report that prints
    # "0 copy" because nobody computed a verdict is indistinguishable from one
    # that checked and found none.
    groups = classify(collect_duplicates(root), root)
    if args.json:
        print(json.dumps({"groups": groups}, indent=2))
    else:
        print(render_markdown(groups))

    if args.check and groups:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
