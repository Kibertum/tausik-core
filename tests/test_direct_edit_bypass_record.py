"""A direct edit of a task artifact leaves a record (SENAR 1.4 §8.6(j)).

The standard does not forbid the edit — it is a REGULATED EXCEPTION, and the
legitimate cases stay open. What it requires is that the record carry the Gate
Bypass (3.13) fields, that metric 8 be computed FROM those records rather than
from self-report, and that the two nested frequencies never be added.

The two negatives are the ones that decide whether the mechanism survives
contact with use: the boundary (an exercise outside a task is not a bypass) and
the form-filled-without-looking (a record with no rationale).
"""

from __future__ import annotations

import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from gate_bypass_record import (  # noqa: E402
    BYPASS_FIELDS,
    COMPLETE,
    DIRECT_EDIT_VECTOR,
    INCOMPLETE,
    UNSTRUCTURED,
    BypassRecordRefused,
    build,
    completeness,
    decode,
    encode,
    missing_fields,
    split_nested,
)

CROSSCUTTING_SCOPE = ["scripts/gate_bypass_record.py", "scripts/hooks/"]

_FULL = {
    "rationale": "incident at 03:00, agent capacity unavailable",
    "risk_accepted": "the fix ships without a scoped verify",
    "remediation": "re-run verify on the task and re-close it in the morning",
    "approved_by": "owner",
}


class TestTheRecordCarriesWhatTheStandardRequires:
    """AC1/AC2: the existing Gate Bypass, with 3.13's four fields in it."""

    def test_all_four_fields_round_trip(self):
        assert decode(encode(_FULL)) == _FULL

    def test_a_full_record_is_complete(self):
        assert completeness(encode(_FULL)) == COMPLETE
        assert missing_fields(encode(_FULL)) == []

    def test_a_partial_record_names_what_is_missing(self):
        """AC6: incomplete is VISIBLE, not drowned."""
        details = encode({"rationale": "incident", "approved_by": "owner"})
        assert completeness(details) == INCOMPLETE
        assert missing_fields(details) == ["risk_accepted", "remediation"]

    def test_free_text_is_unstructured_not_incomplete(self):
        """Three states. Every row written before this existed is free text, and
        calling those incomplete would accuse history of a defect it predates."""
        assert completeness("locked db during commit") == UNSTRUCTURED
        assert completeness(None) == UNSTRUCTURED

    def test_the_field_list_is_the_standard_s_four(self):
        assert set(BYPASS_FIELDS) == {
            "rationale",
            "risk_accepted",
            "remediation",
            "approved_by",
        }


class TestTheBoundaryIsTheTaskArtifact:
    """AC5 NEGATIVE: both sides, because widening is how this gets switched off."""

    def test_work_on_a_task_is_a_bypass(self):
        assert build("some-task", **_FULL)

    def test_an_exercise_outside_a_task_is_not(self):
        with pytest.raises(BypassRecordRefused) as err:
            build(None, **_FULL)
        assert "no declared effect" in str(err.value)

    def test_an_empty_slug_is_not_a_task(self):
        with pytest.raises(BypassRecordRefused):
            build("   ", **_FULL)


class TestTheFormCannotBeFilledWithoutLooking:
    """AC6 NEGATIVE: a record with no reason is refused, not written as a stub."""

    def test_no_rationale_is_refused(self):
        with pytest.raises(BypassRecordRefused) as err:
            build("some-task", risk_accepted="x", remediation="y", approved_by="z")
        assert "rationale" in str(err.value)

    def test_the_refusal_names_the_legitimate_cases(self):
        """A refusal that only says no teaches nothing; the standard's own
        examples are what keep this from reading as a ban."""
        with pytest.raises(BypassRecordRefused) as err:
            build("some-task")
        message = str(err.value)
        assert "incident" in message and "does not run" in message

    def test_whitespace_is_not_a_rationale(self):
        with pytest.raises(BypassRecordRefused):
            build("some-task", rationale="   ")


