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

import os
import re

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


def _is_marked_historical(text: str, offset: int) -> bool:
    """Есть ли у блока по смещению объявленная причина быть старой схемой.

    Пометка ищется в НЕПРЕРЫВНОЙ ПРЕАМБУЛЕ блока: вверх от его строки, пока
    идут комментарии, пустые строки и строка-открытие вызова (`conn.execute(`).
    Первая же содержательная строка обрывает поиск.

    Окном в N строк это делать нельзя. Причина занимает две строки, а сам
    CREATE TABLE обычно лежит внутри conn.execute(...) — то есть расстояние до
    пометки зависит от форматирования, и любое фиксированное N будет либо
    слепым, либо дырой, через которую пометка дотянется до чужого блока.
    """
    lines = text.split("\n")
    line_no = text.count("\n", 0, offset)
    i = line_no
    while i >= 0:
        stripped = lines[i].strip()
        m = _HISTORICAL_MARKER.search(lines[i])
        if m and len(m.group(1).strip()) >= _MIN_REASON_CHARS:
            return True
        if i == line_no or stripped == "" or stripped.startswith("#") or stripped.endswith("("):
            i -= 1
            continue
        return False
    return False


def _column_count(block: str) -> int:
    body = block[block.index("(") + 1 : block.rindex(")")]
    return len([c for c in re.split(r",(?![^()]*\))", body) if c.strip()])


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
        if _column_count(block) <= _STUB_MAX_COLUMNS:
            continue  # заглушка под внешний ключ
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
        assert len(marked) <= 4, (
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
