"""Ссылка на тикет отвергается ПРИ ЗАПИСИ, а не оказывается мусором при чтении.

ГЛАВНЫЙ СЛУЧАЙ ЗДЕСЬ — ГОЛЫЙ НОМЕР, и он проверяется на настоящем столкновении
этого репозитория: GitHub #7 и GitLab #7 — РАЗНЫЕ тикеты, разных авторов, с
разными коммитами-исправлениями. Ссылка `#7` в поле задачи через полгода
отправила бы отвечающего не к тому человеку, и узнать об этом было бы неоткуда.

ВТОРАЯ ПОЛОВИНА — ЧТЕНИЕ, КОТОРОЕ НЕ ПАДАЕТ. Поле заведено ради долгов перед
людьми; если испорченное значение уронит закрытие задачи, оно станет новым
способом не закрыть работу, и первым же решением его выключат.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import tracker_ref  # noqa: E402


class TestФормаПринимаемого:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            pytest.param("github#7", "github#7", id="github"),
            pytest.param("gitlab#12", "gitlab#12", id="gitlab"),
            pytest.param("  gitlab#12  ", "gitlab#12", id="пробелы_обрезаются"),
            pytest.param("GitHub#8", "github#8", id="трекер_к_нижнему_регистру"),
            pytest.param("jira#PROJ-42", "jira#PROJ-42", id="нецифровой_идентификатор"),
            pytest.param("redmine#1", "redmine#1", id="произвольный_трекер"),
        ],
    )
    def test_короткая_ссылка(self, raw, expected):
        assert tracker_ref.normalise(raw) == expected

    def test_приводится_ТОЛЬКО_имя_трекера(self):
        """Обе половины ссылки проверяются ОДНИМ тестом, потому что утверждение
        одно: канонизация трогает трекер и не трогает идентификатор. `PROJ-42` и
        `proj-42` в одних трекерах один тикет, в других разные — угадывать за
        потребителя нечего."""
        assert tracker_ref.normalise("JIRA#Proj-42") == "jira#Proj-42"
        assert tracker_ref.normalise("jira#proj-42") == "jira#proj-42"

    def test_полный_адрес_не_трогается_даже_регистром(self):
        """URL возвращается побайтово. Отдельным утверждением, а не следствием:
        путь в адресе чувствителен к регистру, и приведение, законное для имени
        трекера, здесь сломало бы ссылку."""
        url = "https://GitLab.example/KIBERTUM/Core/-/issues/7"
        assert tracker_ref.normalise(url) == url
        assert tracker_ref.normalise(url.lower()) == url.lower()


class TestГолыйНомерОтвергнут:
    """Главный тест файла: два трекера этого репозитория, номера пересеклись."""

    @pytest.mark.parametrize("raw", ["7", "#7", " #12 "])
    def test_номер_без_трекера_отказ(self, raw):
        with pytest.raises(tracker_ref.TrackerRefError) as exc:
            tracker_ref.normalise(raw)
        assert "GitHub #7 и GitLab #7" in str(exc.value), (
            "отказ обязан НАЗВАТЬ столкновение, иначе читатель считает требование "
            "трекера формальностью и обойдёт его первым же URL"
        )

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param("", id="пусто"),
            pytest.param("   ", id="пробелы"),
            pytest.param("исправить баг в трекере", id="проза"),
            pytest.param("github #7", id="пробел_внутри"),
            pytest.param("ftp://tracker/7", id="не_http"),
        ],
    )
    def test_мусор_отвергается(self, raw):
        with pytest.raises(tracker_ref.TrackerRefError):
            tracker_ref.normalise(raw)

    def test_отказ_называет_верную_форму(self):
        """Отказ без указания, как надо, — тупик в лучшей формулировке."""
        with pytest.raises(tracker_ref.TrackerRefError) as exc:
            tracker_ref.normalise("чепуха")
        assert "github#7" in str(exc.value)


class TestСписок:
    def test_повторы_убираются_порядок_сохраняется(self):
        assert tracker_ref.normalise_all(["gitlab#12", "github#7", "GitLab#12"]) == [
            "gitlab#12",
            "github#7",
        ]

    def test_один_мусорный_элемент_отвергает_весь_список(self):
        """Записать половину списка молча — худший из исходов: задача ДУМАЕТ,
        что помнит тикет, а помнит не тот."""
        with pytest.raises(tracker_ref.TrackerRefError):
            tracker_ref.normalise_all(["github#7", "#8"])

    def test_пустой_список_допустим(self):
        assert tracker_ref.normalise_all([]) == []


class TestЧтениеИзКолонкиНеПадает:
    """Испорченное значение читается как ПУСТО. Иначе поле, заведённое ради
    долгов перед людьми, становится способом не закрыть задачу."""

    @pytest.mark.parametrize(
        "stored",
        [
            pytest.param(None, id="null"),
            pytest.param("", id="пустая_строка"),
            pytest.param("не json", id="не_json"),
            pytest.param('{"github": 7}', id="объект_вместо_списка"),
            pytest.param("[1, 2]", id="числа_вместо_строк"),
            pytest.param('["", null]', id="пустые_элементы"),
        ],
    )
    def test_испорченное_читается_как_пусто(self, stored):
        assert tracker_ref.loads(stored) == []

    def test_круговой_проход(self):
        refs = ["github#7", "gitlab#12"]
        assert tracker_ref.loads(tracker_ref.dumps(refs)) == refs

    def test_кириллица_в_адресе_переживает_запись(self):
        """`ensure_ascii=False` — не косметика: экранированный URL в поле,
        которое человек читает глазами при ответе автору, нечитаем."""
        url = "https://tracker.example/тикет/7"
        assert tracker_ref.loads(tracker_ref.dumps([url])) == [url]
        assert url in tracker_ref.dumps([url])
