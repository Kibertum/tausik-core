"""Гейт mypy обязан мерять то же, что `mypy` по конфигу проекта.

mypy-gate-measures-differently-than-mypy-itself. Гейт был объявлен как
`mypy {files}` и подставлял ИЗМЕНЁННЫЕ файлы аргументами, тогда как
pyproject.toml задаёт СВОЙ набор источников. Два источника истины о том, ЧТО
проверяется, — тот же класс, что решение #277 чинило в CLAUDE.md.

Цена расхождения не теоретическая: файл, переданный явным аргументом,
проверяется ВНЕ набора источников, поэтому импорты, которые в штатном прогоне
резолвятся, перестают резолвиться. На tests/conftest.py это давало три ошибки,
которые несколько смен подряд передавались как «дорелизные ошибки типов». Чинить
в типах было нечего.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from gate_command_runner import run_command_gate  # noqa: E402
from gate_registry import GATE_REGISTRY  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _mypy_gate() -> dict:
    """Живой конфиг гейта из реестра, а не его копия в тесте.

    Копия разошлась бы с реестром на первой же правке и продолжила бы утверждать
    зелёное про то, чего в реестре уже нет.
    """
    return dict(GATE_REGISTRY["mypy"].default_config)


# --- AC1: один источник истины о наборе проверяемых файлов -------------------


def test_mypy_gate_does_not_interpolate_files() -> None:
    """Свойство, а не литерал команды.

    Утверждать дословный текст исходника запрещено конвенцией #417: такой тест
    ломается на каждом рефакторинге и ничего не защищает. Проверяется ровно то,
    от чего защищаемся, — подстановки изменённых файлов быть не должно.
    """
    cmd = _mypy_gate()["command"]
    assert "{files}" not in cmd, (
        "гейт снова подставляет изменённые файлы — вернулось расхождение с "
        "набором источников из pyproject.toml"
    )
    assert cmd.split()[0] == "mypy", "команда гейта обязана называться именем инструмента"


def test_mypy_gate_still_declares_python_scope() -> None:
    """Снятие {files} не имеет права снять ОБЛАСТЬ.

    «Проверяю проект целиком» и «проверяю на КАЖДЫЙ коммит» — разные
    утверждения; второе никто не заказывал.
    """
    assert _mypy_gate()["file_extensions"] == [".py"]


# --- AC2: область работает и без подстановки {files} -------------------------


def test_extension_scope_applies_without_files_placeholder() -> None:
    """Коммит без единого .py гейт с file_extensions не запускает.

    До починки условие в gate_command_runner требовало наличия {files} в
    команде, поэтому у гейта без подстановки объявление «я про .py» не значило
    ничего и молча игнорировалось.
    """
    ok, output = run_command_gate(
        {"command": "python --version", "file_extensions": [".py"]},
        ["README.md", "CHANGELOG.ru.md"],
    )
    assert ok is True, "пустая область — законная пустота, она не имеет права блокировать"
    assert "Python" not in output, f"команда всё-таки исполнилась: {output}"
    assert "No files matching" in output, output


def test_extension_scope_lets_python_through() -> None:
    ok, output = run_command_gate(
        {"command": "python --version", "file_extensions": [".py"]},
        ["scripts/gate_registry.py"],
    )
    assert ok is True
    assert "Python" in output, f"команда не исполнилась: {output}"


# --- AC3(а): НЕГАТИВНЫЙ. Новая фильтрация не выключает гейты молча -----------


def test_gate_without_scope_declaration_always_runs() -> None:
    """Гейт, не объявивший области, обязан исполняться ВСЕГДА.

    Это главный риск правки. Пропущенный гейт хуже ложного срабатывания: он
    выглядит в точности как зелёный, и никто не идёт разбираться.
    """
    ok, output = run_command_gate(
        {"command": "python --version"},
        ["README.md"],
    )
    assert ok is True
    assert "Python" in output, f"гейт без file_extensions был молча пропущен: {output}"


def test_empty_extension_list_is_not_a_scope_declaration() -> None:
    """Пустой список — не объявление области, а его отсутствие."""
    ok, output = run_command_gate(
        {"command": "python --version", "file_extensions": []},
        ["README.md"],
    )
    assert ok is True
    assert "Python" in output, output


# --- AC3(б) и AC4: настоящий conftest.py на настоящем гейте ------------------


def test_conftest_no_longer_reddens_the_mypy_gate() -> None:
    """Прогон на НАСТОЯЩЕМ файле, а не на выдуманном.

    tests/conftest.py — тот самый файл, чьи три ошибки несколько смен подряд
    считались дорелизным долгом типов.
    """
    ok, output = run_command_gate(_mypy_gate(), ["tests/conftest.py"])
    assert ok is True, f"гейт mypy покраснел на tests/conftest.py: {output}"


def test_the_old_form_is_what_reddened_it() -> None:
    """Доказывает ПРИЧИНУ, а не только исчезновение симптома.

    Без этого теста «стало зелено» объяснялось бы одинаково хорошо и починкой
    способа вызова, и чьей-то правкой типов в conftest.py. Здесь предъявлена
    прежняя форма команды на том же файле: она красная, и красная именно
    ненайденными импортами, которые в штатном прогоне резолвятся.
    """
    ok, output = run_command_gate(
        {"command": "mypy {files}", "file_extensions": [".py"]},
        ["tests/conftest.py"],
    )
    assert ok is False, (
        "прежняя форма перестала краснеть — значит дефект починен где-то ещё, "
        "и этот тест больше не доказывает причину"
    )
    assert "import-not-found" in output or "Cannot find implementation" in output, output


def test_conftest_itself_was_not_edited() -> None:
    """Файл, чьи ошибки объявлены ложными, не имеет права быть подправленным.

    Иначе задача отчиталась бы о починке способа вызова, а на деле замаскировала
    бы симптом правкой предмета замера.
    """
    body = open(os.path.join(REPO_ROOT, "tests", "conftest.py"), encoding="utf-8").read()
    assert "import service_gates" in body or "service_gates" in body
    assert "backend_schema" in body
