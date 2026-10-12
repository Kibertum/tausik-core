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
that files it, while the author still remembers what the note meant. Each task is
compared with its persisted start snapshot, so deleting an old note cannot buy an
allowance for a new one. A missing snapshot is named as NOT CHECKED, never clean.
"""

from __future__ import annotations

import ast
import fnmatch
import io
import os
import re
import stat
import subprocess
import tokenize
from dataclasses import dataclass
from datetime import date

import task_baseline

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
#:
#: MATCHED IN UPPER CASE, and the case is load-bearing. `sep` and `iso` are everyday
#: vocabulary in this tree -- `os.sep`, `sep=`, `ISO-8601` appear dozens of times --
#: so a case-insensitive match let any of them launder a date out of a sentence
#: about our own work. Real citations of these standards are always upper case.
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

#: What may stand between the name and the date: a VERSION and nothing else.
#:
#: No prose. That is the whole correction, and it is the difference between proving
#: the date is the standard's version and merely finding it near the name. The first
#: rule allowed any text in the gap, so a sentence about work done here -- name used
#: perfectly correctly, date plainly ours -- had its date erased. A detector that
#: silences its own subject is worse than none.
#:
#: NO BARE PERIOD either, and that is deliberate rather than tidy. A period ends a
#: sentence, so admitting one would let a standard's name in one sentence mask a
#: date belonging to the next. A dot reaches the gap only BETWEEN DIGITS, inside a
#: version token -- which is also why the token cannot end in a dot: a trailing one
#: would swallow the very sentence boundary this paragraph is about.
_SEPARATORS = r"[\s:,;/()\[\]<>=~^#-]{0,8}"
_VERSION_TOKEN = r"(?:v?\d+(?:\.\d+)*" + _SEPARATORS + r")?"
_VERSION_GAP = _SEPARATORS + _VERSION_TOKEN

#: A date the standard's name introduces, name first and across a version-only gap.
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
#: the journals of spec-dates-are-not-project-events,
#: quoted-example-is-counted-as-a-note and spec-date-rule-silences-a-real-project-date.
_SPEC_DATE = re.compile(
    r"\b(?:" + "|".join(_EXTERNAL_STANDARDS) + r")\b" + _VERSION_GAP + r"\b20\d\d-\d\d-\d\d\b"
)
_ISO_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_ACTIONABLE_FUTURE = re.compile(r"\b(?:deadline|expiry)\b", re.IGNORECASE)
_OWNER_MARKER = re.compile(r"\bowner=[A-Za-z0-9_.@/-]+\b")
_ACTION_MARKER = re.compile(r"\baction=[A-Za-z0-9_.:/-]+\b")
_MAX_UNTRACKED_BYTES = 1_000_000


@dataclass(frozen=True)
class CommentRefScan:
    """Result of comparing live comments with a persisted task baseline."""

    checked: bool
    findings: tuple[tuple[str, str, list[str]], ...] = ()
    reason: str | None = None


def _date_is_event(text: str, *, today: date | None = None) -> bool:
    """Whether an unmasked date is history rather than an owned future action."""
    current = today or date.today()
    matches = list(_ISO_DATE.finditer(text))
    for match in matches:
        raw = match.group()
        try:
            parsed = date.fromisoformat(raw)
        except ValueError:
            return True
        start = text.rfind(";", 0, match.start()) + 1
        end = text.find(";", match.end())
        clause = text[start:] if end < 0 else text[start:end]
        actionable = bool(
            len(_ISO_DATE.findall(clause)) == 1
            and _ACTIONABLE_FUTURE.search(clause)
            and _OWNER_MARKER.search(clause)
            and _ACTION_MARKER.search(clause)
        )
        if parsed <= current or not actionable:
            return True
    return False


def event_refs(text: str, *, today: date | None = None) -> list[str]:
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
        if (_date_is_event(without_specs, today=today) if kind == "date" else pattern.search(text))
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


def _matches_declared(path: str, declared: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for raw in declared:
        candidate = raw.replace("\\", "/").rstrip("/")
        if normalized == candidate or normalized.startswith(candidate + "/"):
            return True
        if any(char in candidate for char in "*?[") and fnmatch.fnmatch(normalized, candidate):
            return True
    return False


def _patch_path(header: str) -> str:
    """Decode one Git ``---``/``+++`` path header into repo-relative form."""
    raw = header[4:]
    if raw == "/dev/null":
        return ""
    if raw.startswith('"'):
        try:
            raw = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            return ""
    return raw[2:] if raw.startswith(("a/", "b/")) else raw


def _added_lines(root: str, paths: list[str], baseline: str) -> dict[str, list[str]] | None:
    """Lines ADDED to `paths` since the task started, per file.

    Git compares the persisted task-start commit with the live tree. This spans
    intermediate commits, the index, ordinary working-tree edits and renames.
    Untracked relevant files are added explicitly because ``git diff`` omits
    them. ``None`` means the comparison was not checked, never that it was clean.
    """
    if not paths:
        return {}
    try:
        patch = subprocess.run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "diff",
                "--find-renames",
                "--no-ext-diff",
                "--unified=0",
                baseline,
            ],
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
        return None
    if patch.returncode != 0:
        return None
    per_file: dict[str, list[str]] = {}
    old_path = ""
    current = ""
    included = False
    in_hunk = False
    for line in (patch.stdout or "").splitlines():
        if line.startswith("diff --git "):
            in_hunk = False
            included = False
        elif not in_hunk and line.startswith("--- "):
            old_path = _patch_path(line)
        elif not in_hunk and line.startswith("+++ "):
            new_path = _patch_path(line)
            current = new_path or old_path
            included = bool(
                current
                and (_matches_declared(old_path, paths) or _matches_declared(new_path, paths))
            )
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and included and line.startswith("+"):
            per_file.setdefault(current, []).append(line[1:])
    try:
        untracked = subprocess.run(
            [
                "git",
                "-c",
                "core.quotePath=false",
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                *paths,
            ],
            cwd=root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=False,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if untracked.returncode != 0:
        return None
    untracked_paths = (untracked.stdout or b"").decode("utf-8", errors="replace").split("\0")
    for rel in (path for path in untracked_paths if path):
        normalized = rel.replace("\\", "/")
        try:
            absolute = os.path.abspath(os.path.join(root, normalized))
            if os.path.commonpath((os.path.abspath(root), absolute)) != os.path.abspath(root):
                return None
            info = os.lstat(absolute)
            if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_UNTRACKED_BYTES:
                return None
            with open(absolute, encoding="utf-8") as fh:
                per_file[normalized] = fh.read().splitlines()
        except (OSError, ValueError):
            return None
    return per_file


def new_refs_for_close(root: str, slug: str, paths: list[str]) -> CommentRefScan:
    """`(file, comment text, kinds)` for event references the task itself added.

    Only lines added since the task baseline are read, so a WIP commit cannot
    erase the reminder and an old adjacent note is not dragged into the report.
    """
    baseline = task_baseline.baseline_of(root, slug)
    if baseline is None:
        return CommentRefScan(False, reason="task baseline is missing or unreadable")
    added = _added_lines(root, paths, baseline)
    if added is None:
        return CommentRefScan(False, reason="git baseline diff could not be read")
    found: list[tuple[str, str, list[str]]] = []
    for rel, lines in added.items():
        if not rel.endswith(".py"):
            continue
        for raw in lines:
            text = comment_part(raw)
            if not text:
                continue
            kinds = event_refs(text)
            if kinds:
                found.append((rel, text, kinds))
    return CommentRefScan(True, tuple(found))


def closure_note(slug: str, scan: CommentRefScan | list[tuple[str, str, list[str]]]) -> str | None:
    """The reminder, or ``None`` when the task added no event reference.

    ``None`` is the common case and has to stay silent: a note printed on every
    close is read on none of them.
    """
    if isinstance(scan, list):
        scan = CommentRefScan(True, tuple(scan))
    if not scan.checked:
        return f"\nCOMMENT HISTORY: not checked — {scan.reason or 'unknown baseline error'}."
    found = scan.findings
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
