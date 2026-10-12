"""Build total per-source test edges without rescanning the test tree N times."""

from __future__ import annotations

import ast
import os

from gate_test_resolver import (
    _basename_matches,
    _crosscutting_index,
    _discovery_skip,
    _is_global_tree_prefix,
    _under_prefix,
    build_tests_index,
    is_test_module_path,
    test_roots,
)
from gate_test_observed_edges import observed_test_edges_for


def _qualified_imports(text: str) -> set[str]:
    """Imported module paths, retaining qualification for collision handling."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
            out.update(f"{node.module}.{alias.name}" for alias in node.names if alias.name != "*")
    return out


def _module_candidates(path: str) -> set[str]:
    module = os.path.splitext(path)[0].replace("/", ".")
    parts = module.split(".")
    return {".".join(parts[index:]) for index in range(len(parts))}


def _source_identities(base: str, roots: list[str], changed: list[str]) -> set[str]:
    """Return live and changed/deleted Python source identities."""
    skip = _discovery_skip() | {".git"}
    sources = {path for path in changed if path.endswith(".py")}
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in skip]
        for filename in filenames:
            if not filename.endswith(".py") or filename == "conftest.py":
                continue
            rel = os.path.relpath(os.path.join(dirpath, filename), base).replace("\\", "/")
            if not is_test_module_path(base, rel, roots):
                sources.add(rel)
    return sources


def _candidate_owners(sources: set[str]) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for source in sources:
        for candidate in _module_candidates(source):
            owners.setdefault(candidate, set()).add(source)
    return owners


def source_test_edges_for_relevant(
    sources: list[str], *, root: str | None = None
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Resolve per-source test edges in one test-tree and repository scan."""
    base = root or os.getcwd()
    normalized = [source.replace("\\", "/") for source in sources]
    edges: dict[str, dict[str, list[str]]] = {source: {} for source in normalized}
    roots = test_roots(base)
    tests_index = build_tests_index(base)
    owners = _candidate_owners(_source_identities(base, roots, normalized))

    imports_by_test: dict[str, set[str]] = {}
    for paths in tests_index.values():
        for test_rel in paths:
            try:
                with open(
                    os.path.join(base, test_rel.replace("/", os.sep)), encoding="utf-8"
                ) as fh:
                    imports_by_test[test_rel] = _qualified_imports(fh.read())
            except OSError:
                imports_by_test[test_rel] = set()

    scopes = _crosscutting_index(base)
    observed_edges = observed_test_edges_for(base, normalized)
    for source in normalized:
        stem = os.path.splitext(os.path.basename(source))[0]
        if owners.get(stem) == {source}:
            for test_rel in _basename_matches(stem, tests_index):
                edges[source].setdefault(test_rel, []).append(f"basename:{source}")

        candidates = {
            candidate
            for candidate in _module_candidates(source)
            if owners.get(candidate) == {source}
        }
        for test_rel, imported in imports_by_test.items():
            if candidates & imported:
                edges[source].setdefault(test_rel, []).append(f"direct-import:{source}")

        for test_rel, prefixes in scopes.items():
            for prefix in prefixes:
                if not _is_global_tree_prefix(prefix) and _under_prefix(source, prefix):
                    edges[source].setdefault(test_rel, []).append(f"declared-scope:{prefix}")
                    break

        for test_rel in observed_edges.get(source, set()):
            edges[source].setdefault(test_rel, []).append(f"observed-coverage:{source}")

    return {
        source: {test: tuple(reasons) for test, reasons in tests.items()}
        for source, tests in edges.items()
    }
