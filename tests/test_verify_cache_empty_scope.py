"""Пустая объявленная область — это «неизвестно», а не «проверено пусто».

verify-cache-empty-scope-hit. `tausik verify --task X` до объявления
relevant_files запускается с files=[]; gate_runner в этом случае ПРОПУСКАЕТ
scoped-гейты («No relevant_files passed; gate skipped»). Такой прогон не
доказывает ничего о тестах, но раньше он:

  1. кэшировался — compute_files_hash([]) возвращает стабильный empty-marker,
     который не двигается ни при какой правке дерева, так что зелёный
     оставался валидным в пределах TTL при ЛЮБЫХ изменениях;
  2. принимался релаксированной веткой как сертификат для произвольного
     непустого набора файлов.

Контракт после фикса: пустая область не порождает пригодного для повтора
зелёного (#226 «неизвестно» ≠ «пусто», #221 гейт, не сумевший вычислиться,
блокирует). Наблюдаемость сохраняется — прогон пишется с префиксом
`noncacheable|`.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import service_verification as sv  # noqa: E402
from verify_cache import _build_cache_command, has_fresh_verify_run  # noqa: E402
from verify_files_hash import compute_files_hash  # noqa: E402


@pytest.fixture
def conn(tmp_path):
    from backend_schema_gate_runs import GATE_RUNS_SQL

    c = sqlite3.connect(str(tmp_path / "t.db"))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS verification_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_slug TEXT,
    scope TEXT NOT NULL CHECK(scope IN
        ('lightweight', 'standard', 'high', 'critical', 'manual')),
    command TEXT NOT NULL,
    exit_code INTEGER NOT NULL,
    summary TEXT,
    files_hash TEXT NOT NULL,
    ran_at TEXT NOT NULL,
    duration_ms INTEGER,
    receipt_json TEXT,
    -- l26-verify-git-diff-wire: how the declared scope related to git at run
    -- time. 'complete' | 'under-declared' | 'unknown'; NULL on rows written
    -- before v38 and read as 'unknown' (never as 'complete').
    declared_scope_status TEXT,
    -- JSON array of files git saw change but relevant_files omitted (capped).
    undeclared_files TEXT,
    -- verify-no-test-mapped-dead-end: 1 when the caller declared, for this run,
    -- that its files map to no test on purpose (docs, config, migrations). Such
    -- a run passes with NO gate executed, so it must stay countable:
    --   SELECT * FROM verification_runs WHERE no_tests_declared = 1;
    -- A dedicated column, not a `scope` value — `scope` is a CHECK-constrained
    -- SENAR tier, and overloading it would have required rebuilding the table
    -- to widen the constraint.
    no_tests_declared INTEGER NOT NULL DEFAULT 0
);;
        """
    )
    c.executescript(GATE_RUNS_SQL)
    c.commit()
    yield c
    c.close()


@pytest.fixture
def no_envelope(monkeypatch):
    """Отключить envelope-таймаут: тесты гоняют подменённый run_gates."""
    monkeypatch.setattr(
        "project_config.load_config",
        lambda: {"verify_pipeline_timeout_seconds": 0},
    )


def _gate(name, passed=True, severity="block", skipped=False):
    return {
        "name": name,
        "severity": severity,
        "passed": passed,
        "skipped": skipped,
        "output": "",
        "duration_ms": 3,
    }


def _run(conn, monkeypatch, gate_results, slug="t", files=None, trigger="verify"):
    """Прогнать run_gates_with_cache с подменённым слоем гейтов.

    run_gates импортируется внутри функции, поэтому патчить надо модуль-источник.
    Возвращает (passed, results, cache_status, calls) — calls считает реальные
    запуски гейтов, что и отличает попадание в кэш от промаха.
    """
    import gate_runner

    calls = {"n": 0}
    passed = all(r["passed"] for r in gate_results if not r.get("skipped"))

    def fake_run(*_a, **_kw):
        calls["n"] += 1
        return passed, gate_results

    monkeypatch.setattr(gate_runner, "run_gates", fake_run)
    result = sv.run_gates_with_cache(
        conn,
        slug,
        files if files is not None else ["scripts/x.py"],
        trigger=trigger,
    )
    return (*result, calls["n"])


