"""Measure the shape of the agent's answers in host transcripts.

terse-answers-measured-first (1.10, story J, decision #391). The 1.9 answer
rules (the response contract) were text, and the owner still read
long answers. Before a mechanism is built, the answers are MEASURED:

* final answer — the last assistant text before the next human prompt: words,
  verdict-first (first line short and not process narration), list share,
  filler phrases;
* interim text — assistant text between tool calls in the same turn, which the
  owner also reads and which also costs tokens.

`score(text)` is the unit the UserPromptSubmit budget check reuses; `measure(paths)` is the
report `tausik metrics answers` prints.  Claude-compatible records and native Codex
``response_item`` records share this reader; a caller keeps their host windows separate.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Iterable

_WORD = re.compile(r"\w+", re.UNICODE)
_LIST_LINE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
#: Phrases that narrate the process or pad the answer instead of stating a result.
FILLER = (
    "let me",
    "i'll",
    "i will now",
    "now i",
    "next, i",
    "great",
    "perfect",
    "давай",
    "сейчас я",
    "теперь я",
    "дальше я",
    "сначала я",
    "отлично",
    "итак,",
)
_NARRATION_START = re.compile(
    r"^\s*(let me|i'll|i will|now|next|first|давай|сейчас|теперь|дальше|сначала)\b", re.I
)
VERDICT_MAX_WORDS = 25

#: THE DECLARED MARK OF EVIDENCE (convention #768: the budget is on the retelling, not on
#: the proof). Two forms, both visible in the text rather than guessed: a fenced block
#: (tool output, a command, a quoted receipt) and a markdown table row (measurements).
#: Everything else is retelling. An answer with neither is counted whole — a long answer
#: cannot declare itself evidence by saying so.
_FENCE = re.compile(r"^\s*(```|~~~)")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")

_FORMAT_INTENT = re.compile(
    r"\b(explain|compare|comparison|diagram|flow|sequence|hierarchy|architecture|table|"
    r"interactive|html|visuali[sz]e|video)\b|"
    r"\b(объясн\w*|сравн\w*|диаграм\w*|схем\w*|поток\w*|последовательност\w*|"
    r"иерарх\w*|архитектур\w*|таблиц\w*|интерактив\w*|визуализ\w*|видео)\b",
    re.I,
)

FORMAT_RULE = (
    "**[TAUSIK explanation format]** Use the smallest useful form: prose by default; "
    "a table for 3+ exact mappings/comparisons; Mermaid for hierarchy, sequence, or 3+ "
    "linked parts; HTML only on request or a named interaction need; video only on request, "
    "never auto-selected. If uncertain, unsupported, inaccessible, or not clearer, use prose."
)


def evidence_words(text: str) -> int:
    """Words inside fenced blocks and markdown table rows."""
    inside, n, pending = False, 0, 0
    for ln in (text or "").splitlines():
        if _FENCE.match(ln):
            if inside:
                n += pending  # a block counts only once it is closed
            inside, pending = not inside, 0
            continue
        if inside:
            pending += len(_WORD.findall(ln))
        elif _TABLE_ROW.match(ln):
            n += len(_WORD.findall(ln))
    return n  # an unclosed fence stays retelling: one stray ``` cannot exempt the rest


@dataclass
class Score:
    words: int  # retelling only: everything outside the declared evidence
    verdict_first: bool
    list_share: float
    filler: int
    evidence: int = 0


def score(text: str) -> Score:
    """The shape of one answer."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    first_words = len(_WORD.findall(first))
    verdict = bool(first) and first_words <= VERDICT_MAX_WORDS and not _NARRATION_START.match(first)
    listed = sum(1 for ln in lines if _LIST_LINE.match(ln))
    low = (text or "").lower()
    proof = evidence_words(text)
    return Score(
        words=len(_WORD.findall(text or "")) - proof,
        evidence=proof,
        verdict_first=verdict,
        list_share=round(listed / len(lines), 2) if lines else 0.0,
        filler=sum(low.count(p) for p in FILLER),
    )


class UnparseableTranscript(ValueError):
    """A transcript with no assistant text at all is not 'zero words'."""


@dataclass
class Report:
    transcripts: int = 0
    finals: list[Score] = field(default_factory=list)
    interim_words: list[int] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        if not self.finals:
            return {"transcripts": self.transcripts, "answers": 0}
        words = [s.words for s in self.finals]
        return {
            "transcripts": self.transcripts,
            "answers": len(self.finals),
            "final_words_median": median(words),
            "final_words_p90": sorted(words)[int(0.9 * (len(words) - 1))],
            "verdict_first_pct": round(
                100 * sum(s.verdict_first for s in self.finals) / len(self.finals), 1
            ),
            "evidence_words_median": median(s.evidence for s in self.finals),
            "list_share_median": median(s.list_share for s in self.finals),
            "filler_per_answer": round(sum(s.filler for s in self.finals) / len(self.finals), 2),
            "interim_words_per_turn_median": median(self.interim_words)
            if self.interim_words
            else 0,
        }


