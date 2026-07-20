"""Ни одна фикстура не имеет права объявлять схему сама — по ЛЮБОЙ таблице.

Механический гейт вместо разовой правки (память #236). Обоснование — дважды
оплаченный опыт, оба раза на verification_runs:

  1. l26-verify-git-diff-wire добавила две колонки, и это потребовало ручной
     правки девяти рукописных блоков в тестах;
  2. verify-no-test-mapped-dead-end (сессия #119) закодировала признак как
     scope='no-tests-expected'. Двадцать тестов были ЗЕЛЁНЫМИ, а на живой БД
     падала КАЖДАЯ запись: в рукописных DDL не было
     CHECK(scope IN ('lightweight','standard','high','critical','manual')).

Копия схемы в тесте доказывает соответствие копии, а не продакшену, и
расходится МОЛЧА. Этот тест делает расхождение громким: он не просит писать
фикстуры в каком-то стиле, он лишь запрещает им отличаться от
backend_schema.SCHEMA_SQL.

ЧТО ИЗМЕНИЛОСЬ В СЕССИИ #120. Гейт покрывал ОДНУ таблицу из девятнадцати.
Механизм расхождения у остальных ровно тот же, а проверялись они ничем.
Теперь список таблиц ВЫВОДИТСЯ из SCHEMA_SQL: перечислить их здесь руками
значило бы завести ту самую рукописную копию схемы, только этажом выше
(конвенция #214 — списки объектов схемы выводить, а не хардкодить).

Разведка перед расширением показала, что живого дрейфа сегодня нет. Ценность
гейта поэтому не в починке, а в УДЕРЖАНИИ: он ловит следующую фикстуру, а не
исправляет прошлые.
"""

from __future__ import annotations

import ast
import bisect
import os
import re
import sqlite3
from functools import lru_cache

import pytest

from conftest import VERIFICATION_RUNS_DDL, canonical_ddl

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Тесты миграций ОБЯЗАНЫ объявлять исторические схемы: они прогоняют апгрейд
# v1 -> v2 -> v3 и потому создают заведомо СТАРУЮ таблицу, чтобы было что
# мигрировать. Привести их к канону значило бы уничтожить смысл теста —
# миграция с канона на канон не проверяет ничего.
#
# Исключение объявлено ПОИМЁННО и с причиной, а не сделано молчаливым
# пропуском: список файлов, которым можно расходиться, обязан быть коротким и
# читаемым, иначе он тихо станет способом обойти гейт.
_HISTORICAL_SCHEMA_FILES = {
    "test_migrations.py",  # V1_SCHEMA/V2_SCHEMA — вход миграционного прогона
}

# ПОМЕТКА НА МЕСТЕ, а не список файлов. Храповик сессии #120 держал семь узких
# фикстур; сессия #121 их разобрала и обнаружила, что они РАЗНОРОДНЫ:
#
#   пять были настоящим дрейфом и переведены на canonical_ddl. Одна из них
#   (test_risk_l3_trigger/reviews) прикрывала живой дефект: тест утверждал, что
#   run_type='l3' засчитывается, и был зелёным ТОЛЬКО потому, что в фикстуре не
#   было CHECK(run_type IN ('L1','L2','L3')). В проде такая строка не
#   вставляется вовсе — тест покрывал недостижимую ветку;
#
#   две — заведомо ИСТОРИЧЕСКИЕ схемы: они строят БД формы v31/pre-v34, чтобы
#   было что мигрировать. Привести их к канону значит уничтожить смысл теста.
#
# Файловый список для второго класса не годится: оба файла СМЕШИВАЮТ канонные и
# исторические блоки. Поэтому исключение объявляется у самого блока строкой
#
#     # ddl-parity: historical — <зачем здесь именно старая схема>
#
# на строке блока или в двух строках над ней. Причина обязательна и проверяется:
# голая пометка исключением не является, иначе она станет тихим способом обойти
# гейт. Пометка стоит там, где её увидит правящий фикстуру, — в отличие от
# списка в чужом файле, куда никто не заглядывает.
_HISTORICAL_MARKER = re.compile(r"ddl-parity:\s*historical\s*[-—–]\s*(\S.*?)\s*$", re.MULTILINE)

