"""Response-contract adherence audit: how often real answers break the contract.

`output_mode: caveman` and `/i-have-adhd` tell the agent what to delete before
sending (intent announcements, closing recaps, side branches, empty hedges).
Until this file, nothing measured whether the agent does. A rule whose
adherence is never measured is the class of defect release 1.9 is about: a
check that never ran is indistinguishable from a passing one.

The port of ayghri/i-have-adhd's `evals/` is the idea — cases, rubric, runner —
not its text. The unit is a USER-FACING answer: the last assistant text block
before the next human message (a tool result is not a human). Scoring runs on
prose only: fenced and inline code, quoted tool output, file paths, AC-evidence
and decision lines are stripped first, so a hedge word inside an error message
is not a hit. Nothing from a transcript is stored anywhere; the audit prints
counts.

Adapters: Claude Code project transcripts (the `*.jsonl` files the IDE keeps
per project), Codex rollouts (its sessions directory, filtered by the session's
cwd), and a generic JSONL of `{"text": ...}` records. Pass the directories.

    python scripts/response_contract_audit.py <dir-or-file>... [--project DIR]
        [--json] [--threshold PCT]

`--threshold` exits 1 when the hit rate (answers with at least one marker over
all answers) is at or above PCT — the same corpus re-measured after the
contract compares against the figure this file first produced.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- the rubric ------------------------------------------------------------------
# One table per pre-send deletion of the contract; RU and EN in each. A marker is a
# regex over the prose of ONE answer after protected content is stripped.

_I = re.IGNORECASE

# Intent announcement: the first prose line says what is about to be done instead
# of doing it. Anchored to the start of the answer.
INTENT_OPENER = re.compile(
    r"^(?:"
    r"(?:ok(?:ay)?|sure|got it|understood|alright|great|perfect)[,.!]?\s*"
    r"|(?:понял|хорошо|отлично|ладно|ясно|принято)[,.!]?\s*"
    r")?(?:"
    r"i(?:'ll| will| am going to| can| need to| want to)\s|let me\s|let's\s|now i(?:'ll| will)?\s"
    r"|(?:first|next|now),?\s+(?:i(?:'ll| will)?|let me|let's)\s"
    r"|(?:сейчас|теперь|далее|для начала|сначала)\s+(?:я\s+)?"
    r"(?:посмотрю|проверю|сделаю|начну|запущу|напишу|разберусь|поищу|прочитаю|исправлю|добавлю|обновлю|соберу)"
    r"|(?:посмотрю|проверю|начну|приступаю|запущу|разберусь|поищу|прочитаю)\b"
    r"|(?:начинаю|начинаем|открываю|беру|иду|перехожу)\b"
    r"|(?:starting|moving on|going) (?:with|to)\b"
    r"|давай(?:те)? (?:посмотрим|проверим|начнём|начнем|сделаем)"
    r"|я\s+(?:сейчас\s+)?(?:посмотрю|проверю|сделаю|начну|запущу|напишу|разберусь)\b"
    r")",
    _I,
)

# Closing recap or pleasantry: a paragraph in the final third that summarises what
# the reader just read, or signs off.
CLOSING_RECAP = re.compile(
    r"^(?:"
    r"(?:in )?summary[:,]|to summari[sz]e|to sum up|tl;?dr[:,]?|recap[:,]|overall[:,]|in short[:,]"
    r"|let me know|feel free|hope (?:this|that) helps|happy to help|don't hesitate|if you (?:need|want|have) any"
    r"|(?:итого|итак|подытож|резюм|в итоге|в общем|вкратце|если коротко|коротко говоря)[:,]?"
    r"|если (?:нужно|надо|хотите|есть вопросы)|дайте знать|обращайтесь|надеюсь,? (?:это )?поможет"
    r"|рад(?:а)? помочь|готов(?:а)? (?:помочь|продолжить)"
    r")",
    _I,
)

# Side branch: a paragraph that opens a tangent the question did not ask for.
SIDE_BRANCH = re.compile(
    r"^(?:"
    r"by the way|btw|side note|as an aside|aside[:,]|unrelated(?:ly)?|on a separate note"
    r"|incidentally|fun fact|while (?:i'm|we're) (?:here|at it)"
    r"|кстати|между прочим|заодно|отдельно (?:замечу|отмечу)|к слову|попутно|не по теме"
    r")\b",
    _I,
)

# Empty hedge: uncertainty words that carry no named uncertainty. The marker
# fires on the first one in the answer.
EMPTY_HEDGE = re.compile(
    r"\b(?:"
    r"i think|i believe|i guess|i suppose|i feel like|probably|perhaps|maybe|it seems(?: like)?"
    r"|might be|could be|should (?:be fine|work)|sort of|kind of|more or less|arguably|presumably"
    r"|as far as i (?:can tell|know)|if i'm not mistaken|not (?:100%|entirely) sure|i'm not sure but"
    r"|наверное|наверно|возможно|вероятно|пожалуй|кажется|похоже,? что|думаю,? что|полагаю|скорее всего"
    r"|вроде(?: бы)?|как будто|должно (?:работать|быть ок|быть нормально)|не уверен,? но"
    r"|если не ошибаюсь|по идее|как мне кажется"
    r")\b",
    _I,
)

MARKERS: dict[str, re.Pattern[str]] = {
    "intent_opener": INTENT_OPENER,
    "closing_recap": CLOSING_RECAP,
    "side_branch": SIDE_BRANCH,
    "empty_hedge": EMPTY_HEDGE,
}

# --- protected content ------------------------------------------------------------
# The contract keeps these byte-exact / full; the rubric must not read them.

_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_QUOTED_OUTPUT = re.compile(r"^(?:>|\s{4,}|\t).*$", re.M)
_PATH = re.compile(
    r"(?:[A-Za-z]:)?(?:[\\/][\w.\-~]+){2,}|\b[\w.\-]+\.(?:py|md|json|toml|yml|yaml|txt|js|ts|sh)\b"
)
_PROTECTED_LINE = re.compile(
    r"^\s*(?:AC-\d+|Root cause|Domain:|Decision|Решение|Rollback|verify|Receipt).*$", re.M | _I
)
_HARNESS_MARKUP = re.compile(r"\[external_agent_[^\]]*\].*?(?:\[/external_agent_[^\]]*\]|$)", re.S)
_SYSTEM_TAGS = re.compile(r"<(system-reminder|ide_selection|task-notification)[^>]*>.*?</\1>", re.S)


def prose_of(answer: str) -> str:
    """The answer with everything the contract protects removed."""
    text = _SYSTEM_TAGS.sub(" ", answer)
    text = _HARNESS_MARKUP.sub(" ", text)
    text = _FENCE.sub(" ", text)
    text = _INLINE_CODE.sub(" ", text)
    text = _QUOTED_OUTPUT.sub(" ", text)
    text = _PROTECTED_LINE.sub(" ", text)
    text = _PATH.sub(" ", text)
    return text.strip()


def _paragraphs(prose: str) -> list[str]:
    parts = re.split(r"\n\s*\n|\n(?=\s*(?:[-*]|\d+\.)\s)", prose)
    return [p.strip() for p in parts if p.strip()]


# --- scoring one answer -------------------------------------------------------------


@dataclass
class Score:
    hits: dict[str, bool]
    prose_chars: int
    raw_chars: int

    @property
    def any_hit(self) -> bool:
        return any(self.hits.values())


def score(answer: str) -> Score:
    """Which markers fire on one user-facing answer."""
    prose = prose_of(answer)
    paras = _paragraphs(prose)
    first = paras[0] if paras else ""
    tail = paras[-max(1, len(paras) // 3) :] if paras else []
    hits = {
        "intent_opener": bool(INTENT_OPENER.match(first.lstrip("*_# ").lstrip())),
        "closing_recap": any(CLOSING_RECAP.match(p.lstrip("*_ ")) for p in tail),
        "side_branch": any(SIDE_BRANCH.match(p.lstrip("*_ ")) for p in paras),
        "empty_hedge": bool(EMPTY_HEDGE.search(prose)),
    }
    return Score(hits=hits, prose_chars=len(prose), raw_chars=len(answer))


# --- adapters: where user-facing answers come from ------------------------------------


# A `user` record the harness wrote, not the person: background-task and
# system notifications arrive as user turns, and the agent's reply to them is
# not an answer to anyone.
_NOT_HUMAN = ("[SYSTEM NOTIFICATION", "<task-notification", "<system-reminder", "<local-command")
_SENTINELS = ("No response requested.",)


def _is_human(record: dict[str, Any]) -> bool:
    """A Claude Code `user` record that a person typed (not a tool result, not
    a harness notification)."""
    if record.get("type") != "user":
        return False
    content = (record.get("message") or {}).get("content")
    texts: list[str] = []
    if isinstance(content, str):
        texts = [content]
    elif isinstance(content, list):
        texts = [
            str(c.get("text", ""))
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
    texts = [t.strip() for t in texts if t.strip()]
    return bool(texts) and not all(t.startswith(_NOT_HUMAN) for t in texts)


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def claude_answers(path: Path) -> Iterator[str]:
    """Turn-final assistant text: the last text block before a human message."""
    pending: str | None = None
    for rec in _iter_jsonl(path):
        if rec.get("type") == "assistant":
            if rec.get("isApiErrorMessage"):
                continue
            for c in (rec.get("message") or {}).get("content") or []:
                if (
                    isinstance(c, dict)
                    and c.get("type") == "text"
                    and str(c.get("text", "")).strip()
                ):
                    text = str(c["text"])
                    if text.strip() not in _SENTINELS:
                        pending = text
        elif _is_human(rec):
            if pending:
                yield pending
            pending = None
    if pending:
        yield pending


def _same_dir(a: str, b: str) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def codex_answers(path: Path, project: str | None) -> Iterator[str]:
    """Assistant output_text of a Codex rollout whose session cwd is `project`.
    Imported Claude sessions carry `[external_agent_*]` markup; those blocks are
    tool traffic, not answers, and are dropped."""
    pending: str | None = None
    cwd_ok = project is None
    for rec in _iter_jsonl(path):
        payload = rec.get("payload") or {}
        if rec.get("type") == "session_meta" and project is not None:
            cwd_ok = _same_dir(str(payload.get("cwd", "")), project)
            if not cwd_ok:
                return
        if not cwd_ok or rec.get("type") != "response_item" or payload.get("type") != "message":
            continue
        texts = [
            str(c.get("text", ""))
            for c in payload.get("content") or []
            if isinstance(c, dict) and c.get("type") in ("output_text", "input_text")
        ]
        text = "\n".join(t for t in texts if t.strip())
        if payload.get("role") == "assistant":
            if text.strip() and not text.lstrip().startswith("[external_agent_"):
                pending = text
        elif payload.get("role") == "user":
            if pending:
                yield pending
            pending = None
    if pending:
        yield pending


def generic_answers(path: Path) -> Iterator[str]:
    for rec in _iter_jsonl(path):
        text = rec.get("text")
        if isinstance(text, str) and text.strip():
            yield text


def detect_host(path: Path) -> str:
    """claude | codex | generic, from the first records rather than the path."""
    for i, rec in enumerate(_iter_jsonl(path)):
        if rec.get("type") == "session_meta" or "payload" in rec:
            return "codex"
        if rec.get("type") in ("user", "assistant", "summary", "system"):
            return "claude"
        if "text" in rec:
            return "generic"
        if i > 5:
            break
    return "generic"


def answers_of(path: Path, project: str | None) -> tuple[str, Iterator[str]]:
    host = detect_host(path)
    if host == "claude":
        return host, claude_answers(path)
    if host == "codex":
        return host, codex_answers(path, project)
    return host, generic_answers(path)


def jsonl_files(paths: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out.extend(sorted(path.rglob("*.jsonl")))
        elif path.suffix == ".jsonl" and path.is_file():
            out.append(path)
    return out


# --- the report -------------------------------------------------------------------------


@dataclass
class Report:
    answers: int = 0
    by_host: dict[str, int] = field(default_factory=dict)
    marker_hits: dict[str, int] = field(default_factory=lambda: dict.fromkeys(MARKERS, 0))
    any_hits: int = 0
    lengths: list[int] = field(default_factory=list)
    files: int = 0

    def add(self, host: str, sc: Score) -> None:
        self.answers += 1
        self.by_host[host] = self.by_host.get(host, 0) + 1
        for name, hit in sc.hits.items():
            self.marker_hits[name] += int(hit)
        self.any_hits += int(sc.any_hit)
        self.lengths.append(sc.raw_chars)

    @property
    def hit_rate(self) -> float | None:
        return None if self.answers == 0 else 100.0 * self.any_hits / self.answers

    def as_dict(self) -> dict[str, Any]:
        n = self.answers
        lengths = sorted(self.lengths)
        return {
            "files": self.files,
            "answers": n,
            "by_host": dict(sorted(self.by_host.items())),
            "marker_rate_pct": {
                k: (round(100.0 * v / n, 1) if n else None) for k, v in self.marker_hits.items()
            },
            "hit_rate_pct": (round(self.hit_rate, 1) if self.hit_rate is not None else None),
            "median_chars": (lengths[len(lengths) // 2] if lengths else None),
        }


def audit(paths: Iterable[str], project: str | None = None) -> Report:
    rep = Report()
    for path in jsonl_files(paths):
        rep.files += 1
        host, answers = answers_of(path, project)
        for answer in answers:
            rep.add(host, score(answer))
    return rep


def render(rep: Report) -> str:
    d = rep.as_dict()
    if not d["answers"]:
        return (
            f"response-contract audit: {d['files']} file(s), NO user-facing answers found "
            "— nothing measured."
        )
    hosts = ", ".join(f"{k}={v}" for k, v in d["by_host"].items())
    lines = [
        f"response-contract audit: {d['answers']} user-facing answer(s) in {d['files']} file(s); "
        f"by host: {hosts}; median {d['median_chars']} chars",
        "marker hit rate (share of answers with the marker):",
    ]
    for k, v in d["marker_rate_pct"].items():
        lines.append(f"  {k:<14} {v:>5}%")
    lines.append(f"answers with >=1 marker: {d['hit_rate_pct']}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Response-contract adherence audit over transcripts")
    ap.add_argument("paths", nargs="+", help="transcript files or directories (*.jsonl)")
    ap.add_argument("--project", help="only Codex rollouts whose cwd is this directory")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--threshold", type=float, help="exit 1 when the hit rate is at or above this percent"
    )
    args = ap.parse_args(argv)
    rep = audit(args.paths, args.project)
    print(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2) if args.json else render(rep))
    if args.threshold is not None and rep.hit_rate is not None and rep.hit_rate >= args.threshold:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
