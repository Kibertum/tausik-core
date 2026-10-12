"""Обход соседних MCP-серверов проекта — отдельно от слежения за модулями.

Вынесено из self_check, чей докстринг перечислял ДВЕ сущности сразу: устаревшие
модули в памяти и соседние серверы. Перечисление сущностей в строке документации
и есть признак плохого разреза (конвенция #348), а гейт размера лишь предъявил
счёт: файл перерос 500 строк ровно в тот момент, когда в нём появился вынесенный
предикат сопоставления.

Разрез настоящий: слежение за mtime модулей и обход чужих процессов не делят ни
одной строки состояния и отвечают на разные вопросы — «моя ли память протухла» и
«кто ещё поднят рядом».
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any


def _command_belongs_to_project(
    cmdline: str, project_dir: str, needle: str, cwd: str | None = None
) -> bool:
    """Запущен ли этот процесс сервером ЭТОГО проекта.

    Прежде сопоставление требовало, чтобы АБСОЛЮТНЫЙ путь проекта встречался в
    чужой командной строке. Серверы запускаются относительно —
    ``python ./.claude/mcp/project/server.py --project .`` — и абсолютного пути
    там нет и не будет. Условие не выполнялось никогда: замер на живой машине
    дал десять работающих процессов и счётчик «соседей 0». Ноль, означающий
    «не умею считать», неотличим от нуля, означающего «соседей нет», и вся
    проверка молча превращалась в украшение.

    Считаем совпадением любой из двух признаков, потому что оба однозначно
    указывают на наш сервер:

    * абсолютный путь проекта в командной строке — прежний способ, он верен
      для запусков по полному пути и остаётся;
    * запуск того же серверного модуля с рабочим каталогом, равным проекту, —
      это и есть относительный случай, ради которого правка делается.

    Рабочий каталог передаётся АРГУМЕНТОМ, а не читается отсюда: процедура
    обязана оставаться чистой, чтобы её можно было проверить без поднятия
    процессов. Отсутствие такого шва и было причиной, по которой дефект нельзя
    было закрыть тестом. `cwd=None` означает «неизвестен» и НЕ засчитывается за
    совпадение: догадка вместо измерения даёт тот же ноль, что и раньше.
    """
    if needle.lower() not in cmdline.replace("\\", "/").lower():
        return False
    project_norm = os.path.normpath(project_dir).replace("\\", "/").lower()
    if project_norm in cmdline.replace("\\", "/").lower():
        return True
    if cwd and os.path.normpath(cwd).replace("\\", "/").lower() == project_norm:
        return True
    return False


def _cwd_of(pid: int) -> str | None:
    """Рабочий каталог процесса, если ОС даёт его дёшево. Иначе None.

    Только Linux: ``/proc/<pid>/cwd`` — одна ссылка. На Windows это требует
    открытия чужого процесса, а на macOS — вызова lsof; и то и другое дороже
    самой проверки, поэтому там остаётся сопоставление по командной строке.
    Неизвестное значение возвращается как None и НЕ засчитывается за
    совпадение: догадка вместо измерения — это тот же ноль, что и раньше.
    """
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except (OSError, AttributeError, ValueError):
        return None


def _enumerate_sibling_mcps(self_pid: int, project_dir: str) -> dict[str, Any]:
    """Best-effort sibling enumeration. Returns `{count, pids, error}`.

    `count == -1` means we could not introspect — the agent should treat
    this as "unknown, check manually" rather than "no siblings".

    v14b-defect-mcp-self-check-venv-launcher: also exclude the direct
    parent PID. On Windows, `venv\\Scripts\\python.exe` is a launcher
    shim that re-execs the real interpreter as a child while keeping the
    same command line; the parent process matches the same needle/project
    filter as the child and would otherwise count as a "sibling MCP",
    producing a chronic +1 false-positive that masquerades as a real
    leak. POSIX rarely shows the same shape (venv usually returns the
    interpreter's PID directly), but `os.getppid()` works on all
    platforms so the guard is uniform.
    """
    needle = "mcp/project/server.py"
    # Нормализация пути живёт внутри _command_belongs_to_project: все четыре
    # ветки обхода процессов зовут один предикат, и второй копии правила здесь
    # быть не должно.
    pids: list[int] = []
    err: str | None = None
    try:
        parent_pid = os.getppid()
    except Exception:  # noqa: BLE001
        parent_pid = -1  # never matches a real PID — guard becomes a no-op
    if sys.platform == "win32":
        # Two introspection paths in priority order:
        #   1. wmic.exe — present on legacy Windows / older Win11 builds
        #   2. PowerShell `Get-CimInstance Win32_Process` — modern Windows
        #      (Win11 24H2+ removed wmic from the base image)
        # Each fallback ONLY fires when the prior one raised FileNotFoundError
        # (binary missing). Real failures (permission, hang) propagate as the
        # `err` string and stop the chain — we do not paper over genuine
        # errors with the next backend.
        import subprocess

        wmic_used = False
        try:
            r = subprocess.run(
                [
                    "wmic",
                    "process",
                    "where",
                    "name='python.exe'",
                    "get",
                    "ProcessId,CommandLine",
                    "/FORMAT:CSV",
                ],
                capture_output=True,
                text=True,
                timeout=4,
            )
            wmic_used = True
            for line in r.stdout.splitlines():
                if needle not in line:
                    continue
                parts = line.rsplit(",", 1)
                if len(parts) != 2:
                    continue
                cmd, raw_pid = parts
                try:
                    pid = int(raw_pid.strip())
                except ValueError:
                    continue
                if pid == self_pid or pid == parent_pid:
                    continue
                if _command_belongs_to_project(cmd, project_dir, needle):
                    pids.append(pid)
        except FileNotFoundError:
            # wmic absent → try PowerShell.
            try:
                ps_query = (
                    "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
                    'ForEach-Object { "$($_.ProcessId)|$($_.CommandLine)" }'
                )
                r = subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        ps_query,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                for line in r.stdout.splitlines():
                    if needle not in line:
                        continue
                    raw_pid, _, cmd = line.partition("|")
                    try:
                        pid = int(raw_pid.strip())
                    except ValueError:
                        continue
                    if pid == self_pid or pid == parent_pid:
                        continue
                    if _command_belongs_to_project(cmd, project_dir, needle):
                        pids.append(pid)
            except FileNotFoundError as e:
                err = f"wmic and powershell both missing: {e}"
            except Exception as e:  # noqa: BLE001
                err = f"powershell Get-CimInstance failed: {e}"
        except Exception as e:  # noqa: BLE001
            if wmic_used:
                err = f"wmic introspection failed: {e}"
            else:
                err = f"wmic startup failed: {e}"
    else:
        # POSIX: prefer /proc, fall back to ps.
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                pid = int(entry)
                if pid == self_pid or pid == parent_pid:
                    continue
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmdline = f.read().decode("utf-8", errors="replace")
                except OSError:
                    continue
                # cwd читается только здесь: относительный запуск встречается
                # прежде всего на Linux, и только там ОС отдаёт рабочий каталог
                # одной ссылкой. На остальных платформах он остаётся None, и
                # сопоставление идёт по командной строке, как раньше.
                if _command_belongs_to_project(cmdline, project_dir, needle, _cwd_of(pid)):
                    pids.append(pid)
        except FileNotFoundError:
            try:
                import subprocess

                r = subprocess.run(
                    ["ps", "-A", "-o", "pid=,command="],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
                for line in r.stdout.splitlines():
                    if not _command_belongs_to_project(line, project_dir, needle):
                        continue
                    parts = line.strip().split(None, 1)
                    if len(parts) < 2:
                        continue
                    try:
                        pid = int(parts[0])
                    except ValueError:
                        continue
                    if pid != self_pid and pid != parent_pid:
                        pids.append(pid)
            except Exception as e:  # noqa: BLE001
                err = f"ps fallback failed: {e}"
        except Exception as e:  # noqa: BLE001
            err = f"/proc walk failed: {e}"
    return {
        "count": len(pids) if err is None else -1,
        "pids": pids,
        "error": err,
    }


# Process-scoped TTL cache for the sibling enumeration. The enumeration spawns a
# PowerShell Get-CimInstance on modern Windows (wmic is gone from Win11 26200),
# ~0.6-1s over 100+ processes — paying that on EVERY self_check made /start look
# like a hang. Memoized per project_dir so repeated checks in a session reuse it.
_SIBLING_ENUM_CACHE: dict[str, tuple[float, Any]] = {}


def _enumerate_sibling_mcps_cached(self_pid: int, project_dir: str) -> dict[str, Any]:
    """TTL-cached wrapper over `_enumerate_sibling_mcps` (AC3, decision #189).

    Falls back to a direct (uncached) call if the reaper helper is unavailable —
    correctness before latency, and the MCP server must never crash on a tool
    call because an optional helper failed to import.
    """
    try:
        from mcp_reaper import SIBLING_ENUM_TTL_SECONDS, cached_enumerate
    except Exception:  # noqa: BLE001 — helper missing → just enumerate directly
        return _enumerate_sibling_mcps(self_pid, project_dir)
    return cached_enumerate(
        os.path.normpath(project_dir),
        lambda: _enumerate_sibling_mcps(self_pid, project_dir),
        ttl=SIBLING_ENUM_TTL_SECONDS,
        now=time.monotonic(),
        cache=_SIBLING_ENUM_CACHE,
    )
