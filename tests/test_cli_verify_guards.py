"""Правила записи в кэш verify обязаны быть ОДНИ для CLI и для сервиса.

cli-verify-bypasses-cache-guards. Путей записи в `verification_runs` было два:

  1. `service_verification.run_gates_with_cache` — им ходят `task done` и
     MCP-verify. В нём живут защиты: `has_real_pass`, блок `no-test-mapped`,
     запрет кэшировать пустую объявленную область (префикс `noncacheable|`);
  2. `project_cli_verify.cmd_verify` — путь CLI `tausik verify`. Он звал
     `run_gates` и `record_run` НАПРЯМУЮ, поэтому не имел ни одной из них.

Живое доказательство расхождения — прогон #1054 в рабочей БД проекта:
объявлены два файла CHANGELOG, оба гейта показали `[SKIP]`, а записанная
строка получилась `exit_code=0`, без префикса `noncacheable|`, с summary
«hadolint=PASS, pytest=PASS» (пропущенный гейт рапортует `passed=True`).
Через `run_gates_with_cache` тот же вход даёт блокировку `no-test-mapped`.

Контракт после фикса: правила существуют в ОДНОМ экземпляре, оба входа
приходят к нему, и прогон, в котором не выполнился ни один гейт, не может
стать пригодным для повтора зелёным ни на одном пути.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402
from project_cli_verify import cmd_verify  # noqa: E402
from service_gates import GatesMixin  # noqa: E402

# Единый источник DDL — см. conftest.canonical_ddl и
# tests/test_ddl_fixture_parity.py: рукописная копия схемы уже дважды
# давала зелёные тесты при сломанном коде.
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
    """Отключить envelope-таймаут: тесты гоняют подменённый run_gates."""
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


# Ровно форма прогона #1054: объявлены файлы, ни один гейт не выполнился,
# каждый пропущенный рапортует passed=True.
ALL_SKIPPED = [_gate("hadolint", True, skipped=True), _gate("pytest", True, skipped=True)]


class _FakeBackend:
    def __init__(self, conn, files):
        self._conn = conn
        self._files = files
        self.notes: list[str] = []
        self.events: list[tuple] = []

    def task_get(self, slug):
        return {
            "slug": slug,
            "relevant_files": json.dumps(self._files),
            "started_at": None,
            "created_at": None,
        }

    def task_append_notes(self, slug, msg):
        self.notes.append(msg)

    def event_add(self, *a, **_kw):
        self.events.append(a)


class _FakeSvc(GatesMixin):
    """Настоящий GatesMixin поверх фальшивого бэкенда.

    Мок сервисного метода здесь был бы бессмысленным: проверяется именно то,
    что CLI приходит в общую точку, а не то, что он зовёт что-то похожее.
    """

    def __init__(self, conn, files):
        self.be = _FakeBackend(conn, files)


class _Args:
    def __init__(self, task, scope="manual", no_tests_expected=False):
        self.task = task
        self.scope = scope
        self.no_tests_expected = no_tests_expected


def _patch_gates(monkeypatch, gate_results):
    """Подменить слой гейтов. run_gates импортируется внутри функций —
    патчим модуль-источник, иначе подмена не доедет (гоча сессии #114)."""
    import gate_runner

    calls = {"n": 0}
    passed = all(r["passed"] for r in gate_results if not r.get("skipped"))

    def fake_run(*_a, **_kw):
        calls["n"] += 1
        return passed, gate_results

    monkeypatch.setattr(gate_runner, "run_gates", fake_run)
    return calls


def _rows(conn):
    return [
        dict(r)
        for r in conn.execute(
            "SELECT command, exit_code, summary FROM verification_runs ORDER BY id"
        )
    ]


def _run_cli(conn, files, monkeypatch, gate_results, slug="t", no_tests_expected=False):
    """Прогнать путь CLI. Возвращает (exit_code, число реальных прогонов гейтов)."""
    calls = _patch_gates(monkeypatch, gate_results)
    svc = _FakeSvc(conn, files)
    try:
        cmd_verify(svc, _Args(slug, no_tests_expected=no_tests_expected))
    except SystemExit as e:
        return int(e.code or 0), calls["n"]
    return 0, calls["n"]


def _run_service(conn, files, monkeypatch, gate_results, slug="t"):
    """Прогнать сервисный путь. Возвращает (passed, status, число прогонов)."""
    calls = _patch_gates(monkeypatch, gate_results)
    passed, _results, status = sv.run_gates_with_cache(
        conn, slug, files, scope="manual", trigger="verify"
    )
    return passed, status, calls["n"]


# --- AC1: расхождение воспроизведено -----------------------------------------


class TestAllSkippedRunParity:
    """Один и тот же вход обязан дать один и тот же вердикт на обоих путях."""

    def test_service_path_blocks_all_skipped_run(self, conn, monkeypatch, no_envelope):
        """Опорная точка: сервисный путь блокирует. Это эталон поведения."""
        passed, status, _calls = _run_service(conn, DECLARED, monkeypatch, ALL_SKIPPED)
        assert passed is False
        assert status == "no-test-mapped"

    def test_cli_path_blocks_all_skipped_run(self, conn, monkeypatch, no_envelope):
        """ПАДАЛ ДО ФИКСА: CLI возвращал 0 там, где сервис блокирует."""
        code, _calls = _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED)
        assert code == 1, (
            "прогон, в котором не выполнился ни один гейт, не доказывает ничего; "
            "CLI обязан блокировать так же, как сервисный путь"
        )

    def test_cli_all_skipped_row_is_not_cacheable(self, conn, monkeypatch, no_envelope):
        """ПАДАЛ ДО ФИКСА: строка #1054 писалась без noncacheable| и с exit 0.

        Она и есть сертификат: `task done` находит её строгим поиском по
        (slug, files_hash, command) и закрывает задачу по кэш-хиту.
        """
        _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED)
        rows = _rows(conn)
        assert rows, "наблюдаемость обязана сохраниться — строка пишется всегда"
        leaked = [
            r for r in rows if r["exit_code"] == 0 and not r["command"].startswith("noncacheable|")
        ]
        assert not leaked, f"CLI записал пригодную для повтора зелёную строку: {leaked}"

    def test_task_done_cannot_reuse_cli_all_skipped_run(self, conn, monkeypatch, no_envelope):
        """Главное следствие: закрытие задачи по такой строке невозможно."""
        from verify_cache import has_fresh_verify_run

        _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED)
        ok, hit = has_fresh_verify_run(conn, "t", DECLARED)
        assert ok is False, "прогон без единого выполненного гейта не закрывает задачу"
        assert hit is None


