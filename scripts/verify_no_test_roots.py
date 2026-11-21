"""Early verify refusal when Python scope has no test roots.

``select_affected_tests`` already returns mode ``unavailable`` once the pytest
gate runs. That still spends the static phase. This module answers the same
question before ``run_gates`` so a no-suite project fails fast with a named
NoTestRoots diagnosis.

Docs-only and non-Python scopes are untouched. Explicit ``test_*.py`` /
``*_test.py`` paths remain valid without a discovered root (dead end #846).
"""

from __future__ import annotations

import os
from typing import Any


def _is_explicit_test_path(rel: str) -> bool:
    name = os.path.basename(rel.replace("\\", "/"))
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def python_sources_without_suite(files: list[str]) -> list[str]:
    """Python paths that need a test suite, not themselves tests."""
    sources: list[str] = []
    for raw in files:
        if not isinstance(raw, str) or not raw:
            continue
        rel = raw.replace("\\", "/")
        if not rel.endswith(".py"):
            continue
        if _is_explicit_test_path(rel):
            continue
        sources.append(rel)
    return sources


def no_test_roots_refusal(files: list[str], *, base: str | None = None) -> str | None:
    """Return a refusal message, or None when verify may continue."""
    sources = python_sources_without_suite(files)
    if not sources:
        return None
    from gate_test_resolver import test_roots

    root = base or os.getcwd()
    if test_roots(root):
        return None
    sample = ", ".join(sources[:5])
    more = " …" if len(sources) > 5 else ""
    return (
        "NoTestRoots: no test root found (neither `testing.roots` in "
        ".tausik/config.json nor a discoverable tests/ tree), but the declared "
        f"scope includes Python sources that need a suite: {sample}{more}. "
        "Configure testing.roots or add tests/ before verifying those files. "
        "Docs-only scopes do not need this. `--no-tests-expected` does not clear "
        "COULD_NOT_RUN for an applicable pytest gate — it only declares that "
        "skipped file-scoped gates were expected."
    )


def synth_no_test_roots_result(message: str) -> dict[str, Any]:
    return {
        "name": "no-test-roots",
        "passed": False,
        "skipped": False,
        "severity": "block",
        "output": message,
    }


def record_no_test_roots_block(
    conn: Any,
    *,
    slug: str,
    scope: str,
    cache_command: str,
    files_hash: str,
    files: list[str],
    scope_desc: dict[str, Any],
    trigger: str,
    details: dict[str, Any] | None,
    gate_signature: str,
    message: str,
    append_notes_fn: Any | None,
) -> tuple[bool, list[dict[str, Any]], str]:
    """Persist the early NoTestRoots refusal the same way security-scope does."""
    from verify_run_descriptor import VerificationRunDescriptor
    from verify_run_record import (
        VerificationRecordError,
        _record_verification,
        record_failure_result,
    )

    if append_notes_fn is not None:
        append_notes_fn(slug, message)
    roots_results = [synth_no_test_roots_result(message)]
    try:
        _record_verification(
            conn,
            slug=slug,
            scope=scope,
            command=f"noncacheable|{cache_command}",
            exit_code=1,
            summary="no-test-roots=FAIL (Python scope without a test suite)",
            files_hash=files_hash,
            gate_results=roots_results,
            scope_desc=scope_desc,
            trigger=trigger,
            details=details,
            descriptor=VerificationRunDescriptor.create(
                trigger=trigger,
                files=files,
                gate_signature=gate_signature,
                replayable=False,
                presentable_once=False,
            ),
        )
    except VerificationRecordError as exc:
        roots_results = [roots_results[0], record_failure_result(exc)]
    return False, roots_results, "no-test-roots"
