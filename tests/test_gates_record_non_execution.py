"""Гейт, не сумевший исполниться, записывается как НЕ ИСПОЛНИВШИЙСЯ.

three-more-gates-sign-non-execution-as-a-pass. Продолжение
claudemd-state-gate-reports-passed-when-it-could-not-run: тот дефект чинился в
одном файле, а приём был общий для слоя. Здесь закреплены остальные три гейта —
bootstrap_drift и state_roundtrip (severity=block) и renar_drift (severity=warn).

ПОЧЕМУ УТВЕРЖДЕНИЕ ДЕЛАЕТСЯ НА СТРОКЕ gate_runs, А НЕ НА ВОЗВРАТЕ ФУНКЦИИ.
Дефект был не в том, что функция вернула не то, а в том, что БЫЛО ПОДПИСАНО:
квитанция сессии #192 несла {"outcome": "PASSED", "passed": true} для гейта,
чей собственный текст говорил «check unavailable». Поэтому каждый тест здесь
доводит исход до строки, которую пишет `record_gate_runs`, через настоящий
`run_gates` над настоящей записью реестра. Юнит-проверка возврата не поймала бы
подмену на пути между ними.

ЭТОТ ФАЙЛ ВИДИМ ДЛЯ SCOPED-ВЫБОРКИ ПО ИМПОРТУ: он импортирует все три модуля
гейтов, поэтому изменение любого из них выбирает этот тест. CROSSCUTTING_SCOPE
здесь не нужен — ребро есть (в отличие от tests/test_claudemd_audit_hook.py,
где охраняемый файл гоняется подпроцессом; см. решение #282).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gate_bootstrap_drift  # noqa: E402,F401 — импорт даёт ребро выборки
import gate_outcome  # noqa: E402
import gate_renar_drift  # noqa: E402,F401
import gate_state_roundtrip  # noqa: E402,F401
import project_config  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from gate_run_record import record_gate_runs  # noqa: E402

# Связано на ИМПОРТЕ, до того как autouse-фикстура _mock_run_gates из conftest
# подменит атрибут модуля заглушкой (True, []). Тот же приём, что в
# test_gate_registry.py и test_claudemd_state_gate.py: вызов
# `gate_runner.run_gates` из тела теста мерил бы мок.
from gate_runner import run_gates  # noqa: E402

# Гейт -> (триггер, модуль, имя функции, которую ломаем).
# Ломается ВНУТРЕННОСТЬ гейта, а не сам гейт: так воспроизводится настоящая
# авария окружения (устаревший процесс, битый импорт, недоступная БД), ради
# которой существует COULD_NOT_RUN, а не искусственный raise на входе.
CASES = [
    ("bootstrap_drift", "task-done", "gate_bootstrap_drift", "_harness_drift_names"),
    ("state_roundtrip", "commit", "state_serialize", "check_tree"),
    ("renar_drift_schema", "task-done", "project_config", "get_db_path"),
]


@pytest.fixture(autouse=True)
def _project_the_state_gate_can_reach(tmp_path, monkeypatch):
    """Дать state_roundtrip проект, в котором он ДОХОДИТ до своего детектора.

    Гейт отвечает NOT_APPLICABLE / no_database раньше, чем зовёт `check_tree`, и
    отвечает верно: свежий клон не виноват, что он свежий. Но тесты ниже ломают
    ИМЕННО `check_tree`, чтобы доказать, что раннер записывает непрохождение, — а
    в выгрузке без базы исполнение до него не доходило, и шесть тестов краснели
    (four-tests-fail-in-a-bare-checkout). В полном прогоне они то падали, то нет:
    какой-то тест ленты создаёт базу в корне по ходу, так что ответ зависел от
    ПОРЯДКА — ровно та монета, которую #203 называл хуже выключенного контроля.

    База синтетическая, а не живая, и это отдельная ценность: канонический
    `init_schema` из git вместо остаточного состояния машины, на которой
    запущено (тот же довод, что у `canonical_schema_db`).
    """
    from conftest import canonical_schema_db_file

    root = tmp_path / "project"
    (root / ".tausik").mkdir(parents=True)
    (root / "tausik").mkdir()
    canonical_schema_db_file(root / ".tausik" / "tausik.db")
    monkeypatch.setattr(project_config, "find_tausik_dir", lambda *a, **k: str(root / ".tausik"))


def _spec(name: str, trigger: str) -> dict:
    for g in project_config.get_gates_for_trigger(trigger, project_config.load_config()):
        if g.get("name") == name:
            return g
    pytest.fail(f"гейт {name!r} не подключён к триггеру {trigger!r}")


def _row_for(name: str, trigger: str, module: str, attr: str, monkeypatch) -> dict:
    """Уронить внутренность гейта и вернуть результат настоящего run_gates."""

    def _boom(*a, **k):
        raise RuntimeError("environment fault")

    monkeypatch.setattr(f"{module}.{attr}", _boom)
    spec = _spec(name, trigger)
    monkeypatch.setattr("gate_runner.get_gates_for_trigger", lambda t, c=None: [spec])
    _all_passed, results = run_gates(trigger, [])
    assert len(results) == 1, results
    return results[0]


@pytest.mark.parametrize(("name", "trigger", "module", "attr"), CASES)
class TestNonExecutionIsNotAPass:
    def test_the_row_says_could_not_run(self, name, trigger, module, attr, monkeypatch):
        row = _row_for(name, trigger, module, attr, monkeypatch)
        assert row["outcome"] == gate_outcome.COULD_NOT_RUN, (
            f"{name}: сбой окружения записан как {row['outcome']}, "
            "то есть проверка, не исполнившаяся ни на строку, засчитана"
        )
        assert row["reason_code"] == gate_outcome.REASON_RUNNER_ERROR
        assert row["passed"] is False
        assert row["skipped"] is False, (
            "CANNOT-RUN — не SKIP: весь дефект в том, что не сумевшая исполниться "
            "проверка читалась как та, которой нечего было делать"
        )

    def test_the_reader_is_told_what_to_do(self, name, trigger, module, attr, monkeypatch):
        row = _row_for(name, trigger, module, attr, monkeypatch)
        assert "unavailable" in row["output"] or "no detector" in row["output"]
        assert "certifies nothing" in row["output"], (
            "отказ без следующего действия — тупик #182 под новым именем"
        )

    def test_it_reaches_the_table_a_receipt_is_read_from(
        self, name, trigger, module, attr, monkeypatch, tmp_path
    ):
        row = _row_for(name, trigger, module, attr, monkeypatch)
        conn = sqlite3.connect(":memory:")
        conn.executescript(GATE_RUNS_SQL)  # настоящий DDL, не перепечатанный
        record_gate_runs(
            conn,
            verification_run_id=None,
            task_slug="ac5",
            trigger=trigger,
            gate_results=[row],
        )
        stored = conn.execute(
            "SELECT gate_name, outcome, reason_code, passed, skipped FROM gate_runs"
        ).fetchone()
        conn.close()
        assert stored == (
            name,
            gate_outcome.COULD_NOT_RUN,
            gate_outcome.REASON_RUNNER_ERROR,
            0,
            0,
        ), "до этой задачи та же авария давала ('PASSED', '', 1, 0)"


class TestSeverityDecidesTheCost:
    """AC2: warn-гейт говорит CANNOT-RUN и при этом НИЧЕГО не блокирует.

    Это и есть довод, по которому renar_drift приведён к общему виду, а не
    оставлен fail-open: gate_runner:254 поднимает блокирующий отказ только когда
    `outcome.blocks AND severity == "block"`. Для warn-гейта правдивая квитанция
    достаётся даром — а PASSED поставил бы ложную зелёную отметку ровно там, где
    читатель проверяет, искали ли дрейф вообще.
    """

    def test_a_warn_gate_that_cannot_run_does_not_block(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("environment fault")

        monkeypatch.setattr("project_config.get_db_path", _boom)
        spec = _spec("renar_drift_schema", "task-done")
        assert spec["severity"] == "warn"
        monkeypatch.setattr("gate_runner.get_gates_for_trigger", lambda t, c=None: [spec])
        all_passed, results = run_gates("task-done", [])
        assert results[0]["outcome"] == gate_outcome.COULD_NOT_RUN
        assert all_passed, "warn не блокирует — цена правдивой записи здесь нулевая"

    def test_a_block_gate_that_cannot_run_does_block(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("environment fault")

        monkeypatch.setattr("state_serialize.check_tree", _boom)
        spec = _spec("state_roundtrip", "commit")
        assert spec["severity"] == "block"
        monkeypatch.setattr("gate_runner.get_gates_for_trigger", lambda t, c=None: [spec])
        all_passed, results = run_gates("commit", [])
        assert results[0]["outcome"] == gate_outcome.COULD_NOT_RUN
        assert not all_passed, (
            "SENAR 1.4 §8.6(e): отсутствие отрицательной находки не есть "
            "положительный вердикт — сертифицировать нечем"
        )


class TestTheHonestSkipsStayPasses:
    """AC3: «нечего судить» осталось проходом и осталось различимым.

    Пустой клон не виноват, что он пуст. Один общий код на разные пустые
    состояния перенёс бы неразличимость, а не снял её, — поэтому проверяется и
    то, что коды РАЗНЫЕ.
    """

    def test_no_source_dir_is_not_applicable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "project_config.find_tausik_dir", lambda *a, **k: str(tmp_path / ".tausik")
        )
        (tmp_path / ".tausik").mkdir()
        outcome = gate_bootstrap_drift.run_bootstrap_drift_gate()
        assert outcome.outcome == gate_outcome.NOT_APPLICABLE
        assert outcome.reason_code == gate_outcome.REASON_NO_SOURCE_DIR
        assert not outcome.blocks
        assert outcome.legacy_passed

    def test_the_empty_state_codes_are_distinct(self):
        codes = [
            gate_outcome.REASON_NO_SOURCE_DIR,
            gate_outcome.REASON_NO_PROJECTION,
            gate_outcome.REASON_NO_DATABASE,
        ]
        assert len(set(codes)) == 3
        assert gate_outcome.REASON_RUNNER_ERROR not in codes


class TestBothNonExecutionSitesAreCovered:
    """AC6 требует, чтобы КАЖДОЕ исправленное место краснело по отдельности.

    У state_roundtrip их два, и они лежат по разные стороны от `be = None`:
    первый охватывает поиск проекта и пробы путей, второй — саму сверку.
    Мутация «на файл» подписала бы одно место красным от другого (конвенция
    #449), поэтому у каждого свой тест.

    Ломается `os` ВНУТРИ модуля гейта, а не `project_config.find_tausik_dir`:
    последний зовётся ещё и из `load_config()` в самом начале `run_gates`, так
    что подмена там роняет прогон ДО гейта и меряет не то.
    """

    def test_the_project_lookup_site_is_non_execution(self, monkeypatch):
        def _boom(*a, **k):
            raise OSError("cannot probe path")

        monkeypatch.setattr(gate_state_roundtrip.os.path, "isdir", _boom)
        outcome = gate_state_roundtrip.run_state_roundtrip_gate()
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_RUNNER_ERROR
        assert outcome.blocks
        assert "cannot probe path" in outcome.message

    def test_the_comparison_site_is_non_execution(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("comparison exploded")

        monkeypatch.setattr("state_serialize.check_tree", _boom)
        outcome = gate_state_roundtrip.run_state_roundtrip_gate()
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_RUNNER_ERROR
        assert outcome.blocks
        assert "comparison exploded" in outcome.message


class TestAGateNameWithNoDetectorIsNonExecutionToo:
    """Пятое место невыполнения, найденное МУТАЦИЕЙ, а не планом.

    `run_renar_drift_gate` отвечал на неизвестное имя гейта строкой
    `return True, "Unknown RENAR drift gate ... — skipped"`. Это не пропуск:
    вызывающий назвал гейт, для которого в модуле нет детектора, то есть НЕ
    ПРОВЕРЕНО НИЧЕГО. Слово «skipped» ставило его в один ряд с честными
    пропусками пустого клона, где судить действительно нечего.

    REASON_NO_GATE_IMPLEMENTATION — ровно это событие, и оно уже существует:
    так `gate_runner` называет свою версию того же случая.
    """

    def test_an_unmapped_gate_name_says_it_checked_nothing(self):
        outcome = gate_renar_drift.run_renar_drift_gate("no_such_renar_gate")
        assert outcome.outcome == gate_outcome.COULD_NOT_RUN
        assert outcome.reason_code == gate_outcome.REASON_NO_GATE_IMPLEMENTATION
        assert "no detector is mapped to it" in outcome.message
        assert outcome.remedy, "отказ обязан назвать следующее действие"

    def test_a_mapped_gate_name_still_runs(self):
        outcome = gate_renar_drift.run_renar_drift_gate("renar_drift_schema")
        assert outcome.ran, (
            "детектор для этого имени есть — гейт обязан вынести настоящий "
            "вердикт, иначе правка выключила бы проверку вместо её починки"
        )