def _records(path: str) -> Iterable[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def _is_human(rec: dict) -> bool:
    """Whether a record starts an owner-visible turn on a supported host."""
    payload = rec.get("payload") or {}
    if (
        rec.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "user"
    ):
        return any(
            isinstance(block, dict) and block.get("type") in {"input_text", "input_image"}
            for block in (payload.get("content") or [])
        )
    msg = rec.get("message") or {}
    if rec.get("type") != "user" or msg.get("role") != "user" or rec.get("isMeta"):
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "text" for b in content
    )


def _assistant_text(rec: dict) -> str:
    """Owner-visible assistant prose, excluding tool and collaborator messages."""
    payload = rec.get("payload") or {}
    if (
        rec.get("type") == "response_item"
        and payload.get("type") == "message"
        and payload.get("role") == "assistant"
    ):
        return "\n".join(
            block.get("text", "")
            for block in (payload.get("content") or [])
            if isinstance(block, dict) and block.get("type") == "output_text"
        ).strip()
    msg = rec.get("message") or {}
    if rec.get("type") != "assistant":
        return ""
    content = msg.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
    ).strip()


def measure_transcript(path: str, report: Report) -> None:
    texts: list[str] = []
    seen_text = False

    def close_turn() -> None:
        if texts:
            report.finals.append(score(texts[-1]))
            report.interim_words.append(sum(score(t).words for t in texts[:-1]))
        texts.clear()

    for rec in _records(path):
        if _is_human(rec):
            close_turn()
            continue
        text = _assistant_text(rec)
        if text:
            seen_text = True
            texts.append(text)
    close_turn()
    if not seen_text:
        raise UnparseableTranscript(f"no assistant text found in {path}")
    report.transcripts += 1


def measure(paths: Iterable[str]) -> tuple[Report, list[str]]:
    """Measure transcripts; return the report and the paths that could not be read."""
    report, skipped = Report(), []
    for path in paths:
        try:
            measure_transcript(path, report)
        except (OSError, UnparseableTranscript) as exc:
            skipped.append(f"{path}: {exc}")
    return report, skipped


# --- the mechanism (terse-answers-enforced-by-mechanism) -------------------------

#: Final-answer budget in words. Baseline before 1.10: median 396, p90 915.
DEFAULT_BUDGET_WORDS = 200


def last_final_answer(transcript_path: str, tail_bytes: int = 2_000_000) -> str | None:
    """The last assistant text in a transcript (the answer the human just read)."""
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - tail_bytes))
            chunk = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    last = None
    for line in chunk.splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            text = _assistant_text(rec)
            if text:
                last = text
    return last


#: The shipped answer rules (bootstrap_templates.ANSWER_SHAPE without its heading), put in
#: front of the agent on EVERY human prompt. In the rules file alone they reached consumer
#: projects and not this one, and the budget line spoke only after a long answer was read.
#: tests/test_answer_rules_every_prompt.py holds this byte-equal to ANSWER_SHAPE.
ANSWER_RULES = (
    "- Use user's language.\n"
    "- SHAPE, omit empty: done → verified by → left → your call.\n"
    "- PROSE (no ASD-STE100 claim): name actor/action; active voice if natural; one action/sentence; one term/concept; short paragraphs.\n"
    "- BYTE-EXACT: code, shell commands, tool output, file paths, error messages; FULL: acceptance-criteria evidence, decisions, SPEC/ADAPT, task logs, handoffs.\n"
    "- EXCEPTIONS: explanation asked; destructive action; 3 failed debug turns → assumption + question; ambiguity → one question; rule deletes answer itself.\n"
    "- Steps: numbered, one action each, last ≤2 min; ≤5/group unless more needed; tangent last; estimate if useful.\n"
    "- PRE-SEND: delete announcements, recaps, side branches, empty hedges; first line = next action; last = current state.\n"
)


def rules_line() -> str:
    """The answer rules as the prompt hook injects them, before the answer is written."""
    return "**[TAUSIK answer rules]** Apply to the answer you are about to write:\n" + ANSWER_RULES


def explanation_format_rule(prompt: str) -> str | None:
    """Return the conditional format matrix for explanation-shaped prompts."""
    return FORMAT_RULE if _FORMAT_INTENT.search(prompt or "") else None


def budget_nudge(text: str | None, budget: int = DEFAULT_BUDGET_WORDS) -> str | None:
    """One line for the agent when its last answer broke the budget or the shape."""
    if not text:
        return None
    s = score(text)
    problems = []
    if s.words > budget:
        problems.append(f"{s.words} words, budget {budget}")
    if not s.verdict_first:
        problems.append("no verdict in the first line")
    if not problems:
        return None
    return (
        "**[TAUSIK answer budget]** Your last answer: " + "; ".join(problems) + ". "
        "Next one: verdict in the first line, then facts and numbers as a short list; "
        "no narration of what you did, no repeating what was already said."
    )
