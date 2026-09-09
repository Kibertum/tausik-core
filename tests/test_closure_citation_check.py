"""Цитаты закрытия проверяются в момент, когда их ещё можно поправить.

ДЕТЕКТОР УЖЕ БЫЛ, И В ЭТОМ ВЕСЬ СМЫСЛ. `audit_closure_evidence` на 1404
закрытых задачах и 4026 цитатах сообщает: 20 называют тест, которого git НИКОГДА
не имел, и 31 — тест, исчезнувший ПОСЛЕ закрытия. Не хватало не механизма, а
ВОПРОСА: детектор работает по требованию, и никто не звал его в момент, когда
цитата писалась. Выдуманная ссылка узнаётся месяцы спустя, когда журнал
append-only и исправлять нечего.

НАСТОЯЩИЙ КЛАСС ДЕФЕКТА — НЕ ВЫДУМАННЫЙ ФАЙЛ, А ВЫДУМАННЫЙ ЧЛЕН. Проверено на
живых случаях: `tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath` —
файл настоящий, класса нет. Ссылка на несуществующий ФАЙЛ детектор чаще относит
к ILLUSTRATIVE (условное имя-пример), и это правильно: `tests/test_foo.py` в
прозе — не обещание.

ПОЧЕМУ СООБЩЕНИЕ, А НЕ БЛОК. Направление ошибки — пере-обнаружение: цитата может
не разрешиться, потому что файл ещё не закоммичен или имя приведено примером.
Блок здесь научил бы не цитировать вовсе, то есть уничтожил бы доказательность
ради её проверки.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import closure_citation_check as ccc  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/"]


class TestВыдуманнаяЦитатаНаходится:
    """AC-1 и AC-3."""

    @pytest.mark.parametrize(
        "ref",
        [
            pytest.param(
                "tests/test_ci_lanes_are_honest.py::TestNoLaneExcludesByPath",
                id="real_file_invented_class",
            ),
            pytest.param(
                "tests/test_red_history.py::test_i_made_this_up",
                id="real_file_invented_function",
            ),
        ],
    )
    def test_настоящий_файл_с_выдуманным_членом(self, ref):
        found = ccc.check_citations(str(_REPO), "t", f"AC-1: {ref}")
        assert found == [ref], f"выдуманная цитата не найдена: {found}"

    def test_предупреждение_называет_цитату_а_не_считает_её(self):
        """«2 цитаты не разрешились» отправляет читателя обратно в журнал
        искать какие — а этот поиск проверка и должна была сэкономить."""
        text = ccc.warning_for(
            str(_REPO), "t", "AC-1: tests/test_red_history.py::test_i_made_this_up"
        )
        assert "test_i_made_this_up" in text
        assert "never had" in text


class TestПроверкаНеСрабатываетВпустую:
    """AC-4. Проверка, срабатывающая всегда, — шум, который отключат."""

    def test_верная_цитата_не_даёт_предупреждения(self):
        good = "tests/test_red_history.py::TestУзелТочный"
        assert ccc.check_citations(str(_REPO), "t", f"AC-1: {good}") == []
        assert ccc.warning_for(str(_REPO), "t", f"AC-1: {good}") == ""

    @pytest.mark.parametrize(
        "notes",
        [
            pytest.param("закрыто, всё хорошо", id="prose_without_citations"),
            pytest.param("", id="empty"),
            pytest.param("AC-1: проверено вручную, теста нет", id="explicitly_manual"),
        ],
    )
    def test_заметки_без_цитат_молчат(self, notes):
        """Отсутствие цитаты — предмет ДРУГОГО предупреждения на пути закрытия
        (чеклист верификации). Ругаться здесь значило бы сказать одно и то же
        дважды разными словами, и читатель перестал бы слушать оба."""
        assert ccc.warning_for(str(_REPO), "t", notes) == ""

    def test_имя_примера_не_считается_выдумкой(self):
        """AC-3. ILLUSTRATIVE и NEVER_EXISTED — разные исходы, и сливать их
        значило бы ругаться на прозу, которая ничего не обещала."""
        assert ccc.check_citations(str(_REPO), "t", "AC-1: tests/test_foo.py::test_bar") == []


class TestПроверкаНеЛомаетЗакрытие:
    """AC-2. Проверка, способная уронить закрытие, будет снята первой же."""

    def test_битый_корень_не_бросает(self, tmp_path):
        assert ccc.check_citations(str(tmp_path / "нет"), "t", "AC-1: tests/x.py::y") == []

    def test_мусор_вместо_заметок_не_бросает(self):
        for notes in ("", "\x00", "::::", "AC-1: ::"):
            assert isinstance(ccc.check_citations(str(_REPO), "t", notes), list)


class TestЦенаНазванаЧислом:
    """AC-5. Проверка идёт на КАЖДОМ закрытии."""

    def test_проверка_быстрее_четверти_секунды(self):
        notes = "AC-1: tests/test_red_history.py::TestУзелТочный"
        start = time.perf_counter()
        ccc.check_citations(str(_REPO), "t", notes)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.25, (
            f"{elapsed:.2f} с на закрытие — проверка, заметная на фоне тринадцати "
            "гейтов, будет выключена"
        )


class TestЗакрытиеДействительноЕёЗовёт:
    """Модуль, который работает и которого никто не зовёт, — тот самый класс,
    что этот релиз вычищает. Проверяется ВЫЗОВ, а не наличие функции."""

    def test_сборщик_напоминаний_действительно_её_зовёт(self):
        """ВЫЗОВОМ, а не чтением исходника. С v61 закрытие спрашивает не эту
        проверку напрямую, а `closure_reminders`, который задаёт оба вопроса
        момента закрытия; проверка живёт ровно постольку, поскольку он её зовёт.
        """
        import closure_reminders

        notes = "AC-1: ✓ tests/test_выдуманного_файла_нет.py::test_ничего"
        got = closure_reminders.reminders_at_close("t", notes, {})
        assert got, "сборщик молчит на заведомо испорченной цитате"
        assert any("test_выдуманного_файла_нет" in note for note in got)

    def test_напоминание_попадает_в_список_предупреждений(self):
        source = (_REPO / "scripts" / "service_task_done.py").read_text(encoding="utf-8")
        block = source[source.index("for note in reminders_at_close") :][:300]
        assert 'report["warnings"].append(note)' in block, (
            "напоминание вычисляется и никуда не кладётся"
        )
