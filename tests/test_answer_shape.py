"""The shape of the agent's answers is measured, not assumed (story J, 1.10)."""

from __future__ import annotations

import json

import pytest

from answer_shape import UnparseableTranscript, measure, measure_transcript, score, Report


def test_a_terse_answer_scores_as_one():
    s = score("Готово: 3 задачи закрыты.\n- A: 2\n- I: 1")
    assert s.verdict_first and s.words == 8 and s.list_share == pytest.approx(0.67, 0.01)
    assert s.filler == 0


@pytest.mark.parametrize(
    "first_line",
    ["Let me check the tests first.", "Сначала я посмотрю код.", "Теперь проверю гейты."],
)
def test_process_narration_is_not_a_verdict(first_line):
    assert not score(first_line + "\nDone.").verdict_first


def test_filler_is_counted():
    assert score("Отлично! Давай посмотрим. Great, now I will fix it.").filler >= 3


def _write(tmp_path, records):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    return str(p)


def _human(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def _say(text):
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def _tool():
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "tool_use"}]},
    }


def test_the_final_answer_is_the_last_text_before_the_next_prompt(tmp_path):
    path = _write(
        tmp_path,
        [
            _human("do it"),
            _say("Checking one two three."),
            _tool(),
            _say("Done: ok."),
            _human("next"),
            _say("Fine."),
        ],
    )
    report = Report()
    measure_transcript(path, report)
    assert [s.words for s in report.finals] == [2, 1]
    assert report.interim_words == [4, 0]
    assert report.summary()["answers"] == 2


def test_a_transcript_without_assistant_text_is_refused_not_zeroed(tmp_path):
    """NEGATIVE: unparseable input is reported as skipped, never as 0 words."""
    path = _write(tmp_path, [_human("hi"), _tool()])
    with pytest.raises(UnparseableTranscript):
        measure_transcript(path, Report())
    report, skipped = measure([path])
    assert report.summary() == {"transcripts": 0, "answers": 0}
    assert skipped and "no assistant text" in skipped[0]


def test_budget_nudge_names_words_and_missing_verdict():
    from answer_shape import budget_nudge

    line = budget_nudge("Let me explain.\n" + "x " * 300, budget=200)
    assert "words, budget 200" in line and "no verdict in the first line" in line
    assert budget_nudge("Готово: всё зелёное.", budget=200) is None