# --- AC2: одно место правил ---------------------------------------------------


class TestSingleWritePath:
    """Правила не должны существовать в двух экземплярах."""

    def test_cli_delegates_to_the_shared_entry_point(self, conn, monkeypatch, no_envelope):
        """CLI обязан звать общую функцию, а не собирать свой прогон.

        Дублирование условий в двух файлах — именно то, что породило дефект,
        поэтому проверяется сам факт делегирования, а не похожесть поведения.
        """
        seen = {}
        real = sv.run_gates_with_cache

        def spy(*a, **kw):
            seen["called"] = True
            return real(*a, **kw)

        monkeypatch.setattr(sv, "run_gates_with_cache", spy)
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        cmd_verify(_FakeSvc(conn, DECLARED), _Args("t"))
        assert seen.get("called"), "путь CLI обходит общую точку записи"

    def test_recorded_row_identical_on_both_paths(self, conn, tmp_path, monkeypatch, no_envelope):
        """Одинаковый вход → одинаковая записанная строка."""
        _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", True)])
        cli_rows = _rows(conn)

        other = _make_db(tmp_path / "svc.db")
        try:
            _run_service(other, DECLARED, monkeypatch, [_gate("pytest", True)])
            svc_rows = _rows(other)
        finally:
            other.close()

        assert cli_rows == svc_rows, f"пути разошлись: CLI={cli_rows}, сервис={svc_rows}"

    def test_empty_scope_blocked_identically_on_both_paths(
        self, conn, tmp_path, monkeypatch, no_envelope
    ):
        """Пустая объявленная область: CLI не должен обходить и этот запрет."""
        _run_cli(conn, [], monkeypatch, [_gate("filesize", True)])
        cli_rows = _rows(conn)

        other = _make_db(tmp_path / "svc2.db")
        try:
            _run_service(other, [], monkeypatch, [_gate("filesize", True)])
            svc_rows = _rows(other)
        finally:
            other.close()

        assert cli_rows == svc_rows
        assert all(r["command"].startswith("noncacheable|") for r in cli_rows)


# --- AC3: не сломать то, что работало ----------------------------------------


