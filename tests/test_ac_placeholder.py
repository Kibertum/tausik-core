"""QG-0 measures the SUBSTANCE of goal and criteria, placeholders removed.

qg0-accepts-a-placeholder-as-an-acceptance-criterion: the gate used to check
that the fields were non-empty, so `$(cat /tmp/ac.txt)` — a criterion whose
shell never ran — closed a real task. These tests opt in to the real
thresholds with ``qg0_substance``; the conftest shim zeroes them otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import ac_placeholder
from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError

pytestmark = pytest.mark.qg0_substance

REAL_TERSE_AC = "1. README exists. 2. Error if file already exists."
VAGUE_RU_AC = "1. Работает корректно 2. Ошибка при пустом поле"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("<describe the check here>", id="angle-template"),
        pytest.param("[ACCEPTANCE_CRITERIA]", id="upper-bracket"),
        pytest.param("{{ criteria }}", id="mustache"),
        pytest.param("$(cat /tmp/ac.txt)", id="unexpanded-subshell"),
        pytest.param("${AC_TEXT}", id="unexpanded-variable"),
        pytest.param("TODO TBD FIXME placeholder", id="promise-words-en"),
        pytest.param("уточнить заглушка добавить позже", id="promise-words-ru"),
        pytest.param("| AC | Evidence |\n|---|---|", id="empty-table"),
        pytest.param("works as expected", id="vague-en"),
        pytest.param("работает корректно", id="vague-ru"),
    ],
)
def test_each_placeholder_family_carries_no_substance(text):
    assert ac_placeholder.substance(text) == 0


def test_a_table_with_data_keeps_its_rows():
    table = "| AC | Evidence |\n|---|---|\n| exit code is 2 | test_exit_code |"
    assert ac_placeholder.substance(table) >= 5


@pytest.mark.parametrize(
    "ac, refused",
    [
        pytest.param("$(cat /tmp/ac.txt)", True, id="the-live-leak"),
        pytest.param(VAGUE_RU_AC, True, id="vague-ru-template"),
        pytest.param("1. It works as expected. 2. Tests pass.", True, id="vague-en-template"),
        pytest.param(REAL_TERSE_AC, False, id="terse-real-en"),
        pytest.param(
            "1. Команда возвращает код 2 при пустом имени файла", False, id="terse-real-ru"
        ),
    ],
)
def test_refusal_separates_templates_from_terse_real_criteria(ac, refused):
    assert (ac_placeholder.refusal("Write README file", ac) is not None) is refused


def test_the_refusal_names_the_field_and_the_counts():
    msg = ac_placeholder.refusal("TODO", "$(cat /tmp/ac.txt)")
    assert msg is not None
    assert "the goal has 0 word(s)" in msg
    assert "acceptance criteria have 0 word(s)" in msg


def _seeded(tmp_path: Path, goal: str, ac: str) -> ProjectService:
    svc = ProjectService(SQLiteBackend(str(tmp_path / "tausik.db")))
    svc.session_start()
    svc.task_quick("t-qg0", "stub task")
    svc.be.task_update(
        "t-qg0",
        goal=goal,
        acceptance_criteria=ac,
        complexity="simple",
        rollback_plan="git revert",
        scope="x.py",
    )
    return svc


def test_task_start_refuses_a_placeholder_criterion(tmp_path):
    svc = _seeded(tmp_path, "Write README file", "$(cat /tmp/ac.txt)")
    try:
        with pytest.raises(ServiceError, match="QG-0 Context Gate: the acceptance criteria"):
            svc.task_start("t-qg0")
        assert svc.be.task_get("t-qg0")["status"] != "active"
    finally:
        svc.be.close()


def test_task_start_accepts_a_terse_real_criterion(tmp_path):
    svc = _seeded(tmp_path, "Write README file", REAL_TERSE_AC)
    try:
        svc.task_start("t-qg0")
        assert svc.be.task_get("t-qg0")["status"] == "active"
    finally:
        svc.be.close()


_TWO_AC = "1. Command exits with code 2 on a missing file\n2. The error message names the path"


@pytest.mark.parametrize(
    "notes, expected_type",
    [
        pytest.param(
            "AC-1: ✓ {{tests/test_x.py::test_y}}", "checkmark_only", id="templated-test-ref"
        ),
        pytest.param("AC-1: ✓ manual: TODO", "checkmark_only", id="manual-todo"),
        pytest.param("AC-1: ✓ вручную", "checkmark_only", id="bare-manual-ru"),
        pytest.param("AC-1: ✓ tests/test_x.py::test_y", "test_ref", id="real-test-ref"),
        pytest.param("AC-1: ✓ manual: ran init twice, second exits 2", "manual", id="real-manual"),
        pytest.param(
            "AC-1: ✓ вручную: запустил init дважды, второй вернул 2", "manual", id="real-manual-ru"
        ),
    ],
)
def test_evidence_is_read_with_placeholders_removed(notes, expected_type):
    from service_ac_evidence import build_report

    item = build_report(_TWO_AC, notes).items[0]
    assert [e.evidence_type for e in item.evidence] == [expected_type]
