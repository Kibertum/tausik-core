"""Behavioral tests for scripts/gate_tdd_order.py (gate-integrity-tests).

`run_tdd_order_gate` blocks a closure that changed source code without touching a
test. It was registered with zero behavioral tests, so an inverted verdict —
passing a code-only change, or failing a change that DID include a test — would
ship silently. These pin the verdict on each branch and the full `_TEST_PATTERNS`
recognition table, including Windows-backslash normalisation.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from gate_tdd_order import run_tdd_order_gate  # noqa: E402


# ------------------------------------------------------------ AC3: verdict per branch ---


class TestVerdict:
    def test_source_without_test_blocks(self):
        ok, msg = run_tdd_order_gate({}, ["scripts/foo.py"])
        assert ok is False
        assert "no test files" in msg.lower()

    def test_source_with_test_passes(self):
        ok, msg = run_tdd_order_gate({}, ["scripts/foo.py", "tests/test_foo.py"])
        assert ok is True
        assert "tdd ok" in msg.lower()

    def test_only_non_code_files_skips(self):
        ok, msg = run_tdd_order_gate({}, ["README.md", "docs/x.rst"])
        assert ok is True
        assert "skipped" in msg.lower()

    def test_empty_file_list_skips(self):
        ok, msg = run_tdd_order_gate({}, [])
        assert ok is True
        assert "skipped" in msg.lower()

    def test_test_file_alone_is_not_source(self):
        """A lone test file means no SOURCE changed → skipped, never blocked."""
        ok, _ = run_tdd_order_gate({}, ["tests/test_foo.py"])
        assert ok is True


# ------------------------------------------------------ AC4: _TEST_PATTERNS coverage ---


class TestPatternRecognition:
    @pytest.mark.parametrize(
        "test_path",
        [
            "tests/test_foo.py",  # test_ prefix + tests/ dir
            "app/foo_test.py",  # _test.
            "web/foo.test.ts",  # .test.
            "web/foo.spec.js",  # .spec.
            "java/FooTest.java",  # Test.
            "java/FooTests.kt",  # Tests.
            "web/__tests__/foo.tsx",  # __tests__/
            "svc/test/foo.go",  # test/ dir
        ],
    )
    def test_each_pattern_family_counts_as_test(self, test_path):
        """A source file plus a file matching each pattern family → TDD OK.
        If the file were NOT recognised as a test, the verdict would flip to
        blocked, so a green here proves recognition."""
        ok, msg = run_tdd_order_gate({}, ["src/foo.py", test_path])
        assert ok is True, f"{test_path} not recognised as a test file: {msg}"

    def test_windows_backslash_paths_normalised(self):
        ok, _ = run_tdd_order_gate({}, ["app\\pkg\\foo.py", "app\\pkg\\test_foo.py"])
        assert ok is True

    def test_code_ext_file_under_tests_dir_counts_as_test(self):
        """A helper .py under tests/ is a test by the tests/ pattern, so a source
        change paired with it passes."""
        ok, _ = run_tdd_order_gate({}, ["src/foo.py", "tests/helpers.py"])
        assert ok is True

    def test_non_code_extension_is_ignored_entirely(self):
        """A .json fixture under tests/ is neither source nor test — a source
        change alongside only it still blocks (it is not a test file)."""
        ok, _ = run_tdd_order_gate({}, ["src/foo.py", "tests/data.json"])
        assert ok is False
