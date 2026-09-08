"""The graph is the FRAMEWORK's machinery, not this repository's.

MEASURED BEFORE ANY OF THIS (spike ag-spike-schema-against-three-stacks, run on
the real `tests/consumer_layout.py` fixture and on a real git repository holding
python, terraform and markdown):

    symbol index, consumer project   0 declarations, while backend/api/orders.py
                                     and backend/app/services/quota.py sat there
                                     full of them. Roots were ("scripts",
                                     "bootstrap", "tests", "harness") — OUR
                                     directory names, shipped as a constant.
    artifact kinds                   9 suffixes for 25 declared stacks, and
                                     exactly ONE produced `code`: `.py`.
    graph tables                     0 / 0 / 0 rows, a day after the substrate
                                     shipped, in the repository that wrote it.
    full build                       2m27s, because ~22,000 autocommitted
                                     statements each paid a WAL fsync.

WHAT THIS FILE ASSERTS is that a project which is not this one gets answers. The
consumer fixture is not decoration: it exists because six defects of the class
"green at home, red at the customer" reached live installations, and a graph
proved only on our own tree would be the seventh.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import source_roots as sr  # noqa: E402
from consumer_layout import build_consumer_project  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402
from project_types import DEFAULT_STACKS  # noqa: E402
from service_artifact_graph import classify  # noqa: E402
from symbol_index import build_index, roots_for  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/"]

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _fresh(tmp_path: Path, name: str) -> Path:
    """A NEW empty directory under `tmp_path`.

    `build_consumer_project` creates `<given>/consumer` itself and refuses a
    parent that does not exist, so two consumers in one test need two parents
    made here rather than two paths named here.
    """
    path = tmp_path / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _consumer(tmp_path: Path) -> Path:
    """A consumer project with real source of its own under `backend/`."""
    proj = build_consumer_project(tmp_path)
    root = Path(getattr(proj, "root", getattr(proj, "project_dir", tmp_path)))
    app = root / "backend" / "api"
    app.mkdir(parents=True, exist_ok=True)
    (app / "orders.py").write_text(
        "def place_order(cart):\n    return sum(cart)\n", encoding="utf-8"
    )
    return root


class TestRootsComeFromTheProject:
    """AC1. The number that made this task exist: 0 declarations found."""

    def test_a_consumer_project_is_indexed_at_all(self, tmp_path):
        root = _consumer(tmp_path)
        roots, source = roots_for(root)
        found = build_index(root, roots)
        assert any(s.name == "place_order" for s in found), (
            f"the consumer's own code was not indexed. roots={roots} source={source} — "
            "this is the defect measured at 0 declarations before roots were derived"
        )

    def test_our_own_tree_does_not_regress(self):
        """The constant was RIGHT for us; it was wrong for everybody else.

        Measured: deriving the roots yields the same declarations in the same
        time on this repository. A fix that traded somebody else's project for
        ours would not be a fix.
        """
        roots, source = roots_for(_REPO)
        assert source in ("git", "declared"), source
        for expected in ("scripts", "bootstrap", "tests", "harness"):
            assert expected in roots, f"{expected} disappeared from our own roots"

    def test_a_declaration_by_the_project_outranks_what_we_infer(self, tmp_path):
        (tmp_path / ".tausik").mkdir()
        (tmp_path / ".tausik" / "config.json").write_text(
            '{"source_roots": ["srv", "web"]}', encoding="utf-8"
        )
        roots, source = sr.resolve(str(tmp_path))
        assert (roots, source) == (["srv", "web"], "declared")

    def test_git_and_disk_answer_the_same_question(self, tmp_path):
        """A resolver whose answer depends on which branch it took is worse
        than either branch. `.github` is tracked source to one and was
        invisible to the other until this was asserted."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.go").write_text("package main\n", encoding="utf-8")
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")

        from_disk, source = sr.resolve(str(tmp_path))
        assert source == "disk"

        subprocess.run(["git", "init", "-q"], cwd=tmp_path, env=_GIT_ENV, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, env=_GIT_ENV, check=True)
        subprocess.run(["git", "commit", "-qm", "x"], cwd=tmp_path, env=_GIT_ENV, check=True)
        from_git, source = sr.resolve(str(tmp_path))
        assert source == "git"
        assert from_git == from_disk, (from_git, from_disk)

    def test_a_tree_with_no_locatable_source_says_so_rather_than_guessing(self, tmp_path):
        (tmp_path / "pictures").mkdir()
        (tmp_path / "pictures" / "a.png").write_bytes(b"\x89PNG")
        roots, source = sr.resolve(str(tmp_path))
        assert (roots, source) == ([], "none")
        assert "no source roots found" in sr.describe(roots, source)


