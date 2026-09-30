"""What a closed task cost, in a unit the price list cannot move.

WHY THIS EXISTS. `cost_actual_usd` is filled on 0 tasks of 1675 and `tokens_actual` on 27,
because the per-call hook records the CALL and not the tokens — 120 of 67 081 rows carry a
token count — while the session-level rows carry tokens and no task slug. The rollup joins
on the slug, finds nothing, and correctly writes NULL. So the framework has never been able
to answer the one question asked of it most often: is a task getting cheaper or dearer.

THE NUMBER IS APPORTIONED, NOT MEASURED. A session's tokens are split across the tasks
worked in it by each task's share of that session's calls. A task that made 30 of a
session's 300 calls is charged a tenth of it. That is an estimate and is called one
everywhere it appears; the alternative — leaving the question unanswered because the exact
figure is unobtainable — is what left it unanswered for five releases.

WHY THE TREND IS SPLIT BY COMPLEXITY. A single median per month reads as the framework
getting dearer, and the first person it misled was its own author. The task mix moved
underneath it: May closed 50 simple / 43 medium / 11 complex, September 25 / 73 / 33. Within
each class the answer is different — simple 27k -> 22k, medium 52k -> 88k, complex 68k ->
130k — so the blended line mixes "the work got heavier" with "the work got dearer" and
cannot separate them. Both numbers are printed, the blended one carrying that warning.

WHY TOKENS AND NOT DOLLARS. Measured on this project, the price per million tokens went
$74.43 (May, opus-4-7) → $10.32 (July, opus-4-8) → $15.76 (September, opus-5). Cost per
task in dollars fell 61% across that span while the work itself grew, so a dollar series
answers "did the price list change" and not "did we get cheaper". Tokens are the unit the
price list cannot move, and the dollar figure is reported beside them with that warning
rather than on its own.
"""

from __future__ import annotations

import collections
import sqlite3
import statistics
from typing import Any, NamedTuple

#: Session-level rows: the only ones that carry a token total.
SESSION_SOURCE = "session_record"

#: Per-call rows: the only ones that carry a task slug.
CALL_SOURCE = "posttool"


#: Below this a median is one or two tasks wearing a trend's clothes.
MIN_SAMPLE = 8

#: A task that declared no complexity. It gets its own line rather than joining a class it
#: never claimed — putting it in one would move that class's median on a guess.
UNDECLARED = "(undeclared)"


class Cell(NamedTuple):
    complexity: str
    tasks: int
    #: None when the sample is under MIN_SAMPLE: absence, not a median of three.
    median: float | None
    p90: float | None


class Month(NamedTuple):
    month: str
    tasks: int
    median: float
    p90: float
    #: Per-complexity breakdown, the line the blended median cannot give.
    cells: tuple[Cell, ...] = ()


class Report(NamedTuple):
    per_task: dict[str, float]
    months: list[Month]
    #: Closed tasks whose sessions recorded no tokens. Absence, never zero.
    absent: int
    #: Every complexity seen, in the order they are printed.
    classes: tuple[str, ...] = ()


def _session_totals(conn: sqlite3.Connection) -> dict[Any, tuple[float, int]]:
    """{session: (tokens, calls)} for sessions that recorded BOTH.

    A session with tokens and no call count cannot be divided among its tasks, and one with
    calls and no tokens has nothing to divide. Either way it is left out rather than
    contributed as a zero, which would pull every median it touched towards free.
    """
    out: dict[Any, tuple[float, int]] = {}
    rows = conn.execute(
        "SELECT session_id, SUM(tokens_total) t, SUM(tool_calls) k "
        "FROM usage_events WHERE source = ? GROUP BY 1",
        (SESSION_SOURCE,),
    )
    for session_id, tokens, calls in rows:
        if tokens and calls:
            out[session_id] = (float(tokens), int(calls))
    return out


def _calls_per_task(conn: sqlite3.Connection) -> dict[str, collections.Counter]:
    """{slug: {session: calls}} — how much of each session belongs to each task."""
    per: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    rows = conn.execute(
        "SELECT task_slug, session_id, COUNT(*) n FROM usage_events "
        "WHERE task_slug IS NOT NULL AND source = ? GROUP BY 1, 2",
        (CALL_SOURCE,),
    )
    for slug, session_id, n in rows:
        per[slug][session_id] = int(n)
    return per


