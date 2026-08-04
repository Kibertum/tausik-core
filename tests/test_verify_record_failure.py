"""Отказ записи доказательства обязан менять вердикт, а не только лог.

verify-record-failure-swallowed. `_record_verification` оборачивала запись в
`except Exception`, писала предупреждение в logging и возвращала None, НЕ трогая
`passed`. Наружу — в `task done`, в отчёт агента, в CLI — уходил зелёный,
неотличимый от зелёного с записанным доказательством.

Хуже, чем обычный fail-open: внутренний слой (`gate_run_record`) сделан
fail-closed НАМЕРЕННО и пишет об этом в докстринге («a write that cannot happen
raises… a run that looks recorded but is not is expensive», конвенция #221).
Этот except ловил ровно то исключение, которым слой защищался, — гарантия
аннулировалась на уровень выше.

ЖИВОЕ ДОКАЗАТЕЛЬСТВО (сессия #119, не рассуждение): когда запись падала на
CHECK-констрейнте `scope`, CLI напечатал «Verify PASSED — NOT recorded». Слово
PASSED стояло рядом с признанием, что доказательства нет.

Контракт после фикса: прогон, доказательство которого не записалось, не
является зелёным ни для кого — ни для CLI, ни для сервиса, ни для task done.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402
import verify_run_record  # noqa: E402
from service_gates import GatesMixin  # noqa: E402
from verify_run_record import RECORD_FAILED_STATUS, VerificationRecordError  # noqa: E402

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


@pytest.fixture
def no_sleep(monkeypatch):
    """Убрать backoff из повторов: тест проверяет политику, а не ждёт её."""
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda _s: None)


def _gate(name, passed=True, skipped=False, severity="block"):
    return {
        "name": name,
        "severity": severity,
        "passed": passed,
        "skipped": skipped,
        "output": "",
        "duration_ms": 3,
    }


ALL_SKIPPED = [_gate("hadolint", True, skipped=True), _gate("pytest", True, skipped=True)]


def _patch_gates(monkeypatch, gate_results):
    """Подменить слой гейтов в модуле-источнике (гоча #114: run_gates
    импортируется внутри функции, патч фасада не доедет)."""
    import gate_runner

    passed = all(r["passed"] for r in gate_results if not r.get("skipped"))
    monkeypatch.setattr(gate_runner, "run_gates", lambda *_a, **_kw: (passed, gate_results))


def _break_record(monkeypatch, exc=None, fail_times=None):
    """Заставить record_run падать.

    Патчится `verify_run_record.record_run` — то самое имя, которое
    `_record_verification` резолвит в своём модуле. Подмена фасада
    `service_verification` сюда не доехала бы (память #243).
    """
    calls = {"n": 0}
    boom = exc or sqlite3.IntegrityError("CHECK constraint failed: verification_runs")

    def fake(*_a, **_kw):
        calls["n"] += 1
        if fail_times is None or calls["n"] <= fail_times:
            raise boom
        return 4242

    monkeypatch.setattr(verify_run_record, "record_run", fake)
    return calls


class _FakeBackend:
    def __init__(self, conn):
        self._conn = conn
        self.notes: list[str] = []

    def task_get(self, slug):
        import json

        return {
            "slug": slug,
            "relevant_files": json.dumps(DECLARED),
            "started_at": None,
            "created_at": None,
            "complexity": "simple",
        }

    def task_append_notes(self, slug, msg):
        self.notes.append(msg)


class _FakeSvc(GatesMixin):
    def __init__(self, conn):
        self.be = _FakeBackend(conn)


# --- AC1: регрессия воспроизведена -------------------------------------------


class TestSilentGreenReproduced:
    """ПАДАЛИ ДО ФИКСА: запись провалилась, вердикт остался зелёным."""

    def test_record_failure_is_not_a_green(self, conn, monkeypatch, no_envelope, no_sleep):
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        passed, results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )

        assert passed is False, (
            "прогон, доказательство которого не записалось, неотличим от "
            "прогона, доказательства которого не существует — зелёным он быть не может"
        )
        assert status == RECORD_FAILED_STATUS
        assert any(r["name"] == "verify-record" and not r["passed"] for r in results)

    def test_failure_is_visible_in_the_return_value_not_only_in_the_log(
        self, conn, monkeypatch, no_envelope, no_sleep
    ):
        """AC2: агент через MCP файл .tausik/tausik.log не читает в принципе.

        Решение о закрытии принимается по возвращаемому значению, поэтому
        сигнал обязан жить именно там.
        """
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        _passed, results, _status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )

        synth = next(r for r in results if r["name"] == "verify-record")
        assert synth["severity"] == "block"
        assert synth["skipped"] is False
        assert "record" in synth["output"].lower()

    def test_no_row_was_actually_written(self, conn, monkeypatch, no_envelope, no_sleep):
        """Страховка от тавтологии: подмена действительно ломает запись."""
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)
        sv.run_gates_with_cache(conn, "t", DECLARED, scope="manual", trigger="verify")
        assert conn.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0] == 0


# --- AC3: закрытие задачи блокируется ----------------------------------------


class TestTaskDoneIsBlocked:
    """Уровень сервиса, а не только юнит: именно этот отчёт читает task done."""

    def test_gate_report_blocks_with_a_named_reason(self, conn, monkeypatch, no_envelope, no_sleep):
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        report = _FakeSvc(conn)._run_quality_gates_report("t", DECLARED, trigger="verify")

        assert report["passed"] is False
        assert report["cache_status"] == RECORD_FAILED_STATUS
        blocking = report["blocking_failures"]
        assert blocking, "отказ обязан дойти до blocking_failures, иначе task done закроется"
        assert any(f["gate"] == "verify-record" for f in blocking)

    def test_remediation_names_the_actual_problem(self, conn, monkeypatch, no_envelope, no_sleep):
        """Внятная причина, а не голый трейс: агент должен понять, что делать."""
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        report = _FakeSvc(conn)._run_quality_gates_report("t", DECLARED, trigger="verify")
        out = next(f for f in report["blocking_failures"] if f["gate"] == "verify-record")["output"]
        assert "IntegrityError" in out or "CHECK" in out, (
            f"причина отказа записи обязана быть названа: {out!r}"
        )

    def test_public_verify_entry_point_reports_it_too(
        self, conn, monkeypatch, no_envelope, no_sleep
    ):
        """`run_verify_for_task` — то, что видят MCP и CLI."""
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        report = _FakeSvc(conn).run_verify_for_task("t", DECLARED, trigger="verify")

        assert report["passed"] is False
        assert report["status"] == RECORD_FAILED_STATUS
        assert report["run_id"] is None


class TestCliSurfacesIt:
    def test_cli_exits_nonzero_and_says_evidence_is_missing(
        self, conn, monkeypatch, no_envelope, no_sleep, capsys
    ):
        """ЖИВОЙ СЦЕНАРИЙ #119: было «Verify PASSED — NOT recorded», exit 0."""
        from project_cli_verify import cmd_verify

        class _Args:
            task = "t"
            scope = "manual"
            no_tests_expected = False

        _patch_gates(monkeypatch, [_gate("pytest", True)])
        _break_record(monkeypatch)

        with pytest.raises(SystemExit) as e:
            cmd_verify(_FakeSvc(conn), _Args())

        assert e.value.code == 1
        out = capsys.readouterr().out
        assert "PASSED" not in out, f"слово PASSED рядом с отсутствием доказательства: {out!r}"


# --- AC4: контракт gate_run_record не аннулируется ---------------------------


class TestFailClosedContractHolds:
    def test_record_verification_raises_instead_of_swallowing(self, conn, monkeypatch, no_sleep):
        """#221: проверка, которая не смогла записать результат, не рапортует успех."""
        _break_record(monkeypatch)
        with pytest.raises(VerificationRecordError):
            verify_run_record._record_verification(
                conn,
                slug="t",
                command="c",
                exit_code=0,
                summary="pytest=PASS",
                files_hash="h",
                gate_results=[_gate("pytest", True)],
                scope_desc={"status": "unknown"},
                trigger="verify",
                scope="manual",
            )

    def test_the_cause_is_chained_not_discarded(self, conn, monkeypatch, no_sleep):
        """Диагностируемость: исходное исключение обязано остаться доступным."""
        boom = sqlite3.IntegrityError("CHECK constraint failed")
        _break_record(monkeypatch, exc=boom)
        with pytest.raises(VerificationRecordError) as e:
            verify_run_record._record_verification(
                conn,
                slug="t",
                command="c",
                exit_code=0,
                summary="s",
                files_hash="h",
                gate_results=[_gate("pytest", True)],
                scope_desc={"status": "unknown"},
                trigger="verify",
                scope="manual",
            )
        assert e.value.__cause__ is boom


# --- AC5: временная недоступность БД -----------------------------------------


class TestTransientLockPolicy:
    """Блокировка WAL конкурентом не должна делать прогон вечно падающим."""

    def test_transient_lock_is_retried_and_then_succeeds(self, conn, monkeypatch, no_sleep):
        calls = _break_record(
            monkeypatch,
            exc=sqlite3.OperationalError("database is locked"),
            fail_times=1,
        )
        run_id = verify_run_record._record_verification(
            conn,
            slug="t",
            command="c",
            exit_code=0,
            summary="s",
            files_hash="h",
            gate_results=[_gate("pytest", True)],
            scope_desc={"status": "unknown"},
            trigger="verify",
            scope="manual",
        )
        assert run_id == 4242, "временная блокировка обязана пережиться повтором"
        assert calls["n"] == 2

    def test_retries_are_bounded_and_end_in_an_honest_failure(self, conn, monkeypatch, no_sleep):
        """Не бесконечный цикл и не тихий зелёный — честный отказ."""
        calls = _break_record(monkeypatch, exc=sqlite3.OperationalError("database is locked"))
        with pytest.raises(VerificationRecordError):
            verify_run_record._record_verification(
                conn,
                slug="t",
                command="c",
                exit_code=0,
                summary="s",
                files_hash="h",
                gate_results=[_gate("pytest", True)],
                scope_desc={"status": "unknown"},
                trigger="verify",
                scope="manual",
            )
        assert calls["n"] == verify_run_record.RECORD_MAX_ATTEMPTS

    def test_a_permanent_error_is_not_retried(self, conn, monkeypatch, no_sleep):
        """IntegrityError повтором не лечится — повторять её значит тратить время
        на заведомо безнадёжное и маскировать причину задержкой."""
        calls = _break_record(monkeypatch, exc=sqlite3.IntegrityError("CHECK failed"))
        with pytest.raises(VerificationRecordError):
            verify_run_record._record_verification(
                conn,
                slug="t",
                command="c",
                exit_code=0,
                summary="s",
                files_hash="h",
                gate_results=[_gate("pytest", True)],
                scope_desc={"status": "unknown"},
                trigger="verify",
                scope="manual",
            )
        assert calls["n"] == 1

    def test_a_non_lock_operational_error_is_not_retried(self, conn, monkeypatch, no_sleep):
        """«no such table» — не временная недоступность, а сломанная схема."""
        calls = _break_record(monkeypatch, exc=sqlite3.OperationalError("no such table: x"))
        with pytest.raises(VerificationRecordError):
            verify_run_record._record_verification(
                conn,
                slug="t",
                command="c",
                exit_code=0,
                summary="s",
                files_hash="h",
                gate_results=[_gate("pytest", True)],
                scope_desc={"status": "unknown"},
                trigger="verify",
                scope="manual",
            )
        assert calls["n"] == 1


# --- AC6: путь без единого гейта не считается отказом записи -----------------


class TestNoGatesRanIsNotARecordFailure:
    def test_empty_results_writes_nothing_and_stays_green(
        self, conn, monkeypatch, no_envelope, no_sleep
    ):
        """Гейты не запускались вовсе: писать нечего, отказа записи нет."""
        _patch_gates(monkeypatch, [])
        calls = _break_record(monkeypatch)

        passed, results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )

        assert calls["n"] == 0, "по пустым результатам запись не должна даже пытаться"
        assert passed is True
        assert results == []
        assert status != RECORD_FAILED_STATUS