class TestTheTwoFrequenciesAreNested:
    """AC4: §8.6(i) and metric 8 are nested and SHALL NOT be added."""

    def test_manual_interventions_are_a_subset_of_bypasses(self):
        summary = split_nested(
            {
                "total": 5,
                "by_action": {f"bypass_{DIRECT_EDIT_VECTOR}": 2, "bypass_skip_hooks": 3},
            }
        )
        assert summary["total"] == 5
        assert summary["manual_intervention"] == 2
        assert summary["other"] == 3
        assert summary["manual_intervention"] + summary["other"] == summary["total"], (
            "the parts must partition the total — if they summed to more, a "
            "reader adding them would double-count exactly as §8.6(i) warns"
        )

    def test_the_containment_is_declared_not_left_to_the_reader(self):
        assert split_nested({"total": 1, "by_action": {}})["nested"] is True

    def test_no_direct_edits_reports_zero_rather_than_omitting_the_line(self):
        """Absence rendered as absence is how a metric stops being falsifiable."""
        summary = split_nested({"total": 3, "by_action": {"bypass_skip_hooks": 3}})
        assert summary["manual_intervention"] == 0
        assert summary["other"] == 3


class TestTheMetricIsRenderedAsNested:
    """AC3/AC4 in the output a reader actually sees."""

    def test_the_line_says_of_which_and_forbids_adding(self):
        from render_metrics import _bypass_lines

        lines = _bypass_lines(
            {
                "total": 4,
                "manual_intervention": 1,
                "other": 3,
                "nested": True,
                "by_action": {f"bypass_{DIRECT_EDIT_VECTOR}": 1, "bypass_skip_hooks": 3},
            }
        )
        text = "\n".join(lines)
        assert "of which 1 manual intervention" in text
        assert "do not add" in text.lower()

    def test_a_clean_project_prints_nothing(self):
        from render_metrics import _bypass_lines

        assert _bypass_lines({"total": 0, "by_action": {}}) == []


class TestУдалениеДубликатаНеУнеслоМеханизм:
    """AC-2. Худший исход задачи об удалении мёртвого кода — унести с ним
    работающий механизм.

    `record_direct_edit` была ВТОРОЙ реализацией трёх строк: она звала `build()`
    и `emit_supervision_bypass()`, и её не вызывал никто — ни продуктовый код,
    ни тесты, ни MCP. Живой путь тот же самый и живёт в `project_cli_events.py`,
    который зовёт обе функции сам.

    Проверяется ЖИВОЙ путь целиком, а не отсутствие удалённого имени: отсутствие
    имени проверяется тривиально и ничего не говорит о том, работает ли запись.
    """

    def test_живой_путь_записывает_обход(self, tmp_path):
        sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))
        from hook_supervision import emit_supervision_bypass

        (tmp_path / ".tausik").mkdir()
        details = build(
            "my-task",
            actor="andrey",
            rationale="инцидент, агент недоступен",
            scope="один файл",
            approval="владелец",
        )
        emit_supervision_bypass(str(tmp_path), DIRECT_EDIT_VECTOR, "hook", details)

        written = [p for p in (tmp_path / ".tausik").rglob("*") if p.is_file()]
        assert written, (
            "живой путь ничего не записал — удаление дубликата унесло механизм, "
            "а не только лишнюю копию"
        )

    def test_удалённое_имя_действительно_исчезло(self):
        """Предпосылка, а не утверждение: без неё тест выше был бы зелен и до
        удаления, то есть не проверял бы ничего про эту задачу."""
        with open(
            os.path.join(_ROOT, "scripts", "gate_bypass_record.py"), encoding="utf-8"
        ) as fh:
            source = fh.read()
        assert "def record_direct_edit" not in source

    def test_вторая_копия_не_завелась_снова(self):
        with open(
            os.path.join(_ROOT, "scripts", "gate_bypass_record.py"), encoding="utf-8"
        ) as fh:
            source = fh.read()
        assert "emit_supervision_bypass" not in source, (
            "gate_bypass_record снова зовёт эмиттер сам — это и была вторая копия"
        )
