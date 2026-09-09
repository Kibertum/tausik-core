"""Codex scaffold: хуки, которые ДЕЙСТВИТЕЛЬНО срабатывают.

ЗАМЕР, СДЕЛАННЫЙ НА САМОМ БИНАРЕ, А НЕ ПО ДОКУМЕНТАЦИИ (смена #241). В
`codex.exe` присутствуют строки `hooks.json`, `.codex/hooks`, `PreToolUse`,
`PostToolUse`, `SessionStart`, `UserPromptSubmit`, а также `hook_event_name`,
`hookSpecificOutput` и `permissionDecision` — то есть у Codex есть API хуков с
тем же протоколом обмена, что у Claude Code. Тикет GitLab #17 исходил из
обратного и предлагал держать Rule 1 инструкцией; предпосылка устарела, и Rule 1
здесь ЖЁСТКИЙ.

И ЭТОТ ЖЕ ЗАМЕР НАШЁЛ ЖИВОЙ ДЕФЕКТ, ради которого модуль и написан именно так. В
проекте уже лежал `.codex/hooks.json` — не наш, bootstrap его не создавал, — где
каждая команда имела вид ``python -X utf8 ${CLAUDE_PROJECT_DIR}/.claude/...``.
Строки `CLAUDE_PROJECT_DIR` в бинаре Codex НЕТ. Переменная раскрывается в пустоту,
путь превращается в `/.claude/scripts/hooks/task_gate.py` и не находится. Под
Codex молча не работал НИ ОДИН гейт — ни Rule 1, ни ACL области, ни firewall, ни
сканер секретов — при том что файл на диске выглядел подключённым.

ПОЭТОМУ ПУТИ ЗДЕСЬ АБСОЛЮТНЫЕ. Ни одной переменной: в бинаре нет ни
`CODEX_PROJECT_ROOT`, ни `workspaceFolder`, ни любого другого имени рабочей
области — проверено тем же способом, что и наличие остальных строк. Это то же
решение и по той же причине, что у OpenCode (gotcha #201). Цена известна и
принята: переименование каталога проекта требует повторного bootstrap. Цена
альтернативы измерена выше — тринадцать гейтов, выглядящих подключёнными.

НАБОР ХУКОВ НЕ КОПИРУЕТСЯ, А БЕРЁТСЯ ИЗ ОБЩЕГО ОБЪЯВЛЕНИЯ `build_hooks_dict`.
Второй список означал бы, что хук, добавленный одному хосту, молча не появится у
другого, и разошлись бы они не сразу, а через несколько релизов. Различие между
хостами ровно одно — как строится строка команды, — и оно передаётся параметром.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from bootstrap_codex_mcp import register_mcp_servers
from bootstrap_hooks import build_hooks_dict, deployed_hooks_dir

#: Имя файла хуков у Codex — то, что ищет сам хост (строка `.codex/hooks` в бинаре).
HOOKS_FILE = "hooks.json"

#: Ключи, которые Codex мог положить в тот же файл сам и которые не наши. Всё,
#: кроме `hooks`, переживает перезапись побайтово: генератор владеет одним ключом.
_OWNED_KEY = "hooks"


def _fallback_python() -> str:
    """Абсолютный путь к интерпретатору, либо голое имя, если найти нечем.

    Голое `python` оставлено последним средством, а не первым выбором: Codex
    запускает хук сам, и хост, стартовавший из графической оболочки, не обязан
    передать ему PATH — тогда хук не запустится, а на диске всё выглядит верно.
    Ровно этот класс отказа модуль и чинит.
    """
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return os.path.abspath(found)
    return "python"


def build_codex_hooks(target_dir: str, venv_python: str | None = None) -> dict[str, Any]:
    """Блок `hooks` для Codex: тот же набор, что у Claude, но путями с диска.

    `target_dir` — каталог профиля (`<проект>/.codex`), куда bootstrap уже
    скопировал `scripts/hooks`. Путь берётся у `deployed_hooks_dir`, то есть у
    того же, кто эти файлы туда кладёт: собственное представление о том, где они
    лежат, — это второй источник правды, а модуль существует потому, что первый
    никто не проверял.
    """
    hooks_dir = os.path.abspath(deployed_hooks_dir(target_dir)).replace("\\", "/")
    python_exe = (
        os.path.abspath(venv_python).replace("\\", "/") if venv_python else _fallback_python()
    )

    def _hook_cmd(script: str, suffix: str = "") -> str:
        # -X utf8 по той же причине, что и у остальных хостов: хук запускается
        # напрямую, а не через обёртку CLI, и не наследует её PYTHONUTF8.
        return f"{python_exe} -X utf8 {hooks_dir}/{script}{suffix}"

    return build_hooks_dict(_hook_cmd)


def _load_existing(path: str) -> dict[str, Any]:
    """Прочитать существующий hooks.json. Испорченный файл ЗАМЕНЯЕТСЯ с оглаской.

    Молча заменить — значит унести чужие ключи без следа; уронить bootstrap —
    значит оставить хост без единого гейта из-за одной битой скобки. Оглашение
    выбрано третьим: так же поступает генератор OpenCode с `opencode.json`.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"  WARNING: {path} нечитаем ({e}) — файл заменяется. Ключи из него потеряны.")
        return {}
    if not isinstance(loaded, dict):
        print(f"  WARNING: {path} не JSON-объект — файл заменяется.")
        return {}
    return loaded


def generate_codex_hooks(
    project_dir: str,
    target_dir: str,
    venv_python: str | None = None,
) -> str:
    """Записать `<проект>/.codex/hooks.json`. Возвращает путь.

    Наш ключ ровно один — `hooks`; всё остальное, что Codex или пользователь
    положили в файл, переносится без изменений. Идемпотентность здесь по
    ЗАМЕЩЕНИЮ ключа, а не по дописыванию: набор хуков — это снимок текущего
    объявления, и дописывание растило бы его с каждым прогоном.
    """
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, HOOKS_FILE)
    document = _load_existing(path)
    document[_OWNED_KEY] = build_codex_hooks(target_dir, venv_python)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2, ensure_ascii=False)
    return path


def scaffold_codex(
    project_dir: str,
    target_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
) -> None:
    """Точка входа ветки `--ide codex` в `bootstrap.run_for_ide`.

    AGENTS.md здесь НЕ генерируется: его пишет общий шаг `generate_agents_md`
    для каждого хоста, кроме OpenCode, и Codex читает именно его (строка
    `AGENTS.md` есть в бинаре). Дублировать значило бы иметь два места, где
    правила расходятся.
    """
    path = generate_codex_hooks(project_dir, target_dir, venv_python)
    count = sum(len(entries) for entries in build_codex_hooks(target_dir, venv_python).values())
    print(f"  Codex hooks: {count} matcher(s) → {os.path.relpath(path, project_dir)}")

    config_path, servers = register_mcp_servers(project_dir, target_dir, venv_python, lib_dir)
    where = os.path.relpath(config_path, project_dir)
    if servers:
        print(f"  Codex MCP: {servers} server(s) → {where}")
    else:
        # Ноль — не отказ: блок уже там от прошлого прогона. Сказать «0» без
        # объяснения значило бы отправить читателя искать поломку, которой нет.
        print(f"  Codex MCP: уже зарегистрированы в {where}")
