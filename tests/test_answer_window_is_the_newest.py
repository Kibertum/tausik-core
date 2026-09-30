"""The answer measure reads the NEWEST transcripts, not the first ones ever written.

`project_transcripts` is oldest-first and both readers sliced it with `[:last]`, so
`metrics answers` and its ratchet stayed frozen on the project's earliest sessions
(session #279: p90 1325 on the oldest ten against 453 on the newest ten).
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("scripts", os.path.join("scripts", "hooks")):
    sys.path.insert(0, os.path.join(_ROOT, _p))

import answer_budget_ratchet  # noqa: E402
import transcript_locator  # noqa: E402


def _three(tmp_path):
    paths = []
    for age, name in ((300, "old"), (200, "mid"), (100, "new")):
        p = tmp_path / f"{name}.jsonl"
        p.write_text("", encoding="utf-8")
        t = 1_700_000_000 - age
        os.utime(p, (t, t))
        paths.append(str(p))
    return paths


def test_newest_returns_the_last_n_oldest_first(tmp_path, monkeypatch):
    paths = _three(tmp_path)
    monkeypatch.setattr(
        transcript_locator,
        "project_transcripts",
        lambda _d=None: sorted(paths, key=os.path.getmtime),
    )
    got = transcript_locator.newest_project_transcripts(str(tmp_path), 2)
    assert [os.path.basename(p) for p in got] == ["mid.jsonl", "new.jsonl"]


def test_the_ratchet_reads_the_newest_not_the_oldest(tmp_path, monkeypatch):
    """NEGATIVE: the old slice would hand `measure` old.jsonl and mid.jsonl."""
    paths = _three(tmp_path)
    monkeypatch.setattr(
        transcript_locator,
        "project_transcripts",
        lambda _d=None: sorted(paths, key=os.path.getmtime),
    )
    seen = {}

    def fake_measure(ps):
        seen["paths"] = [os.path.basename(p) for p in ps]

        class R:
            def summary(self):
                return {"answers": 0}

        return R(), []

    import answer_shape

    monkeypatch.setattr(answer_shape, "measure", fake_measure)
    answer_budget_ratchet.measure_local(str(tmp_path), last=2)
    assert seen["paths"] == ["mid.jsonl", "new.jsonl"]