class TestHealthyPathsUnaffected:
    def test_cli_green_with_real_pass_is_cacheable(self, conn, monkeypatch, no_envelope):
        """Настоящий выполненный гейт по-прежнему даёт пригодный зелёный."""
        from verify_cache import _build_cache_command

        code, _calls = _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", True)])
        assert code == 0
        rows = _rows(conn)
        assert len(rows) == 1
        assert rows[0]["command"] == _build_cache_command("verify", DECLARED)
        assert rows[0]["exit_code"] == 0

    def test_cli_second_run_hits_cache(self, conn, monkeypatch, no_envelope, tmp_path):
        """Кэш CLI не сломан: повторный прогон не гоняет гейты."""
        (tmp_path / "CHANGELOG.md").write_text("# x", encoding="utf-8")
        (tmp_path / "CHANGELOG.ru.md").write_text("# x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", True)])
        _code, calls = _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", True)])
        assert calls == 0, "повторный verify обязан попадать в кэш"

    def test_cli_red_gate_still_exits_one(self, conn, monkeypatch, no_envelope):
        """Красный гейт по-прежнему роняет CLI и пишется с exit_code=1."""
        code, _calls = _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", False)])
        assert code == 1
        rows = _rows(conn)
        assert len(rows) == 1
        assert rows[0]["exit_code"] == 1

    def test_cli_reports_missing_task(self, conn, monkeypatch, no_envelope):
        """Несуществующая задача по-прежнему даёт понятный отказ, а не трейс."""
        _patch_gates(monkeypatch, [_gate("pytest", True)])
        svc = _FakeSvc(conn, DECLARED)
        svc.be.task_get = lambda _slug: None
        with pytest.raises(SystemExit) as e:
            cmd_verify(svc, _Args("nope"))
        assert e.value.code == 2


# --- verify-no-test-mapped-dead-end ------------------------------------------


class TestNoTestsExpectedEscape:
    """Тупик снят объявлением, а не выводом из типа файлов (AC1, AC2, AC3)."""

    def test_declared_run_closes_instead_of_blocking(self, conn, monkeypatch, no_envelope):
        """AC1: набор, не мапящийся на тесты, закрывается при явном объявлении."""
        code, _calls = _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED, no_tests_expected=True)
        assert code == 0, "документационная задача обязана иметь способ закрыться"

    def test_declared_run_is_reusable_by_task_done(self, conn, monkeypatch, no_envelope, tmp_path):
        """AC1: иначе выход был бы декоративным — task done всё равно не закрылся бы."""
        from verify_cache import has_fresh_verify_run

        for name in DECLARED:
            (tmp_path / name).write_text("# x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED, no_tests_expected=True)
        ok, hit = has_fresh_verify_run(conn, "t", DECLARED)
        assert ok is True
        assert hit is not None

    def test_declared_run_is_auditable_by_one_query(self, conn, monkeypatch, no_envelope):
        """AC2: «сколько закрытий прошло без единого выполненного гейта» — один SELECT."""
        from verify_cached_run import AUDIT_NO_TESTS_DECLARED_SQL

        _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED, no_tests_expected=True)
        _run_cli(conn, DECLARED, monkeypatch, [_gate("pytest", True)], slug="honest")

        rows = conn.execute(AUDIT_NO_TESTS_DECLARED_SQL).fetchall()
        assert [r[0] for r in rows] == ["t"], (
            "признак обязан выделять ровно объявленные прогоны и не задевать честные"
        )

    def test_summary_does_not_claim_pass_for_skipped_gates(self, conn, monkeypatch, no_envelope):
        """AC2: строка не должна выглядеть как обычный зелёный при чтении глазами."""
        _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED, no_tests_expected=True)
        summary = _rows(conn)[0]["summary"]
        assert "PASS" not in summary, f"пропущенный гейт не рапортует PASS: {summary!r}"
        assert summary == "hadolint=SKIP, pytest=SKIP"

    def test_without_declaration_behaviour_is_unchanged(self, conn, monkeypatch, no_envelope):
        """AC3 НЕГАТИВНЫЙ: без флага — по-прежнему блокировка и непригодная строка."""
        code, _calls = _run_cli(conn, DECLARED, monkeypatch, ALL_SKIPPED)
        assert code == 1
        rows = _rows(conn)
        assert all(r["command"].startswith("noncacheable|") for r in rows)
        assert all(r["exit_code"] == 1 for r in rows)

    def test_declaration_does_not_mask_a_real_failure(self, conn, monkeypatch, no_envelope):
        """AC3: объявление касается ТОЛЬКО пропущенных гейтов, а не упавших."""
        code, _calls = _run_cli(
            conn,
            DECLARED,
            monkeypatch,
            [_gate("pytest", False), _gate("hadolint", True, skipped=True)],
            no_tests_expected=True,
        )
        assert code == 1, "флаг не должен превращать красный гейт в зелёный"
        assert _rows(conn)[0]["exit_code"] == 1

    def test_block_message_names_only_real_flags(self, conn, monkeypatch, no_envelope):
        """AC4: подсказка называет существующий механизм, а не --no-knowledge.

        no_knowledge управляет захватом знаний (service_task_done.py) и на
        гейты не влияет — предлагать его здесь значило звать в тупик.
        """
        _patch_gates(monkeypatch, ALL_SKIPPED)
        svc = _FakeSvc(conn, DECLARED)
        with pytest.raises(SystemExit):
            cmd_verify(svc, _Args("t"))
        notes = " ".join(svc.be.notes)
        assert "--no-knowledge" not in notes
        assert "--no-tests-expected" in notes


