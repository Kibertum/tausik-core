"""Map source files → existing test files via basename heuristic.

Extracted from gate_runner.py to keep that module under the filesize budget.
Used by the pytest gate's `{test_files_for_files}` substitution to scope
runs to relevant tests instead of the full suite.
"""

from __future__ import annotations

import ast
import os

# Module-level constant a cross-cutting test declares to name the source trees it
# guards, e.g. CROSSCUTTING_SCOPE = ["scripts/hooks/", "bootstrap/"]. The resolver
# reads it statically (no import — a test module runs fixtures on import) and adds
# the test to a scoped run when a changed file falls under any prefix.
_CROSSCUTTING_CONST = "CROSSCUTTING_SCOPE"


def read_crosscutting_scope(test_path: str) -> list[str] | None:
    """Path prefixes a test declares it guards, or None if it declares nothing.

    Returns a list (possibly empty — the visible opt-out `CROSSCUTTING_SCOPE = []`,
    meaning "reviewed, not cross-cutting") when the module-level constant is a
    literal list/tuple; None when absent, unparseable, or not a literal. Never
    imports the module and never raises — a bad file simply reads as undeclared.
    """
    try:
        with open(test_path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == _CROSSCUTTING_CONST for t in node.targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError, SyntaxError):
            return None
        if isinstance(value, (list, tuple)):
            return [str(p).replace("\\", "/") for p in value]
        return None
    return None


def _crosscutting_index(base: str) -> dict[str, list[str]]:
    """{test_relpath: [prefixes]} for every declaring test under tests/.

    Text-filters to files that mention the constant before parsing, so the common
    case (a test that does not declare one) costs a cheap substring check, not an
    AST parse of all ~300 test files."""
    tests_root = os.path.join(base, "tests")
    index: dict[str, list[str]] = {}
    try:
        walker = os.walk(tests_root)
    except OSError:
        return index
    for dirpath, _dirnames, filenames in walker:
        for fn in filenames:
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            abs_path = os.path.join(dirpath, fn)
            try:
                with open(abs_path, encoding="utf-8") as fh:
                    if _CROSSCUTTING_CONST not in fh.read():
                        continue
            except OSError:
                continue
            scope = read_crosscutting_scope(abs_path)
            if scope:  # non-empty list only; [] opt-out and None both skip
                rel = os.path.relpath(abs_path, base).replace("\\", "/")
                index[rel] = scope
    return index


def _under_prefix(path: str, prefix: str) -> bool:
    """True when `path` lies at or under `prefix`, respecting directory bounds:
    `scripts/hooks/` matches `scripts/hooks/x.py` but not `scripts/hooks_x/y.py`."""
    path = path.replace("\\", "/")
    prefix = prefix.replace("\\", "/").rstrip("/")
    if not prefix:
        return False
    return path == prefix or path.startswith(prefix + "/")


def build_tests_index(base: str) -> dict[str, list[str]]:
    """Bucket every `tests/**/test_*.py` under `base` by basename.

    Walk tests/ once; supports nested layouts (tests/integration/test_foo.py).
    Permission errors / missing tests/ → empty index, callers fall back.

    Public because the pytest gate needs the DENOMINATOR of its own scope: a
    scoped run that reports "PASS" without saying "2 of 318 test files" reads
    as a statement about the whole project. See `run_command_gate`.
    """
    tests_root = os.path.join(base, "tests")
    tests_index: dict[str, list[str]] = {}
    try:
        for dirpath, _dirnames, filenames in os.walk(tests_root):
            for fn in filenames:
                if not (fn.startswith("test_") and fn.endswith(".py")):
                    continue
                abs_path = os.path.join(dirpath, fn)
                rel_path = os.path.relpath(abs_path, base).replace("\\", "/")
                tests_index.setdefault(fn, []).append(rel_path)
    except OSError:
        return {}
    return tests_index


def count_test_files(root: str | None = None) -> int:
    """How many test files exist in total — the denominator of a scoped run."""
    return sum(len(paths) for paths in build_tests_index(root or os.getcwd()).values())


def resolve_test_files_for_relevant(
    relevant_files: list[str] | None, *, root: str | None = None
) -> list[str]:
    """Map source files → existing test files via basename heuristic.

    For each `relevant_files` entry like `scripts/brain_init.py`, look for
    `tests/test_brain_init.py` and `tests/test_brain_init_*.py`. Also matches
    when the relevant file IS already a test file (returns it as-is).

    Returns a deduplicated list of existing test file paths (forward-slashed).
    Empty list = no mapping; caller decides whether to fall back to the full
    suite (only safe when relevant_files itself is empty) or to skip.
    """
    if not relevant_files:
        return []
    base = root or os.getcwd()
    found: list[str] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        norm = path.replace("\\", "/")
        if norm in seen:
            return
        seen.add(norm)
        found.append(norm)

    tests_index = build_tests_index(base)

    for raw in relevant_files:
        if not raw or not isinstance(raw, str):
            continue
        rel = raw.replace("\\", "/")
        # If the entry already points at a test file, accept it as-is.
        if "/tests/" in f"/{rel}" or os.path.basename(rel).startswith("test_"):
            abs_p = rel if os.path.isabs(rel) else os.path.join(base, rel)
            if os.path.isfile(abs_p):
                _add(rel)
                continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        if not stem:
            continue
        # Exact match: test_<stem>.py at any depth.
        for path in tests_index.get(f"test_{stem}.py", []):
            _add(path)
        # Glob suffix variants: test_<stem>_*.py at any depth.
        prefix = f"test_{stem}_"
        for fn, paths in tests_index.items():
            if fn.startswith(prefix) and fn.endswith(".py"):
                for path in paths:
                    _add(path)

    # Cross-cutting tests: a declared CROSSCUTTING_SCOPE prefix that any changed
    # file falls under pulls the test in — BY PATH, not basename. This is additive
    # only: it never falls back to the full suite (that promise is the caller's),
    # and a change matching no prefix adds nothing.
    cc_index = _crosscutting_index(base)
    if cc_index:
        rels = [r.replace("\\", "/") for r in relevant_files if r and isinstance(r, str)]
        for test_rel, prefixes in cc_index.items():
            if any(_under_prefix(f, p) for f in rels for p in prefixes):
                _add(test_rel)
    return found
