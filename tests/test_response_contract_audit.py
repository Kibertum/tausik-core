"""Cases for the response-contract audit: what each marker catches and spares.

The rubric is four regex tables mirroring the contract's pre-send deletions.
Every marker has a positive case (the phrase, in prose) and a negative case
(the same phrase where the contract forbids reading it — inside code, a quoted
error, a path, an AC line), so a rubric that grew blind or greedy fails here
before it mis-measures a corpus.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import response_contract_audit as rca  # noqa: E402

CROSSCUTTING_SCOPE: list[str] = []  # reads transcripts, never the tree


def _hits(text: str) -> dict[str, bool]:
    return rca.score(text).hits


# --- positives: the phrase in prose fires the marker ------------------------------

POSITIVE = {
    "intent_opener": [
        "I'll start with the session handoff and then look at the tests.",
        "Okay, let me check the gate output first.",
        "Сейчас посмотрю, что упало в гейте, и вернусь.",
        "Начинаю с хендоффа смены #224.",
    ],
    "closing_recap": [
        "Fixed the parser.\n\nTests pass.\n\nIn summary: the parser now accepts both forms.",
        "Готово, три файла.\n\nВсё зелёное.\n\nИтого: парсер принимает обе формы.",
        "Done.\n\nLet me know if you need anything else.",
    ],
    "side_branch": [
        "Fixed the parser.\n\nBy the way, the README still says 21 hooks.",
        "Парсер починен.\n\nПопутно: счётчик хуков в README отстал на единицу.",
    ],
    "empty_hedge": [
        "The cache is invalidated on write, so this should be fine.",
        "Кэш сбрасывается на запись, так что, скорее всего, всё в порядке.",
    ],
}


@pytest.mark.parametrize(
    ("marker", "text"),
    [(m, t) for m, texts in POSITIVE.items() for t in texts],
    ids=lambda v: v if v in POSITIVE else v[:28],
)
def test_the_phrase_in_prose_is_a_hit(marker, text):
    assert _hits(text)[marker], (marker, text)


# --- negatives: a conforming answer and protected content stay clean --------------


def test_a_conforming_answer_fires_nothing():
    text = (
        "Task closed, commit 3fd4db65.\n\n"
        "Verified by tests/test_x.py::test_y (12 passed) and verify run #2523.\n\n"
        "Left: the docs paragraph in docs/ru/cli.md.\n\n"
        "Your call: bump the manifest to 1.1 or keep it pending."
    )
    assert not any(_hits(text).values()), _hits(text)


PROTECTED = [
    (
        "empty_hedge",
        "Error was:\n\n```\nRuntimeError: maybe the socket is closed\n```\n\nFixed in the client.",
    ),
    ("empty_hedge", "The call `should_work()` returns early.\n\nFixed."),
    ("empty_hedge", "Output:\n\n    warning: probably stale cache\n\nCleared it."),
    (
        "intent_opener",
        "AC-1 ✓ tests/test_x.py::test_y — I'll start is the tested opener.\n\nClosed.",
    ),
    (
        "side_branch",
        "Root cause (docs): the file docs/by the way.md was never linked.\n\nRelinked.",
    ),
    (
        "closing_recap",
        "> In summary: the quoted tool output says so\n\nThe quote is the tool's, not mine.",
    ),
    ("intent_opener", "<system-reminder>I'll start with nothing</system-reminder>State: green."),
]


@pytest.mark.parametrize(
    ("marker", "text"), PROTECTED, ids=[m + ":" + t[:20] for m, t in PROTECTED]
)
def test_protected_content_is_not_read(marker, text):
    """Code, quoted output, paths, AC/root-cause lines and harness tags are the
    contract's own keep-lists; a hedge word inside them is not the agent's."""
    assert not _hits(text)[marker], (marker, rca.prose_of(text))


def test_a_hedge_that_names_its_uncertainty_is_still_counted():
    """The rubric is lexical on purpose: it cannot tell an empty hedge from a
    named one, and says so in the docs. This pins that it does NOT pretend to."""
    assert _hits("Perhaps the socket closed — I could not reproduce it in 20 runs.")["empty_hedge"]


# --- adapters -----------------------------------------------------------------------


def _write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", "utf-8")


def _claude(role, text, **extra):
    return {"type": role, "message": {"content": [{"type": "text", "text": text}]}, **extra}


def test_claude_adapter_takes_the_last_text_before_a_human_turn(tmp_path):
    """Between-tool-call notes are not answers; the turn-final block is. A
    harness notification is not a human, so the reply to it is not an answer."""
    p = tmp_path / "s.jsonl"
    _write_jsonl(
        p,
        [
            _claude("user", "fix the parser"),
            _claude("assistant", "Looking at the parser now."),
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            _claude("assistant", "Parser fixed, 12 tests pass."),
            _claude("user", "[SYSTEM NOTIFICATION - NOT USER INPUT] task done"),
            _claude("assistant", "No response requested."),
            _claude("user", "thanks, and the docs?"),
            _claude("assistant", "Docs updated."),
            _claude("assistant", "Error: overloaded", isApiErrorMessage=True),
        ],
    )
    assert rca.detect_host(p) == "claude"
    assert list(rca.claude_answers(p)) == ["Parser fixed, 12 tests pass.", "Docs updated."]


def _codex(role, text, cwd=None):
    if cwd is not None:
        return {"type": "session_meta", "payload": {"cwd": cwd}}
    return {
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": role,
            "content": [{"type": "output_text", "text": text}],
        },
    }


def test_codex_adapter_filters_by_cwd_and_drops_imported_tool_traffic(tmp_path):
    ours = tmp_path / "ours.jsonl"
    theirs = tmp_path / "theirs.jsonl"
    _write_jsonl(
        ours,
        [
            _codex(None, None, cwd=str(tmp_path)),
            _codex("user", "go"),
            _codex("assistant", "[external_agent_tool_call: Bash]\ncommand: ls"),
            _codex("assistant", "Tree listed, nothing stale."),
            _codex("user", "ok"),
        ],
    )
    _write_jsonl(
        theirs, [_codex(None, None, cwd=str(tmp_path / "other")), _codex("assistant", "Hi.")]
    )
    assert rca.detect_host(ours) == "codex"
    assert list(rca.codex_answers(ours, str(tmp_path))) == ["Tree listed, nothing stale."]
    assert list(rca.codex_answers(theirs, str(tmp_path))) == []
    assert list(rca.codex_answers(theirs, None)) == ["Hi."]


def test_generic_adapter_and_report(tmp_path):
    p = tmp_path / "answers.jsonl"
    _write_jsonl(
        p, [{"text": "I'll start now."}, {"text": "Done. Verified by test_x."}, {"other": 1}]
    )
    rep = rca.audit([str(tmp_path)])
    d = rep.as_dict()
    assert d["answers"] == 2 and d["by_host"] == {"generic": 2}
    assert d["marker_rate_pct"]["intent_opener"] == 50.0 and d["hit_rate_pct"] == 50.0


# --- the runner's contract --------------------------------------------------------------


def test_an_empty_corpus_is_named_not_reported_as_full_adherence(tmp_path, capsys):
    (tmp_path / "empty.jsonl").write_text("", "utf-8")
    assert rca.main([str(tmp_path), "--threshold", "0"]) == 0
    out = capsys.readouterr().out
    assert "NO user-facing answers" in out and "%" not in out
    assert rca.audit([str(tmp_path)]).hit_rate is None


def test_threshold_exits_one_at_or_above_and_zero_below(tmp_path, capsys):
    p = tmp_path / "a.jsonl"
    _write_jsonl(p, [{"text": "I'll start now."}, {"text": "Done."}])  # 50% hit rate
    assert rca.main([str(p), "--threshold", "50"]) == 1
    assert rca.main([str(p), "--threshold", "50.1"]) == 0
    assert rca.main([str(p), "--json"]) == 0
    assert (
        json.loads(capsys.readouterr().out.rsplit("\n{", 1)[-1].join(["{", ""]))["hit_rate_pct"]
        == 50.0
    )
