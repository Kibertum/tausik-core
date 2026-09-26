"""A comment that records an EVENT is a memory note filed where nobody looks.

MEASURED, session #277: 2584 references to project history sit inside source
prose across 642 files -- 900 "ЗАМЕР/measured", 743 ISO dates, 402 "decision #N",
387 "session #N", 152 conventions and dead ends. Prose-to-code ratios: scripts
38%, bootstrap 28%, tests 23%, harness 19%.

THE DISTINCTION THIS MODULE IS BUILT ON, and it is not "fewer comments":

  * INVARIANT -- why the code is the way it is. It belongs in the docstring, it is
    read by whoever changes the code next, and it is this project's strongest
    habit. Nothing here touches it.
  * EVENT -- what happened, when, and in which session. It belongs in the project
    memory, where it is searchable, datable, supersedable and paid for once. In a
    comment it is paid for on every read of the file, never updated, and found by
    nobody who did not already open that file.

WHY THE MARKER IS A REFERENCE AND NOT A TONE. "Session #241", "decision #350",
"2026-09-07", "ЗАМЕР" are addresses into the project's own record. A sentence
carrying one is making a claim about history; a sentence explaining a constraint
is not. That is a syntactic difference, which a check can hold, rather than a
stylistic one, which it cannot.

WHAT THIS DOES NOT DO: block. The note is offered at closure with the command
that files it, while the author still remembers what the note meant. A gate that
refused a close over prose would be switched off the same week, and the 2584
already here are a DECLARED REMAINDER for the same reason the closure-citation
count is: the journal is append-only and rewriting history to look tidy is the
harm, not the fix.
"""

from __future__ import annotations

import io
import re
import subprocess
import tokenize

#: Addresses into the project's own record. Each one is a memory that exists (or
#: should) under its own id, so a comment repeating it is a second copy that
#: cannot be superseded.
_EVENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("session", re.compile(r"\b(?:смен[аеуы]|session)\s*#\s*\d+", re.IGNORECASE)),
    ("decision", re.compile(r"\b(?:решени[еяю]|decision)\s*#\s*\d+", re.IGNORECASE)),
    (
        "knowledge",
        re.compile(
            r"\b(?:конвенци[яию]|convention|gotcha|dead\s*end|тупик|память|memory)\s*#\s*\d+",
            re.IGNORECASE,
        ),
    ),
    ("date", re.compile(r"\b20\d\d-\d\d-\d\d\b")),
    ("measurement", re.compile(r"\b(?:ЗАМЕР|ЗАМЕРЕНО|MEASURED)\b")),
)

#: Names of standards this project does not own. A date next to one is the VERSION
#: OF A SPECIFICATION, not something that happened here: "MCP 2026-07-28
#: CacheableResult" says which revision of the protocol the cache header answers
#: to, and moving that into memory would leave the reader unable to tell whether
#: the code still matches the standard.
#:
#: SENAR and RENAR are listed although the project implements them -- a dated
#: version number is a property of THEIR document, not a record of a session here.
_EXTERNAL_STANDARDS = (
    "MCP",
    "RENAR",
    "SENAR",
    "RFC",
    "CVE",
    "CVSS",
    "GHSA",
    "PEP",
    "ISO",
    "OWASP",
    "JSON-RPC",
    "SEP",
)

#: A date the standard's name introduces, name first and within a short reach.
#:
#: Name FIRST only, though the reverse reads just as naturally. A project date
#: FOLLOWED by a standard's name is still a project date -- it merely mentions the
#: standard -- and matching that direction would swallow it.
#:
#: The shape is described rather than quoted, and that is not squeamishness: a
#: reference inside quotation marks is invisible to this module, because comments
#: are read line by line and a quotation that wraps opens on one line and closes
#: on the next. Spelling an example out here would have left a note the module
#: cannot see itself carrying. What the rule costs and what it buys are counted in
#: the journals of spec-dates-are-not-project-events and
#: quoted-example-is-counted-as-a-note.
_SPEC_DATE = re.compile(
    r"\b(?:" + "|".join(_EXTERNAL_STANDARDS) + r")\b[^.\n]{0,24}?\b20\d\d-\d\d-\d\d\b",
    re.IGNORECASE,
)


