"""Наш MCP-тред не должен опираться на примитивы, депрекируемые спекой.

l26-mcp-deprecation-audit. Спека MCP от 2026-07-28 (SEP-2577) депрекирует три
примитива: sampling, logging и roots. Депрекация annotation-only с гарантией не
менее 12 месяцев до удаления — это НЕ пожар. Но два P0-пункта роадмапа 2.0
построены именно на Roots, и прежде чем вкладывать в них человеко-недели, надо
ЗНАТЬ, а не предполагать, насколько тред затронут сегодня.

РЕЗУЛЬТАТ АУДИТА (сессия #121): вхождений в коде НОЛЬ. Три сервера
(project, brain, codebase-rag) регистрируют только list_tools, list_prompts,
list_resources и call_tool. Объявляемые возможности выводятся SDK из
зарегистрированных хендлеров, поэтому `get_capabilities()` на нашем сервере
возвращает `logging=None` — возможность не объявляется вовсе. Миграционная
нагрузка нулевая, как и предполагала оценка спеки для локальных stdio-серверов.

ПОЧЕМУ ЭТОТ ФАЙЛ СУЩЕСТВУЕТ. Вывод «не затронуто» — утверждение о ВЧЕРАШНЕМ
дереве. Без гейта он протухает на следующем коммите, и следующий, кто спросит,
будет искать заново (конвенция #236: разовую находку закрывать механическим
гейтом). Этот тест превращает результат аудита в свойство, которое нельзя
потерять молча.

РАЗБОР, А НЕ ТЕКСТ. Код проверяется AST: `create_message` в комментарии и
`session.create_message(...)` в коде — разные события, и текстовый поиск их не
различает. Документации МОЖНО упоминать депрекируемые примитивы (этот файл сам
их упоминает); запрещено ими ПОЛЬЗОВАТЬСЯ.

ОБЕЩАНИЕ ВЫШЕ ОДНАЖДЫ ОКАЗАЛОСЬ ШИРЕ КОДА (сессия #122, состязательное ревью).
Для `_code_usages` оно держалось, для второй половины файла — нет: литералы
протокола искались простым вхождением подстроки по сырым строкам, и честный
комментарий «# older clients still send "roots/list"; we ignore it» ронял
проверку. Заодно `_code_usages` флагует голое имя, из-за чего несвязанная
функция `list_roots(tree)` — правдоподобное имя вообще, а в MCP-сервере
терминология «roots» встречается и по другим поводам — давала ложное падение с
сообщением про депрекированный API.

ВЫБОР СДЕЛАН ЯВНО, а не оставлен подразумеваемым: обещание СОХРАНЕНО, а под него
приведён код. Литералы протокола ищутся теперь только среди строк, реально
участвующих в коде (комментарии в AST не попадают вовсе, докстроки исключены
поимённо), а обращения сужены до доступа к атрибуту. Обратный вариант —
признать строгость и урезать докстринг — отвергнут: гейт, падающий на
собственной документации, отключают, а отключённый гейт хуже отсутствующего,
потому что выглядит защитой.

СУЖЕНИЕ НЕ ИМЕЕТ ПРАВА ЗАВОДИТЬ СЛЕПОЕ ПЯТНО. Отказ от голого имени закрыт
веткой на прямой импорт: `from mcp.server.session import list_roots` поймается,
хотя доступа к атрибуту в нём нет. Иначе правка обменяла бы шумный гейт на
слепой, а это тот же дефект с другим знаком.
"""

from __future__ import annotations

import ast
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_ROOT, "harness")

# Имена API питоновского SDK `mcp`, через которые депрекируемые примитивы только
# и могут быть использованы. Проверены интроспекцией установленного пакета, а не
# выписаны из спеки по памяти: mcp.server.Server.set_logging_level и
# mcp.server.session.ServerSession.{create_message,list_roots,send_log_message}.
_DEPRECATED_ATTRS = {
    # sampling — сервер занимает модель клиента
    "create_message": "sampling",
    # logging — заменяется на stderr либо OpenTelemetry
    "set_logging_level": "logging",
    "send_log_message": "logging",
    # roots — заменяются параметрами тулов, resource URI или конфигом сервера
    "list_roots": "roots",
}

