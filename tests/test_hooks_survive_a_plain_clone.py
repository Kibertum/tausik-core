"""Сгенерированный конфиг обязан указывать на хуки, которые есть в обычном клоне.

ЧТО БЫЛО СЛОМАНО. Оба генератора настроек брали адрес хуков из БИБЛИОТЕКИ —
`lib_dir/scripts/hooks`. В этом репозитории library и project — один каталог,
поэтому дома всё работало и тест бы ничего не заметил. В потребительском
проекте библиотека подключается сабмодулем под `.tausik-lib`, а сабмодуль даёт
индексу git РОВНО ОДНУ запись — свой гитлинк. Клон без `--recurse-submodules`
получает дерево, где по этим путям нет ничего: ни гейта задачи, ни скана
секретов, ни пуш-гейта. При этом тот же bootstrap пишет CLAUDE.md, объявляющий
Rule 1 жёстким правилом уровня PreToolUse-хука.

Замерено на живом потребительском проекте 12.08.2026: 22 команды хуков вели в
`.tausik-lib`, в индексе там 1 файл, а рядом — 26 байт-в-байт тех же хуков,
которые git ОТСЛЕЖИВАЕТ, потому что их развернул тот же bootstrap.

ПОЧЕМУ ТЕСТ УСТРОЕН ТАК. Он не спрашивает платформу и не ищет подстроку
`.tausik-lib`: он строит раскладку, В КОТОРОЙ БИБЛИОТЕКА ПУСТА, и проверяет, что
каждая команда указывает на существующий файл. Такой тест переживёт и
переименование каталога библиотеки, и появление шестого профиля IDE — потому
что проверяет СВОЙСТВО (хук достижим), а не написание пути.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "bootstrap"))

from bootstrap_generate import generate_settings_claude  # noqa: E402
from bootstrap_hooks import (  # noqa: E402
    HooksNotDeployedError,
    assert_hooks_deployed,
    deployed_hooks_dir,
)
from bootstrap_qwen import generate_settings_qwen  # noqa: E402

# Генераторы, которые пишут команды хуков. Список — из кода, а не из головы:
# добавится шестой профиль, и он обязан попасть сюда, иначе дефект вернётся
# в него одного (конвенция #361 — закрывать форму, а не найденный отказ).
GENERATORS = (
    ("claude", generate_settings_claude),
    ("qwen", generate_settings_qwen),
)


def _consumer_layout(tmp_path, ide: str):
    """Потребительская раскладка: библиотека ПУСТА, хуки развёрнуты в проект.

    Ровно то, что видит клонировавший без --recurse-submodules.
    """
    project = tmp_path / "consumer"
    lib = project / ".tausik-lib"
    (lib / "scripts" / "hooks").mkdir(parents=True)  # каталог есть, файлов нет
    deployed = project / f".{ide}" / "scripts" / "hooks"
    deployed.mkdir(parents=True)
    # Разворачиваем ТЕ ЖЕ имена, что кладёт copy_scripts, — читая их из живого
    # каталога хуков, а не перечисляя руками. Список руками устарел бы на первом
    # же новом хуке, и тест бы покраснел на своей фикстуре, а не на дефекте.
    for name in os.listdir(os.path.join(_REPO, "scripts", "hooks")):
        if name.endswith(".py"):
            (deployed / name).write_text("# развёрнутая копия\n", encoding="utf-8")
    return project, lib


def _hook_commands(settings_path) -> list[str]:
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return [
        h["command"]
        for entries in (data.get("hooks") or {}).values()
        for entry in entries
        for h in (entry.get("hooks") or [])
    ]


def _named_file(command: str) -> str:
    """Путь к скрипту из команды вида `python -X utf8 <path>/<script>.py`."""
    for token in command.split():
        if token.endswith(".py"):
            return token
    raise AssertionError(f"в команде нет скрипта: {command!r}")


@pytest.mark.parametrize("ide,generate", GENERATORS)
def test_every_hook_command_names_a_file_that_exists(tmp_path, ide, generate):
    """Главное свойство: в обычном клоне каждый хук достижим."""
    project, _lib = _consumer_layout(tmp_path, ide)
    target = project / f".{ide}"
    generate(str(target), str(project))

    commands = _hook_commands(target / "settings.json")
    assert commands, f"{ide}: генератор не выписал ни одной команды хука"

    missing = []
    for command in commands:
        path = _named_file(command)
        # Хост подставляет переменную рабочей папки; для проверки на диске
        # заменяем её тем, чем она станет у пользователя.
        resolved = path.replace("${CLAUDE_PROJECT_DIR}", str(project))
        if not os.path.isabs(resolved):
            resolved = os.path.join(str(project), resolved)
        if not os.path.isfile(resolved):
            missing.append(resolved)

    assert not missing, (
        f"{ide}: {len(missing)} из {len(commands)} команд хуков ведут в никуда "
        f"при обычном клоне. Первая: {missing[0]}. Это конфиг, который выглядит "
        "настроенным и не охраняет ничего."
    )


@pytest.mark.parametrize("ide,generate", GENERATORS)
def test_the_old_wiring_would_have_failed_this(tmp_path, ide, generate):
    """Негативная половина: проверка обязана ЛОВИТЬ прежнюю проводку.

    Зелёный результат теста выше ничего не значит, если проверка не умеет
    краснеть. Поэтому здесь конфиг собирается СТАРЫМ способом — адрес хуков из
    библиотеки, как было до правки, — и та же процедура применяется к нему.
    Она обязана найти промахи, причём ВСЕ: в обычном клоне библиотека пуста.
    """
    project, lib = _consumer_layout(tmp_path, ide)
    old_hooks = os.path.join(str(lib), "scripts", "hooks")

    # Ровно то, что делали генераторы до правки.
    old_commands = [
        f"python -X utf8 {old_hooks}/{name}"
        for name in ("task_gate.py", "bash_firewall.py", "git_push_gate.py")
    ]

    missing = [c for c in old_commands if not os.path.isfile(_named_file(c))]
    assert len(missing) == len(old_commands), (
        "процедура проверки не поймала прежнюю проводку — значит она не умеет "
        "краснеть, и зелёный результат основной проверки ничего не доказывает"
    )


@pytest.mark.parametrize("ide,_generate", GENERATORS)
def test_bootstrap_refuses_to_write_a_config_pointing_at_nothing(tmp_path, ide, _generate):
    """Хуков нет вовсе — конфиг не пишется, а отказ громкий.

    Молчаливо записанный конфиг, называющий несуществующие файлы, неотличим от
    рабочего до первой правки, проскочившей мимо гейта.
    """
    target = tmp_path / f".{ide}"
    target.mkdir()
    with pytest.raises(HooksNotDeployedError) as excinfo:
        assert_hooks_deployed(str(target))
    assert "not deployed" in str(excinfo.value)


def test_generators_list_covers_every_profile_that_writes_hooks():
    """Список генераторов выше сверяется с кодом, а не поддерживается памятью."""
    import bootstrap_hooks

    writers = []
    for module_name in ("bootstrap_generate", "bootstrap_qwen"):
        module = __import__(module_name)
        for attr in dir(module):
            if attr.startswith("generate_settings_"):
                writers.append(attr)
    assert len(writers) == len(GENERATORS), (
        f"генераторов настроек в коде {len(writers)} ({sorted(writers)}), "
        f"а в списке теста {len(GENERATORS)}. Появившийся профиль обязан быть "
        "добавлен сюда, иначе дефект вернётся в него одного."
    )
    assert bootstrap_hooks.deployed_hooks_dir is deployed_hooks_dir
