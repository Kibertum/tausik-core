"""Вопросы, задаваемые В МОМЕНТ ЗАКРЫТИЯ — последний раз, когда автор ещё может ответить.

ПОЧЕМУ ИМЕННО ТУТ, А НЕ В ОТДЕЛЬНОМ ПРОГОНЕ. У обоих вопросов один и тот же
срок годности. Журнал задачи append-only: выдуманную ссылку на тест через час
уже не исправить, её можно только опровергнуть новой записью. Долг перед автором
тикета живёт ещё меньше — закрытую задачу никто не перечитывает, и напоминание,
пришедшее сметой позже, приходит к тому, кто уже не помнит, о чём был тикет.
Развёрнутая проверка, находящая порчу цитат по всему дереву, существует и
запускается по требованию — она находит ИСТОРИЮ; здесь ловится СВЕЖЕЕ.

ПОЧЕМУ ОНИ В ОДНОМ МОДУЛЕ. Не ради экономии строк, хотя `service_task_done`
стоял ровно на своём пределе. Это одна категория: не «ошибка», из-за которой
закрытие обязано отказать, а «пока ты здесь — вот что останется несделанным».
Ни один из них не блокирует; оба возвращаются текстом и печатаются рядом с
`completed`.

ЧЕГО ЗДЕСЬ НЕТ: обращения к сети и любых действий вовне. Модуль читает строку
задачи и складывает текст.
"""

from __future__ import annotations


def reminders_at_close(slug: str, notes: str | None, task: dict) -> list[str]:
    """Напоминания к печати при закрытии `slug`. Пустой список — норма.

    Порядок постоянный: сначала доказательства (цитаты этой задачи), потом
    долги наружу (тикет). Читатель отказа читает сверху вниз, и вопрос «чем
    подтверждено» стоит раньше вопроса «кому сообщить».
    """
    from closure_citation_check import citation_warning
    from tracker_closure_proposal import proposal_for_task

    out: list[str] = []
    # `notes` is nullable on the row and `citation_warning` takes a str: an empty
    # journal has no citations to judge, which is the same answer as "nothing
    # wrong", so it is normalised here rather than widening the checker.
    cite = citation_warning(slug, notes or "")
    if cite:
        out.append(cite)
    ticket = proposal_for_task(task)
    if ticket:
        out.append(ticket)
    note = _comment_note(slug, task)
    if note:
        out.append(note)
    return out


def _comment_note(slug: str, task: dict) -> str | None:
    """Записка о событии, добавленная В КОММЕНТАРИЙ этой же задачей.

    Спрашивается здесь по той же причине, что и остальные два: автор ещё помнит,
    что записка значила, а через час её уже нельзя ни перенести, ни объяснить.
    Область берётся из объявленной задачей — за её пределами правки не её, и
    сообщать о них значило бы превратить напоминание в шум.
    """
    import json
    import os

    from comment_history_refs import closure_note, new_refs_for_close

    try:
        declared = task.get("relevant_files") or task.get("scope_paths")
        paths = json.loads(declared) if isinstance(declared, str) else (declared or [])
        paths = [p for p in paths if isinstance(p, str) and p.endswith(".py")]
        if not paths:
            return None
        from project_config import find_tausik_dir

        root = os.path.dirname(os.path.abspath(find_tausik_dir()))
        return closure_note(slug, new_refs_for_close(root, paths))
    except Exception:  # noqa: BLE001 — напоминание не смеет уронить закрытие
        return None