class TestTheAnswerNamesWhereItLooked:
    """AC2. "Nothing here" and "we searched the wrong tree" are different
    answers, and only one of them is about the symbol."""

    def test_the_positive_answer_carries_the_roots_and_their_provenance(self, tmp_path):
        from symbol_answer import answer

        root = _consumer(tmp_path)
        out = answer(root, "place_order", with_callers=False)
        assert "searched:" in out
        assert "backend" in out

    def test_the_negative_answer_carries_them_too(self, tmp_path):
        from symbol_answer import answer

        out = answer(_consumer(tmp_path), "no_such_name_at_all")
        assert "searched:" in out

    def test_the_fallback_is_named_as_a_failure_not_dressed_as_a_finding(self):
        from symbol_answer import _roots_line

        line = _roots_line(("scripts",), "fallback")
        assert "NOT DERIVED" in line
        assert "may be about the wrong files" in line


class TestKindsCoverTheStacksTheFrameworkClaims:
    """AC3. 9 suffixes for 25 declared stacks, one of which produced `code`."""

    #: One representative source path per declared stack. Written out rather
    #: than derived, because the point is to check OUR table against the stacks
    #: we advertise — a derivation from the same table would check nothing.
    SAMPLE = {
        "python": "app/main.py",
        "django": "app/models.py",
        "flask": "app/routes.py",
        "fastapi": "app/api.py",
        "javascript": "src/index.js",
        "typescript": "src/index.ts",
        "react": "src/App.jsx",
        "next": "app/page.tsx",
        "nuxt": "pages/index.vue",
        "vue": "src/App.vue",
        "svelte": "src/App.svelte",
        "go": "cmd/main.go",
        "rust": "src/lib.rs",
        "java": "src/Main.java",
        "kotlin": "src/Main.kt",
        "swift": "Sources/App.swift",
        "flutter": "lib/main.dart",
        "php": "src/Kernel.php",
        "laravel": "app/Http/Controllers/HomeController.php",
        "blade": "resources/views/home.blade.php",
        "terraform": "infra/main.tf",
        "ansible": "playbooks/site.yml",
        "helm": "chart/values.yaml",
        "kubernetes": "k8s/deployment.yaml",
        "docker": "Dockerfile",
    }

    def test_every_declared_stack_has_a_sample(self):
        """PREMISE. If a stack is added and no sample is, this file goes quiet
        about it — which is how the previous table stayed at nine suffixes."""
        missing = sorted(set(DEFAULT_STACKS) - set(self.SAMPLE))
        assert not missing, f"stacks declared but not represented here: {missing}"

    @pytest.mark.parametrize("stack", sorted(SAMPLE))
    def test_its_source_is_code_or_config_never_other(self, stack):
        kind = classify(self.SAMPLE[stack])
        assert kind in ("code", "config"), (
            f"{stack}: {self.SAMPLE[stack]} classified {kind!r}. Before this task 24 of "
            "25 declared stacks landed in 'other', indistinguishable from a binary blob"
        )

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("assets/logo.png", id="image"),
            pytest.param("bin/tool.exe", id="binary"),
            pytest.param("fonts/Inter.woff2", id="font"),
        ],
    )
    def test_a_suffix_we_genuinely_do_not_know_is_still_other(self, path):
        """`other` is not the defect — claiming to know is. No new kind was
        invented for the unknown case, because the kind column is a closed list
        and widening it would be the migration AC10 forbids."""
        assert classify(path) == "other"


class TestATestIsRecognisedInAnyStacksConvention:
    """AC4. A framework that knows only `tests/` tells 24 stacks they have none."""

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param("src/orders_test.go", id="go"),
            pytest.param("spec/models/user_spec.rb", id="ruby_spec_dir"),
            pytest.param("web/__tests__/app.js", id="js_tests_dir"),
            pytest.param("web/src/App.spec.ts", id="ts_spec_suffix"),
            pytest.param("web/src/App.test.tsx", id="ts_test_suffix"),
            pytest.param("tests/test_x.py", id="python"),
            pytest.param("backend/tests/conftest.py", id="python_not_named_test"),
        ],
    )
    def test_it_is_a_test(self, path):
        assert classify(path) == "test", path

    @pytest.mark.parametrize(
        "path,kind",
        [
            pytest.param("data/latest/rows.csv", "data", id="the_word_inside_another_word"),
            pytest.param("src/contest/engine.go", "code", id="contest_is_not_test"),
            pytest.param("docs/testing-guide.md", "doc", id="prose_about_testing"),
        ],
    )
    def test_it_is_not(self, path, kind):
        """The half that decides whether the classifier is usable: a substring
        match would call all three of these tests."""
        assert classify(path) == kind, path


