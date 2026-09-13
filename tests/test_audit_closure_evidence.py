"""Tests for `scripts/audit_closure_evidence.py`.

Task: closure-evidence-references-rot-and-nothing-notices.

  AC-2 — the extractor is the PRODUCT'S. The audit must not carry a private
    regex for `path::name`; it reads citations through
    `service_ac_evidence.parse_evidence_lines`, the same code the closure gate
    reads them with.
  AC-3 — path resolution is a named policy: a bare file name is looked up
    across the test tree, and two hits are reported ambiguous, not silently
    resolved to the first.
  AC-4 — three distinguishable outcomes plus a successor CANDIDATE.
  AC-5 — a citation whose target was never in git history is NEVER_EXISTED,
    not rot, and the distinction is drawn by history rather than by a list of
    exempt task slugs.
  AC-7 — the audit blocks nothing.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_closure_evidence import (
    ILLUSTRATIVE,  # noqa: E402
    NEVER_EXISTED,
    RESOLVED,
    ROTTED,
    UNKNOWN_HISTORY,
    audit_closure_evidence,
    extract_refs,
    index_test_files,
    resolve_path,
)

REPO = Path(__file__).resolve().parents[1]
AUDIT_SRC = REPO / "scripts" / "audit_closure_evidence.py"


def _tree(tmp_path: Path) -> Path:
    """A repo-shaped tmp dir with one real test module."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_alpha.py").write_text(
        "class TestGroup:\n"
        "    def test_kept(self):\n"
        "        pass\n"
        "\n"
        "def test_renamed_to_this(self=None):\n"
        "    pass\n",
        encoding="utf-8",
    )
    return tmp_path


def _note(text: str) -> str:
    """A closure-receipt line in the shape task_log writes it."""
    return f"- 2026-01-01T00:00:00Z [done] — AC-1: ✓ {text}"


# --- AC-2: one extractor, and it is the product's -------------------------


def test_the_audit_carries_no_private_citation_regex() -> None:
    """A second extractor would make the audit and the closure gate disagree.

    Guarded structurally rather than by reading the text: any `re.compile`
    in this module would be a private parser of the very thing
    `service_ac_evidence` already parses (convention #301).
    """
    tree = ast.parse(AUDIT_SRC.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compile"
    ]
    assert calls == [], "audit must reuse the product extractor, not compile its own regex"
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "re" not in imported, "the regex module has no business here"


def test_citations_come_from_the_same_parser_the_gate_uses() -> None:
    from service_ac_evidence import parse_evidence_lines

    notes = _note("tests/test_alpha.py::test_kept and also bare test_beta.py")
    expected = [ref for line in parse_evidence_lines(notes) for ref in line.test_refs]
    assert extract_refs(notes) == expected
    assert expected, "fixture must actually produce citations, else the test proves nothing"


# --- AC-3: resolution policy ---------------------------------------------


