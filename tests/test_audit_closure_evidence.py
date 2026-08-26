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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_closure_evidence import (  # noqa: E402
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
        [{"slug": "detector-task", "notes": _note("tests/test_foo.py::test_bar")}],
        probe=_probe_saying(set()),
    )
    (finding,) = report["findings"]
    assert finding["verdict"] == NEVER_EXISTED
    assert finding["verdict"] != ROTTED


def test_the_two_causes_are_never_merged_into_one_count(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    report = audit_closure_evidence(
        str(root),
        [
            {"slug": "rotted-one", "notes": _note("tests/test_alpha.py::test_gone")},
            {"slug": "synthetic-one", "notes": _note("tests/test_foo.py::test_bar")},
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
