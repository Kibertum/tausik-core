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
    done_count = sum(1 for t in tasks if t["status"] == "done")

    session_info = f"#{session['id']} (active)" if session else "none"
    lines = [
        "## Current State",
        f"Session: {session_info} | Branch: {resolve_branch(project_dir)} | "
        f"Version: {resolve_version()}",
        f"Tasks: {done_count}/{len(tasks)} done, {len(active)} active, {len(blocked)} blocked",
    ]
    if active:
        lines.append(f"Active: {', '.join(t['slug'] for t in active)}")
    if blocked:
        lines.append(f"Blocked: {', '.join(t['slug'] for t in blocked)}")

    if (be := getattr(svc, "be", None)) is not None:
        try:
            import service_knowledge_aggregates

            if memory_tail := service_knowledge_aggregates.build_compact_memory_tail(be):
                lines.append("")
                lines.extend(memory_tail)
        except Exception:  # noqa: BLE001 — best-effort: см. docstring
            pass

    return "\n".join(lines)


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