def test_a_bare_file_name_resolves_through_the_test_tree(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    index = index_test_files(str(root))
    path, ambiguous = resolve_path(str(root), "test_alpha.py", index)
    assert path == "tests/test_alpha.py"
    assert ambiguous is False


def test_two_files_of_the_same_name_are_reported_ambiguous(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    nested = root / "tests" / "unit"
    nested.mkdir()
    (nested / "test_alpha.py").write_text("def test_kept():\n    pass\n", encoding="utf-8")
    index = index_test_files(str(root))
    path, ambiguous = resolve_path(str(root), "test_alpha.py", index)
    assert ambiguous is True, "which of the two the closure meant is not the audit's to decide"
    assert path in ("tests/test_alpha.py", "tests/unit/test_alpha.py")


def test_a_citation_with_a_directory_is_taken_literally(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    index = index_test_files(str(root))
    path, _ = resolve_path(str(root), "tests/test_alpha.py", index)
    assert path == "tests/test_alpha.py"


# --- AC-4 / AC-5: the three outcomes, told apart by history ---------------


def _probe_saying(known: set[str]):
    """A git stand-in: `known` holds the targets history did contain."""

    def probe(repo_root: str, rel: str, name: str | None) -> bool:
        return (f"{rel}::{name}" if name else rel) in known

    return probe


def test_a_live_citation_produces_no_finding(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_alpha.py::test_kept")}],
        probe=_probe_saying(set()),
    )
    assert report["findings"] == []
    assert report["resolved_unique"] == 1


def test_a_name_that_history_once_held_is_rot_with_a_candidate(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_alpha.py::test_renamed_from_that")}],
        probe=_probe_saying({"tests/test_alpha.py::test_renamed_from_that"}),
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == ROTTED
    assert finding["successor_candidate"] == "test_renamed_to_this"
    assert finding["tasks"] == ["t"]


def test_a_target_history_never_held_is_not_called_rot(tmp_path: Path) -> None:
    """AC-5 without an exemption list: a path that never existed cannot have rotted."""
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "detector-task", "notes": _note("tests/test_invented.py::test_never_written")}],
        probe=_probe_saying(set()),
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == NEVER_EXISTED
    assert finding["verdict"] != ROTTED
    # The fixture deliberately avoids `tests/test_foo.py::test_bar`, which this
    # test used to carry: that name is now read as an EXAMPLE, and a fixture
    # that lands in the illustrative bucket would silently stop exercising the
    # never-existed branch while still passing on the first assertion.
    assert finding["verdict"] != ILLUSTRATIVE


def test_the_two_causes_are_never_merged_into_one_count(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [
            {"slug": "rotted-one", "notes": _note("tests/test_alpha.py::test_gone")},
            {"slug": "synthetic-one", "notes": _note("tests/test_invented.py::test_never_written")},
        ],
        probe=_probe_saying({"tests/test_alpha.py::test_gone"}),
    )
    assert report["counts"][ROTTED] == 1
    assert report["counts"][NEVER_EXISTED] == 1
    assert "broken" not in report, "a single broken count would hide two different causes"


def test_without_history_the_verdict_is_withheld_rather_than_guessed(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_alpha.py::test_gone")}],
        probe=None,
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == UNKNOWN_HISTORY


def test_a_probe_that_cannot_answer_is_not_read_as_never_existed(tmp_path: Path) -> None:
    """git failing is not evidence of absence — the crash-as-silence class."""
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_alpha.py::test_gone")}],
        probe=lambda *_a: None,
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == UNKNOWN_HISTORY


def test_the_same_citation_from_two_tasks_is_one_finding(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    notes = _note("tests/test_alpha.py::test_gone")
    report = audit_closure_evidence(
        str(root),
        [{"slug": "a", "notes": notes}, {"slug": "b", "notes": notes}],
        probe=_probe_saying({"tests/test_alpha.py::test_gone"}),
    )
    (finding,) = report["findings"]
    assert finding["tasks"] == ["a", "b"]
    assert report["refs_total"] == 2
    assert report["refs_unique"] == 1


def test_an_unreadable_module_is_not_accused(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "tests" / "test_broken.py").write_text("def (:\n", encoding="utf-8")
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_broken.py::test_whatever")}],
        probe=_probe_saying(set()),
    )
    assert report["findings"] == [], "a syntax error in the target is not evidence of rot"


# --- AC-7: it blocks nothing ---------------------------------------------


def test_the_cli_exits_zero_with_findings_present() -> None:
    """The audit reports; it never fails a run. Renaming a test stays legal."""
    proc = subprocess.run(
        [sys.executable, "-c", CLI_SNIPPET],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Closure-evidence audit" in proc.stdout
    assert "never blocks" in proc.stdout


CLI_SNIPPET = (
    "import sys, types;"
    "sys.path.insert(0, 'scripts');"
    "from project_cli_audit import cmd_audit_evidence;"
    "from audit_closure_evidence import RESOLVED;"
    "svc = types.SimpleNamespace(task_list=lambda **k: ["
    "  {'slug': 'x', 'notes': '- [t] AC-1: \\u2713 tests/test_foo.py::test_bar'}"
    "]);"
    "cmd_audit_evidence(svc, types.SimpleNamespace(as_json=False, no_git=True))"
)


def test_the_report_labels_a_successor_as_a_candidate(tmp_path: Path) -> None:
    """AC-4: name similarity suggests, it does not rule."""
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_alpha.py::test_renamed_from_that")}],
        probe=_probe_saying({"tests/test_alpha.py::test_renamed_from_that"}),
    )
    assert report["findings"][0]["successor_candidate"] == "test_renamed_to_this"
    assert RESOLVED not in {f["verdict"] for f in report["findings"]}


def test_git_output_in_the_projects_own_language_does_not_crash_the_probe() -> None:
    """The console code page is not a text decoder.

    `git log -S` over THIS repo emits Cyrillic commit subjects. With
    subprocess defaults on Windows the reader thread raised
    UnicodeDecodeError and the module reported "cannot tell" — a crash wearing
    the costume of an honest unknown. Measured in session #186; five citations
    were mislabelled UNKNOWN_HISTORY before the fix.
    """
    from audit_closure_evidence import git_ever_had_name

    answer = git_ever_had_name(str(REPO), "CHANGELOG.ru.md", "TAUSIK")
    assert answer is not None, "git answered, so the audit must not report 'cannot tell'"


# --- an example quoted is not a citation invented -------------------------
# Session #209. Before the split the headline said 25 refs "never existed";
# 13 were conventional examples quoted by tasks whose SUBJECT is the citation
# format, and 3 were genuine. Both ends are pinned here, because a bucket that
# only ever grows is a detector being switched off one name at a time.


def test_an_example_name_gets_its_own_verdict(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "detector-task", "notes": _note("tests/test_does_not_exist.py")}],
        probe=_probe_saying(set()),
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == ILLUSTRATIVE
    assert finding["verdict"] != NEVER_EXISTED
    assert finding["illustrative_reason"]


def test_a_genuine_miss_is_not_moved_into_the_example_bucket(tmp_path: Path) -> None:
    """The negative end, on a ref the live corpus proved genuine: it names a
    real successor and must keep asking to be reconciled."""
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_ble001_enforced.py::test_ble001_selected")}],
        probe=_probe_saying(set()),
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == NEVER_EXISTED


def test_a_resolving_path_is_never_called_an_example(tmp_path: Path) -> None:
    """A real file at a real path is a citation whatever it is named — the
    example rules are only ever asked about a ref that failed to resolve."""
    root = _tree(tmp_path)
    (root / "tests" / "test_foo.py").write_text("def test_bar():\n    pass\n", encoding="utf-8")
    report = audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/test_foo.py::test_bar")}],
        probe=_probe_saying(set()),
    )
    assert report["findings"] == []
    assert report["resolved_unique"] == 1


def test_the_example_count_is_published_not_folded_away(tmp_path: Path) -> None:
    """A number that silently drops entries is the next version of the same
    problem, so the bucket is counted alongside the other three."""
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [
            {"slug": "rotted-one", "notes": _note("tests/test_alpha.py::test_gone")},
            {"slug": "example-one", "notes": _note("tests/foo.py")},
        ],
        probe=_probe_saying({"tests/test_alpha.py::test_gone"}),
    )
    assert report["counts"][ILLUSTRATIVE] == 1
    assert report["counts"][ROTTED] == 1
    assert report["counts"][NEVER_EXISTED] == 0
    assert sum(report["counts"].values()) == len(report["findings"])