# --- Ветки, которые уже блокируют -------------------------------------------


class TestAlreadyBlockingBranchesStayBlocked:
    """Вердикт не эскалируется (он и так False), но отказ записи виден."""

    def test_no_test_mapped_block_survives_a_record_failure(
        self, conn, monkeypatch, no_envelope, no_sleep
    ):
        _patch_gates(monkeypatch, ALL_SKIPPED)
        _break_record(monkeypatch)

        passed, results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )

        assert passed is False
        assert status == "no-test-mapped", "первичная причина блокировки не подменяется"
        assert any(r["name"] == "verify-record" for r in results), (
            "потеря следа обязана быть видна, даже когда вердикт и так блокирующий"
        )

    def test_declared_no_tests_green_becomes_red_when_evidence_is_lost(
        self, conn, monkeypatch, no_envelope, no_sleep
    ):
        """--no-tests-expected опирается ТОЛЬКО на запись (no_tests_declared=1).

        Если строки нет, закрытие не опирается ни на что: ни на выполненный
        гейт, ни на аудируемое объявление.
        """
        _patch_gates(monkeypatch, ALL_SKIPPED)
        _break_record(monkeypatch)

        passed, _results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify", no_tests_expected=True
        )

        assert passed is False
        assert status == RECORD_FAILED_STATUS


# --- Здоровые пути не сломаны ------------------------------------------------


class TestHealthyPathsUnaffected:
    def test_successful_record_is_unchanged(self, conn, monkeypatch, no_envelope):
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        passed, _results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )
        assert passed is True
        assert status == "miss"
        assert conn.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0] == 1

    def test_red_gate_still_reads_as_a_gate_failure(self, conn, monkeypatch, no_envelope):
        _patch_gates(monkeypatch, [_gate("pytest", False)])
        passed, results, status = sv.run_gates_with_cache(
            conn, "t", DECLARED, scope="manual", trigger="verify"
        )
        assert passed is False
        assert status == "miss"
        assert not any(r["name"] == "verify-record" for r in results)
