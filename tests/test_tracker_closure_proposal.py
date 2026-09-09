"""Закрытие задачи ПРЕДЛАГАЕТ ответить в тикет и никогда не отвечает само.

ОТРИЦАТЕЛЬНОЕ ТРЕБОВАНИЕ ЗДЕСЬ ГЛАВНОЕ, и оно записано в самой задаче: не
автоматизировать закрытие БЕЗ подтверждения человеком. Тикет мог описывать
больше, чем закрыла задача, — тогда автозакрытие обрубает чужую находку на
половине. Тихое закрытие чужого тикета хуже незакрытого: незакрытый хотя бы
виден.

ПОЭТОМУ ПРОВЕРЯЕТСЯ НЕ «ЧТО НАПЕЧАТАНО», А «ЧЕГО НЕ ПРОИСХОДИТ». Сеть на пути
закрытия глушится, и путь обязан пройти целиком. Проверка на подстроку в тексте
доказала бы, что текст такой; глушение сокета доказывает, что тикет остался
нетронут, — а это и есть требование.

ВТОРАЯ ПОЛОВИНА — ТИШИНА ПРИ ОТСУТСТВИИ ПРИВЯЗКИ. Напоминание, печатающееся
всем, читается всеми как шум и через неделю не читается никем. Задача без тикета
не получает при закрытии ни одной новой строки, и это тоже проверяется.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import closure_reminders  # noqa: E402
import tracker_closure_proposal as tcp  # noqa: E402


class TestБезПривязкиНиОднойНовойСтроки:
    """AC-4. Напоминание, печатающееся всем, перестают читать все."""

    @pytest.mark.parametrize(
        "task",
        [
            pytest.param({}, id="поля_нет_вовсе"),
            pytest.param({"tracker_refs": None}, id="null"),
            pytest.param({"tracker_refs": "[]"}, id="пустой_список"),
            pytest.param({"tracker_refs": "не json"}, id="испорченное_значение"),
        ],
    )
    def test_молчит(self, task):
        assert tcp.proposal_for_task(task) is None

    def test_испорченное_значение_молчит_а_не_падает(self):
        """Поле заведено ради долгов перед людьми и не смеет стать новым
        способом не закрыть работу."""
        assert closure_reminders.reminders_at_close("t", None, {"tracker_refs": "{"}) == []


class TestСПривязкойНапоминаниеЕсть:
    @pytest.mark.parametrize(
        ("refs", "expected"),
        [
            pytest.param(["github#7"], "Тикет — НЕТ:", id="один"),
            pytest.param(["github#7", "gitlab#12"], "Тикеты — НЕТ:", id="несколько"),
        ],
    )
    def test_согласование_не_ломается_на_числе(self, refs, expected):
        """Первая версия печатала «1 тикета» на первом же живом закрытии, потому
        что подставляла число в фразу с русским согласованием. Число убрано:
        ссылки перечислены строкой ниже и их видно."""
        text = tcp.proposal_for(refs)
        assert expected in text
        assert "1 тикета" not in text and "2 тикетов" not in text

    def test_названы_все_тикеты(self):
        text = tcp.proposal_for(["github#7", "gitlab#12"])
        assert text is not None
        assert "github#7" in text and "gitlab#12" in text

    def test_сказано_что_ничего_не_отправлено(self):
        """Читатель обязан узнать состояние тикета из самой строки, а не
        достраивать его догадкой."""
        text = tcp.proposal_for(["github#7"])
        assert "ничего никуда не отправило" in text

    def test_названо_условие_закрытия_а_не_просто_sha(self):
        """Вывод ручного разбора смены #189, добытый проверкой: ни один из
        четырёх коммитов-исправлений не достижим из публичного репозитория.
        Напоминание, советующее закрыть тикет по коммиту ветки разработки,
        воспроизводило бы ровно ту ошибку, которую разбор обошёл."""
        text = tcp.proposal_for(["github#7"])
        assert "ДОСТИЖИМО" in text
        assert "merge-base" in text, "условие названо, а способ проверить — нет"

    def test_сказано_что_тикет_мог_быть_шире_задачи(self):
        text = tcp.proposal_for(["github#7"])
        assert "БОЛЬШЕ, чем закрыла задача" in text

    def test_читается_из_поля_задачи(self):
        text = tcp.proposal_for_task({"tracker_refs": '["gitlab#17"]'})
        assert text is not None and "gitlab#17" in text


class TestПриЗакрытииНЕТСЕТИ:
    """AC-3, отрицательная половина и главный тест файла.

    Проверка на подстроку доказала бы, что текст такой. Глушение сокета
    доказывает, что тикет остался нетронут.
    """

    @pytest.fixture
    def сеть_отключена(self, monkeypatch):
        def отказ(*_a, **_kw):
            raise AssertionError(
                "путь закрытия задачи полез в сеть — тикет не смеет закрываться "
                "автоматически, и закрытие не смеет зависеть от доступности трекера"
            )

        monkeypatch.setattr(socket, "socket", отказ)
        monkeypatch.setattr(socket, "create_connection", отказ)
        return True

    def test_напоминание_собирается_без_единого_сокета(self, сеть_отключена):
        got = closure_reminders.reminders_at_close("t", None, {"tracker_refs": '["github#7"]'})
        assert any("github#7" in note for note in got)

    def test_и_без_привязки_тоже(self, сеть_отключена):
        assert closure_reminders.reminders_at_close("t", None, {}) == []


class TestФреймворкНеХранитСОСТОЯНИЯТикета:
    """Структурная половина того же требования.

    Нечего закрывать автоматически, если состояния тикета нет вовсе: связь —
    это ССЫЛКА, а не копия чужой строки. Проверяется схемой, а не намерением,
    потому что намерение не переживает следующую миграцию.
    """

    def test_у_задачи_ровно_одно_поле_про_трекер(self):
        from backend_schema import SCHEMA_SQL

        tasks_ddl = SCHEMA_SQL[SCHEMA_SQL.index("CREATE TABLE IF NOT EXISTS tasks") :]
        tasks_ddl = tasks_ddl[: tasks_ddl.index(");")]
        for forbidden in ("ticket_state", "ticket_status", "issue_state", "ticket_closed"):
            assert forbidden not in tasks_ddl, (
                f"появилось поле {forbidden}: фреймворк начал хранить СОСТОЯНИЕ чужого "
                "тикета, а значит появился и соблазн его синхронизировать"
            )
        assert "tracker_refs" in tasks_ddl

    def test_модуль_напоминания_не_импортирует_сети(self):
        """Читается ИСХОДНИК: модуль, которому незачем знать про сеть, не должен
        уметь в неё выйти даже случайно."""
        source = (_REPO / "scripts" / "tracker_closure_proposal.py").read_text(encoding="utf-8")
        for banned in ("import socket", "import http", "import urllib", "requests"):
            assert banned not in source
