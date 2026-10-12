"""Человекочитаемое поле прогона обязано быть честным так же, как таблица.

verify-summary-reports-skipped-as-pass. Таблица gate_runs говорила правду:
hadolint skipped=1, pytest skipped=0. Колонка summary той же строки говорила
«hadolint=PASS, pytest=PASS». Формула не спрашивала про skipped, а пропущенный
гейт по контракту gate_runner возвращает passed=True.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Машинные защиты (has_real_pass, блок no-test-mapped,
префикс noncacheable|) уже не дают такой строке стать сертификатом — но они
защищают КЭШ, а не читателя. summary читает человек, и она попадает в отчёт
агента о закрытии. Прогон #1054 — ровно этот класс: «hadolint=PASS,
pytest=PASS» при обоих [SKIP]. Именно эта строка создала у агента сессии #118
впечатление зелёного и продлила жизнь дыре на сессию.

ЖИВОЕ ПОДТВЕРЖДЕНИЕ, полученное ПОВТОРНО в сессии #120: прогон #1067 записан
с summary «hadolint=PASS, pytest=PASS» при выводе CLI `[PASS] hadolint` и
`[SKIP] pytest`. Дефект воспроизводится сам собой при обычной работе.

ПОЧЕМУ ОБЩАЯ ФУНКЦИЯ, А НЕ ТРИ ПРАВКИ. «Как назвать исход гейта» было
записано в проекте ПЯТЬ раз: три копии врали (verify_cached_run x2,
verify_no_test_mapped), две были правильными (project_cli_task,
gate_runner.format_results). Расхождение уже случилось, причём в обе стороны.
Три точечные правки дали бы шестую копию.
"""

from __future__ import annotations

import ast
import os
import sqlite3
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402
from gate_runner import gate_verdict, summarize_results  # noqa: E402

from conftest import VERIFICATION_RUNS_DDL  # noqa: E402

DECLARED = ["CHANGELOG.md", "CHANGELOG.ru.md"]


