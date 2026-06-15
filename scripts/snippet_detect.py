"""AST-based clone detection engine (v15-snippet-ast-detect).

Walks Python sources, parses each into an AST, normalizes identifiers and
literals to placeholders (type-2 clone normalization), hashes the structural
signature of each candidate definition, and groups identical signatures into
clone clusters. Pure stdlib (``ast`` + ``hashlib``); no DB or CLI deps — the
CLI layer (project_cli_snippet) persists the clusters into the snippets table.

Normalization (what makes two near-duplicates collapse to one signature):
  * variable / arg / attribute / function / class names  → fixed placeholders
  * every literal constant                               → ``CONST``
  * position info (lineno/col), expression context, type comments → dropped
Two functions that differ only in their identifiers or literal values therefore
share a signature and cluster together; two structurally different functions do
not. Boilerplate guard: a candidate must carry at least ``min_stmts``
*significant* statements (docstrings and bare ``pass`` do not count), so trivial
stubs never form a cluster.

A candidate is a function / async-function / class definition spanning at least
``min_lines`` source lines. A cluster needs ≥2 members (same or different
files); re-running is idempotent because clusters are keyed by their content
hash and the snippets store dedups on it.
"""

from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import dataclass, field

# Directories never worth scanning for source clones — VCS, caches, vendored
# deps, build output, and TAUSIK's own data/generated dirs.
_SKIP_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        ".tausik",
        ".claude",
        ".cursor",
        "site-packages",
    }
)

# AST fields that carry no structural meaning for clone comparison.
_IGNORE_FIELDS = frozenset(
    {
        "lineno",
        "col_offset",
        "end_lineno",
        "end_col_offset",
        "ctx",
        "type_comment",
        "type_ignores",
        "kind",  # Constant.kind (the 'u'/None string prefix marker)
    }
)

# (NodeType, field) -> placeholder. Identifier-bearing fields are flattened to a
# constant token so type-2 clones (rename-only edits) hash identically.
_NAME_FIELDS = {
    ("Name", "id"): "VAR",
    ("arg", "arg"): "ARG",
    ("FunctionDef", "name"): "FUNC",
    ("AsyncFunctionDef", "name"): "FUNC",
    ("ClassDef", "name"): "CLASS",
    ("Attribute", "attr"): "ATTR",
    ("keyword", "arg"): "KW",
    ("alias", "name"): "ALIAS",
    ("alias", "asname"): "ALIAS",
    ("ExceptHandler", "name"): "EXC",
    # NOTE: Global.names / Nonlocal.names are list[str], NOT scalar identifier
    # fields. They are intentionally NOT mapped here — flattening a list to one
    # token would collapse `global a` and `global x, y` to the same signature
    # (cardinality lost → false-positive clusters). _dump recurses into the
    # list instead, preserving arity. The bare names stay verbatim, which only
    # makes the guard MORE conservative (two different globals won't cluster).
}


@dataclass
class CloneCluster:
    """One detected clone group: identical structure across ≥2 locations."""

    hash: str
    language: str
    code: str  # representative source (first member, verbatim)
    members: list[tuple[str, int, int]]  # (file, start_line, end_line)


@dataclass
class DetectResult:
    """Outcome of a detection run: clusters plus scan bookkeeping."""

    clusters: list[CloneCluster] = field(default_factory=list)
    scanned: int = 0  # files successfully parsed
    skipped: list[str] = field(default_factory=list)  # files that failed to parse


def iter_python_files(root: str):
    """Yield .py file paths under ``root`` (recursive), pruning noise dirs.

    ``root`` may be a single file (yielded as-is if it ends in .py) or a
    directory walked depth-first. Symlinked dirs are not followed.
    """
    if os.path.isfile(root):
        if root.endswith(".py"):
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune in place so os.walk does not descend into skipped dirs.
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _norm_field(node: ast.AST, name: str, value):
    """Normalize one AST field value into its structural signature."""
    key = (type(node).__name__, name)
    if key in _NAME_FIELDS:
        return _NAME_FIELDS[key]
    if isinstance(node, ast.Constant) and name == "value":
        return "CONST"
    return _dump(value)