def event_refs(text: str) -> list[str]:
    """Which kinds of event reference a piece of prose carries, in a stable order.

    A list rather than a bool: the closure note says WHAT kind of record the
    author is duplicating, and "session" and "date" call for different memories.

    Spec versions are masked for the date check ONLY, and the other four kinds
    still read the original text: a line saying "смена #277 привела код к MCP
    2026-07-28" duplicates a session record whatever its date means.
    """
    without_specs = _SPEC_DATE.sub(" ", text)
    return [
        kind
        for kind, pattern in _EVENT_PATTERNS
        if pattern.search(without_specs if kind == "date" else text)
    ]


def comment_part(line: str) -> str:
    """Текст комментария из строки кода, либо пусто.

    Написано сканером по символам, а не `split("#", 1)`: решётка живёт внутри
    строковых литералов — `"github#7"`, `"# not a comment"` — и наивное деление
    объявило бы комментарием половину значения. Ровно этой ошибкой первая версия
    пропускала САМУЮ частую форму записки: хвост у строки кода, а не строка,
    начинающаяся с решётки.
    """
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "\"'":
            quote = char
        elif char == "#":
            return line[index + 1 :].strip()
        index += 1
    return ""


def comment_lines(source: str) -> list[tuple[int, str]]:
    """`(line number, text)` for every comment. Docstrings are not included.

    Comments and docstrings are separated on purpose. A docstring is the declared
    home of the invariant, so an event reference there is a weaker signal: often
    the invariant IS "this literal is frozen because of decision #646". A comment
    beside a line of code is where a working note lands, and that is what the
    owner observed.
    """
    out: list[tuple[int, str]] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                out.append((token.start[0], token.string.lstrip("#").strip()))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return out
    return out


def refs_in_source(source: str) -> list[tuple[int, str, list[str]]]:
    """`(line, comment text, kinds)` for comments carrying an event reference."""
    found: list[tuple[int, str, list[str]]] = []
    for line, text in comment_lines(source):
        kinds = event_refs(text)
        if kinds:
            found.append((line, text, kinds))
    return found


def _added_lines(root: str, paths: list[str]) -> dict[str, list[str]]:
    """Lines ADDED to `paths` since the task started, per file.

    Git decides what is new, because the alternative -- comparing against a
    stored snapshot -- would make the check depend on a file that can go stale,
    and a stale snapshot reports the whole file as new. Any git failure yields
    nothing: a closure must not hinge on the shape of someone's working tree.
    """
    if not paths:
        return {}
    try:
        proc = subprocess.run(
            ["git", "diff", "--unified=0", "--", *paths],
            cwd=root,
            # Путь достижим из MCP: git, спросивший что-нибудь у пустого stdin,
            # подвесил бы сервер, а не только закрытие задачи.
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    per_file: dict[str, list[str]] = {}
    current = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and current:
            per_file.setdefault(current, []).append(line[1:])
    return per_file


def new_refs_for_close(root: str, paths: list[str]) -> list[tuple[str, str, list[str]]]:
    """`(file, comment text, kinds)` for event references the task itself added.

    Only added lines are read, so a file edited beside an old note does not drag
    that note into the report. Reporting what the author did not write is how a
    reminder becomes noise.
    """
    found: list[tuple[str, str, list[str]]] = []
    for rel, lines in _added_lines(root, paths).items():
        if not rel.endswith(".py"):
            continue
        for raw in lines:
            text = comment_part(raw)
            if not text:
                continue
            kinds = event_refs(text)
            if kinds:
                found.append((rel, text, kinds))
    return found


def closure_note(slug: str, found: list[tuple[str, str, list[str]]]) -> str | None:
    """The reminder, or ``None`` when the task added no event reference.

    ``None`` is the common case and has to stay silent: a note printed on every
    close is read on none of them.
    """
    if not found:
        return None
    kinds = sorted({kind for _, _, entry in found for kind in entry})
    lines = [
        f"\nЗАПИСКА В КОММЕНТАРИИ: {len(found)} ссылк(и) на историю добавлено в код.",
    ]
    for rel, text, _ in found[:3]:
        shown = text if len(text) <= 88 else text[:85].rstrip() + "…"
        lines.append(f"  {rel}: {shown}")
    if len(found) > 3:
        lines.append(f"  … и ещё {len(found) - 3}")
    lines.append(f"  Вид записи: {', '.join(kinds)}. В комментарии это ищется только тем, кто уже")
    lines.append("  открыл файл, и оплачивается при каждом чтении. В памяти — ищется и")
    lines.append("  переписывается. Обоснование ИНВАРИАНТА оставьте где оно есть.")
    lines.append(f'  Перенести: .tausik/tausik memory add context "<итог>" "<факт>" --task {slug}')
    return "\n".join(lines)