# Причина короче этого — не причина, а отписка вроде «так надо».
_MIN_REASON_CHARS = 15

# Пометка действует на блок, к преамбуле которого она примыкает, — см.
# _is_marked_historical. Расстояние в строках не задаётся: оно зависит от
# форматирования вызова, и любое фиксированное число было бы либо слепым, либо
# дырой.

# Блок такого размера — заглушка под внешний ключ: таблица существует как цель
# REFERENCES, в неё никогда не пишут, и полная схема там была бы шумом.
_STUB_MAX_COLUMNS = 2

# Число колонок неизвестно: DDL не исполнился. НЕ ноль — иначе блок молча
# получил бы освобождение по правилу заглушки. См. _column_count.
_COLUMNS_UNKNOWN = -1


def _schema_tables() -> list[str]:
    """Имена таблиц, ВЫВЕДЕННЫЕ из SCHEMA_SQL.

    Захардкоженный список здесь был бы тем же дефектом, против которого
    написан весь файл: он расходился бы с продакшеном молча, и гейт перестал
    бы замечать таблицу, добавленную после его написания.
    """
    import sys

    scripts = os.path.abspath(os.path.join(_TESTS_DIR, "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from backend_schema import SCHEMA_SQL

    return sorted(set(re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([a-z_]+)", SCHEMA_SQL)))


def _iter_ddl_blocks(text: str, table: str):
    """Выдать `(смещение, блок)` для каждого `CREATE TABLE <table> (...)`.

    Смещение нужно, чтобы найти пометку `ddl-parity: historical` рядом с
    конкретным блоком: в одном файле законно соседствуют канонный и намеренно
    исторический — освобождать файл целиком было бы слишком грубо.

    Разбор по БАЛАНСУ СКОБОК.

    Регулярка с `(.*?)` здесь неприменима: определения содержат вложенные
    скобки (CHECK(...), DEFAULT (...)), и нежадный поиск обрывается на первой
    же внутренней. Именно так моя разведочная регулярка «нашла» в одном файле
    расхождение, которого нет.
    """
    for m in re.finditer(rf"CREATE TABLE (?:IF NOT EXISTS )?{table}\s*\(", text):
        start = m.start()
        open_paren = text.index("(", start)
        depth, i = 0, open_paren
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield start, text[start : i + 1]


@lru_cache(maxsize=None)
def _statement_lines(text: str) -> tuple[int, ...] | None:
    """Строки (1-based) начал ВСЕХ инструкций файла, либо None если он не разбирается.

    None — не «пусто», а «не знаю»: вызывающий обязан трактовать его как отказ
    в освобождении. Файл, который не является валидным Python, не имеет права
    молча выключать гейт.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    return tuple(sorted({n.lineno for n in ast.walk(tree) if isinstance(n, ast.stmt)}))


@lru_cache(maxsize=None)
def _string_line_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Строчные диапазоны (1-based, включительно) ВСЕХ строковых литералов файла.

    Нужны, чтобы отличить пустую строку в КОДЕ от пустой строки ВНУТРИ DDL.
    Первая означает, что посреди выражения оказался чужой текст, и привязку
    пометки рвёт; вторая — просто форматирование SQL, и рвать по ней значило
    бы завести ложное падение на совершенно законной фикстуре.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return ()
    return tuple(
        (n.lineno, n.end_lineno or n.lineno)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    )


def _is_marked_historical(text: str, offset: int) -> bool:
    """Есть ли у блока по смещению объявленная причина быть старой схемой.

    ПРИВЯЗКА СТРУКТУРНАЯ, а не текстовая. Прежняя версия шла вверх от блока и
    считала продолжением ЛЮБУЮ строку, оканчивающуюся на «(». Этого достаточно,
    чтобы пометка перепрыгнула через несвязанную цепочку `wrap_a(`/`wrap_b(`/
    `wrap_c(` и освободила ДАЛЬНИЙ, реально расходящийся блок: дрейф есть, гейт
    молчит. Дефект найден состязательным ревью в аудите #122 — то есть гейт
    против молчаливого расхождения расходился молча сам.

    Теперь блок сначала сопоставляется с ИНСТРУКЦИЕЙ, внутри которой лежит
    (ast: последнее начало инструкции на строке блока или выше), и пометка
    ищется ровно в двух местах:

      1. в собственных строках этой инструкции — от её начала до строки блока;
      2. в непрерывном ряду комментариев и пустых строк НАД её началом.

    Пустая строка КОДА между началом инструкции и блоком привязку рвёт: у
    `conn.execute(` с DDL следующей строкой её не бывает, а вот вставленный
    посреди выражения чужой код читается именно так — это и есть цепочка
    обёрток из воспроизведения. Пустые строки ВНУТРИ строкового литерала не
    в счёт: это форматирование самого SQL, и рвать по ним значило бы завести
    ложное падение вместо закрытого молчания (см. _string_line_spans).

    Фиксированного окна в N строк здесь нет намеренно: расстояние до пометки
    зависит от форматирования вызова, и любое число было бы либо слепым, либо
    дырой.
    """
    lines = text.split("\n")
    block_line = text.count("\n", 0, offset)  # 0-based

    starts = _statement_lines(text)
    if starts is None:
        return False  # fail-closed: неразбираемый файл не освобождает ничего
    idx = bisect.bisect_right(starts, block_line + 1) - 1
    if idx < 0:
        return False
    stmt_line = starts[idx] - 1  # 0-based начало инструкции с блоком

    spans = _string_line_spans(text)
    for i in range(stmt_line + 1, block_line):
        if lines[i].strip():
            continue
        if any(lo <= i + 1 <= hi for lo, hi in spans):
            continue  # пустая строка ВНУТРИ литерала — это форматирование SQL
        return False  # пустая строка в КОДЕ посреди инструкции рвёт привязку

    def _reason(line: str) -> bool:
        m = _HISTORICAL_MARKER.search(line)
        return bool(m and len(m.group(1).strip()) >= _MIN_REASON_CHARS)

    if any(_reason(lines[i]) for i in range(stmt_line, block_line + 1)):
        return True

    for i in range(stmt_line - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped and not stripped.startswith("#"):
            return False  # чужая инструкция обрывает преамбулу
        if _reason(lines[i]):
            return True
    return False


@lru_cache(maxsize=None)
def _column_count(block: str) -> int:
    """Число колонок ПО PRAGMA table_info, а не по запятым.

    Разбиение по запятым не исключало SQL-комментарии «--», которыми канон
    насыщен, и врало ровно там, где от него зависит освобождение: канонический
    verification_runs давал 18 колонок против 13 настоящих, session_usage_metrics
    — 10 против 9. Законная двухколоночная заглушка с поясняющим комментарием,
    содержащим запятую, посчиталась бы четырёхколоночной и дала бы ЛОЖНОЕ
    падение.

    Источник истины — сам sqlite (тот же довод, по которому список таблиц
    выводится из SCHEMA_SQL, а не хардкодится, — конвенция #214).

    Неисполнимый DDL даёт _COLUMNS_UNKNOWN, а не ноль: правило заглушки его
    тогда НЕ освобождает. Молчаливое освобождение при ошибке разбора — ровно
    тот класс дефекта, против которого написан этот файл.
    """
    try:
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute(block)
            row = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
            if row is None:
                return _COLUMNS_UNKNOWN
            cols = conn.execute(f'PRAGMA table_info("{row[0]}")').fetchall()
            return len(cols) if cols else _COLUMNS_UNKNOWN
        finally:
            conn.close()
    except (sqlite3.Error, sqlite3.Warning, ValueError):
        return _COLUMNS_UNKNOWN


def _test_files() -> list[str]:
    return [
        os.path.join(_TESTS_DIR, name)
        for name in sorted(os.listdir(_TESTS_DIR))
        if name.startswith("test_") and name.endswith(".py")
    ]


def _normalize(sql: str) -> str:
    """Сравнивать по существу: пробелы и отступы значения не имеют."""
    return re.sub(r"\s+", " ", sql).strip()


def _drift(path: str, table: str) -> str | None:
    """Вернуть текст расхождения для (файл, таблица) или None."""
    if os.path.basename(path) in _HISTORICAL_SCHEMA_FILES:
        return None
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    canonical = _normalize(canonical_ddl(table).rstrip(";").rstrip())
    for offset, block in _iter_ddl_blocks(text, table):
        if 0 <= _column_count(block) <= _STUB_MAX_COLUMNS:
            continue  # заглушка под внешний ключ (_COLUMNS_UNKNOWN сюда НЕ попадает)
        if _is_marked_historical(text, offset):
            continue  # объявленная старая схема — см. _HISTORICAL_MARKER
        if _normalize(block) != canonical:
            return (
                f"{os.path.basename(path)} объявляет {table} своей копией схемы. "
                "Копия расходится молча — бери DDL из conftest: "
                f"`from conftest import canonical_ddl` -> canonical_ddl({table!r}). "
                f"Расхождение:\n  фикстура: {_normalize(block)[:300]}\n"
                f"  канон:    {canonical[:300]}"
            )
    return None


@pytest.mark.parametrize("table", _schema_tables())
def test_no_test_file_declares_this_table_by_hand(table):
    """AC1: параметризация по ВСЕМ таблицам SCHEMA_SQL, а не по одной.

    Параметр — таблица, а не файл: имя упавшего параметра тогда сразу
    называет, ЧТО разошлось, а сообщение называет где.
    """
    drifted = [d for d in (_drift(p, table) for p in _test_files()) if d]
    assert not drifted, "\n\n".join(drifted)


# --- AC2: гейт ПРОВЕРЕН, а не только написан ---------------------------------


class TestTheGateActuallyCatchesDrift:
    """Гейт, который никогда не ловил расхождения, — это гейт-гипотеза.

    Живого дрейфа в репозитории нет (разведка сессии #120), поэтому основной
    тест выше зелёный по причине «нечего ловить». Отличить это от «сломан и
    не ловит ничего» можно только внесённым расхождением.
    """

    def _canonical_block(self, table: str) -> str:
        return canonical_ddl(table).rstrip(";").rstrip()

    def test_a_missing_column_is_caught(self, tmp_path):
        """Фикстура ОТСТАЛА от прода — сценарий 68 падений «no such column»."""
        block = self._canonical_block("sessions")
        crippled = re.sub(r",\s*[a-z_]+ TEXT[^,)]*(?=[,)])", "", block, count=1)
        assert crippled != block, "не удалось изготовить расхождение — тест бессмыслен"
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{crippled};"""\n', encoding="utf-8")
        assert _drift(str(f), "sessions") is not None

    def test_a_dropped_constraint_is_caught(self, tmp_path):
        """Фикстура БЕДНЕЕ прода — сценарий 20 зелёных тестов при сломанной фиче.

        Опаснее предыдущего: он не падает вообще, он молча врёт.
        """
        block = self._canonical_block("verification_runs")
        # `IN` и открывающая скобка разделены переносом строки — пробел здесь
        # был бы ровно тем допущением о форматировании, из-за которого гейты и
        # слепнут.
        crippled = re.sub(r"\s*CHECK\(scope IN\s*\([^)]*\)\)", "", block, count=1)
        assert crippled != block, "не удалось убрать CHECK — тест бессмыслен"
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{crippled};"""\n', encoding="utf-8")
        assert _drift(str(f), "verification_runs") is not None

    def test_an_extra_column_is_caught(self, tmp_path):
        """Расхождение в ДРУГУЮ сторону: тест создаёт то, чего нет в проде.

        Эту сторону не заметил бы никто — тесты бы проходили, а прод не имел
        бы колонки, на которую они опираются.
        """
        block = self._canonical_block("epics")
        inflated = block[: block.rindex(")")] + ", invented_column TEXT)"
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{inflated};"""\n', encoding="utf-8")
        assert _drift(str(f), "epics") is not None

    def test_an_identical_copy_is_not_flagged(self, tmp_path):
        """НЕГАТИВНЫЙ: точная копия канона расхождением не является."""
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{self._canonical_block("epics")};"""\n', encoding="utf-8")
        assert _drift(str(f), "epics") is None

    def test_whitespace_differences_are_not_drift(self, tmp_path):
        """НЕГАТИВНЫЙ: переформатирование не должно ронять сборку."""
        squashed = re.sub(r"\s+", " ", self._canonical_block("epics"))
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{squashed};"""\n', encoding="utf-8")
        assert _drift(str(f), "epics") is None


# --- AC5: исключения объявлены, а не подразумеваются -------------------------


class TestDeclaredExceptions:
    def test_fk_stub_is_allowed(self, tmp_path):
        """Таблица-цель внешнего ключа объявляется минимумом, и это законно."""
        f = tmp_path / "test_fake.py"
        f.write_text(
            'S = """CREATE TABLE IF NOT EXISTS epics (id INTEGER PRIMARY KEY);"""\n',
            encoding="utf-8",
        )
        assert _drift(str(f), "epics") is None

    def test_migration_fixtures_are_exempt_by_name(self):
        """Исторические схемы — вход миграционного прогона, а не дрейф."""
        assert "test_migrations.py" in _HISTORICAL_SCHEMA_FILES

    def test_the_exemption_list_stays_short(self):
        """Список исключений — способ обойти гейт, если ему дать разрастись.

        Порог намеренно жёсткий: расширять его придётся осознанно, с правкой
        этого теста и объяснением, а не походя.
        """
        assert len(_HISTORICAL_SCHEMA_FILES) <= 2, (
            f"исключений стало {len(_HISTORICAL_SCHEMA_FILES)} — каждое обязано "
            "иметь причину в комментарии рядом"
        )

    def test_a_marked_block_is_exempt(self, tmp_path):
        """Объявленная старая схема — не дрейф."""
        block = re.sub(r",\s*model_id TEXT[^,)]*", "", canonical_ddl("sessions"))
        f = tmp_path / "test_fake.py"
        f.write_text(
            f'# ddl-parity: historical — вход миграционного прогона v31\nS = """{block}"""\n',
            encoding="utf-8",
        )
        assert _drift(str(f), "sessions") is None

    def test_a_marker_without_a_reason_does_not_exempt(self, tmp_path):
        """Голая пометка — способ обойти гейт, и потому не работает.

        Без этого теста `# ddl-parity: historical` стало бы однострочной
        индульгенцией, которую пишут не думая.
        """
        block = re.sub(r",\s*model_id TEXT[^,)]*", "", canonical_ddl("sessions"))
        f = tmp_path / "test_fake.py"
        f.write_text(
            f'# ddl-parity: historical — v31\nS = """{block}"""\n',
            encoding="utf-8",
        )
        assert _drift(str(f), "sessions") is not None

    def test_a_marker_does_not_leak_to_a_distant_block(self, tmp_path):
        """Пометка освобождает СВОЙ блок, а не весь файл.

        Иначе один исторический блок молча прикрыл бы настоящий дрейф ниже по
        файлу — ровно то, чего файловый список исключений и не умеет.
        """
        crippled = re.sub(r",\s*model_id TEXT[^,)]*", "", canonical_ddl("sessions"))
        f = tmp_path / "test_fake.py"
        f.write_text(
            "# ddl-parity: historical — вход миграционного прогона v31\n"
            f'HISTORICAL = """{canonical_ddl("sessions")}"""\n'
            + "\n" * 10
            + f'DRIFTED = """{crippled}"""\n',
            encoding="utf-8",
        )
        assert _drift(str(f), "sessions") is not None

    def test_markers_in_the_suite_stay_countable(self):
        """Пометок должно быть мало, и каждая — на виду.

        Порог намеренно жёсткий: следующая пометка потребует правки этого
        теста, то есть осознанного решения, а не привычки.

        Собственный файл гейта исключён: пометки в нём — не освобождение
        фикстуры, а образец в комментарии и полезная нагрузка тестов выше.
        """
        marked = []
        for path in _test_files():
            if os.path.basename(path) == os.path.basename(__file__):
                continue
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for m in _HISTORICAL_MARKER.finditer(text):
                marked.append(f"{os.path.basename(path)}: {m.group(1)[:60]}")
        # Порог поднят с 4 до 5 ОСОЗНАННО, в задаче
        # ddl-parity-marker-leak-and-column-miscount: пятая пометка не новая
        # индульгенция, а ЛЕГАЛИЗАЦИЯ уже существовавшего освобождения. В
        # test_reasoning_steps.py стоял комментарий «Same reason as events
        # above», который читался как объявленное исключение, но пометки не
        # содержал; блок выживал случайно, по порогу заглушки. Число здесь —
        # бюджет обхода гейта, и расти оно обязано с объяснением, как это.
        assert len(marked) <= 5, (
            f"исторических пометок стало {len(marked)} — каждая обязана быть "
            f"осознанной, а не привычкой:\n" + "\n".join(marked)
        )

    def test_migrations_file_really_declares_an_older_schema(self):
        """Страховка от протухшего исключения.

        Если test_migrations.py однажды перестанет объявлять старую схему,
        исключение станет дырой, прикрывающей обычный дрейф.
        """
        path = os.path.join(_TESTS_DIR, "test_migrations.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        assert "V1_SCHEMA" in text, (
            "test_migrations.py больше не объявляет историческую схему — "
            "исключение из _HISTORICAL_SCHEMA_FILES надо снять"
        )


# --- Регрессия аудита #122: пометка не дотягивается до чужого блока ----------


class TestTheMarkerCannotReachAnotherBlock:
    """Дефект, найденный состязательным ревью в аудите #122.

    Обратный обход преамбулы считал продолжением любую строку, оканчивающуюся
    на «(», и потому пометка перепрыгивала через несвязанный код к ДАЛЬНЕМУ,
    реально расходящемуся блоку.

    Тест `test_a_marker_does_not_leak_to_a_distant_block` выше давал ЛОЖНУЮ
    УВЕРЕННОСТЬ, что дыра закрыта: между пометкой и вторым блоком он клал SQL
    первого, а на такой строке обход честно обрывался. Цепочку
    скобко-открывающих строк он не проверял никогда — при том что стиль этот в
    репозитории обычен (`@pytest.mark.parametrize(`, вложенные конструкторы).

    Поэтому расхождение подсаживается здесь в ХУДШЕЙ форме, а не в первой
    пришедшей: вопрос не «ловит ли гейт мой пример», а «какой вход мой обход
    ПРИМЕТ ЗА ПРОДОЛЖЕНИЕ».
    """

    _MARKER = "# ddl-parity: historical — вход миграционного прогона v31\n"

    def _drifted_epics(self) -> str:
        block = canonical_ddl("epics").rstrip(";").rstrip()
        crippled = re.sub(r",\s*description TEXT", "", block, count=1)
        assert crippled != block, "не удалось изготовить расхождение — тест бессмыслен"
        return crippled

    def _verdict(self, tmp_path, source: str):
        f = tmp_path / "test_fake.py"
        f.write_text(source, encoding="utf-8")
        return _drift(str(f), "epics")

    def test_a_chain_of_open_parens_does_not_carry_the_marker(self, tmp_path):
        """ВОСПРОИЗВЕДЕНИЕ ИЗ АУДИТА. Три несвязанные обёртки подряд.

        Файл намеренно НЕ является валидным Python — ровно так выглядел
        пробник ревьюера. Освобождение здесь недопустимо по двум независимым
        причинам: обёртки не относятся к блоку, и разбор файла невозможен.
        """
        src = self._MARKER + f'wrap_a(\nwrap_b(\nwrap_c(\n\nD = """{self._drifted_epics()};"""\n'
        assert self._verdict(tmp_path, src) is not None

    def test_the_same_chain_as_valid_python_also_does_not_carry_it(self, tmp_path):
        """Та же цепочка, но синтаксически корректная и ЗАМКНУТАЯ.

        Без этого теста починка опиралась бы только на отказ разбора, то есть
        закрывала бы форму пробника, а не сам дефект: цепочку легко записать
        так, что файл разбирается.
        """
        src = (
            self._MARKER + "wrap_a(\n  wrap_b(\n    wrap_c(\n\n"
            f'      """{self._drifted_epics()};"""\n    )))\n'
        )
        assert self._verdict(tmp_path, src) is not None

    def test_a_single_wrapper_with_a_blank_line_does_not_carry_it(self, tmp_path):
        """Одиночная обёртка — тот же дефект в минимальной форме.

        Цепочки из трёх недостаточно: если чинить «длинные цепочки», дыра
        останется на цепочке длиной один.
        """
        src = self._MARKER + f'conn.execute(\n\n    """{self._drifted_epics()};"""\n)\n'
        assert self._verdict(tmp_path, src) is not None

    def test_a_foreign_statement_between_marker_and_block_stops_it(self, tmp_path):
        src = self._MARKER + f'x = 1\n\nD = """{self._drifted_epics()};"""\n'
        assert self._verdict(tmp_path, src) is not None

    def test_the_legitimate_shape_still_exempts_its_own_block(self, tmp_path):
        """НЕГАТИВНЫЙ и обязательный: починка не имеет права запретить всё.

        Гейт, который перестал освобождать законную пометку, вынудит писать
        исключения списком файлов — то есть вернёт ровно ту грубость, ради
        отказа от которой пометка и заведена.
        """
        src = self._MARKER + f'conn.execute(\n    """{self._drifted_epics()};"""\n)\n'
        assert self._verdict(tmp_path, src) is None

    def test_a_blank_line_inside_the_ddl_literal_is_not_a_break(self, tmp_path):
        """Граница правила «пустая строка рвёт привязку», проверенная явно.

        Правило существует ради цепочки обёрток, но пустые строки бывают и
        внутри самого DDL — это форматирование SQL, а не чужой код. Считать их
        разрывом значило бы завести ЛОЖНОЕ падение на законной фикстуре, то
        есть заменить одну молчаливую ошибку другой, громкой и тоже неверной.
        """
        src = self._MARKER + f'conn.execute(\n    """\n\n{self._drifted_epics()};\n"""\n)\n'
        assert self._verdict(tmp_path, src) is None

    def test_an_unparseable_file_exempts_nothing(self, tmp_path):
        """FAIL-CLOSED (ось «а»): файл не разбирается — освобождений нет.

        Иначе достаточно сломать синтаксис, чтобы выключить гейт.
        """
        src = self._MARKER + f'D = """{self._drifted_epics()};"""\ndef (((\n'
        assert _statement_lines(src) is None
        assert self._verdict(tmp_path, src) is not None


# --- Счётчик колонок: PRAGMA, а не регулярка ---------------------------------


class TestColumnCountComesFromSqlite:
    """Разбиение по запятым врало на SQL-комментариях, которыми канон насыщен.

    От счётчика зависит освобождение по правилу заглушки под внешний ключ —
    то есть врущий примитив даёт и ложное освобождение, и ложное падение.
    """

    @pytest.mark.parametrize(
        "table,expected",
        [("verification_runs", 13), ("session_usage_metrics", 9)],
    )
    def test_the_measured_miscount_is_pinned(self, table, expected):
        """Замер из карточки закреплён числом: регулярка давала 18 и 10."""
        block = canonical_ddl(table).rstrip(";").rstrip()
        assert _column_count(block) == expected

    def test_every_canonical_table_is_countable(self):
        """Если канон какой-то таблицы перестанет исполняться, счётчик вернёт
        _COLUMNS_UNKNOWN — и правило заглушки начнёт вести себя иначе. Такое
        обязано быть громким."""
        bad = [
            t for t in _schema_tables() if _column_count(canonical_ddl(t).rstrip(";").rstrip()) < 1
        ]
        assert not bad, f"канон этих таблиц не исполняется в sqlite: {bad}"

    def test_a_stub_with_a_comma_inside_a_comment_stays_exempt(self, tmp_path):
        """ЛОЖНОЕ ПАДЕНИЕ, которое давала регулярка.

        Двухколоночная заглушка законна. Регулярка считала запятую внутри
        `--` комментария разделителем колонок и насчитывала четыре, лишая
        заглушку освобождения.
        """
        # Имя таблицы подставляется НАМЕРЕННО: записанное литералом рядом с
        # объявлением таблицы, оно сделало бы этот тест фикстурой-копией схемы,
        # и гейт поймал бы собственный файл. Он это и сделал при первом
        # прогоне — то есть заодно доказал, что ловит.
        stub = (
            f"CREATE TABLE IF NOT EXISTS {'epics'} (\n"
            "    id INTEGER PRIMARY KEY,  -- цель REFERENCES, сюда не пишут\n"
            "    slug TEXT  -- нужен, чтобы связать эпик, задачу и историю\n"
            ")"
        )
        assert _column_count(stub) == 2, "заглушка обязана считаться двухколоночной"
        f = tmp_path / "test_fake.py"
        f.write_text(f'S = """{stub};"""\n', encoding="utf-8")
        assert _drift(str(f), "epics") is None

    def test_the_unparseable_blocks_in_the_suite_stay_a_named_list(self):
        """ХРАПОВИК с поимённым списком, а не «сегодня и так работает».

        Извлечение блока идёт по тексту файла, поэтому у фикстур, собранных
        КОНКАТЕНАЦИЕЙ строковых литералов, в блок попадают кавычки и переносы:
        такой DDL sqlite не исполняет, и счётчик честно отвечает «не знаю».

        Сегодня таких блоков ровно два, и оба ПОМЕЧЕНЫ историческими — то есть
        освобождены пометкой, а не счётчиком, и ничего не теряют. Опасен
        ТРЕТИЙ: непомеченная двухколоночная заглушка, записанная тем же стилем,
        потеряет освобождение и даст ложное падение. Список поимённый, чтобы
        появление третьего было громким и потребовало решения, а не прошло
        незамеченным под общим «блоков стало больше».
        """
        known = {
            ("test_reasoning_steps.py", "events"),
            ("test_v34_hashchain_backfill.py", "events"),
        }
        found = set()
        for path in _test_files():
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for table in _schema_tables():
                for offset, block in _iter_ddl_blocks(text, table):
                    if _column_count(block) >= 0:
                        continue
                    found.add((os.path.basename(path), table))
                    assert _is_marked_historical(text, offset), (
                        f"{os.path.basename(path)}: блок {table} не разбирается sqlite И не "
                        "помечен историческим — он потерял освобождение по правилу заглушки "
                        "молча. Либо приведи фикстуру к canonical_ddl, либо объяви пометку."
                    )
        assert found == known, (
            f"состав неразбираемых блоков изменился: появились {sorted(found - known)}, "
            f"исчезли {sorted(known - found)}. Это осознанное решение, а не правка числа."
        )

    def test_unparseable_ddl_is_not_treated_as_a_stub(self, tmp_path):
        """FAIL-CLOSED (ось «б»): неисполнимый DDL освобождения НЕ получает.

        Ноль колонок и «не смог посчитать» — разные вещи. Смешать их значит
        отдать освобождение любому синтаксически битому блоку.
        """
        assert _column_count("CREATE TABLE broken (id INTEGER,,,") == _COLUMNS_UNKNOWN
        assert _COLUMNS_UNKNOWN < 0, "признак «не знаю» обязан не попадать в диапазон заглушки"


# --- AC6: гейт не выродился в пустышку ---------------------------------------


class TestTheGateIsNotHollow:
    @pytest.mark.parametrize("table", _schema_tables())
    def test_canonical_ddl_is_non_empty_for_every_table(self, table):
        """Без этого гейт мог бы сравнивать пустое с пустым и считать себя
        выполненным — тот же класс молчаливого зелёного, против которого он
        написан."""
        ddl = canonical_ddl(table)
        assert ddl.strip().endswith(");"), f"канон для {table} обрезан: {ddl[-80:]!r}"
        assert _column_count(ddl.rstrip(";").rstrip()) >= 1

    def test_the_table_list_is_not_empty(self):
        tables = _schema_tables()
        assert len(tables) >= 15, f"вывод списка таблиц сломан: {tables}"
        assert "verification_runs" in tables

    def test_the_scan_actually_reads_test_files(self):
        assert len(_test_files()) > 50

    def test_canonical_ddl_actually_carries_constraints(self):
        assert "CHECK(scope IN" in VERIFICATION_RUNS_DDL
        assert "no_tests_declared" in VERIFICATION_RUNS_DDL
        assert VERIFICATION_RUNS_DDL.strip().endswith(");")

    def test_canonical_ddl_helper_rejects_unknown_table(self):
        with pytest.raises(ValueError):
            canonical_ddl("no_such_table_anywhere")
