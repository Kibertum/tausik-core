"""Plan an explainable affected-test lane with a fail-open full fallback.

The existing resolver deliberately answers a narrow question: which test files
have a deterministic edge from ``relevant_files``?  An ordinary verify needs a
second answer as well: whether that narrow answer is trustworthy.  This module
keeps those concerns separate.  It never guesses through malformed config,
unparseable dependency declarations, missing mappings for Python source, or a
security-sensitive scope; those states widen to the complete applicable pytest
lane and are recorded in a durable evidence artifact.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from dataclasses import dataclass

from gate_test_resolver import (
    _is_global_tree_prefix,
    _observed_tests_for,
    _under_prefix,
    build_tests_index,
    parse_errors_for_relevant,
    read_crosscutting_scope,
    resolve_test_files_for_relevant,
    test_roots,
    top_level_imports,
)
from security_pattern import is_security_sensitive
from tausik_utils import tausik_config_path

_CROSSCUTTING_CONST = "CROSSCUTTING_SCOPE"


@dataclass(frozen=True)
class AffectedTestPlan:
    """A pytest selection and the evidence that justified every test file."""

    mode: str  # affected | full | none | unavailable
    test_files: tuple[str, ...]
    reasons: dict[str, tuple[str, ...]]
    fallback_reason: str | None = None


def _all_test_files(base: str) -> list[str]:
    index = build_tests_index(base)
    return sorted(path for paths in index.values() for path in paths)


def _config_uncertainty(base: str) -> str | None:
    """Return why test-root configuration cannot safely narrow, if anything."""
    path = tausik_config_path(base)
    if not os.path.isfile(path):
        return None  # discovery/default tests/ is the documented path
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        return f"test-root config is unreadable or invalid: {type(exc).__name__}"
    testing = cfg.get("testing")
    if testing is None:
        return None
    if not isinstance(testing, dict):
        return "testing config is not an object"
    if "roots" not in testing:
        return None
    roots = testing["roots"]
    if not isinstance(roots, list) or not roots:
        return "testing.roots is not a non-empty list"
    if any(not isinstance(root, str) or not root.strip() for root in roots):
        return "testing.roots contains a non-string or empty entry"
    missing = [root for root in roots if not os.path.isdir(os.path.join(base, root))]
    if missing:
        return "configured test root is missing: " + ", ".join(sorted(missing))
    return None


def _declaration_uncertainty(base: str, tests: list[str]) -> str | None:
    """Reject malformed CROSSCUTTING_SCOPE state instead of dropping it."""
    for rel in tests:
        path = os.path.join(base, rel.replace("/", os.sep))
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            return f"candidate test source is unreadable: {rel} ({type(exc).__name__})"
        if _CROSSCUTTING_CONST not in text:
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            return f"candidate dependency declaration is unparseable: {rel}"
        declared = False
        for node in tree.body:
            targets = getattr(node, "targets", None) or [getattr(node, "target", None)]
            if _CROSSCUTTING_CONST in {getattr(target, "id", None) for target in targets}:
                declared = True
                break
        if declared and read_crosscutting_scope(path) is None:
            return f"candidate dependency declaration is not a literal path list: {rel}"
    return None


def _fixture_tests(base: str, relevant_files: list[str], all_tests: list[str]) -> dict[str, str]:
    """Tests reached by a changed conftest.py according to pytest directory scope."""
    reached: dict[str, str] = {}
    for raw in relevant_files:
        rel = raw.replace("\\", "/")
        if os.path.basename(rel) != "conftest.py":
            continue
        parent = os.path.dirname(rel).rstrip("/")
        prefix = parent + "/" if parent else ""
        for test_rel in all_tests:
            if test_rel.startswith(prefix):
                reached[test_rel] = f"fixture-scope:{rel}"
    return reached


def _explain_affected(
    base: str, relevant_files: list[str], selected: list[str], fixture_reasons: dict[str, str]
) -> dict[str, tuple[str, ...]]:
    """Attach one or more deterministic edges to every selected test file."""
    changed = [raw.replace("\\", "/") for raw in relevant_files if isinstance(raw, str) and raw]
    modules = {os.path.splitext(os.path.basename(rel))[0] for rel in changed if rel.endswith(".py")}
    observed = _observed_tests_for(base, relevant_files)
    explained: dict[str, tuple[str, ...]] = {}
    for test_rel in selected:
        reasons: list[str] = []
        if test_rel in changed:
            reasons.append(f"changed-test:{test_rel}")
        stem = os.path.splitext(os.path.basename(test_rel))[0]
        for rel in changed:
            if not rel.endswith(".py"):
                continue
            source_stem = os.path.splitext(os.path.basename(rel))[0]
            if stem == f"test_{source_stem}" or stem.startswith(f"test_{source_stem}_"):
                reasons.append(f"basename:{rel}")
        path = os.path.join(base, test_rel.replace("/", os.sep))
        try:
            with open(path, encoding="utf-8") as fh:
                imports = top_level_imports(fh.read())
        except OSError:
            imports = set()
        for module in sorted(modules & imports):
            reasons.append(f"direct-import:{module}")
        scope = read_crosscutting_scope(path) or []
        for prefix in scope:
            if not _is_global_tree_prefix(prefix) and any(
                _under_prefix(rel, prefix) for rel in changed
            ):
                reasons.append(f"declared-scope:{prefix}")
        if test_rel in observed:
            reasons.append("observed-coverage")
        if test_rel in fixture_reasons:
            reasons.append(fixture_reasons[test_rel])
        # The legacy resolver can only add one further edge: a valid observed
        # coverage row. Keep the artifact total even if a future resolver edge
        # lands before this explainer is extended; the label makes that drift
        # visible rather than silently emitting an unexplained choice.
        if not reasons:
            reasons.append("resolver-edge:unclassified")
        explained[test_rel] = tuple(dict.fromkeys(reasons))
    return explained


def select_affected_tests(
    relevant_files: list[str] | None, *, root: str | None = None
) -> AffectedTestPlan:
    """Return the smallest defensible selection, widening on uncertainty."""
    base = root or os.getcwd()
    files = [raw for raw in (relevant_files or []) if isinstance(raw, str) and raw]
    uncertainty = _config_uncertainty(base)
    roots = test_roots(base)
    if not roots:
        explicit_tests = []
        if uncertainty is None:
            for raw in files:
                rel = raw.replace("\\", "/")
                name = os.path.basename(rel)
                if (
                    name.endswith(".py")
                    and (name.startswith("test_") or name.endswith("_test.py"))
                    and os.path.isfile(os.path.join(base, rel.replace("/", os.sep)))
                ):
                    explicit_tests.append(rel)
        if explicit_tests:
            selected_explicit = tuple(dict.fromkeys(explicit_tests))
            return AffectedTestPlan(
                "affected",
                selected_explicit,
                {rel: (f"changed-test:{rel}",) for rel in selected_explicit},
            )
        return AffectedTestPlan(
            "unavailable", (), {}, uncertainty or "no applicable test root was found"
        )
    all_tests = _all_test_files(base)

    if uncertainty is None:
        uncertainty = _declaration_uncertainty(base, all_tests)
    parse_errors = parse_errors_for_relevant(files, root=base)
    if uncertainty is None and parse_errors:
        uncertainty = "candidate test source is unparseable: " + ", ".join(parse_errors[:10])
    if uncertainty is None and is_security_sensitive(files):
        uncertainty = "security-sensitive scope requires the complete applicable lane"

    fixture_reasons = _fixture_tests(base, files, all_tests)
    selected = resolve_test_files_for_relevant(files, root=base)
    # conftest.py is support code, not a collectable test target. The legacy
    # resolver accepts any Python file under tests/ as a direct target; replace
    # that passthrough with the fixture subtree it actually affects.
    selected = [rel for rel in selected if os.path.basename(rel) != "conftest.py"]
    for rel in fixture_reasons:
        if rel not in selected:
            selected.append(rel)

    normalized_files = [rel.replace("\\", "/") for rel in files]
    python_sources = [
        rel
        for rel in normalized_files
        if rel.endswith(".py")
        and "/tests/" not in f"/{rel}"
        and not os.path.basename(rel).startswith("test_")
    ]
    if uncertainty is None and python_sources and not selected:
        uncertainty = "Python source has no defensible test dependency mapping"

    if uncertainty is not None:
        reasons: dict[str, tuple[str, ...]] = {
            rel: (f"fail-open:{uncertainty}",) for rel in all_tests
        }
        return AffectedTestPlan("full", tuple(all_tests), reasons, uncertainty)
    if not selected:
        return AffectedTestPlan("none", (), {})
    reasons = _explain_affected(base, files, selected, fixture_reasons)
    # The legacy basename resolver also paired arbitrary prose/config names
    # (for example docs/en/mcp.md) with every test_mcp_*.py module. Basename is
    # evidence for Python source, not for unrelated file types. Keep a test only
    # when at least one real edge above explains it.
    selected = [rel for rel in selected if reasons[rel] != ("resolver-edge:unclassified",)]
    if not selected:
        return AffectedTestPlan("none", (), {})
    return AffectedTestPlan("affected", tuple(selected), {rel: reasons[rel] for rel in selected})


def write_selection_evidence(
    plan: AffectedTestPlan, relevant_files: list[str] | None, *, root: str | None = None
) -> str:
    """Persist the complete explanation and return its repo-relative path."""
    base = root or os.getcwd()
    payload = {
        "schema_version": 1,
        "mode": plan.mode,
        "fallback_reason": plan.fallback_reason,
        "relevant_files": list(relevant_files or []),
        "selected": [
            {"test": rel, "reasons": list(plan.reasons.get(rel, ()))} for rel in plan.test_files
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]
    rel_path = f".tausik/evidence/affected-tests-{digest}.json"
    path = os.path.join(base, rel_path.replace("/", os.sep))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(encoded)
    except OSError:
        return "unavailable"
    return rel_path
