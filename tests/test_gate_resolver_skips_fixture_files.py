"""A fixture declared in relevant_files is not a pytest path.

scoped-verify-passes-fixture-files-to-pytest: the upgrade task declared
`tests/fixtures/schema_v44_tausik_1_8_0.sql`; the resolver accepted anything
under tests/ as-is, pytest was handed the .sql among the test files, collected
nothing from any of them, and the gate answered CANNOT-RUN.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_test_resolver import resolve_test_files_for_relevant  # noqa: E402


def _tree(tmp_path, *rel_paths):
    for rel in rel_paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("def test_x(): pass\n" if rel.endswith(".py") else "CREATE TABLE t(x);\n")
    return str(tmp_path)


def test_a_non_python_file_under_tests_is_not_returned(tmp_path):
    base = _tree(tmp_path, "tests/fixtures/schema_v44.sql", "tests/fixtures/data.json")
    got = resolve_test_files_for_relevant(
        ["tests/fixtures/schema_v44.sql", "tests/fixtures/data.json"], root=base
    )
    assert not [p for p in got if not p.endswith(".py")]


def test_the_test_beside_the_fixture_is_still_returned(tmp_path):
    base = _tree(tmp_path, "tests/test_upgrade.py", "tests/fixtures/schema_v44.sql")
    got = resolve_test_files_for_relevant(
        ["tests/test_upgrade.py", "tests/fixtures/schema_v44.sql"], root=base
    )
    assert got == ["tests/test_upgrade.py"]
