"""ROADMAP.md — the release map, DERIVED from the live DB instead of drawn.

The predecessor was a PDF built on 2026-08-12 whose page 4 asked "does it work
for other people?" as the question of version 1.9. Ten days later decision #256
redefined 1.9 as a refactor of the EVIDENCE CORE and took that question off the
version. Nothing connected the two, so the map went on answering a question the
project had already dropped — and nobody could tell, because a PDF has no state
to compare against.

Everything here is therefore read, not written:

* WHICH stories are in the release is the owner's declaration, and it is read
  back out of the decisions — the newest decision that DECLARES the composition
  («Состав: …»), or, in a journal that never wrote that line, the newest one
  that names two or more stories (`release_roadmap_composition`). Naming them
  in this file would put the owner's call in my source, where it would rot the
  same way the PDF did.
* HOW MANY tasks each story still holds is counted in the database at reissue
  time. A count typed into a document is true once.
* WHY 1.9 is what it is comes from the charter decision, QUOTED from the row —
  the earliest decision that named this composition points at it by number.

What may NOT be derived says so out loud rather than guessing: no composition
decision at all is a refusal (`RoadmapUnreadable`), not an empty map, and a
missing trajectory line is reported as "not recorded" rather than as no points.
An unreadable source and an empty answer are different answers.

Freshness is guarded by tests/test_release_roadmap.py, which regenerates from
the live DB and compares to the committed file — the same shape of control as
the manifest's, and for the same reason: a stale published map is a false
statement, worse than no map.

Reissue: ``tausik doc roadmap``. Check: ``tausik doc roadmap --check``.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from release_roadmap_composition import (  # noqa: F401 — re-exported for callers and tests
    RoadmapUnreadable,
    _stories,
    composition,
)

OUTPUT_FILENAME = "ROADMAP.md"

#: Task statuses that mean "still owed". Derived from the schema's CHECK rather
#: than listed: everything that is not `done` is remaining work, and a new
#: status added tomorrow counts as remaining without an edit here.
DONE_STATUS = "done"

#: The one non-done status the map names, because being stuck is a property of
#: the PLAN. Every other in-flight status (`active`, `review`) describes the
#: current minute, and printing it made the committed map stale the instant a
#: task was started — see `_blocked`.
BLOCKED_STATUS = "blocked"

#: The snapshot paragraph. The date is a literal on purpose and it is the ONE
#: literal in this file: it is a property of an artifact that will never be
#: rebuilt, so it cannot drift. Reading it off the file's mtime was rejected —
#: mtime differs in every clone, which would make the freshness guard report on
#: the machine instead of on the project, and the file is gitignored, so most
#: clones do not have it at all.
PDF_SNAPSHOT_DATE = "2026-08-12"


def _task_counts(conn: sqlite3.Connection, story_id: int) -> dict[str, int]:
    return {
        status: n
        for status, n in conn.execute(
            "SELECT status, COUNT(*) FROM tasks WHERE story_id = ? GROUP BY status",
            (story_id,),
        )
    }


def _remaining(counts: dict[str, int]) -> int:
    return sum(n for status, n in counts.items() if status != DONE_STATUS)


def _blocked(counts: dict[str, int]) -> int:
    """How many tasks wait on something. A fact about the PLAN, so it belongs here.

    This column replaced a full per-status breakdown, and the reason is the one
    property this whole artifact rests on: the map must change when the release
    changes and NOT otherwise. The breakdown printed `active 1` the moment any
    task was started, so simply opening a task made the committed map stale and
    reddened the freshness guard on a file nobody had touched — three times in
    one shift. Who is holding what right now is a question `tausik team`
    answers; what remains, and how much of it is stuck, is this one's.
    """
    return counts.get(BLOCKED_STATUS, 0)


def _out_of_scope(conn: sqlite3.Connection, comp: dict[str, Any]) -> list[dict[str, Any]]:
    """Stories of the release's own epics that the composition does NOT name.

    Derived by subtraction, never listed: what is out of the release is exactly
    what the decision in force did not put in, and computing it any other way
    would let the two lists disagree.
    """
    inside = {s["slug"] for s in comp["stories"]}
    epics = {s["epic_slug"] for s in comp["stories"]}
    return [
        st
        for slug, st in sorted(_stories(conn).items())
        if st["epic_slug"] in epics and slug not in inside
    ]


def _quote(text: str) -> list[str]:
    """Markdown blockquote of a decision, paragraphs preserved."""
    out: list[str] = []
    for i, para in enumerate([p for p in (text or "").split("\n") if p.strip()]):
        if i:
            out.append(">")
        out.append(f"> {para.strip()}")
    return out


def render(conn: sqlite3.Connection) -> str:
    """The whole of ROADMAP.md as text. No clock is read: see the guard test."""
    comp = composition(conn)
    basis, charter = comp["basis"], comp["charter"]
    version = comp["version"] or "(версия в решении о составе не названа)"
    lines: list[str] = [
        f"# Дорожная карта TAUSIK {version}",
        "",
        "<!-- ПОРОЖДЁННЫЙ ФАЙЛ. Руками не редактируется: перевыпуск —",
        "     `tausik doc roadmap`, проверка свежести — `tausik doc roadmap --check`.",
        "     Состав релиза читается из решений владельца, счётчики — из живой БД. -->",
        "",
    ]
    lines += _charter_section(charter, version)
    lines += _scope_section(conn, comp, basis, version)
    lines += _out_section(conn, comp)
    lines += _trajectory_section(conn, comp, basis)
    lines += _pdf_section(version)
    return "\n".join(lines).rstrip() + "\n"


def _charter_section(charter: dict[str, Any] | None, version: str) -> list[str]:
    lines = ["## Вопрос версии", ""]
    if charter is None:
        lines += [
            f"Решение, определяющее {version}, из журнала решений не читается. "
            "Это НЕ значит, что его нет: это значит, что состав в силе на него "
            "не ссылается, и связь надо восстановить решением, а не догадкой.",
            "",
        ]
        return lines
    lines += [
        f"Задано решением #{charter['id']} от {charter['created_at'][:10]}:",
        "",
    ]
    lines += _quote(charter["decision"])
    lines += [""]
    return lines


def _scope_section(
    conn: sqlite3.Connection,
    comp: dict[str, Any],
    basis: dict[str, Any],
    version: str,
) -> list[str]:
    if comp.get("declared"):
        source = (
            "Состав — из последнего решения, ОБЪЯВИВШЕГО его строкой «Состав:»: "
            f"#{basis['id']} от {basis['created_at'][:10]}; решения после него, "
            "которые лишь упоминают истории, состав не меняют."
        )
    else:
        source = (
            "Состав — из последнего решения, упоминающего две и более истории: "
            f"#{basis['id']} от {basis['created_at'][:10]}. Явной строки "
            "«Состав:» журнал не содержит, так что это вывод из прозы, а не "
            "объявление; пересказ состава строкой снимет двусмысленность."
        )
    lines = [
        f"## Что входит в {version}",
        "",
        f"{source} Счётчики сняты с живой базы в момент перевыпуска этого файла.",
        "",
        "| История | Статус | Осталось | Заблокировано | Закрыто |",
        "|---|---|---|---|---|",
    ]
    total_left = total_done = total_blocked = 0
    for st in comp["stories"]:
        counts = _task_counts(conn, st["id"])
        left, done, blocked = (
            _remaining(counts),
            counts.get(DONE_STATUS, 0),
            _blocked(counts),
        )
        total_left += left
        total_done += done
        total_blocked += blocked
        lines.append(
            f"| `{st['slug']}`<br>{st['title']} | {st['status']} | {left} | {blocked} | {done} |"
        )
    lines += [
        f"| **Итого** | | **{total_left}** | **{total_blocked}** | **{total_done}** |",
        "",
    ]
    return lines


def _out_section(conn: sqlite3.Connection, comp: dict[str, Any]) -> list[str]:
    """Stories the composition does not name — OPEN ones apart from DONE ones.

    One table with one caption called both "not in this version", and for a
    closed story that is false: its work is in the release tree, it is only not
    part of what the release PROMISES. The deferred cost — the reason this
    section exists — is carried by the open stories alone.
    """
    outside = _out_of_scope(conn, comp)
    epics = ", ".join(sorted({s["epic_slug"] for s in comp["stories"]}))
    lines = [
        "## Что в релиз НЕ входит",
        "",
        f"Истории эпиков ({epics}), которых решение о составе не называет.",
        "",
    ]
    if not outside:
        lines += ["Таких историй нет: эпики целиком в релизе.", ""]
        return lines
    open_: list[dict[str, Any]] = []
    done: list[dict[str, Any]] = []
    for st in outside:
        (done if st["status"] == DONE_STATUS else open_).append(st)
    lines += [
        "**Открытые — отложенная цена.** Они не отменены — они не в этой версии, "
        "и их остаток здесь для того, чтобы граница релиза была видна вместе с "
        "ценой, которую она отложила.",
        "",
    ]
    if not open_:
        lines += ["Открытых историй вне состава нет.", ""]
    else:
        lines += ["| История | Статус | Осталось |", "|---|---|---|"]
        for st in open_:
            counts = _task_counts(conn, st["id"])
            lines.append(f"| `{st['slug']}` | {st['status']} | {_remaining(counts)} |")
        lines += [""]
    if done:
        lines += [
            "**Закрытые, составом не названные.** Их работа в дереве релиза, но "
            "обещанием релиза она не объявлена; отложенной цены у них нет.",
            "",
            "| История | Закрыто |",
            "|---|---|",
        ]
        for st in done:
            counts = _task_counts(conn, st["id"])
            lines.append(f"| `{st['slug']}` | {counts.get(DONE_STATUS, 0)} |")
        lines += [""]
    return lines


def _trajectory_section(
    conn: sqlite3.Connection, comp: dict[str, Any], basis: dict[str, Any]
) -> list[str]:
    live = sum(_remaining(_task_counts(conn, s["id"])) for s in comp["stories"])
    lines = ["## Траектория объёма", ""]
    points = comp["points"]
    if points is None:
        lines += [
            f"Решение #{basis['id']} траекторию не записало — не «ноль точек», "
            "а не записало. Ряд восстанавливается по журналу решений об объёме.",
            "",
        ]
    else:
        lines += [
            f"Точки, как их записало решение #{basis['id']}:",
            "",
            "```",
            " → ".join(points),
            "```",
            "",
        ]
        if points:
            tail = (
                "Живая база это подтверждает: после решения счёт не двигался."
                if points[-1] == str(live)
                else (
                    "Разница — это работа, закрытая или заведённая ПОСЛЕ решения; "
                    "объявленное число не ошибочно, оно просто старше."
                )
            )
            lines += [
                f"Объявлено там же: {points[-1]}. В живой базе сейчас: {live}. {tail}",
                "",
            ]
    return lines


def _pdf_section(version: str) -> list[str]:
    return [
        "## TAUSIK-roadmap.pdf — снимок, который сознательно не переиздаётся",
        "",
        f"PDF собран {PDF_SNAPSHOT_DATE} и на стр. 4 объявляет вопросом {version} "
        "«Работает ли у чужих?». Решение о переопределении версии принято позже "
        "и этот вопрос с версии сняло, так что снимок разошёлся с релизом по "
        "существу, а не по формулировке.",
        "",
        "Снимок НЕ переиздаётся и НЕ удаляется: он — датированная запись того, "
        "чем релиз считался в момент сборки, и переписать её значило бы стереть "
        "историю решения. Под git он не ставится (правило в `.gitignore`) — "
        "бинарник со своей копией тех же утверждений есть второе место, где им "
        "расходиться, и ничего за ним не следит.",
        "",
        "Действующая карта — этот файл. Он порождается из живой базы, и тест "
        "перегенерирует его при каждом прогоне: разойтись с состоянием "
        "незаметно, как разошёлся PDF, он не может.",
        "",
    ]


def output_path(root: str) -> str:
    return os.path.join(root, OUTPUT_FILENAME)


def run_main(conn: sqlite3.Connection, root: str, check: bool = False) -> int:
    """Write (or verify) ROADMAP.md. Returns a process exit code."""
    path = output_path(root)
    fresh = render(conn)
    if check:
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                committed = fh.read()
        except OSError as exc:
            print(f"{OUTPUT_FILENAME} unreadable ({exc}) — reissue: tausik doc roadmap")
            return 1
        if committed != fresh:
            print(
                f"{OUTPUT_FILENAME} is stale — the committed map no longer matches "
                "the live database. Reissue: tausik doc roadmap. Closing a task "
                "moves these counters, so the reissue belongs AFTER `task done` "
                "and before the commit."
            )
            return 1
        print(f"{OUTPUT_FILENAME} is current.")
        return 0
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        fh.write(fresh)
    os.replace(tmp, path)  # atomic — never a half-written map on disk
    print(f"Wrote {path}")
    return 0
