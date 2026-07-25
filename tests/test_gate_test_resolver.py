"""The denominator the pytest gate reports has to be a real count.

full-pytest-hangs-while-scoped-pytest-is-green. `count_test_files` exists so a
scoped gate can say "2 of 318" instead of an unqualified "42 passed". The
mapping half of this module is pinned in tests/test_gates.py
(TestResolveTestFilesForRelevant); what is new here is the counting half and the
index it now shares with it.

Named for the module by the same basename heuristic the module implements, so a
scoped verify of gate_test_resolver.py actually runs these.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_test_resolver import (  # noqa: E402
    build_tests_index,
    count_test_files,
    resolve_test_files_for_relevant,
)


def _tree(tmp_path, *rel_paths):
    for rel in rel_paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("def test_x(): pass")
    return str(tmp_path)


class TestCountTestFiles:
    def test_it_counts_nested_layouts(self, tmp_path):
        root = _tree(
            tmp_path,
            "tests/test_a.py",
            "tests/integration/test_b.py",
            "tests/unit/deep/test_c.py",
        )
        assert count_test_files(root) == 3

    def test_it_ignores_non_test_files_in_tests(self, tmp_path):
        root = _tree(tmp_path, "tests/test_a.py", "tests/conftest.py", "tests/helpers.py")
        assert count_test_files(root) == 1

    def test_a_missing_tests_dir_counts_zero_rather_than_raising(self, tmp_path):
        """A project without tests/ must not blow up the gate that reports scope."""
        assert count_test_files(str(tmp_path)) == 0

    def test_same_basename_at_two_depths_counts_twice(self, tmp_path):
        """The index buckets by basename; the count is of FILES, not of names."""
        root = _tree(tmp_path, "tests/test_dup.py", "tests/integration/test_dup.py")
        assert len(build_tests_index(root)["test_dup.py"]) == 2
        assert count_test_files(root) == 2


class TestIndexIsTheOneUsedForMapping:
    def test_the_counter_and_the_mapper_see_the_same_files(self, tmp_path):
        """Numerator and denominator must come from one walk, or they can disagree.

        A count taken from a second, differently-written walk is free to drift
        from the mapping — and then the gate reports "1 of 2" for a suite of
        three, which is exactly the kind of quietly-wrong number this label was
        added to prevent.
        """
        root = _tree(tmp_path, "tests/test_alpha.py", "tests/integration/test_beta.py")
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "alpha.py").write_text("# src")

        mapped = resolve_test_files_for_relevant(["scripts/alpha.py"], root=root)
        indexed = [p for paths in build_tests_index(root).values() for p in paths]

        assert mapped == ["tests/test_alpha.py"]
        assert set(mapped) <= set(indexed)
        assert count_test_files(root) == len(indexed)