def test_an_example_costs_no_git_call(tmp_path: Path) -> None:
    """Asked before history: an example has none to look up, and the sweep runs
    one `git log -S` per unresolved ref."""
    root = _tree(tmp_path)
    asked: list[str] = []

    def _probe(_root, path, member):
        asked.append(path)
        return False

    audit_closure_evidence(
        str(root),
        [{"slug": "t", "notes": _note("tests/foo.py")}],
        probe=_probe,
    )
    assert asked == []


# --- session #257: a node id is a CHAIN, not one name --------------------------


class TestANodeIdIsAChainOfNames:
    """`file::Class::method[param]` — the form the extractor reads whole since GitLab #16.

    Measured before the fix (session #257): `tausik coherence` reported 908
    citations as never having existed against a declared remainder of 39; 872
    were `Class::method`, 10 were `[param]` — all committed tests, looked up as
    one name `Class::method` that no module defines.
    """

    def test_class_and_method_both_defined_resolves(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note("tests/test_alpha.py::TestGroup::test_kept")}],
            probe=_probe_saying(set()),
        )
        assert report["findings"] == [], report["findings"]
        assert report["resolved_unique"] == 1

    def test_a_parametrised_id_is_the_method_it_names(self, tmp_path: Path) -> None:
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note("tests/test_alpha.py::TestGroup::test_kept[en]")}],
            probe=_probe_saying(set()),
        )
        assert report["findings"] == [], report["findings"]

    def test_an_id_carrying_its_own_double_colon_is_cut_at_the_bracket(self) -> None:
        from audit_closure_evidence import member_segments

        assert member_segments("TestGroup::test_kept[tests/a.py::b-1]") == [
            "TestGroup",
            "test_kept",
        ]
        assert member_segments("test_kept[en]") == ["test_kept"]
        assert member_segments("TestGroup::test_kept") == ["TestGroup", "test_kept"]

    @pytest.mark.parametrize(
        "chain,successor",
        [
            ("TestGroup::test_kep", "test_kept"),  # an invented leaf under a real class
            ("TestNope::test_kept", "TestGroup"),  # a real leaf under a class the file never had
        ],
        ids=["invented-leaf", "invented-class"],
    )
    def test_one_invented_link_is_never_existed_with_its_successor(
        self, tmp_path: Path, chain: str, successor: str
    ) -> None:
        """NEGATIVE: resolving the chain resolves neither an invented leaf nor an invented class."""
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note(f"tests/test_alpha.py::{chain}")}],
            probe=_probe_saying(set()),
        )
        (finding,) = report["findings"]
        assert finding["verdict"] == NEVER_EXISTED
        assert finding["successor_candidate"] == successor

    def test_the_old_single_name_lookup_is_what_produced_the_908(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The finding, reproduced on the auditor itself: with the tail read as ONE
        name — what `_classify` did before — a committed `Class::method` is
        reported never to have existed. Same input, same probe, other segmenter."""
        import audit_closure_evidence as ace

        root = _tree(tmp_path)
        cite = [{"slug": "t", "notes": _note("tests/test_alpha.py::TestGroup::test_kept")}]
        monkeypatch.setattr(ace, "member_segments", lambda member: [member])
        (finding,) = ace.audit_closure_evidence(str(root), cite, probe=_probe_saying(set()))[
            "findings"
        ]
        assert finding["verdict"] == NEVER_EXISTED
        monkeypatch.undo()
        assert (
            ace.audit_closure_evidence(str(root), cite, probe=_probe_saying(set()))["findings"]
            == []
        )

    def test_a_method_defined_elsewhere_than_under_the_named_class_is_not_resolved(
        self, tmp_path: Path
    ) -> None:
        """NEGATIVE (review, session #257): `TestGroup::test_renamed_to_this` — the
        leaf exists at module level, the chain does not. A flat set resolved it."""
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note("tests/test_alpha.py::TestGroup::test_renamed_to_this")}],
            probe=_probe_saying({"tests/test_alpha.py::test_renamed_to_this"}),
        )
        (finding,) = report["findings"]
        assert finding["verdict"] == ROTTED
        assert finding["missing_segments"] == ["test_renamed_to_this"]

    def test_an_invented_leaf_under_a_renamed_class_is_never_existed_not_rot(
        self, tmp_path: Path
    ) -> None:
        """NEGATIVE (review, session #257): the WORST answer is the verdict — a
        class git once held does not excuse a method git never held."""
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note("tests/test_alpha.py::TestOldGroup::test_invented")}],
            probe=_probe_saying({"tests/test_alpha.py::TestOldGroup"}),
        )
        (finding,) = report["findings"]
        assert finding["verdict"] == NEVER_EXISTED
        assert finding["missing_segments"] == ["TestOldGroup", "test_invented"]

    def test_a_bare_name_keeps_the_flat_lookup(self, tmp_path: Path) -> None:
        """`file::test_kept` for a method inside a class — honest shorthand, accepted before."""
        root = _tree(tmp_path)
        report = audit_closure_evidence(
            str(root),
            [{"slug": "t", "notes": _note("tests/test_alpha.py::test_kept")}],
            probe=_probe_saying(set()),
        )
        assert report["findings"] == []

    def test_a_nested_class_chain_is_followed_link_by_link(self, tmp_path: Path) -> None:
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_nested.py").write_text(
            "class TestOuter:\n"
            "    class TestInner:\n"
            "        def test_leaf(self):\n"
            "            pass\n",
            encoding="utf-8",
        )
        ok = audit_closure_evidence(
            str(tmp_path),
            [
                {
                    "slug": "t",
                    "notes": _note("tests/test_nested.py::TestOuter::TestInner::test_leaf"),
                }
            ],
            probe=_probe_saying(set()),
        )
        assert ok["findings"] == []
        skipped_link = audit_closure_evidence(
            str(tmp_path),
            [{"slug": "t", "notes": _note("tests/test_nested.py::TestOuter::test_leaf")}],
            probe=_probe_saying(set()),
        )
        (finding,) = skipped_link["findings"]
        assert finding["missing_segments"] == ["test_leaf"]

    def test_a_member_that_reduces_to_no_segment_is_not_vacuously_resolved(
        self, tmp_path: Path
    ) -> None:
        """The extractor never yields `file::[en]`; if it did, an empty chain must
        not read as verified — the raw member is asked of git instead."""
        import audit_closure_evidence as ace

        root = _tree(tmp_path)
        assert ace.member_segments("[en]") == []
        finding = ace._classify(
            str(root),
            "tests/test_alpha.py::[en]",
            ace.index_test_files(str(root)),
            {},
            _probe_saying(set()),
        )
        assert finding["verdict"] == NEVER_EXISTED
        assert finding["missing_segments"] == ["[en]"]
