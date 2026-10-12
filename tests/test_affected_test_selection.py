"""Ordinary verify selects evidence-backed tests and fails open on uncertainty."""

from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import affected_test_selection as ats  # noqa: E402
import gate_command_runner as command_runner  # noqa: E402
import gate_test_source_edges as source_edges  # noqa: E402


def _write(root, rel, body=""):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_every_affected_test_carries_its_selection_evidence(tmp_path):
    _write(tmp_path, "scripts/alpha.py", "def alpha(): pass\n")
    _write(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write(tmp_path, "tests/test_importer.py", "import alpha\n\ndef test_it(): alpha.alpha()\n")
    _write(
        tmp_path,
        "tests/test_declared.py",
        'CROSSCUTTING_SCOPE = ["scripts/alpha.py"]\n\ndef test_declared(): pass\n',
    )

    plan = ats.select_affected_tests(["scripts/alpha.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert set(plan.test_files) == {
        "tests/test_alpha.py",
        "tests/test_importer.py",
        "tests/test_declared.py",
    }
    assert all(plan.reasons[test] for test in plan.test_files)
    assert plan.reasons["tests/test_alpha.py"] == ("basename:scripts/alpha.py",)
    assert "direct-import:alpha" in plan.reasons["tests/test_importer.py"]
    assert "direct-import:scripts/alpha.py" in plan.reasons["tests/test_importer.py"]
    assert "declared-scope:scripts/alpha.py" in plan.reasons["tests/test_declared.py"]


def test_changed_conftest_selects_only_its_fixture_subtree(tmp_path):
    _write(tmp_path, "tests/conftest.py", "import pytest\n")
    _write(tmp_path, "tests/test_root.py", "def test_root(): pass\n")
    _write(tmp_path, "tests/unit/conftest.py", "import pytest\n")
    _write(tmp_path, "tests/unit/test_unit.py", "def test_unit(): pass\n")
    _write(tmp_path, "tests/integration/test_other.py", "def test_other(): pass\n")

    plan = ats.select_affected_tests(["tests/unit/conftest.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert plan.test_files == ("tests/unit/test_unit.py",)
    assert plan.reasons["tests/unit/test_unit.py"] == ("fixture-scope:tests/unit/conftest.py",)


@pytest.mark.parametrize(
    "relevant",
    [
        ["scripts/covered.py", "scripts/orphan.py"],
        ["scripts/orphan.py", "scripts/covered.py"],
    ],
    ids=["covered-first", "orphan-first"],
)
def test_each_changed_python_source_needs_its_own_selection_edge(tmp_path, relevant):
    _write(tmp_path, "scripts/covered.py", "def covered(): pass\n")
    _write(tmp_path, "scripts/orphan.py", "def orphan(): pass\n")
    _write(tmp_path, "tests/test_covered.py", "def test_covered(): pass\n")
    _write(tmp_path, "tests/test_other.py", "def test_other(): pass\n")

    plan = ats.select_affected_tests(relevant, root=str(tmp_path))

    assert plan.mode == "full"
    assert plan.fallback_reason == (
        "Python source has no defensible test dependency mapping: scripts/orphan.py"
    )
    assert all(
        plan.reasons[test] == (f"fail-open:{plan.fallback_reason}",) for test in plan.test_files
    )


def test_changed_test_always_selects_declaration_validator(tmp_path):
    _write(tmp_path, "tests/test_new_guard.py", "def test_guard(): pass\n")
    _write(tmp_path, "tests/test_crosscutting_registry.py", "def test_registry(): pass\n")

    plan = ats.select_affected_tests(["tests/test_new_guard.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert plan.test_files == (
        "tests/test_new_guard.py",
        "tests/test_crosscutting_registry.py",
    )
    assert plan.reasons["tests/test_crosscutting_registry.py"] == (
        "declaration-validator:tests/test_new_guard.py",
    )


def test_nested_roots_keep_duplicate_basenames_as_distinct_tests(tmp_path):
    _write(
        tmp_path,
        ".tausik/config.json",
        json.dumps({"testing": {"roots": ["backend/tests", "frontend/tests"]}}),
    )
    _write(tmp_path, "src/alpha.py", "def alpha(): pass\n")
    _write(tmp_path, "backend/tests/test_alpha.py", "def test_backend(): pass\n")
    _write(tmp_path, "frontend/tests/test_alpha.py", "def test_frontend(): pass\n")

    plan = ats.select_affected_tests(["src/alpha.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert plan.test_files == (
        "backend/tests/test_alpha.py",
        "frontend/tests/test_alpha.py",
    )
    assert set(plan.reasons) == set(plan.test_files)


@pytest.mark.parametrize(
    ("test_body", "expected_mode"),
    [
        ("def test_it(): pass\n", "full"),
        ("import helpers\n\ndef test_it(): pass\n", "affected"),
    ],
    ids=["unmapped-test-helper-widens", "imported-test-helper-is-covered"],
)
def test_non_test_python_inside_test_root_still_needs_a_disposition(
    tmp_path, test_body, expected_mode
):
    _write(tmp_path, "tests/helpers.py", "def helper(): pass\n")
    _write(tmp_path, "tests/test_consumer.py", test_body)

    plan = ats.select_affected_tests(["tests/helpers.py"], root=str(tmp_path))

    assert plan.mode == expected_mode


def test_duplicate_source_basenames_need_unambiguous_edges(tmp_path):
    _write(tmp_path, "src/a/util.py", "VALUE = 'a'\n")
    _write(tmp_path, "src/b/util.py", "VALUE = 'b'\n")
    _write(
        tmp_path,
        "tests/test_util.py",
        "from src.a import util\n\ndef test_a(): assert util.VALUE == 'a'\n",
    )

    plan = ats.select_affected_tests(["src/a/util.py", "src/b/util.py"], root=str(tmp_path))

    assert plan.mode == "full"
    assert plan.fallback_reason == (
        "Python source has no defensible test dependency mapping: src/b/util.py"
    )

    sibling_only = ats.select_affected_tests(["src/b/util.py"], root=str(tmp_path))
    assert sibling_only.mode == "full"
    assert "src/b/util.py" in (sibling_only.fallback_reason or "")


def test_qualified_import_is_selected_even_without_a_basename_match(tmp_path):
    _write(tmp_path, "src/a/util.py", "VALUE = 'a'\n")
    _write(
        tmp_path,
        "tests/test_behavior.py",
        "from src.a import util\n\ndef test_behavior(): assert util.VALUE == 'a'\n",
    )

    plan = ats.select_affected_tests(["src/a/util.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert plan.test_files == ("tests/test_behavior.py",)
    assert "direct-import:src/a/util.py" in plan.reasons["tests/test_behavior.py"]


def test_deleted_duplicate_source_cannot_inherit_bare_import_edge(tmp_path):
    _write(tmp_path, "src/b/util.py", "VALUE = 'b'\n")
    _write(tmp_path, "tests/test_behavior.py", "import util\n\ndef test_it(): pass\n")

    edges = source_edges.source_test_edges_for_relevant(["src/a/util.py"], root=str(tmp_path))

    assert edges["src/a/util.py"] == {}


def test_shared_qualified_suffix_is_not_a_defensible_import_edge(tmp_path):
    _write(tmp_path, "src/a/util.py", "VALUE = 'src'\n")
    _write(tmp_path, "lib/a/util.py", "VALUE = 'lib'\n")
    _write(tmp_path, "tests/test_behavior.py", "import a.util\n\ndef test_it(): pass\n")

    edges = source_edges.source_test_edges_for_relevant(["src/a/util.py"], root=str(tmp_path))

    assert edges["src/a/util.py"] == {}


def test_test_named_production_module_is_not_a_test_target(tmp_path):
    _write(tmp_path, "scripts/test_helper.py", "def helper(): pass\n")
    _write(tmp_path, "tests/test_other.py", "def test_other(): pass\n")

    plan = ats.select_affected_tests(["scripts/test_helper.py"], root=str(tmp_path))

    assert plan.mode == "full"
    assert "scripts/test_helper.py" in (plan.fallback_reason or "")


@pytest.mark.parametrize("core_marker", [True, False], ids=["core-tree", "validator-deleted"])
def test_expected_declaration_validator_cannot_disappear(tmp_path, core_marker):
    _write(tmp_path, "tests/test_new_guard.py", "def test_guard(): pass\n")
    relevant = ["tests/test_new_guard.py"]
    if core_marker:
        _write(tmp_path, "scripts/affected_test_selection.py", "# core marker\n")
    else:
        relevant.append("tests/test_crosscutting_registry.py")

    plan = ats.select_affected_tests(relevant, root=str(tmp_path))

    assert plan.mode == "full"
    assert plan.fallback_reason == (
        "test declaration validator is missing: test_crosscutting_registry.py"
    )


@pytest.mark.parametrize(
    ("setup", "relevant", "reason_part"),
    [
        (
            lambda root: _write(root, ".tausik/config.json", "{broken"),
            ["scripts/alpha.py"],
            "config",
        ),
        (
            lambda root: _write(root, "tests/test_broken.py", "import alpha\ndef (:\n"),
            ["scripts/alpha.py"],
            "unparseable",
        ),
        (
            lambda root: _write(
                root,
                "tests/test_declared.py",
                "CROSSCUTTING_SCOPE = make_scope()\ndef test_x(): pass\n",
            ),
            ["scripts/alpha.py"],
            "literal path list",
        ),
        (
            lambda root: _write(root, "scripts/auth.py", "def authenticate(): pass\n"),
            ["scripts/auth.py"],
            "security-sensitive",
        ),
        (
            lambda root: _write(root, "scripts/orphan.py", "def orphan(): pass\n"),
            ["scripts/orphan.py"],
            "no defensible",
        ),
    ],
    ids=["invalid-config", "bad-test-source", "bad-declaration", "security", "unknown-source"],
)
def test_uncertainty_fails_open_to_every_applicable_test(tmp_path, setup, relevant, reason_part):
    _write(tmp_path, "scripts/alpha.py", "def alpha(): pass\n")
    _write(tmp_path, "tests/test_alpha.py", "def test_alpha(): pass\n")
    _write(tmp_path, "tests/test_other.py", "def test_other(): pass\n")
    setup(tmp_path)

    plan = ats.select_affected_tests(relevant, root=str(tmp_path))

    assert plan.mode == "full"
    assert set(plan.test_files) >= {"tests/test_alpha.py", "tests/test_other.py"}
    assert reason_part in (plan.fallback_reason or "")
    assert all(
        reason.startswith("fail-open:") for reasons in plan.reasons.values() for reason in reasons
    )


@pytest.mark.parametrize(
    ("changed", "test_rel"),
    [
        ("docs/note.md", "tests/test_other.py"),
        ("docs/mcp.md", "tests/test_mcp_transport.py"),
    ],
    ids=["unmapped-prose", "basename-collision"],
)
def test_non_python_basename_is_not_source_dependency_evidence(tmp_path, changed, test_rel):
    _write(tmp_path, changed, "prose\n")
    _write(tmp_path, test_rel, "def test_case(): pass\n")

    plan = ats.select_affected_tests([changed], root=str(tmp_path))

    assert plan.mode == "none"
    assert plan.test_files == ()


def test_missing_test_roots_cannot_pretend_a_full_lane_exists(tmp_path):
    _write(tmp_path, "scripts/alpha.py", "def alpha(): pass\n")

    plan = ats.select_affected_tests(["scripts/alpha.py"], root=str(tmp_path))

    assert plan.mode == "unavailable"
    assert "no applicable test root" in (plan.fallback_reason or "")


def test_explicit_root_level_test_is_still_an_applicable_lane(tmp_path):
    _write(tmp_path, "src/alpha.py", "def alpha(): pass\n")
    _write(tmp_path, "test_alpha.py", "def test_alpha(): assert True\n")

    plan = ats.select_affected_tests(["src/alpha.py", "test_alpha.py"], root=str(tmp_path))

    assert plan.mode == "affected"
    assert plan.test_files == ("test_alpha.py",)
    assert plan.reasons == {"test_alpha.py": ("changed-test:test_alpha.py",)}


def test_gate_reports_selection_unavailable_when_no_full_lane_exists(tmp_path, monkeypatch):
    _write(tmp_path, "scripts/alpha.py", "def alpha(): pass\n")
    monkeypatch.chdir(tmp_path)

    outcome = command_runner.run_command_gate(
        {"command": "pytest -q {test_files_for_files}"}, ["scripts/alpha.py"]
    )

    assert outcome.outcome == "COULD_NOT_RUN"
    assert outcome.reason_code == "test_selection_unavailable"


def test_full_fallback_runs_the_test_root_once_and_writes_complete_evidence(tmp_path, monkeypatch):
    _write(tmp_path, "scripts/orphan.py", "def orphan(): pass\n")
    _write(tmp_path, "tests/test_one.py", "def test_one(): pass\n")
    _write(tmp_path, "tests/test_two.py", "def test_two(): pass\n")
    monkeypatch.chdir(tmp_path)
    commands = []

    def run(command, _timeout):
        commands.append(command)
        return 0, "2 passed"

    monkeypatch.setattr(command_runner, "_run_shellless", run)
    outcome = command_runner.run_command_gate(
        {"command": "pytest -q {test_files_for_files}"}, ["scripts/orphan.py"]
    )

    assert outcome.outcome == "PASSED"
    assert commands == ["pytest -q tests"]
    label, _body = command_runner.split_scope(outcome.detail)
    assert "fail-open complete applicable lane over 2 test file(s)" in label
    evidence_rel = label.split("selection evidence: ", 1)[1]
    payload = json.loads((tmp_path / evidence_rel).read_text(encoding="utf-8"))
    assert payload["mode"] == "full"
    assert {row["test"] for row in payload["selected"]} == {
        "tests/test_one.py",
        "tests/test_two.py",
    }