# Строки протокольного уровня. Ищутся отдельно и только ради полноты отчёта:
# найденная в коде, такая строка означала бы ручную сборку запроса в обход SDK.
_DEPRECATED_WIRE = {
    "sampling/createMessage": "sampling",
    "logging/setLevel": "logging",
    "notifications/message": "logging",
    "roots/list": "roots",
    "notifications/roots/list_changed": "roots",
}


def _mcp_sources() -> list[str]:
    """Питоновские исходники нашего MCP-треда.

    Сканируется harness/ — это ИСТОЧНИК. Профили IDE (.claude/, .cursor/ и
    прочие) из него генерируются, и проверять их значило бы проверять копию.
    """
    found = []
    for dirpath, dirs, files in os.walk(_HARNESS):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        if os.sep + "mcp" + os.sep not in dirpath + os.sep:
            continue
        found.extend(os.path.join(dirpath, f) for f in files if f.endswith(".py"))
    return sorted(found)


def _code_usages(path: str) -> list[tuple[int, str, str]]:
    """(строка, примитив, имя) для КАЖДОГО обращения к депрекируемому API.

    AST, а не поиск по тексту: упоминание в докстринге или комментарии — не
    использование, и гейт, который их не различает, будет либо слепым, либо
    падающим на собственной документации.
    """
    with open(path, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    hits = []
    for node in ast.walk(tree):
        # ТОЛЬКО доступ к атрибуту. Депрекируемые примитивы — всегда методы
        # объектов SDK (ServerSession, Server), и голое имя до них не дотянется,
        # не пройдя через атрибут. Раньше здесь ловился и ast.Name, из-за чего
        # несвязанная функция list_roots(tree) давала ложное падение с
        # сообщением про депрекированный API.
        if isinstance(node, ast.Attribute) and node.attr in _DEPRECATED_ATTRS:
            hits.append((node.lineno, _DEPRECATED_ATTRS[node.attr], node.attr))
        # Единственный способ добраться до примитива БЕЗ доступа к атрибуту —
        # импортировать имя напрямую. Без этой ветки сужение выше открыло бы
        # слепое пятно, то есть обменяло бы шумный гейт на слепой.
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _DEPRECATED_ATTRS:
                    hits.append((node.lineno, _DEPRECATED_ATTRS[alias.name], alias.name))
    return hits


def _docstring_constants(tree: ast.AST) -> set[int]:
    """id() строковых узлов, являющихся ДОКСТРОКАМИ модуля, класса или функции.

    Нужны, чтобы отделить обсуждение примитива от его применения. Комментарии
    отделять не нужно — в AST они не попадают вовсе.
    """
    out: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            out.add(id(body[0].value))
    return out


def _wire_mentions(path: str) -> list[tuple[int, str, str]]:
    """Строки протокола, реально УЧАСТВУЮЩИЕ В КОДЕ.

    Раньше здесь был поиск подстроки по сырым строкам файла, и честный
    комментарий с литералом протокола ронял проверку — то есть вторая половина
    файла нарушала обещание, которое держит первая.

    Литерал протокола, собранный в запрос вручную, — это ЗНАЧЕНИЕ в коде.
    Литерал, упомянутый в документации, — это комментарий или докстрока.
    Разница структурная, и потому берётся из разбора, а не угадывается.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    docstrings = _docstring_constants(tree)
    hits = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstrings:
            continue
        for literal, primitive in _DEPRECATED_WIRE.items():
            if literal in node.value:
                hits.append((node.lineno, primitive, literal))
    return hits


class TestNoDeprecatedPrimitivesInUse:
    """AC1-AC3: результат аудита закреплён, а не записан прозой."""

    def test_no_code_uses_a_deprecated_primitive(self):
        offenders = []
        for path in _mcp_sources():
            for line, primitive, name in _code_usages(path):
                rel = os.path.relpath(path, _ROOT)
                offenders.append(f"{rel}:{line}: {name} ({primitive})")
        assert not offenders, (
            "MCP-тред начал пользоваться примитивом, депрекированным SEP-2577.\n"
            "sampling -> параметры тула; logging -> stderr или OpenTelemetry; "
            "roots -> параметры тула, resource URI или конфиг сервера.\n"
            "Найдено:\n" + "\n".join(offenders)
        )

    def test_no_source_builds_a_deprecated_request_by_hand(self):
        """Строка протокола в коде означала бы обход SDK."""
        offenders = []
        for path in _mcp_sources():
            for line, primitive, literal in _wire_mentions(path):
                rel = os.path.relpath(path, _ROOT)
                offenders.append(f"{rel}:{line}: {literal!r} ({primitive})")
        assert not offenders, "ручная сборка депрекированного запроса:\n" + "\n".join(offenders)

    def test_the_server_advertises_none_of_them(self):
        """Проверка не нашего текста, а того, что реально уходит клиенту.

        Возможности выводятся SDK из ЗАРЕГИСТРИРОВАННЫХ хендлеров. Это и есть
        итоговый ответ на вопрос задачи: объявляем ли мы депрекируемое.
        """
        from mcp.server import Server
        from mcp.server.lowlevel.server import NotificationOptions

        caps = Server("probe").get_capabilities(
            notification_options=NotificationOptions(), experimental_capabilities={}
        )
        assert caps.logging is None, (
            "сервер объявил capability logging — она депрекирована SEP-2577 "
            "и заменяется на stderr либо OpenTelemetry"
        )


class TestTheGateActuallyCatchesUsage:
    """AC4: гейт, никогда ничего не ловивший, — это гейт-гипотеза."""

    @pytest.mark.parametrize(
        "snippet,expected",
        [
            ("async def f(s):\n    await s.create_message(x)\n", "sampling"),
            ("async def f(s):\n    await s.list_roots()\n", "roots"),
            ("async def f(s):\n    await s.send_log_message('x')\n", "logging"),
            ("@server.set_logging_level()\nasync def f():\n    pass\n", "logging"),
        ],
    )
    def test_a_planted_call_is_caught(self, tmp_path, snippet, expected):
        f = tmp_path / "probe.py"
        f.write_text(snippet, encoding="utf-8")
        hits = _code_usages(str(f))
        assert hits, f"внесённое использование не найдено: {snippet!r}"
        assert expected in {primitive for _, primitive, _ in hits}

    def test_a_mention_in_a_comment_is_not_a_usage(self, tmp_path):
        """НЕГАТИВНЫЙ: документации можно ОБСУЖДАТЬ депрекацию.

        Без этого гейт падал бы на собственном докстринге, и его отключили бы —
        отключённый гейт хуже отсутствующего, потому что выглядит защитой.
        """
        f = tmp_path / "probe.py"
        f.write_text(
            '"""Roots заменяются: create_message и list_roots больше не наши."""\n'
            "# list_roots упомянут здесь намеренно\n"
            "X = 1\n",
            encoding="utf-8",
        )
        assert _code_usages(str(f)) == []

    def test_a_planted_wire_string_is_caught(self, tmp_path):
        f = tmp_path / "probe.py"
        f.write_text('PAYLOAD = {"method": "roots/list"}\n', encoding="utf-8")
        assert _wire_mentions(str(f))


class TestTheGateDoesNotFireOnHonestText:
    """Регрессия аудита #122: обещание докстринга было шире кода.

    Оба дефекта — ЛОЖНЫЕ ПАДЕНИЯ, и оба опасны одинаково: гейт, который ругается
    на честный комментарий и на чужое имя, отключают. Отключённый гейт хуже
    отсутствующего, потому что выглядит защитой.

    Каждая пара тестов проверяет ОБЕ стороны. Проверка «стало меньше ложных
    падений» без парной «настоящее нарушение всё ещё ловится» прошла бы и на
    функции, всегда возвращающей пустой список, — то есть заменила бы шумный
    гейт слепым.
    """

    def test_a_wire_literal_in_a_comment_is_not_a_usage(self, tmp_path):
        """ВОСПРОИЗВЕДЕНИЕ ДЕФЕКТА 1.

        Прежний негативный тест покрывал только питоновское ИМЯ в комментарии
        (list_roots), а литерал протокола ("roots/list") искался другой,
        текстовой половиной файла и не покрывался никогда.
        """
        f = tmp_path / "probe.py"
        f.write_text(
            '# Note: older clients still send "roots/list" over the wire; we ignore it.\n'
            "def handler():\n    return 1\n",
            encoding="utf-8",
        )
        assert _wire_mentions(str(f)) == []

    def test_a_wire_literal_in_a_docstring_is_not_a_usage(self, tmp_path):
        """Докстрока — та же документация, только в другой синтаксической форме."""
        f = tmp_path / "probe.py"
        f.write_text(
            '"""Клиенты постарше шлют roots/list и sampling/createMessage."""\n\nX = 1\n',
            encoding="utf-8",
        )
        assert _wire_mentions(str(f)) == []

    def test_a_wire_literal_in_actual_code_is_still_caught(self, tmp_path):
        """ОБРАТНАЯ СТОРОНА дефекта 1 — без неё правка была бы ослеплением.

        Литерал внутри f-строки проверяется намеренно: сборка запроса
        подстановкой — самый правдоподобный способ обойти SDK, и разбор обязан
        видеть её так же, как обычную строку.
        """
        f = tmp_path / "probe.py"
        f.write_text(
            'METHOD = "roots/list"\n'
            "def send(rid):\n"
            '    return f\'{{"id": {rid}, "method": "sampling/createMessage"}}\'\n',
            encoding="utf-8",
        )
        found = {literal for _, _, literal in _wire_mentions(str(f))}
        assert "roots/list" in found
        assert "sampling/createMessage" in found

    def test_an_unrelated_local_name_is_not_a_usage(self, tmp_path):
        """ВОСПРОИЗВЕДЕНИЕ ДЕФЕКТА 2.

        «roots» в MCP-сервере встречается и по другим поводам, и перечисление
        корней дерева — совершенно правдоподобная функция. Падать на ней с
        сообщением про депрекированный API значит заставлять читателя
        догадываться, что срабатывание ложное.
        """
        f = tmp_path / "probe.py"
        f.write_text(
            "def list_roots(tree):\n"
            '    """Перечислить корни дерева каталогов — к MCP отношения не имеет."""\n'
            "    return [n for n in tree if n.parent is None]\n"
            "roots = list_roots([])\n",
            encoding="utf-8",
        )
        assert _code_usages(str(f)) == []

    def test_an_attribute_access_is_still_caught(self, tmp_path):
        """ОБРАТНАЯ СТОРОНА дефекта 2: сужение не смеет пропускать настоящее."""
        f = tmp_path / "probe.py"
        f.write_text(
            "async def h(session):\n    return await session.list_roots()\n", encoding="utf-8"
        )
        assert {p for _, p, _ in _code_usages(str(f))} == {"roots"}

    def test_a_direct_import_is_caught_despite_the_narrowing(self, tmp_path):
        """AC-6: единственный путь к примитиву БЕЗ доступа к атрибуту.

        Сужение до ast.Attribute без этой ветки открыло бы дыру ровно того
        размера, который оно закрыло, — и закрытие выглядело бы починкой.
        """
        f = tmp_path / "probe.py"
        f.write_text(
            "from mcp.server.session import list_roots, create_message\n\nX = 1\n",
            encoding="utf-8",
        )
        assert {p for _, p, _ in _code_usages(str(f))} == {"roots", "sampling"}


class TestTheGateIsNotHollow:
    """AC5: гейт, сканирующий пустоту, зелен всегда."""

    def test_the_scan_finds_our_actual_servers(self):
        sources = _mcp_sources()
        names = {os.path.basename(p) for p in sources}
        assert len(sources) >= 5, f"обход MCP-треда сломан, найдено {len(sources)} файлов"
        assert "server.py" in names, "server.py не найден — обход смотрит не туда"

    def test_the_pattern_sets_are_not_empty(self):
        assert _DEPRECATED_ATTRS and _DEPRECATED_WIRE
        assert set(_DEPRECATED_ATTRS.values()) == {"sampling", "logging", "roots"}

    def test_the_ast_scanner_parses_real_code(self):
        """Страховка от разбора, который молча возвращает пустоту.

        Ищется имя, которое в нашем сервере ТОЧНО есть: если оно не находится,
        значит разбор не работает, а не «депрекированного нет».
        """
        server_py = [p for p in _mcp_sources() if p.endswith(os.path.join("project", "server.py"))]
        assert server_py, "harness/claude/mcp/project/server.py не найден"
        with open(server_py[0], encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "call_tool" in attrs, "AST-обход не видит заведомо присутствующего имени"
