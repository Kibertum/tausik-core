"""Answer a question about a symbol with its DEFINITION, not with its address.

symbol-index-answers-with-the-definition-not-the-address. Derived from Graft
(github.com/trailhq/Graft), whose deterministic core builds a symbol graph with
no model involved and answers a query with the source inlined, so the agent does
not open the file afterwards. Graft is TypeScript on tree-sitter; this is Python
on `ast`, because that is what this project can carry.

WHY IT IS WORTH BUILDING HERE, MEASURED (session #233, eight transcripts):

    tool result payload            4,826,406 chars
    code navigation by TOOL NAME     461,434  (9.6%)  Read, Grep, Glob, ToolSearch
    grep/sed/find/ls inside Bash   1,789,369  (37.1% of the total)
    ----------------------------------------------------------------
    code exploration, really          ~47% of everything tools returned

The first number alone says "not worth it" — a 2.7% ceiling on context growth.
The second says the opposite. Counting by TOOL NAME missed half the
reconnaissance because on this project it wears the name `Bash`: 1,192 calls
averaging 1,501 characters each. Checking the fact rather than the name is the
same lesson as decision #335, arriving in a new place.

WHAT IS DELIBERATELY NOT COPIED FROM GRAFT: the concept layer, where a model
writes plain-English summaries of each part of the system. It needs a key, a
network and money, and the measurable half of the saving comes from the
deterministic core. A layer whose benefit we cannot measure is not shipped as if
we could.

THE INDEX IS DERIVED, NEVER EDITED. It is a cache of what `ast` says about the
tree; a hand-maintained symbol registry would rot exactly the way every other
hand-maintained registry in this project has (decision #335).

SOURCES ARE PARSED, NEVER IMPORTED. `ast.parse` reads; `import` would EXECUTE
module-level code from every file in the tree during indexing.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path

#: Trees worth indexing. The deployed IDE profiles are byte-copies of `scripts/`
#: and would triple every answer with duplicates of the same definition.
DEFAULT_ROOTS: tuple[str, ...] = ("scripts", "bootstrap", "tests", "harness")

#: Directories never descended into, whatever they contain.
_SKIP_DIRS = frozenset(
    {".git", ".tausik", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache"}
)

#: A source file larger than this is skipped rather than read. Untrusted only in
#: the weak sense — it is our own tree — but an index that can be made to eat
#: memory by dropping one enormous file in is an index with a switch on it.
MAX_SOURCE_BYTES = 2 * 1024 * 1024

#: How much of a definition an answer carries before it is cut. Past this, the
#: answer stops being cheaper than reading the file, which is the whole point.
DEFAULT_BODY_LINES = 60


@dataclass(frozen=True)
class Symbol:
    """One top-level or class-level definition, and where it lives."""

    name: str
    kind: str  # "function" | "class" | "method"
    path: str  # repo-relative, forward slashes
    lineno: int
    end_lineno: int
    signature: str
    parent: str | None  # enclosing class for a method, else None

    @property
    def qualname(self) -> str:
        return f"{self.parent}.{self.name}" if self.parent else self.name


def _iter_python_files(repo_root: Path, roots: tuple[str, ...]) -> list[Path]:
    """Every .py file under `roots`, without following links out of the tree."""
    found: list[Path] = []
    real_root = repo_root.resolve()
    for root in roots:
        base = repo_root / root
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = Path(dirpath) / name
                try:
                    # A symlink pointing outside the project is not ours to read.
                    if not path.resolve().is_relative_to(real_root):
                        continue
                    if path.stat().st_size > MAX_SOURCE_BYTES:
                        continue
                except OSError:
                    continue
                found.append(path)
    return sorted(found)


def _signature(node: ast.AST, source_lines: list[str]) -> str:
    """The `def`/`class` line as written, collapsed to one line.

    Taken from the SOURCE rather than unparsed from the AST: `ast.unparse`
    rewrites defaults and annotations into a normalised form, and a reader
    comparing the answer with the file would find two different sentences.
    """
    start = getattr(node, "lineno", 1) - 1
    parts: list[str] = []
    depth = 0
    for line in source_lines[start : start + 12]:
        parts.append(line.strip())
        depth += line.count("(") - line.count(")")
        if depth <= 0 and line.rstrip().endswith(":"):
            break
    return " ".join(parts).rstrip(":").strip()


def build_index(repo_root: str | Path, roots: tuple[str, ...] = DEFAULT_ROOTS) -> list[Symbol]:
    """Every definition in the tree. Parsed, never imported.

    A file that does not parse is SKIPPED, not fatal: one syntactically broken
    file in a working tree must not cost the whole index. It is skipped
    silently here and reported by `unparsable`, so "could not read" never
    reaches a caller as "does not exist".
    """
    root = Path(repo_root)
    symbols: list[Symbol] = []
    for path in _iter_python_files(root, roots):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            continue
        lines = source.splitlines()
        rel = path.relative_to(root).as_posix()
        for node in tree.body:
            symbols.extend(_symbols_of(node, rel, lines, parent=None))
    return symbols


def _symbols_of(node: ast.AST, rel: str, lines: list[str], parent: str | None) -> list[Symbol]:
    out: list[Symbol] = []
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        out.append(
            Symbol(
                name=node.name,
                kind="method" if parent else "function",
                path=rel,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                signature=_signature(node, lines),
                parent=parent,
            )
        )
    elif isinstance(node, ast.ClassDef):
        out.append(
            Symbol(
                name=node.name,
                kind="class",
                path=rel,
                lineno=node.lineno,
                end_lineno=getattr(node, "end_lineno", node.lineno),
                signature=_signature(node, lines),
                parent=parent,
            )
        )
        for child in node.body:
            out.extend(_symbols_of(child, rel, lines, parent=node.name))
    return out


def unparsable(repo_root: str | Path, roots: tuple[str, ...] = DEFAULT_ROOTS) -> list[str]:
    """Files the index could not read. Absence of a symbol may be one of these."""
    root = Path(repo_root)
    bad: list[str] = []
    for path in _iter_python_files(root, roots):
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            bad.append(path.relative_to(root).as_posix())
    return bad


def callers_of(
    repo_root: str | Path, name: str, roots: tuple[str, ...] = DEFAULT_ROOTS
) -> list[str]:
    """`path:line` of every call whose callee is spelled `name`.

    BY NAME, and the limit is stated rather than hidden: two functions sharing a
    name produce one list. Resolving that needs type inference, which `ast` does
    not do — and a list that says so beats a list that quietly picks one.
    """
    root = Path(repo_root)
    hits: list[str] = []
    for path in _iter_python_files(root, roots):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = getattr(func, "attr", None) or getattr(func, "id", None)
            if called == name:
                hits.append(f"{rel}:{node.lineno}")
    return sorted(hits)
