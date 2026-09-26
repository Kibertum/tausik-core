"""Динамический блок CLAUDE.md — ОДНА реализация на CLI и MCP.

До этого модуля блок собирали два независимых куска кода: `cmd_update_claudemd`
в CLI и `handle_update_claudemd` в MCP-сервере. Копии разошлись, и разошлись
молча: в MCP-версии не было ни впрыска хвоста памяти, ни обновления
файла-побратима AGENTS.md. Поскольку /start Phase 2 предписывает MCP-вызов, а
правило проекта — MCP-first, штатный старт сессии УДАЛЯЛ из CLAUDE.md блок
памяти, который тот же /start обещает впрыснуть, и рапортовал об успехе.

Отсюда форма модуля: собирать блок умеет ровно одна функция, а вызывающие
стороны отвечают только за то, где лежит файл и как его писать. Третьей потери
по той же причине быть не может — терять больше нечего, копия одна.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


def resolve_branch(project_dir: str) -> str:
    """Текущая ветка, или 'unknown'.

    Спрашивается у git, а не читается из `.git/HEAD`: в git-worktree `.git` —
    это ФАЙЛ со ссылкой, и прямое чтение там даёт мусор вместо имени ветки.
    MCP-копия читала файл и в worktree всегда писала 'unknown'.

    stdin=DEVNULL обязателен: без него дочерний процесс наследует канал
    JSON-RPC MCP-сервера и подвешивает вызов (v14b-defect-mcp-task-done-stdin-hang).
    """
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            stdin=subprocess.DEVNULL,
            cwd=project_dir or None,
        )
        return r.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 — best-effort: имя ветки не стоит падения обновления
        return "unknown"


# The label names the OWNER of the number. This block lands in the PRODUCT's
# CLAUDE.md / AGENTS.md, one line above the product's own tasks and next to its
# branch; a bare `Version:` there was read as the product's version — measured
# on a consumer at 0.1.0 whose CLAUDE.md declared 1.8.0 (GitLab #5).
STAMP_LABEL = "TAUSIK"


def resolve_version() -> str:
    try:
        from tausik_version import __version__

        return __version__
    except ImportError:
        return "unknown"


def build_dynamic_state(svc: Any, project_dir: str) -> str:
    """Содержимое секции DYNAMIC: Current State плюс хвост памяти.

    Хвост строится best-effort: сломанная память НЕ имеет права отменить запись
    состояния сессии, иначе один сбой подсистемы знаний оставляет свежего агента
    вообще без двери в проект.
    """
    tasks = svc.task_list()
    session = svc.session_current()

    active = [t for t in tasks if t["status"] == "active"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    # An obsolete close is done but not delivered (task_obsolete.py): counted apart.
    obsolete = sum(1 for t in tasks if t.get("resolution") == "obsolete")
    done_count = sum(1 for t in tasks if t["status"] == "done") - obsolete

    session_info = f"#{session['id']} (active)" if session else "none"
    lines = [
        "## Current State",
        f"Session: {session_info} | Branch: {resolve_branch(project_dir)} | "
        f"{STAMP_LABEL}: {resolve_version()}",
        f"Tasks: {done_count}/{len(tasks)} done"
        + (f", {obsolete} obsolete" if obsolete else "")
        + f", {len(active)} active, {len(blocked)} blocked",
    ]
    if active:
        lines.append(f"Active: {', '.join(t['slug'] for t in active)}")
    if blocked:
        lines.append(f"Blocked: {', '.join(t['slug'] for t in blocked)}")
    if transcript := _transcript_path(project_dir):
        lines.append(f"Full history (grep it for what a compaction dropped): {transcript}")

    if (be := getattr(svc, "be", None)) is not None:
        try:
            import service_knowledge_aggregates

            if memory_tail := service_knowledge_aggregates.build_compact_memory_tail(be):
                lines.append("")
                lines.extend(memory_tail)
        except Exception:  # noqa: BLE001 — best-effort: см. docstring
            pass

    return "\n".join(lines)


def _transcript_path(project_dir: str) -> str | None:
    """Путь к транскрипту ЭТОЙ смены, либо ``None``.

    Зачем он в блоке состояния. Сводка компакции умышленно короткая, и всё, что в
    шесть её пунктов не попало, теряется — а полная история в это время лежит на
    диске: 36 МБ за одну смену, 37 файлов по проекту. Агент не знает об этом,
    потому что имя каталога получается искажением пути проекта, и угадать его
    нельзя — ровно для этого существует `transcript_locator`, находящий файл
    ДОКАЗАТЕЛЬСТВОМ, а не совпадением имени.

    Строка живёт в переменной половине блока, то есть не удорожает неизменную
    часть инструкций. Любая ошибка поиска — ``None``: блок состояния не смеет
    падать из-за подсказки.
    """
    try:
        import os
        import sys

        hooks = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
        if hooks not in sys.path:
            sys.path.insert(0, hooks)
        from transcript_locator import latest_project_transcript

        found = latest_project_transcript(project_dir)
        if not found:
            return None
        # ДОМАШНИЙ КАТАЛОГ СВЁРНУТ В `~`, и это не косметика. CLAUDE.md и AGENTS.md
        # версионируются, а полный путь несёт имя пользователя — гейт границы
        # публикации поймал именно это на первой же записи. `~` раскрывает и
        # оболочка, и сам агент, поэтому подсказка не теряет пользы.
        home = os.path.expanduser("~")
        text = str(found)
        return "~" + text[len(home) :] if home and text.startswith(home) else text
    except Exception:  # noqa: BLE001 — подсказка не смеет уронить запись состояния
        return None


def resolve_project_dir(svc: Any) -> str | None:
    """Каталог проекта, ВЫВЕДЕННЫЙ ИЗ БАЗЫ, которая даёт содержимое блока.

    АДРЕС ЗАПИСИ И ДАННЫЕ ОБЯЗАНЫ ИМЕТЬ ОДИН ИСТОЧНИК. Оба вызывающих брали адрес
    из `os.getcwd()`, а содержимое — из переданного `svc`, то есть из двух разных
    мест, и совпадали они лишь потому, что обычно процесс стоит в своём проекте.
    Когда не совпадали, получалось ровно то, ради чего написана эта функция:
    состояние ЧУЖОЙ базы, записанное в НАСТОЯЩИЕ файлы репозитория.

    Замерено, а не предположено (claudemd-dynamic-block-wiped-to-an-empty-project).
    Аудит-хук на `open` поймал одну запись на всю ленту из 7452 тестов:
    `tests/test_mcp_integration.py::test_every_tool_name_has_handler` поднимает
    ВРЕМЕННЫЙ проект и зовёт каждый инструмент MCP, включая
    `tausik_update_claudemd`; cwd при этом — корень репозитория. Блок между
    маркерами обоих корневых файлов переписывался состоянием «Tasks: 0/1 done»
    с полностью снесённым хвостом памяти. Подпись двусоставна и обе половины
    объясняются этим расхождением: счётчик 0/1 пришёл из временной базы, а
    «Branch: v1-9-wave» — из git, спрошенного в cwd. Порча идемпотентна
    (writer не пишет, когда содержимое совпадает), поэтому переживала прогоны
    молча и попала в ДВАДЦАТЬ коммитов между v1.0.0 и 2026-08.

    Возвращает ``None``, когда сказать, какой проект описывает эта база, НЕЛЬЗЯ —
    нет backend, нет `db_path`, или база лежит не в `.tausik/`. Вызывающий обязан
    ОТКАЗАТЬ, а не подставить cwd: молча согласиться значит вернуть тот же дефект
    под другим именем. Цена ошибки — потеря контекста, который следующий агент
    читает первым и которому верит.
    """
    be = getattr(svc, "be", None)
    db_path = getattr(be, "db_path", None)
    if not db_path:
        return None
    try:
        tausik_dir = os.path.dirname(os.path.abspath(db_path))
    except (TypeError, ValueError):
        return None
    try:
        from project_config import TAUSIK_DIR
    except ImportError:  # pragma: no cover — путь без scripts/ на sys.path
        TAUSIK_DIR = ".tausik"
    if os.path.basename(tausik_dir) != TAUSIK_DIR:
        return None
    return os.path.dirname(tausik_dir) or None


def resolve_claudemd(project_dir: str) -> str | None:
    """Путь к CLAUDE.md проекта, или None.

    Кандидаты берутся АБСОЛЮТНЫМИ от project_dir, а не относительными от cwd:
    MCP-сервер стоит там, где его запустили, и относительное имя способно
    попасть в чужой файл (тот же класс, что дефект mcp-config-read-paths).
    """
    try:
        from ide_utils import detect_ide, get_ide_dir

        candidates = [
            os.path.join(project_dir, "CLAUDE.md"),
            os.path.join(get_ide_dir(project_dir, detect_ide(project_dir)), "CLAUDE.md"),
        ]
    except ImportError:
        candidates = [
            os.path.join(project_dir, "CLAUDE.md"),
            os.path.join(project_dir, ".claude", "CLAUDE.md"),
        ]
    return next((c for c in candidates if os.path.exists(c)), None)