def build(conn: sqlite3.Connection) -> Report:
    """Apportion session tokens onto closed tasks, and roll the result up by month."""
    totals = _session_totals(conn)
    per = _calls_per_task(conn)
    closed = {
        slug: (done, complexity or UNDECLARED)
        for slug, done, complexity in conn.execute(
            "SELECT slug, completed_at, complexity FROM tasks "
            "WHERE status = 'done' AND completed_at IS NOT NULL"
        )
    }

    per_task: dict[str, float] = {}
    by_month: dict[str, list[float]] = collections.defaultdict(list)
    by_cell: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    seen_classes: set[str] = set()
    absent = 0
    for slug, sessions in per.items():
        if slug not in closed:
            continue
        charged = 0.0
        reached = False
        for session_id, calls in sessions.items():
            total = totals.get(session_id)
            if not total:
                continue
            charged += total[0] * (calls / total[1])
            reached = True
        if not reached:
            absent += 1
            continue
        done, complexity = closed[slug]
        per_task[slug] = charged
        by_month[done[:7]].append(charged)
        by_cell[(done[:7], complexity)].append(charged)
        seen_classes.add(complexity)

    order = [c for c in ("simple", "medium", "complex", UNDECLARED) if c in seen_classes]
    order += sorted(seen_classes - set(order))

    months = []
    for month in sorted(by_month):
        values = sorted(by_month[month])
        cells = []
        for complexity in order:
            sample = sorted(by_cell.get((month, complexity), ()))
            if not sample:
                continue
            enough = len(sample) >= MIN_SAMPLE
            cells.append(
                Cell(
                    complexity=complexity,
                    tasks=len(sample),
                    # Under the threshold the count still shows — the reader needs to know
                    # the class was worked — but no median is offered for it.
                    median=statistics.median(sample) if enough else None,
                    p90=sample[int(len(sample) * 0.9)] if enough else None,
                )
            )
        months.append(
            Month(
                month=month,
                tasks=len(values),
                median=statistics.median(values),
                p90=values[int(len(values) * 0.9)],
                cells=tuple(cells),
            )
        )
    return Report(per_task=per_task, months=months, absent=absent, classes=tuple(order))


def render(report: Report, closed_total: int) -> str:
    """The report, with the two things that make it readable honestly: how it was derived
    and how far it reaches."""
    reached = len(report.per_task)
    lines = [
        "Cost per closed task — APPORTIONED, not measured per task.",
        "  A session's tokens are split across its tasks by each task's share of that "
        "session's calls.",
        f"  COVERAGE: {reached} of {closed_total} closed task(s) reached "
        f"({100 * reached / closed_total:.0f}%); {report.absent} more were worked in "
        "sessions that recorded no tokens and are absent, not zero.",
        "  TOKENS, not dollars: on this project the price per million tokens moved "
        "$74.43 -> $10.32 -> $15.76 between May and September, so a dollar series would "
        "report the price list rather than the work.",
        "",
        f"{'month':9}{'tasks':>7}{'median':>12}{'p90':>12}   per complexity",
    ]
    for row in report.months:
        cells = []
        for cell in row.cells:
            if cell.median is None:
                # The COUNT still shows: the class was worked, and hiding that would read
                # as though nobody touched it. Only the median is withheld.
                cells.append(f"{cell.complexity}: n={cell.tasks}, median absent (<{MIN_SAMPLE})")
            else:
                cells.append(f"{cell.complexity}: n={cell.tasks}, {cell.median / 1000:.0f}k")
        lines.append(
            f"{row.month:9}{row.tasks:7}{row.median / 1000:11.0f}k{row.p90 / 1000:11.0f}k   "
            + " | ".join(cells)
        )
    if len(report.months) >= 2:
        first, last = report.months[0], report.months[-1]
        ratio = last.median / first.median if first.median else 0
        lines += [
            "",
            f"BLENDED {first.month} -> {last.month}: median {first.median / 1000:.0f}k -> "
            f"{last.median / 1000:.0f}k ({ratio:.1f}x) — READ THE PER-COMPLEXITY FIGURES "
            "INSTEAD. The task mix is not constant between months, so a blended line mixes "
            "'the work got heavier' with 'the work got dearer' and cannot tell them apart.",
        ]
        for complexity in report.classes:
            pair = [
                cell.median
                for row in (first, last)
                for cell in row.cells
                if cell.complexity == complexity and cell.median is not None
            ]
            # A class needs a median at BOTH ends to have a trend. One end alone is a
            # single measurement, and printing a ratio against nothing is how a table
            # turns into a claim.
            if len(pair) == 2:
                was, now = pair
                lines.append(
                    f"  {complexity:12} {was / 1000:.0f}k -> {now / 1000:.0f}k ({now / was:.2f}x)"
                )
        lines.append(
            "  Descriptive, not a forecast — even within a class, task size is not held constant."
        )
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
