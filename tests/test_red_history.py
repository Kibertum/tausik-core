"""Тест, ни разу не бывший красным, не является доказательством.

RENAR §9.18.2. Изоляция авторства доказывает, что тест написан ДО кода, но не
доказывает, что он ЧТО-ТО проверяет: пустой тест, честно написанный
изолированным агентом, зелен с рождения и проходит все оси P8. Узел, хоть раз
наблюдавшийся КРАСНЫМ, в этот момент показал, что умеет отличить одно состояние
мира от другого, — это наименьшее честное определение слов «он что-то
проверяет».

ЧТО ЭТОТ МЕХАНИЗМ НЕ УТВЕРЖДАЕТ, и это половина его ценности. Красная история не
делает тест ХОРОШИМ: он мог упасть по глупой причине и ничего полезного при этом
не утверждать. Исключается ровно одно — тест, который за всю жизнь ни разу не
мог упасть. Утверждение узкое, и записано узко: широкое («красная история значит
настоящее доказательство») не заслужено и есть тот самый класс, который весь
релиз вычищается.

ЗАМЕР ПЕРЕД ПРОЕКТИРОВАНИЕМ (смена #239) и разбор трёх разных чисел, которые в
описании задачи были одним: tests/ определяет 7 524 тестовые ФУНКЦИИ, pytest
собирает 10 357 УЗЛОВ, docs/_generated/constants.json говорит 10 240. Описание
называло 5 722 — это было верно раньше в релизе. Ключом взят УЗЕЛ: его сообщает
прогон и его цитирует закрытие.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import red_history as rh  # noqa: E402
from backend_migrations_v60 import MIGRATION_V60  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/", "tests/"]


@pytest.fixture
def db(tmp_path):
    """База со схемой v60 и больше ничем: предмет проверки — эта таблица."""
    path = tmp_path / "t.db"
    conn = sqlite3.connect(str(path))
    for statement in MIGRATION_V60:
        conn.execute(statement)
    conn.commit()
    conn.close()
    return str(path)


class TestМеханизмУмеетСказатьНЕТ:
    """AC-5, и та половина, без которой остальное — украшение."""

    def test_узел_без_красной_истории_не_засчитывается(self, db):
        assert rh.ever_red(db, "tests/test_x.py::test_never_failed") is False

    def test_узел_с_красной_историей_засчитывается(self, db):
        rh.record_reds(db, ["tests/test_x.py::test_did_fail"])
        assert rh.ever_red(db, "tests/test_x.py::test_did_fail") is True

    def test_ответ_не_один_и_тот_же_на_обоих_входах(self, db):
        """Явно, а не как следствие двух тестов выше: проверка, всегда дающая
        один ответ, зелена по обеим причинам сразу и не различает их."""
        rh.record_reds(db, ["tests/test_x.py::a"])
        assert rh.ever_red(db, "tests/test_x.py::a") != rh.ever_red(db, "tests/test_x.py::b")


class TestУзелТочный:
    """Красное в одном параметре ничего не говорит о другом."""

    def test_параметры_различаются(self, db):
        rh.record_reds(db, ["tests/test_x.py::test_p[a]"])
        assert rh.ever_red(db, "tests/test_x.py::test_p[a]")
        assert not rh.ever_red(db, "tests/test_x.py::test_p[b]")

    def test_вопрос_о_файле_отвечается_отдельно(self, db):
        """Широкий ответ доступен, но ТОЛЬКО через другой вызов: иначе можно
        получить широкий ответ, думая, что задал узкий вопрос."""
        rh.record_reds(db, ["tests/test_x.py::test_p[a]", "tests/test_x.py::test_q"])
        assert rh.reds_for_file(db, "tests/test_x.py") == [
            "tests/test_x.py::test_p[a]",
            "tests/test_x.py::test_q",
        ]
        assert rh.reds_for_file(db, "tests/test_other.py") == []


class TestЗаписьНеЛомаетПрогон:
    """Наблюдение обязано быть настолько дешёвым и тихим, чтобы его не
    выключили. Механизм, который роняет прогон, будет снят первым же, кому он
    помешает."""

    def test_отсутствующая_база_не_бросает(self, tmp_path):
        assert rh.record_reds(str(tmp_path / "нет.db"), ["a::b"]) == 0

    def test_база_без_таблицы_не_бросает(self, tmp_path):
        path = tmp_path / "bare.db"
        sqlite3.connect(str(path)).close()
        assert rh.record_reds(str(path), ["a::b"]) == 0

    def test_битая_база_не_бросает(self, tmp_path):
        path = tmp_path / "broken.db"
        path.write_bytes(b"not a database")
        assert rh.record_reds(str(path), ["a::b"]) == 0
        assert rh.ever_red(str(path), "a::b") is False

    def test_пустой_список_ничего_не_пишет(self, db):
        assert rh.record_reds(db, []) == 0
        assert rh.count(db) == 0

    def test_отсутствие_базы_не_выдаётся_за_отсутствие_красных(self, tmp_path):
        """Граница, которую легко стереть: «не смог прочитать» и «ни один не был
        красным» — разные утверждения, и второе было бы ложью."""
        assert rh.count(str(tmp_path / "нет.db")) == 0
        assert rh.ever_red(str(tmp_path / "нет.db"), "a::b") is False


class TestПовторноеНаблюдение:
    def test_один_узел_дважды_в_одном_прогоне_есть_одно_наблюдение(self, db):
        rh.record_reds(db, ["a::b", "a::b"])
        assert rh.count(db) == 1

    def test_второй_прогон_увеличивает_счётчик_а_не_строки(self, db):
        rh.record_reds(db, ["a::b"], when="2026-01-01T00:00:00Z")
        rh.record_reds(db, ["a::b"], when="2026-02-01T00:00:00Z")
        assert rh.count(db) == 1
        conn = sqlite3.connect(db)
        first, last, reds = conn.execute(
            "SELECT first_red_at, last_red_at, reds FROM test_red_history"
        ).fetchone()
        conn.close()
        assert first == "2026-01-01T00:00:00Z", "первое наблюдение переписано"
        assert last == "2026-02-01T00:00:00Z"
        assert reds == 2


class TestПравилоСообщаетАНеБлокирует:
    """AC-6. Красная история накапливается только прогонами, поэтому в день
    введения её нет ни у одного узла."""

    def test_режим_объявлен_и_порог_назван_числом(self):
        assert rh.REPORTING_ONLY is True
        assert isinstance(rh.BLOCKING_NEEDS_NODES, int) and rh.BLOCKING_NEEDS_NODES > 0
        assert isinstance(rh.BLOCKING_NEEDS_DAYS, int) and rh.BLOCKING_NEEDS_DAYS > 0

    def test_остаток_про_непереносимость_назван_в_исходнике(self):
        """AC-7. `.tausik/tausik.db` не версионируется, значит история НЕ
        переезжает между машинами. Сказано там, где прочтёт следующий."""
        source = (_REPO / "scripts" / "red_history.py").read_text(encoding="utf-8")
        assert "not version-controlled" in source
        assert "does NOT travel" in source


class TestПрогонДействительноПишет:
    """Сквозная проверка: не логика записи, а то, что хук её вызывает.

    Запускается ВЛОЖЕННЫЙ pytest на временном каталоге с одним падающим тестом.
    Иначе зелёным был бы модуль, который никто не зовёт, — ровно тот класс,
    который в этом релизе находили дважды.
    """

    def test_падение_вложенного_прогона_попадает_в_историю(self, tmp_path, db):
        project = tmp_path / "proj"
        (project / ".tausik").mkdir(parents=True)
        os.replace(db, project / ".tausik" / "tausik.db")
        (project / "tests").mkdir()
        (project / "tests" / "test_falls.py").write_text(
            "def test_falls():\n    assert False\n", encoding="utf-8"
        )

        # Загружается ПЛАГИН, а не копия хуков: копия зеленела бы, пока
        # настоящий модуль гниёт. Наш conftest сюда не годится — он тянет
        # десяток модулей проекта и вне этого репозитория не грузится, что
        # первая редакция этого теста и обнаружила падением.
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_falls.py",
                "-q",
                "-p",
                "no:xdist",
                "-p",
                "red_history_plugin",
            ],
            cwd=str(project),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={
                **os.environ,
                "PYTHONUTF8": "1",
                "PYTHONPATH": str(_REPO / "scripts"),
            },
            timeout=300,
        )

        recorded = rh.reds_for_file(str(project / ".tausik" / "tausik.db"), "tests/test_falls.py")
        assert recorded == ["tests/test_falls.py::test_falls"], (
            "хук не записал падение — модуль работает, а его никто не зовёт"
        )