class TestTheGraphCanBeFilledAndAsked:
    """AC5. Three tables at zero rows, a day after the substrate shipped."""

    @pytest.fixture
    def svc(self, tmp_path):
        s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
        yield s
        s.be.close()

    def test_build_fills_all_three_tables_in_a_consumer_project(self, svc, tmp_path):
        root = _consumer(_fresh(tmp_path, "c"))
        subprocess.run(["git", "init", "-q"], cwd=root, env=_GIT_ENV, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, env=_GIT_ENV, check=True)
        subprocess.run(["git", "commit", "-qm", "one"], cwd=root, env=_GIT_ENV, check=True)

        from project_cli_graph import _index_everything, index_symbols

        paths, roots, _source = _index_everything(svc, str(root))
        assert paths, f"nothing indexed under {roots}"

        counts = svc.be.graph_counts()
        assert counts["artifacts"] == len(paths)

        symbols = index_symbols(svc, str(root), paths)
        assert symbols["symbols"] > 0, "the consumer's own definitions produced no symbols"
        assert svc.be.graph_counts()["symbols"] == symbols["symbols"]

    def test_counts_report_absence_rather_than_zero_when_a_table_cannot_be_read(self, svc):
        """A table that cannot be read is not a table with nothing in it."""
        svc.be._conn.execute("DROP TABLE artifact_edges")
        assert svc.be.graph_counts()["edges"] == -1

    def test_clear_reports_what_it_destroyed(self, svc, tmp_path):
        root = _consumer(_fresh(tmp_path, "c"))
        from project_cli_graph import _index_everything

        paths, _roots, _source = _index_everything(svc, str(root))
        assert svc.be.graph_clear() == len(paths)
        assert svc.be.graph_counts()["artifacts"] == 0


