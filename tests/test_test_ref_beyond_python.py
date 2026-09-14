"""GitLab #16: a test citation is read in the ecosystem's own form, not only `.py`.

`TEST_REF_RE` required `.py` in both of its branches, so a Rust project citing
`src-tauri/src/commands/project_extras_tests.rs::name` — a file that existed,
a test that was green — was refused on a `substantial` tier with "a path that
does not resolve", which was untrue twice: the path resolved, and the form was
what went unread. Three things changed and each has a test here: the detector
reads the declared forms; the resolver accepts a file NAMED as a test outside
a `tests/` root (Rust and Go keep tests beside code) and checks the `::name`
in that language's idiom; the refusal says which of the two things went wrong.
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ac_evidence_detectors import find_test_refs  # noqa: E402
from gate_ac_check import checklist_hard_block  # noqa: E402
from gate_test_citation import _test_ref_exists  # noqa: E402


def _refs(text: str) -> list[str]:
    return find_test_refs(text)


class TestTheDetectorReadsEcosystemForms:
    @pytest.mark.parametrize(
        "citation",
        [
            "src-tauri/src/commands/project_extras_tests.rs::a_project_copy_shadows_it",
            "pkg/foo_test.go::TestBar",
            "src/foo.test.ts",
            "src/__tests__/app.test.tsx",
            "src/test/FooTest.java::bar",
            "spec/foo_spec.rb",
            "app/Tests/FooTest.php::testBar",
            "tests/test_foo.py::TestX::test_y[case-3]",
        ],
    )
    def test_a_test_form_is_read_whole(self, citation):
        assert _refs(f"AC-2: ✓ {citation}") == [citation]

    @pytest.mark.parametrize("text", ["README.md::x", "scripts/foo.py", "docs/en/hooks.md"])
    def test_a_non_test_is_not_read_as_one(self, text):
        assert _refs(text) == []


class TestTheResolverAcceptsATestNamedAsOneBesideTheCode:
    """Negative boundary lives here too: the same citation with the file absent
    is refused, and a `::name` the file does not declare is refused."""

    @pytest.fixture
    def rust_project(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        monkeypatch.chdir(tmp_path)
        tests = tmp_path / "src-tauri" / "src" / "commands"
        tests.mkdir(parents=True)
        (tests / "project_extras_tests.rs").write_text(
            "#[test]\nfn a_project_copy_shadows_it() {\n    assert!(true);\n}\n",
            encoding="utf-8",
        )
        go = tmp_path / "pkg"
        go.mkdir()
        (go / "foo_test.go").write_text("func TestBar(t *testing.T) {}\n", encoding="utf-8")
        js = tmp_path / "src"
        js.mkdir()
        (js / "app.test.ts").write_text("it('renders the title', () => {});\n", encoding="utf-8")
        return tmp_path

    def test_rust_go_and_ts_citations_resolve(self, rust_project):
        root = str(rust_project)
        assert _test_ref_exists(
            "src-tauri/src/commands/project_extras_tests.rs::a_project_copy_shadows_it", root
        )
        assert _test_ref_exists("pkg/foo_test.go::TestBar", root)
        assert _test_ref_exists("src/app.test.ts::renders the title", root)

    def test_a_missing_file_or_an_undeclared_name_still_fails_closed(self, rust_project):
        root = str(rust_project)
        assert not _test_ref_exists("src-tauri/src/commands/other_tests.rs::anything", root)
        assert not _test_ref_exists(
            "src-tauri/src/commands/project_extras_tests.rs::invented_fn", root
        )

    def test_a_source_file_beside_the_test_is_not_a_test(self, rust_project):
        (rust_project / "src-tauri" / "src" / "commands" / "project_extras.rs").write_text(
            "fn real_code() {}\n", encoding="utf-8"
        )
        assert not _test_ref_exists(
            "src-tauri/src/commands/project_extras.rs::real_code", str(rust_project)
        )


class TestTheRefusalNamesTheRightCause:
    def _task(self, notes: str) -> dict:
        return {
            "tier": "substantial",
            "notes": notes,
            "relevant_files": "[]",
            "acceptance_criteria": "1. labels classified\n2. errors on unknown label",
        }

    @pytest.mark.parametrize(
        "citation,named,absent",
        [
            pytest.param(
                "src/commands/extras.rs::shadows",
                "FORM NOT RECOGNISED",
                "NOT RESOLVED",
                id="unrecognised-form",
            ),
            pytest.param(
                "pkg/missing_test.go::TestBar",
                "NOT RESOLVED",
                "FORM NOT RECOGNISED",
                id="recognised-but-missing",
            ),
        ],
    )
    def test_the_refusal_names_one_cause_and_not_the_other(
        self, tmp_path, monkeypatch, citation, named, absent
    ):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        monkeypatch.chdir(tmp_path)
        block, msg = checklist_hard_block(self._task(f"AC-1: ✓ {citation}"))
        assert block is True
        assert named in msg and citation in msg
        assert absent not in msg

    def test_a_rust_citation_that_exists_clears_the_substantial_gate(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        monkeypatch.chdir(tmp_path)
        d = tmp_path / "src-tauri" / "src" / "commands"
        d.mkdir(parents=True)
        (d / "project_extras_tests.rs").write_text("fn shadows_it() {}\n", encoding="utf-8")
        block, msg = checklist_hard_block(
            self._task("AC-1: ✓ src-tauri/src/commands/project_extras_tests.rs::shadows_it")
        )
        assert block is False and msg == ""


class TestTheTierNoteIsSilentOnAMeasuredClose:
    def test_a_verification_run_citation_does_not_draw_the_test_ref_note(self):
        from gate_ac_check import check_verification_checklist

        task = {
            "tier": "critical",
            "complexity": "complex",
            "notes": "AC-1: ✓ verification_run #338\nAC-2: ✓ verification_run #338 Negative: refused",
            "relevant_files": "[]",
            "acceptance_criteria": "1. it works\n2. it refuses bad input",
        }
        text = check_verification_checklist(task, verified_run_ids={338})
        assert "requires test-ref evidence" not in text, text


class TestTheWideningDoesNotCheapenACitation:
    """Review, session #254: the adversary writes its own notes. Each case here
    was a live false positive of the first cut and must stay refused."""

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))
        monkeypatch.chdir(tmp_path)
        return tmp_path

    def test_a_python_file_merely_suffixed_tests_is_not_a_test_form(self, project):
        (project / "scripts").mkdir()
        (project / "scripts" / "gate_ac_check_tests.py").write_text("x = 1\n", encoding="utf-8")
        assert not _test_ref_exists("scripts/gate_ac_check_tests.py", str(project))
        assert _refs("scripts/gate_ac_check_tests.py") == []

    def test_a_vendored_tests_directory_is_not_this_project_s(self, project):
        d = project / "node_modules" / "pkg" / "tests"
        d.mkdir(parents=True)
        (d / "evil_test.py").write_text("def test_x(): pass\n", encoding="utf-8")
        assert not _test_ref_exists("node_modules/pkg/tests/evil_test.py", str(project))

    def test_a_file_named_as_a_test_without_a_name_must_declare_a_test(self, project):
        d = project / "src"
        d.mkdir()
        (d / "helpers_tests.rs").write_text("pub fn helper() {}\n", encoding="utf-8")
        assert not _test_ref_exists("src/helpers_tests.rs", str(project))
        (d / "real_tests.rs").write_text("#[test]\nfn it_works() {}\n", encoding="utf-8")
        assert _test_ref_exists("src/real_tests.rs", str(project))

    def test_a_name_in_a_comment_or_a_stray_string_is_not_a_declaration(self, project):
        d = project / "src"
        d.mkdir()
        (d / "x_tests.rs").write_text(
            '// TODO fn shadows_it\nfn real_test() { log("shadows_it"); }\n', encoding="utf-8"
        )
        assert not _test_ref_exists("src/x_tests.rs::shadows_it", str(project))
        (d / "y.test.ts").write_text("it('renders', () => {});\n", encoding="utf-8")
        assert _test_ref_exists("src/y.test.ts::renders", str(project))
        assert not _test_ref_exists("src/y.test.ts::vanished", str(project))

    def test_a_pathological_notes_field_is_bounded(self):
        """40 KB of slash-heavy text took 42 s in the first cut; per-line scanning
        with a 2000-char cap keeps the gate answering in well under a second."""
        import time

        from gate_ac_check import checklist_hard_block

        notes = "deep/" * 8000 + "file.notarealext"
        t0 = time.perf_counter()
        block, _msg = checklist_hard_block(
            {
                "tier": "substantial",
                "notes": notes,
                "relevant_files": "[]",
                "acceptance_criteria": "1. x",
            }
        )
        assert block is True
        assert time.perf_counter() - t0 < 2.0

    def test_the_tier_note_stays_when_the_run_is_not_verified_for_this_task(self):
        from gate_ac_check import check_verification_checklist

        task = {
            "tier": "critical",
            "complexity": "complex",
            "notes": "AC-1: ✓ verification_run #999999\nAC-2: ✓ 9999 passed in 0.1s",
            "relevant_files": "[]",
            "acceptance_criteria": "1. it works\n2. it refuses bad input",
        }
        text = check_verification_checklist(task, verified_run_ids=set())
        assert "requires test-ref evidence" in text
