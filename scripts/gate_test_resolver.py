"""Map source files → existing test files via basename heuristic.

Extracted from gate_runner.py to keep that module under the filesize budget.
Used by the pytest gate's `{test_files_for_files}` substitution to scope
runs to relevant tests instead of the full suite.
"""

from __future__ import annotations

import os


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

    tests_root = os.path.join(base, "tests")
    # Walk tests/ once and bucket by basename; supports nested layouts
    # (tests/integration/test_foo.py, tests/unit/scoped/test_bar.py, …).
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
        # Permission errors / missing tests/ → empty index, callers fall back.
        tests_index = {}

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
    return found
