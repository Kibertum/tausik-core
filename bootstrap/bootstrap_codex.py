"""Codex scaffold with absolute hook commands and an explicit write adapter.

Hook configuration and binary symbols do not prove enforcement. Live host
checks must establish trust, dispatch, denial before mutation and allowed writes.
Codex patch payloads contain command text; Windows shell payloads can be named
Bash even for PowerShell. The adapter bridges the observed bounded forms to
shared task/scope gates and emits the native JSON permission decision.

Shared hooks come from build_hooks_dict; host-specific adaptation stays here.
Absolute paths avoid relying on another host's environment variables. Moving a
project requires bootstrap again. See the versioned live enforcement evidence.
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


def build_codex_hooks(
    target_dir: str,
    venv_python: str | None = None,
    governance_profile: str = "full",
) -> dict[str, Any]:
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

    hooks = build_hooks_dict(_hook_cmd, governance_profile)
    # Live 0.153.4 payloads differ from Claude's canonical Write/PowerShell shapes.
    # Keep shared registrations intact and add one narrowly scoped adapter.
    if governance_profile == "full":
        project = os.path.dirname(os.path.abspath(target_dir)).replace("\\", "/")
        hooks["PreToolUse"].append(
            {
                "matcher": "apply_patch|Bash|PowerShell",
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_cmd("codex_write_gate.py", f' --project "{project}"'),
                        "timeout": 10,
                    }
                ],
            }
        )
    return hooks


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
    governance_profile: str = "full",
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
    document[_OWNED_KEY] = build_codex_hooks(target_dir, venv_python, governance_profile)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2, ensure_ascii=False)
    return path


def scaffold_codex(
    project_dir: str,
    target_dir: str,
    venv_python: str | None = None,
    lib_dir: str | None = None,
    governance_profile: str = "full",
) -> None:
    """Точка входа ветки `--ide codex` в `bootstrap.run_for_ide`.

    AGENTS.md здесь НЕ генерируется: его пишет общий шаг `generate_agents_md`
    для каждого хоста, кроме OpenCode, и Codex читает именно его (строка
    `AGENTS.md` есть в бинаре). Дублировать значило бы иметь два места, где
    правила расходятся.
    """
    path = generate_codex_hooks(project_dir, target_dir, venv_python, governance_profile)
    count = sum(
        len(entries)
        for entries in build_codex_hooks(target_dir, venv_python, governance_profile).values()
    )
    print(f"  Codex hooks: {count} matcher(s) → {os.path.relpath(path, project_dir)}")

    config_path, servers = register_mcp_servers(project_dir, target_dir, venv_python, lib_dir)
    where = os.path.relpath(config_path, project_dir)
    if servers:
        print(f"  Codex MCP: {servers} server(s) → {where}")
    else:
        # Ноль — не отказ: блок уже там от прошлого прогона. Сказать «0» без
        # объяснения значило бы отправить читателя искать поломку, которой нет.
        print(f"  Codex MCP: уже зарегистрированы в {where}")