def _insert_row(conn, *, slug, command, files_hash, exit_code=0, scope="manual"):
    """Прямая вставка строки: нужна, чтобы собрать ровно ту форму command,
    которая раньше протекала (noncacheable-префикс, чужой бакет)."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    conn.execute(
        "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
        "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
        (slug, scope, command, exit_code, "ok", files_hash, now),
    )
    conn.commit()


# --- AC2: запись ------------------------------------------------------------


class TestEmptyScopeIsNotCacheable:
    """Пустая область не порождает пригодного для повтора зелёного."""

    def test_empty_scope_green_is_recorded_as_noncacheable(self, conn, monkeypatch, no_envelope):
        """Гейт, не зависящий от области (filesize), проходит при files=[].

        Раньше has_real_pass=True делал строку кэшируемой, и зелёный
        привязывался к empty-marker хэшу, который не двигается никогда.
        """
        _run(conn, monkeypatch, [_gate("filesize", True)], files=[])
        commands = [r[0] for r in conn.execute("SELECT command FROM verification_runs")]
        assert len(commands) == 1
        assert commands[0].startswith("noncacheable|"), (
            "пустая область = «неизвестно»: строка обязана быть непригодной "
            f"для повтора, получено {commands[0]!r}"
        )

    def test_empty_scope_run_is_still_recorded(self, conn, monkeypatch, no_envelope):
        """Непригодность для кэша не отменяет наблюдаемости (решение #146)."""
        _run(conn, monkeypatch, [_gate("filesize", True)], files=[])
        assert conn.execute("SELECT COUNT(*) FROM verification_runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM gate_runs").fetchone()[0] == 1

    def test_declared_scope_still_cacheable(self, conn, monkeypatch, no_envelope):
        """Негативный контроль: обычный путь с объявленной областью не задет."""
        _run(conn, monkeypatch, [_gate("pytest", True)], files=["scripts/x.py"])
        commands = [r[0] for r in conn.execute("SELECT command FROM verification_runs")]
        assert commands == [_build_cache_command("verify", ["scripts/x.py"])]
        assert not commands[0].startswith("noncacheable|")


# --- AC1: воспроизведение исходной регрессии --------------------------------


class TestEditAfterEmptyScopeVerifyIsSeen:
    """Головной сценарий карточки: verify → правка → повторная проверка."""

    def test_edit_after_empty_scope_verify_must_miss(
        self, conn, monkeypatch, no_envelope, tmp_path
    ):
        src = tmp_path / "scripts" / "x.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# before", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        # 1. `tausik verify --task t` до объявления relevant_files.
        _run(conn, monkeypatch, [_gate("filesize", True)], files=[])
        # 2. Правка файла, который затем объявят в relevant_files.
        src.write_text("# after — правка, которую зелёный не видел", encoding="utf-8")
        # 3. `task done t --relevant-files scripts/x.py`.
        ok, hit = has_fresh_verify_run(conn, "t", ["scripts/x.py"])

        assert ok is False, (
            "зелёный, снятый по пустой области, не видел правки: "
            "empty-marker хэш не двигается, поэтому такой прогон не может "
            "сертифицировать НИ ОДИН файл"
        )
        assert hit is None

    def test_second_verify_reruns_gates_instead_of_hitting(self, conn, monkeypatch, no_envelope):
        """Повторный verify с пустой областью обязан снова гонять гейты."""
        _run(conn, monkeypatch, [_gate("filesize", True)], files=[])
        _p, _r, status, calls = _run(conn, monkeypatch, [_gate("filesize", True)], files=[])
        assert calls == 1, "пустая область не должна попадать в кэш по самой себе"
        assert status != "hit"


# --- AC3: чтение симметрично записи -----------------------------------------


class TestManualScopeRowCertifiesNothing:
    """Обе релаксированные ветки больше не принимают пустую область."""

    def test_has_fresh_verify_run_rejects_manual_row(self, conn):
        _insert_row(
            conn,
            slug="t",
            command=_build_cache_command("verify", []),
            files_hash=compute_files_hash([]),
        )
        ok, hit = has_fresh_verify_run(conn, "t", ["scripts/foo.py"])
        assert ok is False
        assert hit is None

    def test_run_gates_with_cache_rejects_manual_row(self, conn, monkeypatch, no_envelope):
        _insert_row(
            conn,
            slug="t",
            command=_build_cache_command("verify", []),
            files_hash=compute_files_hash([]),
        )
        _p, _r, status, calls = _run(
            conn, monkeypatch, [_gate("pytest", True)], files=["scripts/foo.py"]
        )
        assert calls == 1, "строка с пустой областью не сертифицирует набор файлов"
        assert status != "hit"

    def test_empty_task_done_call_does_not_hit_manual_row(self, conn):
        """Пустая область и на чтении не совпадает сама с собой."""
        _insert_row(
            conn,
            slug="t",
            command=_build_cache_command("verify", []),
            files_hash=compute_files_hash([]),
        )
        ok, _hit = has_fresh_verify_run(conn, "t", [])
        assert ok is False


# --- AC4: вторая дыра, найденная чтением ------------------------------------


class TestRelaxedLookupBucketAndPrefixLeak:
    """service_verification.py:236 звал релаксированный поиск БЕЗ command_prefix.

    Из-за этого он принимал (а) строку, помеченную noncacheable|, вопреки
    комментарию на строках 330-337, и (б) строку чужого бакета task-done.
    """

    def test_noncacheable_row_is_not_a_cache_hit(self, conn, monkeypatch, no_envelope):
        _insert_row(
            conn,
            slug="t",
            command="noncacheable|" + _build_cache_command("verify", []),
            files_hash=compute_files_hash([]),
        )
        _p, _r, status, calls = _run(
            conn, monkeypatch, [_gate("pytest", True)], files=["scripts/foo.py"]
        )
        assert calls == 1, (
            "префикс noncacheable| обязан быть непроходим для ОБОИХ поисков — "
            "комментарий в service_verification это уже утверждает"
        )
        assert status != "hit"

    def test_task_done_bucket_row_does_not_satisfy_verify_trigger(
        self, conn, monkeypatch, no_envelope
    ):
        _insert_row(
            conn,
            slug="t",
            command=_build_cache_command("task-done", []),
            files_hash=compute_files_hash([]),
        )
        _p, _r, status, calls = _run(
            conn, monkeypatch, [_gate("pytest", True)], files=["scripts/foo.py"], trigger="verify"
        )
        assert calls == 1, "разделение бакетов обязано работать и в этой точке вызова"
        assert status != "hit"


# --- AC5: не сломать то, что работало ---------------------------------------


class TestUnrelatedPathsUnaffected:
    def test_strict_hit_still_works(self, conn, monkeypatch, no_envelope, tmp_path):
        """Объявленная область → строгое попадание, гейты не гоняются повторно."""
        src = tmp_path / "scripts" / "x.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        files = ["scripts/x.py"]

        _run(conn, monkeypatch, [_gate("pytest", True)], files=files)
        _p, _r, status, calls = _run(conn, monkeypatch, [_gate("pytest", True)], files=files)
        assert status == "hit"
        assert calls == 0

    def test_strict_hit_invalidated_by_edit(self, conn, monkeypatch, no_envelope, tmp_path):
        """И обратное: правка объявленного файла двигает хэш и снимает зелёный."""
        src = tmp_path / "scripts" / "x.py"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("# before", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        files = ["scripts/x.py"]

        _run(conn, monkeypatch, [_gate("pytest", True)], files=files)
        src.write_text("# after", encoding="utf-8")
        _p, _r, status, calls = _run(conn, monkeypatch, [_gate("pytest", True)], files=files)
        assert status != "hit"
        assert calls == 1

    def test_empty_slug_never_hits(self, conn):
        ok, hit = has_fresh_verify_run(conn, "", ["scripts/x.py"])
        assert ok is False
        assert hit is None
