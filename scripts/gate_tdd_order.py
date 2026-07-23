"""TDD-order gate — test files must move alongside source files.

Lived in `gate_runner` until the gate registry (gate-registry-single-source)
made every built-in implementation addressable by module path: an
implementation that lives in the dispatcher cannot be pointed at from the
registry without the registry importing its own caller. It also bought
`gate_runner` the headroom it needed to stay under the 400-line cap it
enforces on everyone else.

`gate_runner` re-exports `run_tdd_order_gate`, so existing imports and the
architecture docs that name it keep working.
"""

from __future__ import annotations

import os

_CODE_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".php",
}

_TEST_PATTERNS = (
    "test_",
    "_test.",
    ".test.",
    ".spec.",
    "Test.",  # Java/Kotlin: FooTest.java, FooTest.kt
    "Tests.",  # Java/Kotlin: FooTests.java
    "tests/",
    "test/",
    "__tests__/",
)


def run_tdd_order_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Check that test files are present among changed files.

    TDD enforcement: if source files were changed, test files should also be changed.
    Skips if only non-code files were modified.
    """
    code_files = []
    test_files = []
    for f in files:
        normalized = f.replace("\\", "/")
        _, ext = os.path.splitext(f)
        if ext.lower() not in _CODE_EXTS:
            continue
        if any(p in normalized for p in _TEST_PATTERNS):
            test_files.append(f)
        else:
            code_files.append(f)

    if not code_files:
        return True, "No source code files changed — TDD check skipped."
    if test_files:
        return (
            True,
            f"TDD OK: {len(test_files)} test file(s) modified alongside {len(code_files)} source file(s).",
        )
    return False, (
        f"{len(code_files)} source file(s) changed but no test files modified. "
        "TDD requires tests to be written/updated alongside code changes."
    )
