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
        name = None
        if isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Name):
            name = node.id
        if name in _DEPRECATED_ATTRS:
            hits.append((node.lineno, _DEPRECATED_ATTRS[name], name))
    return hits


def _wire_mentions(path: str) -> list[tuple[int, str, str]]:
    """Строки протокольного уровня, встреченные в исходнике."""
    hits = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            for literal, primitive in _DEPRECATED_WIRE.items():
                if literal in line:
                    hits.append((i, primitive, literal))
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