class TestInheritedFromParentTask:
    """AC5 и AC6: наследство cli-verify-bypasses-cache-guards."""

    def test_full_suite_run_without_task_is_not_cache_material(
        self, conn, monkeypatch, no_envelope
    ):
        """AC5: verify без --task не порождает строки, пригодной для кэш-поиска.

        Родительская задача проверила это только чтением кода.
        """
        from verify_recent_lookup import lookup_recent_for_task

        _patch_gates(monkeypatch, [_gate("pytest", True)])
        svc = _FakeSvc(conn, [])
        cmd_verify(svc, _Args(None))

        rows = conn.execute("SELECT task_slug, command FROM verification_runs").fetchall()
        assert rows, "наблюдаемость сохраняется и здесь"
        assert all(r[0] is None for r in rows), "строка не привязана ни к одной задаче"
        assert lookup_recent_for_task(conn, "", files_hash="x", command="y") is None

    def test_pre_fix_row_expires_and_cannot_be_reused(self, conn, monkeypatch, no_envelope):
        """AC6: строки, записанные CLI ДО фикса, не принимаются задним числом.

        Механизм — не спецпроверка, а TTL: lookup отбраковывает всё старше
        DEFAULT_CACHE_TTL_S независимо от совпадения files_hash. Строка вида
        #1054 (exit 0, без префикса, все гейты пропущены) живёт максимум 600 с.
        """
        from datetime import datetime, timedelta, timezone

        from verify_cache import _build_cache_command, has_fresh_verify_run
        from verify_constants import DEFAULT_CACHE_TTL_S
        from verify_files_hash import compute_files_hash

        stale = datetime.now(timezone.utc) - timedelta(seconds=DEFAULT_CACHE_TTL_S + 60)
        conn.execute(
            "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
            "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
            (
                "t",
                "manual",
                _build_cache_command("verify", DECLARED),
                0,
                "hadolint=PASS, pytest=PASS",
                compute_files_hash(DECLARED),
                stale.isoformat().replace("+00:00", "Z"),
            ),
        )
        conn.commit()

        ok, hit = has_fresh_verify_run(conn, "t", DECLARED)
        assert ok is False, f"отравленная строка старше TTL={DEFAULT_CACHE_TTL_S}s не принимается"
        assert hit is None


class TestFixtureMatchesRealSchema:
    """Страховка от того, что уже один раз произошло в этой самой задаче."""

    def test_fixture_carries_the_scope_check_constraint(self, conn):
        """Рукописная DDL без CHECK давала зелёные тесты при сломанной фиче.

        Первая редакция признака кодировала его как scope='no-tests-expected'.
        Тесты проходили, на живой БД падала КАЖДАЯ запись. Пока фикстура
        строится из backend_schema, этот класс расхождения невозможен —
        тест проверяет, что вырезание канона не выродилось в пустышку.
        """
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO verification_runs (scope, command, exit_code, "
                "files_hash, ran_at) VALUES ('not-a-tier', 'c', 0, 'h', 'now')"
            )

    def test_fixture_has_the_no_tests_declared_column(self, conn):
        cols = {r[1] for r in conn.execute("PRAGMA table_info(verification_runs)")}
        assert "no_tests_declared" in cols
