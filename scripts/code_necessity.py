"""The question "is code needed at all" asked once, at the start, as a line of text.

WHY NOT A GATE. The project already has six, and a seventh required field is filled
without looking; that is the whole of AC3. The rate at which closures record a
refusal was measured before anything was built, and it answers the design question
by itself: 3.0% in 2026-03, 2.7% in 04, 3.1% in 05, 0.0% in 06, then 10.8% in 07,
27.5% in 08, 23.3% in 09. The discipline grew roughly eightfold in three months
with no mechanism at all -- so a mechanism is not what was missing, and one that
blocked would be resented rather than obeyed.

WHY IT IS NOT PRINTED EVERY TIME. A note shown on every start is read on none of
them. Refusal rate by complexity, over 1620 closures: simple 6.9% (35/508), medium
12.4% (92/741), complex 14.4% (25/174). By role, architect leads at 15.1%
(27/179). The question therefore pays on the larger tasks, not the small ones,
which is the opposite of where one would put a cheap check. Medium and complex
together hold 72% of all recorded refusals.

THE ORDER IS THE CONTENT. Is any code needed; then, is it already in the standard
library or a native capability; only then write something. Reversing those steps is
how a project ends up with its own implementation of something it already had.
"""

from __future__ import annotations

from typing import Any

#: Where the question pays, measured rather than assumed -- see the module docstring.
_WORTH_ASKING = frozenset({"medium", "complex"})


def code_necessity_prompt(task: dict[str, Any]) -> str:
    """The prompt for this task, or ``""`` when it is not worth a line.

    ``""`` is the common case and has to stay that way: silence on the 508 simple
    tasks is what keeps the line readable on the 915 where refusal is three times
    as likely.
    """
    if (task.get("complexity") or "").strip().lower() not in _WORTH_ASKING:
        return ""
    return (
        "Нужен ли код: сначала спросите, нужен ли он вообще; затем — нет ли этого в "
        "стандартной библиотеке или в готовой возможности; и только потом пишите своё. "
        "Если ответ «не нужен» — это ЗАКРЫТИЕ с причиной, а не зависшая задача: "
        f'`tausik task obsolete {task.get("slug", "<slug>")} --reason "<что и где записано>"`.'
    )