def _make_db(path):
    from backend_schema_gate_runs import GATE_RUNS_SQL

    c = sqlite3.connect(str(path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(VERIFICATION_RUNS_DDL)
    c.executescript(GATE_RUNS_SQL)
    c.commit()
    return c


@pytest.fixture
def conn(tmp_path):
    c = _make_db(tmp_path / "t.db")
    yield c
    c.close()


@pytest.fixture
def no_envelope(monkeypatch):
    monkeypatch.setattr(
        "project_config.load_config",
        lambda: {"verify_pipeline_timeout_seconds": 0},
    )


def _gate(name, passed=True, skipped=False, severity="block"):
    return {
        "name": name,
        "severity": severity,
        "passed": passed,
        "skipped": skipped,
        "output": "",
        "duration_ms": 3,
    }


def _patch_gates(monkeypatch, gate_results):
    import gate_runner

    passed = all(r["passed"] for r in gate_results if not r.get("skipped"))
    monkeypatch.setattr(gate_runner, "run_gates", lambda *_a, **_kw: (passed, gate_results))


def _summaries(conn) -> list[str]:
    return [r[0] for r in conn.execute("SELECT summary FROM verification_runs ORDER BY id")]


# --- AC1 + AC2: пропуск — третье состояние ------------------------------------


class TestSummaryTellsTheTruthAboutSkips:
    """ПАДАЛИ ДО ФИКСА: колонка summary называла пропуск успехом."""

    def test_a_skipped_gate_is_not_reported_as_pass(self, conn, monkeypatch, no_envelope):
        """Ровно форма прогона #1067: один гейт выполнен, второй пропущен."""
        _patch_gates(monkeypatch, [_gate("hadolint", True), _gate("pytest", True, skipped=True)])
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")

        summary = _summaries(conn)[0]
        assert "pytest=PASS" not in summary, (
            f"пропущенный гейт рапортует об успехе, которого не было: {summary!r}"
        )
        assert "pytest=SKIP" in summary, f"пропуск обязан быть назван пропуском: {summary!r}"

    def test_the_executed_gate_is_still_reported_as_pass(self, conn, monkeypatch, no_envelope):
        """AC5 НЕГАТИВНЫЙ: честный успех не должен пострадать от правки."""
        _patch_gates(monkeypatch, [_gate("hadolint", True), _gate("pytest", True, skipped=True)])
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")
        assert "hadolint=PASS" in _summaries(conn)[0]

    def test_summary_agrees_with_the_gate_runs_table(self, conn, monkeypatch, no_envelope):
        """Суть дефекта: две записи ОДНОГО прогона противоречили друг другу.

        Проверяется согласованность, а не текст — именно расхождение между
        честной таблицей и лгущей колонкой ввело агента в заблуждение.
        """
        _patch_gates(monkeypatch, [_gate("hadolint", True), _gate("pytest", True, skipped=True)])
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")

        summary = _summaries(conn)[0]
        for name, skipped in conn.execute("SELECT gate_name, skipped FROM gate_runs"):
            token = f"{name}=SKIP" if skipped else f"{name}=PASS"
            assert token in summary, (
                f"строка {summary!r} расходится с таблицей gate_runs "
                f"(гейт {name}, skipped={skipped})"
            )

    def test_all_skipped_blocking_run_says_skip(self, conn, monkeypatch, no_envelope):
        """Ветка no-test-mapped: блокировка тоже пишется, и тоже честно."""
        _patch_gates(
            monkeypatch,
            [_gate("hadolint", True, skipped=True), _gate("pytest", True, skipped=True)],
        )
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")
        summary = _summaries(conn)[0]
        assert "PASS" not in summary, (
            f"ни один гейт не выполнился, PASS неоткуда взяться: {summary!r}"
        )

    def test_a_failing_gate_is_still_fail(self, conn, monkeypatch, no_envelope):
        """AC5 НЕГАТИВНЫЙ: падение не должно превратиться в SKIP."""
        _patch_gates(monkeypatch, [_gate("pytest", False)])
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")
        assert "pytest=FAIL" in _summaries(conn)[0]


# --- AC2/AC5: сама функция ----------------------------------------------------


class TestGateVerdictVocabulary:
    def test_three_states(self):
        assert gate_verdict(_gate("g", passed=True)) == "PASS"
        assert gate_verdict(_gate("g", passed=False)) == "FAIL"
        assert gate_verdict(_gate("g", passed=True, skipped=True)) == "SKIP"

    def test_skip_wins_over_the_passed_flag(self):
        """Пропущенный гейт по контракту gate_runner несёт passed=True.

        Именно это и делало пропуск неотличимым от успеха: читать passed,
        не спросив про skipped, значит читать заглушку вместо результата.
        """
        assert gate_verdict(_gate("g", passed=True, skipped=True)) == "SKIP"

    def test_skip_wins_even_if_passed_is_false(self):
        """Сочетание не порождается gate_runner ни в одной из трёх точек, но
        трактовка обязана быть однозначной: гейт, который не выполнялся, не
        мог упасть. Молчаливое 'FAIL' здесь было бы выдумкой."""
        assert gate_verdict(_gate("g", passed=False, skipped=True)) == "SKIP"

    def test_summarize_joins_in_a_stable_order(self):
        line = summarize_results([_gate("b", True), _gate("a", True, skipped=True)])
        assert line == "b=PASS, a=SKIP", "порядок обязан следовать входу, а не сортировке"

    def test_summarize_handles_no_gates(self):
        assert summarize_results([]) == "ok"


# --- AC3 + AC4: одна формула, механически ------------------------------------


class TestSingleSpellingIsEnforced:
    """Гейт против шестой копии (конвенция #236).

    Формула уже разъезжалась в ОБЕ стороны: три копии врали, две говорили
    правду. Разовая починка трёх мест это состояние не фиксирует.
    """

    OWNER = "gate_runner.py"

    def _copies(self) -> list[str]:
        found: list[str] = []
        for name in sorted(os.listdir(_SCRIPTS)):
            if not name.endswith(".py") or name == self.OWNER:
                continue
            path = os.path.join(_SCRIPTS, name)
            with open(path, encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=path)
                except SyntaxError:  # pragma: no cover
                    continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.IfExp):
                    continue
                body = node.body
                if not (isinstance(body, ast.Constant) and body.value == "PASS"):
                    continue
                # Только вердикты О ГЕЙТЕ. `"PASS" if exit_code == 0` в
                # service_replay говорит про код возврата прогона, а не про
                # результат гейта — придираться к нему значит учить обходить
                # гейт вместо того, чтобы его соблюдать.
                if "passed" in ast.dump(node.test):
                    found.append(f"{name}:{node.lineno}")
        return found

    def test_no_module_spells_the_gate_verdict_itself(self):
        copies = self._copies()
        assert not copies, (
            "вердикт о гейте формулируется заново вместо вызова "
            f"gate_runner.gate_verdict: {copies}. Именно расхождение таких "
            "копий и породило лгущую summary."
        )

    def test_the_detector_is_not_blind(self):
        """Антитавтология: детектор обязан ловить настоящего нарушителя."""
        src = 'x = r["name"] + "=" + ("PASS" if r["passed"] else "FAIL")\n'
        tree = ast.parse(src)
        hits = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.IfExp)
            and isinstance(n.body, ast.Constant)
            and n.body.value == "PASS"
            and "passed" in ast.dump(n.test)
        ]
        assert hits, "детектор копий сломан — он не видит даже эталонного нарушителя"

    def test_the_detector_ignores_non_gate_verdicts(self):
        """НЕГАТИВНЫЙ: вердикт по коду возврата — не вердикт о гейте."""
        src = 'v = "PASS" if ec == 0 else "FAIL"\n'
        tree = ast.parse(src)
        hits = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.IfExp)
            and isinstance(n.body, ast.Constant)
            and n.body.value == "PASS"
            and "passed" in ast.dump(n.test)
        ]
        assert not hits

    def test_the_scan_actually_reads_modules(self):
        """Антипустышка: пустой каталог дал бы зелёное на любом коде."""
        names = [n for n in os.listdir(_SCRIPTS) if n.endswith(".py")]
        assert len(names) > 50, f"сканирование scripts/ не нашло модулей: {len(names)}"


# --- AC6: история не переписывается ------------------------------------------


class TestHistoryIsNotRewritten:
    def test_existing_rows_are_left_alone(self, conn, monkeypatch, no_envelope):
        """Запись прошлого прогона — факт о том, что было записано.

        Переписать её задним числом значило бы подделать журнал ради
        красоты: строка #1054 действительно была записана со словом PASS, и
        именно поэтому агент ошибся. Стереть след этой ошибки — потерять
        единственное доказательство, что дефект существовал. Миграции нет
        сознательно.
        """
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            ("old", "manual", "c", 0, "hadolint=PASS, pytest=PASS", "h", "2026-01-01T00:00:00Z"),
        )
        conn.commit()

        _patch_gates(monkeypatch, [_gate("pytest", True)])
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")

        old = conn.execute("SELECT summary FROM verification_runs WHERE task_slug='old'").fetchone()
        assert old[0] == "hadolint=PASS, pytest=PASS", (
            "исторические строки не подлежат исправлению задним числом"
        )
