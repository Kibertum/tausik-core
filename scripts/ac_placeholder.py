"""Measure the SUBSTANCE of a goal or acceptance criteria, templates stripped.

QG-0 used to check that the fields were non-empty, so a template, a TODO or an
empty evidence table passed as a criterion. Families of placeholder, split as in
check-context-budget.mjs (github.com/kiaquila/unicorn-hub, MIT), plus one this
project's own data produced:

  * template brackets — `<...>`, `[UPPER_CASE]`, `{{...}}`;
  * promise words — TODO, TBD, FIXME, NEEDS CLARIFICATION, «уточнить», «заглушка»,
    «добавить позже», placeholder;
  * an EMPTY markdown table — a header row and a separator row with no data;
  * an unexpanded shell substitution — `$(...)`, `${VAR}`: one closed task here
    carries the criterion `$(cat /tmp/ac.txt)` verbatim, because the shell that
    was meant to expand it never ran.

The placeholders are REMOVED before measuring; what remains is counted in words
of two or more letters, in Latin and Cyrillic alike.

A fifth family is the vague claim that names no check — «работает корректно»,
"works as expected" — removed the same way.

THRESHOLDS, from the 1,372 closed tasks with criteria (session #267): the
thinnest real criteria carry 9 words and the thinnest real goal 3. The vague
`1. Работает корректно 2. Ошибка при пустом поле` keeps 4 once its vague claim is
removed, while a terse real one (`1. README exists. 2. Error if file already
exists.`) keeps 7. So MIN_AC_WORDS = 5 and MIN_GOAL_WORDS = 3: no real task in
the database is refused, and that template is.
"""

from __future__ import annotations

import re

MIN_AC_WORDS = 5
MIN_GOAL_WORDS = 3

_PLACEHOLDERS = (
    re.compile(r"<[^<>\n]{1,80}>"),
    re.compile(r"\[[A-ZА-ЯЁ0-9_ -]{2,}\]"),
    re.compile(r"\{\{[^{}\n]{0,80}\}\}"),
    re.compile(r"\$\([^()\n]*\)|\$\{[^{}\n]*\}"),
    re.compile(
        r"\b(?:TODO|TBD|FIXME|NEEDS CLARIFICATION|placeholder)\b|уточнить|заглушк\w*|добавить позже",
        re.IGNORECASE,
    ),
    # Vague claims that name no check: removed like a template.
    re.compile(
        r"(?:работает|работают|всё работает)\s+(?:корректно|правильно|как ожидается)|"
        r"\bworks?\s+(?:correctly|as expected|fine)\b|\bas expected\b",
        re.IGNORECASE,
    ),
)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё]{2,}")


def _drop_empty_tables(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        header, sep = lines[i], lines[i + 1] if i + 1 < len(lines) else ""
        has_data = i + 2 < len(lines) and _TABLE_ROW.match(lines[i + 2])
        if _TABLE_ROW.match(header) and _TABLE_SEP.match(sep) and not has_data:
            i += 2
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def strip_placeholders(text: str) -> str:
    text = _drop_empty_tables(text or "")
    for pattern in _PLACEHOLDERS:
        text = pattern.sub(" ", text)
    return text


def substance(text: str) -> int:
    """Words of two or more letters that remain once placeholders are removed."""
    return len(_WORD.findall(strip_placeholders(text)))


def refusal(goal: str, ac: str) -> str | None:
    """A QG-0 message when the goal or the criteria are a placeholder, else None."""
    problems = []
    if substance(goal) < MIN_GOAL_WORDS:
        problems.append(
            f"the goal has {substance(goal)} word(s) of substance (need {MIN_GOAL_WORDS})"
        )
    if substance(ac) < MIN_AC_WORDS:
        problems.append(
            f"the acceptance criteria have {substance(ac)} word(s) of substance (need {MIN_AC_WORDS})"
        )
    if not problems:
        return None
    return (
        "QG-0 Context Gate: " + "; ".join(problems) + ". Templates, TODO/TBD, empty tables and "
        "unexpanded $(…) are removed before counting — write what is checked and how."
    )