def _dump(value) -> str:
    """Recursive canonical signature of an AST node / list / scalar."""
    if isinstance(value, ast.AST):
        parts = [
            f"{name}={_norm_field(value, name, child)}"
            for name, child in ast.iter_fields(value)
            if name not in _IGNORE_FIELDS
        ]
        return f"{type(value).__name__}({','.join(parts)})"
    if isinstance(value, list):
        return "[" + ",".join(_dump(v) for v in value) + "]"
    return repr(value)


def signature(node: ast.AST) -> str:
    """Normalized structural signature string for a subtree."""
    return _dump(node)


def _is_docstring(stmt: ast.stmt) -> bool:
    """True for a bare string-literal expression statement (docstring shape)."""
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _significant_count(node: ast.AST) -> int:
    """Number of significant statements in a definition's body (boilerplate guard).

    Structural noise that does NOT count: a bare ``pass``; the *leading*
    docstring only (a non-leading string-literal Expr is a deliberate inline
    statement and counts); and a nested function/class whose own body is itself
    insignificant — so an interface-shaped class of stub methods (each just
    ``pass``) scores 0 and never forms a clone cluster.
    """
    body = getattr(node, "body", None)
    if not isinstance(body, list):
        return 0
    count = 0
    for i, s in enumerate(body):
        if not isinstance(s, ast.stmt):
            continue
        if isinstance(s, ast.Pass):
            continue
        if i == 0 and _is_docstring(s):
            continue  # only the FIRST statement is the docstring
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if _significant_count(s) <= 0:
                continue  # a stub def/class contributes nothing real
        count += 1
    return count


def _line_span(node: ast.AST) -> int:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if start is None or end is None:
        return 0
    return int(end) - int(start) + 1


# Definition nodes treated as reusable units / clone candidates.
_CANDIDATE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _iter_candidates(tree: ast.AST, source: str, min_lines: int, min_stmts: int):
    """Yield (signature, code, start, end) for each qualifying definition.

    Walks the whole tree, so a nested function/class is also a candidate —
    duplicated inner definitions are real clones worth surfacing, even when
    their enclosing definition differs.
    """
    for node in ast.walk(tree):
        if not isinstance(node, _CANDIDATE_TYPES):
            continue
        if _line_span(node) < min_lines:
            continue
        if _significant_count(node) < min_stmts:
            continue  # boilerplate guard: too few real statements
        code = ast.get_source_segment(source, node)
        if not code:
            continue  # cannot recover verbatim source — skip rather than guess
        yield signature(node), code, node.lineno, node.end_lineno


def detect_clones(
    root: str,
    *,
    min_lines: int = 10,
    min_stmts: int = 3,
    language: str = "python",
) -> DetectResult:
    """Detect clone clusters under ``root``.

    A syntactically invalid (or unreadable) file is recorded in
    ``result.skipped`` and the scan continues — a finding, never a crash.
    Clusters are returned largest-first; each is keyed by a content hash so a
    later re-run dedups against the snippets store.
    """
    result = DetectResult()
    # signature -> list of (file, start, end, code) candidate occurrences
    groups: dict[str, list[tuple[str, int, int, str]]] = {}

    for path in iter_python_files(root):
        try:
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source)
        except (OSError, SyntaxError, ValueError):
            result.skipped.append(path)
            continue
        result.scanned += 1
        rel = os.path.normpath(path).replace(os.sep, "/")
        for sig, code, start, end in _iter_candidates(tree, source, min_lines, min_stmts):
            groups.setdefault(sig, []).append((rel, start, end, code))

    for sig, occ in groups.items():
        if len(occ) < 2:
            continue
        # Sort occurrences so both the member order AND the representative code
        # are independent of filesystem walk order — a re-run produces byte-for
        # -byte identical cluster content (the snippets store dedups on hash,
        # but a stable `code` keeps the persisted row reproducible too).
        occ.sort(key=lambda o: (o[0], o[1], o[2]))
        members = [(f, s, e) for (f, s, e, _c) in occ]
        digest = hashlib.sha256(sig.encode("utf-8")).hexdigest()
        result.clusters.append(
            CloneCluster(
                hash=digest,
                language=language,
                code=occ[0][3],
                members=members,
            )
        )

    result.clusters.sort(key=lambda c: (-len(c.members), c.hash))
    return result
