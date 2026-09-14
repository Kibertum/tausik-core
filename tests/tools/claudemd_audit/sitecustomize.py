"""Аудит-хук: кто открывает корневые CLAUDE.md / AGENTS.md на ЗАПИСЬ.

Лежит в каталоге, добавленном в PYTHONPATH, поэтому подхватывается КАЖДЫМ
процессом Python — и родительским pytest, и любым подпроцессом, который тест
породит. Предыдущая ловушка (сверка sha256 после каждого теста) дала окно в одну
секунду и девятнадцать подозреваемых в разных воркерах xdist: она видит ФАКТ
записи, но не автора. Этот хук видит автора — он снимает стек в момент открытия.

Ничего не блокирует и ничего не чинит: только записывает строку JSON.

ПОЧЕМУ ФАЙЛ ЛЕЖИТ ЗДЕСЬ, А НЕ В КОРНЕ РЕПОЗИТОРИЯ. Имя `sitecustomize` модуль
получил не для красоты: интерпретатор импортирует его САМ, если находит на
sys.path, и именно это даёт нужное свойство — хук встаёт и в подпроцессах,
которые никто не инструментировал. Оборотная сторона того же свойства: файл с
этим именем в корне репозитория ЗАТЕНИЛ БЫ системный sitecustomize для всякого
процесса Python, запущенного отсюда. Диагностический инструмент такой цены не
стоит, поэтому он живёт в отдельном каталоге и взводится ЯВНО.

КАК ВЗВЕСТИ (Git Bash):
    export PYTHONPATH="$PWD/tests/tools/claudemd_audit:$PYTHONPATH"
    export CLAUDEMD_AUDIT_ROOT="$PWD"
    export CLAUDEMD_AUDIT_LOG="$PWD/.tausik/tmp/claudemd-audit.jsonl"
    python -m pytest -n auto            # лента идёт как обычно
    cat "$CLAUDEMD_AUDIT_LOG"           # события записи, если они были

БЕЗ ОБЕИХ ПЕРЕМЕННЫХ ХУК НЕ СТАВИТСЯ ВОВСЕ — не «ставится и молчит», а не
вызывает sys.addaudithook. Это делает его безопасным для случайного попадания на
PYTHONPATH и проверяется регрессией tests/test_claudemd_audit_hook.py.

ПОЧЕМУ СЛЕПОЙ EXCEPT — И ПОЧЕМУ ЗДЕСЬ ЭТО НЕ НЕБРЕЖНОСТЬ. Три `except
Exception` погашены `noqa: BLE001` СОЗНАТЕЛЬНО. Аудит-хук вызывается на КАЖДОМ
`open()` в процессе; исключение, выпущенное отсюда наружу, уронит не хук, а
наблюдаемую программу — то есть инструмент наблюдения изменит поведение того,
за чем наблюдает, и любой замер под ним станет недействителен. Ловить узкий
класс нельзя: аргументы события приходят из интерпретатора и их форма не
гарантирована контрактом, а `os.path.abspath` на пути-мусоре может бросить чем
угодно. Цена слепоты здесь — потерянное событие в ленте; цена узости — сломанный
прогон.

ЧТО ОН ОДНАЖДЫ НАШЁЛ (сессия #190, задача
claudemd-dynamic-block-wiped-to-an-empty-project). На ПОЛНОЙ ленте — РОВНО ДВА
события записи: CLAUDE.md в 22:46:12.220 и AGENTS.md в 22:46:12.318, оба pid
6808, воркер gw17. Стек назвал виновника без единой догадки:
handlers_skill.py:231-232 handle_update_claudemd -> claudemd_writer.py:68
apply_dynamic_section. Писатель был ОДИН. Ловушка по sha256 на том же дереве
давала 42 события в одну секунду в 19 воркерах и автора назвать не могла — она
отвечает на вопрос «изменился ли файл», а не «кто его изменил». Обе живут в
дереве и обе нужны: tests/claudemd_watch.py дешевле, этот хук — точнее.
"""

import json
import os
import sys
import time
import traceback

_ROOT = os.environ.get("CLAUDEMD_AUDIT_ROOT", "")
_LOG = os.environ.get("CLAUDEMD_AUDIT_LOG", "")
_TARGETS = set()
if _ROOT:
    for _name in ("CLAUDE.md", "AGENTS.md"):
        _TARGETS.add(os.path.normcase(os.path.abspath(os.path.join(_ROOT, _name))))


def _record(path, mode, flags):
    try:
        entry = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}",
            "pid": os.getpid(),
            "worker": os.environ.get("PYTEST_XDIST_WORKER", "main"),
            "path": str(path),
            "mode": mode,
            "flags": flags,
            "cwd": os.getcwd(),
            "argv": sys.argv[:6],
            "stack": [s.rstrip() for s in traceback.format_stack()[:-2]][-18:],
        }
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - см. ПОЧЕМУ СЛЕПОЙ EXCEPT ниже
        pass


def _hook(event, args):
    if event != "open" or not _TARGETS or not _LOG:
        return
    try:
        path, mode, flags = args
    except Exception:  # noqa: BLE001 - см. ПОЧЕМУ СЛЕПОЙ EXCEPT ниже
        return
    if mode is None or "w" not in str(mode) and "a" not in str(mode) and "+" not in str(mode):
        return
    try:
        resolved = os.path.normcase(os.path.abspath(str(path)))
    except Exception:  # noqa: BLE001 - см. ПОЧЕМУ СЛЕПОЙ EXCEPT ниже
        return
    if resolved in _TARGETS:
        _record(path, mode, flags)


if _TARGETS and _LOG:
    sys.addaudithook(_hook)
