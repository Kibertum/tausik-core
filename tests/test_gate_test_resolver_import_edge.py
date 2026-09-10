"""The IMPORT edge of scoped test resolution (invariant-guards-are-invisible-...).

The basename heuristic maps `scripts/foo.py` -> `tests/test_foo.py`. A guard named
after the RELATION it pins — `test_ddl_fixture_parity` for `backend_schema.SCHEMA_SQL`
against the fixtures — is named after neither side and so maps to nothing. Measured
before this edge existed: 200 of 408 test files (49%) could not be selected by ANY
change to any of the 3142 tracked source files, and all five guards that the shift
handover told humans to remember by name were among them.

A test that IMPORTS a module is relevant to a change in that module, whatever the
two files are called. That is the edge added here, and it revives 180 of those 200.
The remaining 18 import no product code at all (they read files and configs), and
`tests/test_crosscutting_registry.py` keeps them visible rather than silent.

DEPTH ONE ON PURPOSE — pinned by `test_transitive_import_is_deliberately_not_followed`
below, so nobody "fixes" it without reading the measurement: following imports
transitively takes the median module's fan-out from 1 test to 177 of 408, which is
the full lane wearing a scope's clothes.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import gate_test_resolver as gtr  # noqa: E402


def _mk(tmp_path, rel, body=""):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


class TestTopLevelImports:
    def test_plain_import(self):
        assert gtr.top_level_imports("import backend_schema\n") == {"backend_schema"}

    def test_from_import_names_the_module_not_the_symbol(self):
        assert gtr.top_level_imports("from backend_schema import SCHEMA_SQL\n") == {
            "backend_schema"
        }

    def test_dotted_import_yields_the_top_package(self):
        assert gtr.top_level_imports("import a.b.c\n") == {"a"}

    def test_relative_import_names_no_module_of_its_own(self):
        assert gtr.top_level_imports("from . import sibling\n") == set()

    def test_import_inside_a_function_still_counts(self):
        """A late import is still a dependency — `test_schema_upgrade_parity`
        imports its baseline schema inside the test body."""
        assert gtr.top_level_imports("def t():\n    import backend_schema\n") == {"backend_schema"}

    def test_a_mention_is_not_an_import(self):
        """Parsed, never matched as text: a substring hits the name inside a
        comment, a docstring or a longer word (convention #417)."""
        text = (
            '"""backend_schema is compared here."""\n'
            "# see backend_schema for the DDL\n"
            "NAME = 'backend_schema'\n"
            "import backend_schema_indexes\n"
        )
        assert gtr.top_level_imports(text) == {"backend_schema_indexes"}

    def test_unparseable_source_reads_as_no_imports_not_a_crash(self):
        assert gtr.top_level_imports("def (:\n") == set()


class TestResolverFollowsImports:
    def _tree(self, tmp_path):
        _mk(tmp_path, "scripts/backend_schema.py", "SCHEMA_SQL = ''\n")
        _mk(tmp_path, "scripts/unrelated.py", "x = 1\n")
        # named after the relation it guards — basename maps it to nothing
        _mk(tmp_path, "tests/test_ddl_parity.py", "from backend_schema import SCHEMA_SQL\n")
        # mentions the module without importing it
        _mk(tmp_path, "tests/test_mentions_only.py", "# backend_schema is nice\n")
        return tmp_path

    def test_importing_test_is_selected_by_a_change_to_the_module(self, tmp_path):
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(["scripts/backend_schema.py"], root=str(tmp_path))
        assert "tests/test_ddl_parity.py" in got

    def test_a_mere_mention_is_not_selected(self, tmp_path):
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(["scripts/backend_schema.py"], root=str(tmp_path))
        assert "tests/test_mentions_only.py" not in got

    def test_unrelated_module_selects_nothing(self, tmp_path):
        self._tree(tmp_path)
        got = gtr.resolve_test_files_for_relevant(["scripts/unrelated.py"], root=str(tmp_path))
        assert got == []

    def test_non_python_change_adds_no_import_edge(self, tmp_path):
        """`docs/backend_schema.md` is not a module; nothing imports it."""
        self._tree(tmp_path)
        _mk(tmp_path, "docs/backend_schema.md", "prose\n")
        got = gtr.resolve_test_files_for_relevant(["docs/backend_schema.md"], root=str(tmp_path))
        assert "tests/test_ddl_parity.py" not in got

    def test_unparseable_candidate_is_named_not_silently_dropped(self, tmp_path):
        self._tree(tmp_path)
        _mk(tmp_path, "tests/test_broken.py", "import backend_schema\ndef (:\n")
        assert gtr.parse_errors_for_relevant(["scripts/backend_schema.py"], root=str(tmp_path)) == [
            "tests/test_broken.py"
        ]

    def test_direct_import_count_excludes_a_mere_mention(self, tmp_path):
        self._tree(tmp_path)
        assert gtr.direct_import_count_for_relevant(["scripts/backend_schema.py"], root=str(tmp_path)) == 1

    def test_transitive_import_is_deliberately_not_followed(self, tmp_path):
        """DEPTH ONE, measured and chosen. A test importing `handlers` does NOT run
        when `backend_schema`, which `handlers` imports, changes. Following the
        chain was measured on this repo: the median module goes from pulling 1 test
        to pulling 177 of 408 — a scope that selects half the suite is not a scope.
        Change this only with a fresh measurement, not with an intuition."""
        self._tree(tmp_path)
        _mk(tmp_path, "scripts/handlers.py", "import backend_schema\n")
        _mk(tmp_path, "tests/test_via_handlers.py", "import handlers\n")
        got = gtr.resolve_test_files_for_relevant(["scripts/backend_schema.py"], root=str(tmp_path))
        assert "tests/test_via_handlers.py" not in got
        # ...and the direct edge to `handlers` itself still works
        assert "tests/test_via_handlers.py" in gtr.resolve_test_files_for_relevant(
            ["scripts/handlers.py"], root=str(tmp_path)
        )


class TestTheFiveGuardsNeedNoHumanToRememberThem:
    """AC2, asserted against THIS repository, not a fixture.

    Memory #421 told every agent to hand-mix five file names into any scoped run,
    because none of them could be selected automatically. The rule was forgotten
    once already — that is how it came to be written down. These are the five.
    """

    FIVE = [
        "tests/test_ddl_fixture_parity.py",
        "tests/test_schema_upgrade_parity.py",
        "tests/test_schema_index_parity.py",
        "tests/test_consumer_layout.py",
        "tests/test_crosscutting_registry.py",
    ]

    def _product_modules(self):
        """{module name: repo-relative path} across the source trees.

        `os.listdir` of three named directories, not a tree walk: this file is
        basename-reachable and has no business declaring a cross-cutting scope.
        """
        out: dict[str, str] = {}
        for tree in ("scripts", "bootstrap", "harness"):
            d = os.path.join(_ROOT, tree)
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if fn.endswith(".py"):
                    out.setdefault(os.path.splitext(fn)[0], f"{tree}/{fn}")
        return out

    def test_each_guard_is_pulled_in_by_every_module_it_guards(self):
        prod = self._product_modules()
        misses = []
        for guard in self.FIVE:
            path = os.path.join(_ROOT, guard.replace("/", os.sep))
            assert os.path.isfile(path), f"{guard} moved — this AC names a real file"
            with open(path, encoding="utf-8") as fh:
                guarded = sorted(gtr.top_level_imports(fh.read()) & set(prod))
            assert guarded, f"{guard} imports no product module — the edge cannot reach it"
            for module in guarded:
                got = gtr.resolve_test_files_for_relevant([prod[module]], root=_ROOT)
                if guard not in got:
                    misses.append(f"{prod[module]} -> {guard}")
        assert not misses, (
            "these invariant guards are still invisible to a scoped run, so the "
            "shift handover would have to name them by hand again:\n  " + "\n  ".join(misses)
        )

    def test_a_scoped_run_stays_scoped(self):
        """The edge must not quietly become 'run everything'. A narrow change stays
        narrow; the three broad modules are broad because the change is."""
        total = gtr.count_test_files(_ROOT)
        got = gtr.resolve_test_files_for_relevant(["scripts/backend_schema_indexes.py"], root=_ROOT)
        assert 0 < len(got) < total * 0.15, (
            f"a one-module change selected {len(got)} of {total} test files — the "
            "import edge stopped being a scope"
        )
