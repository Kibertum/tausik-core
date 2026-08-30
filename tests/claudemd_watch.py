"""Наблюдатель за корневыми CLAUDE.md / AGENTS.md на время прогона ленты.

claudemd-dynamic-block-wiped-to-an-empty-project. Динамический блок обоих файлов
затирается состоянием ПУСТОГО проекта («Tasks: 0/1 done», хвост памяти снесён), и
это не редкость: подпись порчи найдена в ДВАДЦАТИ коммитах между релизом v1.0.0
(2026-04-10) и 2026-08-26. Последнее появление замерено по времени — 20:52:36,
ВНУТРИ полного прогона ленты, то есть писатель работает где-то среди тестов.

ЧТО УЖЕ ИСКЛЮЧЕНО ЗАМЕРОМ, ЧТОБЫ НЕ ИСКАЛИ ТАМ ЖЕ. bootstrap.py --init во
временный каталог, запущенный из корня репозитория, sha256 корневых файлов не
меняет. bootstrap.py --ide all без --init — тоже не меняет (замер #191-БД).
Генератор цел: update-claudemd восстанавливает блок из живой базы корректно. Все
35 тестовых файлов, упоминающих CLAUDE.md, прогнанные вместе, файлы не трогают.

ПОЭТОМУ НЕ ГАДАЕМ, А ЛОВИМ. Плагин считает sha256 обоих файлов после КАЖДОГО
теста и записывает первое же изменение: nodeid, воркер xdist, время, sha до и
после, начало нового блока. Ответ «за N тестов файл не изменился» — тоже
результат: он выносит писателя за пределы ленты.

ИНЕРТЕН ПО УМОЛЧАНИЮ. Никакой conftest его не подхватывает; включается только
явным `-p claudemd_watch` при наличии `tests/` в PYTHONPATH. Ничего не чинит и
ничего не восстанавливает — наблюдение не должно менять наблюдаемое.

ЗАПУСК:
    PYTHONPATH=tests CLAUDEMD_WATCH_LOG=<путь> python -m pytest -m '' -p claudemd_watch
"""

from __future__ import annotations

import hashlib
import json
import os
import time

_WATCHED = ("CLAUDE.md", "AGENTS.md")

_REPO_ROOT = os.environ.get("CLAUDEMD_WATCH_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
_LOG = os.environ.get("CLAUDEMD_WATCH_LOG") or os.path.join(_REPO_ROOT, "claudemd-watch.jsonl")

_MARKER_START = "<!-- DYNAMIC:START -->"
_MARKER_END = "<!-- DYNAMIC:END -->"

# Последний известный слепок на ЭТОТ процесс. Под xdist у каждого воркера свой,
# и это правильно: воркер видит и записывает то изменение, которое застал он.
_seen: dict[str, str | None] = {}
_checks = 0


def _worker() -> str:
    return os.environ.get("PYTEST_XDIST_WORKER", "main")


def _digest(path: str) -> str | None:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def _block_head(path: str, limit: int = 400) -> str:
    """Начало динамического блока — чтобы в журнале было видно ЧТО записали."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as e:
        return f"<не прочитан: {e}>"
    start = text.find(_MARKER_START)
    if start == -1:
        return "<маркера DYNAMIC:START нет>"
    start += len(_MARKER_START)
    end = text.find(_MARKER_END, start)
    block = text[start:] if end == -1 else text[start:end]
    return block.strip()[:limit]


def _record(event: dict) -> None:
    event["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    event["worker"] = _worker()
    event["checks_so_far"] = _checks
    try:
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _scan(where: str, nodeid: str | None = None) -> None:
    """Сверить оба файла и записать КАЖДОЕ расхождение с прошлым слепком."""
    global _checks
    _checks += 1
    for name in _WATCHED:
        path = os.path.join(_REPO_ROOT, name)
        now = _digest(path)
        was = _seen.get(name, "<не снят>")
        if was == "<не снят>":
            _seen[name] = now
            _record({"event": "baseline", "where": where, "file": name, "sha": now})
            continue
        if now != was:
            _seen[name] = now
            _record(
                {
                    "event": "CHANGED",
                    "where": where,
                    "nodeid": nodeid,
                    "file": name,
                    "sha_before": was,
                    "sha_after": now,
                    "block_head": _block_head(path),
                }
            )


def pytest_sessionstart(session):  # noqa: ARG001 — хук pytest
    _scan("sessionstart")


def pytest_collection_finish(session):  # noqa: ARG001 — хук pytest
    _scan("collection_finish")


def pytest_runtest_teardown(item, nextitem):  # noqa: ARG001 — хук pytest
    _scan("after_test", nodeid=item.nodeid)


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001 — хук pytest
    _scan("sessionfinish")
    _record({"event": "summary", "checks": _checks, "final": dict(_seen)})