class TestAnUnsupportedLanguageIsNamedNotSilent:
    """AC6. Decision #334: absence yields absence, never zero."""

    @pytest.fixture
    def svc(self, tmp_path):
        s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
        yield s
        s.be.close()

    def test_a_go_file_is_counted_as_having_no_extractor(self, svc, tmp_path):
        root = tmp_path / "proj"
        (root / "app").mkdir(parents=True)
        (root / "app" / "main.go").write_text("package main\n", encoding="utf-8")
        (root / "app" / "util.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

        from project_cli_graph import _index_everything, index_symbols

        paths, _roots, _source = _index_everything(svc, str(root))
        result = index_symbols(svc, str(root), paths)
        assert result["symbols"] >= 1, "the Python file should still yield symbols"
        assert result["no_extractor"] >= 1, (
            "the Go file must be counted as unreadable, not silently contribute zero — "
            "a Go project reading '0 symbols' would conclude its code has none"
        )


class TestTheConsumersAgentIsToldTheGraphExists:
    """AC8. A capability an agent is never told about is one measured, in this
    project's own transcripts, at 2 uses against 226 greps."""

    def _generated(self, tmp_path) -> str:
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_generate import generate_claude_md

        generate_claude_md(str(tmp_path), "proj", ["python"])
        return (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")

    def test_the_generated_rules_name_the_command(self, tmp_path):
        """The GENERATED file, not ours. A consumer never reads our CLAUDE.md."""
        assert "tausik graph" in self._generated(tmp_path)

    def test_it_was_paid_for_and_not_appended(self, tmp_path):
        """The file stood at exactly 180 of its 80-180 budget when `graph` was
        added, so a line had to be freed for it. This asserts the budget, which
        is the thing that would actually break."""
        lines = self._generated(tmp_path).splitlines()
        assert 80 <= len(lines) <= 180, f"{len(lines)} lines — the budget was spent, not paid"


class TestTheBuildStaysCheapEnoughToBeRun:
    """AC9. Measured at 2m27s before the commit boundary moved, 5-9s after.

    The threshold is deliberately loose: this asserts the ORDER OF MAGNITUDE,
    because the failure it guards against is a build so slow that people stop
    running it — at which point the framework ships an empty graph everywhere.
    """

    def test_a_small_project_builds_in_well_under_a_minute(self, tmp_path):
        import time

        root = _consumer(_fresh(tmp_path, "c"))
        subprocess.run(["git", "init", "-q"], cwd=root, env=_GIT_ENV, check=True)
        subprocess.run(["git", "add", "-A"], cwd=root, env=_GIT_ENV, check=True)
        subprocess.run(["git", "commit", "-qm", "one"], cwd=root, env=_GIT_ENV, check=True)

        svc = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
        try:
            from project_cli_graph import _index_everything, index_symbols

            started = time.perf_counter()
            with svc.be.transaction():
                paths, _roots, _source = _index_everything(svc, str(root))
                index_symbols(svc, str(root), paths)
                svc.graph_build_cochange(root=str(root))
                svc.graph_build_declared(root=str(root))
            elapsed = time.perf_counter() - started
        finally:
            svc.be.close()
        assert elapsed < 30.0, f"{elapsed:.1f}s for a handful of files — something is per-row"

    def test_the_build_runs_inside_one_transaction(self):
        """The 29x difference was ENTIRELY the commit boundary: WAL with
        synchronous=FULL fsyncs every autocommitted statement, and the build
        writes about 22,000 of them. Asserted on the source because a timing
        test on a fast machine would pass either way."""
        source = (_REPO / "scripts" / "project_cli_graph.py").read_text(encoding="utf-8")
        assert "with svc.be.transaction():" in source


class TestGraphShowReadsTheSymbolsItStores:
    """Found by the review sweep of session #235: `graph build` wrote 13,312
    symbol rows on this repository and `symbols_for_artifact` had no caller
    anywhere in the tree. Storing and never reading is the same defect as
    building and never invoking, one level down."""

    @pytest.fixture
    def svc(self, tmp_path):
        s = ProjectService(SQLiteBackend(str(tmp_path / "g.db")))
        yield s
        s.be.close()

    def _capture(self, svc, root: Path, rel: str) -> str:
        import io
        from contextlib import redirect_stdout

        from project_cli_graph import _print_symbols

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            _print_symbols(svc, rel)
        return buffer.getvalue()

    def _seed(self, svc, tmp_path) -> Path:
        from project_cli_graph import _index_everything, index_symbols

        root = tmp_path / "proj"
        (root / "app").mkdir(parents=True)
        (root / "app" / "orders.py").write_text(
            "def place_order(cart):\n    return cart\n\n\nclass OrderService:\n    pass\n",
            encoding="utf-8",
        )
        (root / "app" / "notes.md").write_text("# Notes\n\nprose only\n", encoding="utf-8")
        paths, _roots, _source = _index_everything(svc, str(root))
        index_symbols(svc, str(root), paths)
        return root

    def test_a_file_with_definitions_lists_them(self, svc, tmp_path):
        root = self._seed(svc, tmp_path)
        out = self._capture(svc, root, "app/orders.py")
        assert "defines:" in out
        assert "place_order" in out and "OrderService" in out

    def test_a_file_the_framework_cannot_parse_says_NOTHING(self, svc, tmp_path):
        """An empty heading would read as 'defines nothing', which is a
        different claim from 'we cannot read its definitions'."""
        root = self._seed(svc, tmp_path)
        assert self._capture(svc, root, "app/notes.md") == ""

    def test_an_unknown_path_says_nothing_rather_than_erroring(self, svc, tmp_path):
        root = self._seed(svc, tmp_path)
        assert self._capture(svc, root, "app/nowhere.py") == ""

    def test_the_listing_is_bounded_and_the_remainder_is_named(self, svc, tmp_path):
        """The same bound as `tausik symbol`, for the same reason: past it the
        answer stops being cheaper than opening the file."""
        from project_cli_graph import MAX_SYMBOLS_SHOWN, _index_everything, index_symbols

        root = tmp_path / "big"
        (root / "app").mkdir(parents=True)
        body = "\n\n".join(f"def f{n}():\n    return {n}" for n in range(MAX_SYMBOLS_SHOWN + 5))
        (root / "app" / "many.py").write_text(body + "\n", encoding="utf-8")
        paths, _roots, _source = _index_everything(svc, str(root))
        index_symbols(svc, str(root), paths)

        out = self._capture(svc, root, "app/many.py")
        assert "more)" in out, "the cut must be named, not silent"
        assert out.count(":") >= MAX_SYMBOLS_SHOWN
