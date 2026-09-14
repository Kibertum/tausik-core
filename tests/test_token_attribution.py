"""Session attribution and context measurement for .tausik/token_metrics.jsonl.

The ledger claimed to be a token-economy instrument and was not one. Measured on
this project in session #227, before the fix:

  * `input_tokens` was 2 in all 5301 rows — the TRUE API value, because prompt
    caching moves the whole context into cache_read/cache_create and leaves only
    the uncached remainder behind. The report called that "the input".
  * 3840 of 5301 rows (72.4%) were cross-session duplicates. `resolve_session_id`
    answered "the newest session in the DB" and `extract_token_rows` re-walked
    the whole transcript, so sessions 221/222/223 each got a copy of it —
    identical first timestamps, and a 25-minute session carrying 1409 rows over
    16 hours.
  * Summed cache_read was inflated exactly 2.03x by that duplication alone.
  * 7 of 227 sessions had rows, and the report said "5 session(s) observed
    total" without the denominator.

Every test here pins one of those down. The last class runs against the LIVE
ledger when there is one, because a fixture cannot prove the real file is clean.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from conftest import canonical_ddl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

from service_token_metrics import aggregate, format_table  # noqa: E402
from session_windows import (  # noqa: E402
    load_session_windows,
    make_session_resolver,
    parse_ts,
    session_for_ts,
)
from token_rows import extract_token_rows, rebuild_ledger  # noqa: E402

# Three sessions, back to back, with a deliberate 10-minute gap before the third.
SESSIONS = [
    ("2026-09-06T16:00:00Z", "2026-09-06T17:00:00Z"),  # id 1
    ("2026-09-06T17:00:00Z", "2026-09-06T18:00:00Z"),  # id 2
    ("2026-09-06T18:10:00Z", None),  # id 3, still open
]


def _make_db(project_dir: Path, sessions=SESSIONS) -> None:
    tausik = project_dir / ".tausik"
    tausik.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(tausik / "tausik.db"))
    conn.execute(canonical_ddl("sessions"))
    for started, ended in sessions:
        conn.execute("INSERT INTO sessions(started_at, ended_at) VALUES (?, ?)", (started, ended))
    conn.commit()
    conn.close()


def _turn(ts: str, tools: list[str], usage: dict | None = None) -> dict:
    return {
        "type": "assistant",
        "timestamp": ts,
        "model": "claude-opus-5",
        "content": [{"type": "tool_use", "name": t} for t in tools],
        "usage": usage
        if usage is not None
        else {
            "input_tokens": 2,
            "output_tokens": 100,
            "cache_read_input_tokens": 30000,
            "cache_creation_input_tokens": 20000,
        },
    }


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n", encoding="utf-8"
    )


class TestTimestampParsing:
    def test_z_and_offset_forms_are_the_same_instant(self):
        """The DB holds both shapes: `+00:00` for early sessions, `Z` for later."""
        assert parse_ts("2026-09-07T13:51:40Z") == parse_ts("2026-09-07T13:51:40+00:00")

    def test_subsecond_ordering_is_not_lexicographic(self):
        """`'…:40Z' > '…:40.350Z'` as strings, because Z sorts after the dot.

        Comparing the raw strings would push a sub-second transcript timestamp
        past a whole-second session boundary and into the wrong session.
        """
        assert "2026-09-07T13:51:40Z" > "2026-09-07T13:51:40.350Z"
        assert parse_ts("2026-09-07T13:51:40Z") < parse_ts("2026-09-07T13:51:40.350Z")

    def test_unparseable_is_absence_not_epoch(self):
        for bad in (None, "", "   ", "not-a-time", 17, "a"):
            assert parse_ts(bad) is None

    def test_naive_value_is_read_as_utc(self):
        assert parse_ts("2026-09-07T13:51:40") == datetime(
            2026, 9, 7, 13, 51, 40, tzinfo=timezone.utc
        )


class TestSessionWindows:
    def test_open_session_is_closed_by_the_next_start(self, tmp_path):
        """An abandoned session left un-ended must not swallow all later work."""
        _make_db(
            tmp_path,
            [("2026-09-06T16:00:00Z", None), ("2026-09-06T17:00:00Z", "2026-09-06T18:00:00Z")],
        )
        windows = load_session_windows(str(tmp_path))
        assert windows[0][1] == parse_ts("2026-09-06T17:00:00Z")
        assert session_for_ts("2026-09-06T17:30:00Z", windows) == 2

    def test_newest_open_session_stays_unbounded(self, tmp_path):
        _make_db(tmp_path)
        windows = load_session_windows(str(tmp_path))
        assert windows[-1][1] is None
        assert session_for_ts("2027-01-01T00:00:00Z", windows) == 3

    def test_containment_places_each_instant_in_exactly_one_session(self, tmp_path):
        _make_db(tmp_path)
        windows = load_session_windows(str(tmp_path))
        assert session_for_ts("2026-09-06T16:30:00Z", windows) == 1
        assert session_for_ts("2026-09-06T17:30:00Z", windows) == 2
        assert session_for_ts("2026-09-06T18:30:00Z", windows) == 3

    def test_boundary_instant_belongs_to_the_later_session_only(self, tmp_path):
        """Ends are exclusive, so two adjacent sessions never both claim a row."""
        _make_db(tmp_path)
        windows = load_session_windows(str(tmp_path))
        assert session_for_ts("2026-09-06T17:00:00Z", windows) == 2

    def test_before_every_session_is_absence(self, tmp_path):
        _make_db(tmp_path)
        windows = load_session_windows(str(tmp_path))
        assert session_for_ts("2026-09-06T15:59:59Z", windows) is None

    def test_gap_between_sessions_is_absence_not_the_nearest_guess(self, tmp_path):
        """Decision #334: unmeasurable attribution yields None, never a neighbour."""
        _make_db(tmp_path)
        windows = load_session_windows(str(tmp_path))
        assert session_for_ts("2026-09-06T18:05:00Z", windows) is None

    def test_a_db_that_cannot_speak_yields_no_windows_and_does_not_raise(self, tmp_path):
        """Absent and corrupt are the same answer: no attribution, no exception.

        A hook may not break the session it is measuring, and it may not invent
        an attribution either — both failures end in an empty window list.
        """
        assert load_session_windows(str(tmp_path)) == []  # no DB at all
        tausik = tmp_path / ".tausik"
        tausik.mkdir()
        (tausik / "tausik.db").write_bytes(b"this is not a database")
        assert load_session_windows(str(tmp_path)) == []  # DB present, unreadable
        assert make_session_resolver(str(tmp_path))("2026-09-06T16:30:00Z") is None


class TestRowAttribution:
    def test_one_transcript_across_three_sessions_is_split_not_copied(self, tmp_path):
        """THE defect: one transcript spanning three sessions used to produce
        three identical copies, one per session."""
        _make_db(tmp_path)
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _turn("2026-09-06T16:30:00Z", ["Read"]),
                _turn("2026-09-06T17:30:00Z", ["Grep"]),
                _turn("2026-09-06T18:30:00Z", ["Edit"]),
            ],
        )
        rows = extract_token_rows(str(transcript), make_session_resolver(str(tmp_path)))
        assert [r["session_id"] for r in rows] == [1, 2, 3]
        by_session = {}
        for row in rows:
            by_session.setdefault(row["session_id"], set()).add(row["tool_name"])
        assert by_session == {1: {"Read"}, 2: {"Grep"}, 3: {"Edit"}}

    def test_no_timestamp_appears_under_two_sessions(self, tmp_path):
        _make_db(tmp_path)
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _turn(f"2026-09-06T{h:02d}:{m:02d}:00Z", ["Read", "Grep"])
                for h in (16, 17)
                for m in (5, 35)
            ],
        )
        rows = extract_token_rows(str(transcript), make_session_resolver(str(tmp_path)))
        seen: dict[tuple, set] = {}
        for row in rows:
            seen.setdefault((row["ts"], row["tool_name"]), set()).add(row["session_id"])
        assert all(len(sessions) == 1 for sessions in seen.values())

    def test_row_outside_every_session_carries_null_not_a_guess(self, tmp_path):
        _make_db(tmp_path)
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _turn("2026-09-06T15:00:00Z", ["Read"]),  # before session 1
                _turn("2026-09-06T18:05:00Z", ["Grep"]),  # in the gap
                _turn("2026-09-06T18:30:00Z", ["Edit"]),  # inside session 3
            ],
        )
        rows = extract_token_rows(str(transcript), make_session_resolver(str(tmp_path)))
        assert [r["session_id"] for r in rows] == [None, None, 3]

    def test_fixed_session_id_still_supported_for_single_session_transcripts(self, tmp_path):
        transcript = tmp_path / "t.jsonl"
        _write_transcript(transcript, [_turn("2026-09-06T16:30:00Z", ["Read"])])
        rows = extract_token_rows(str(transcript), 42)
        assert rows[0]["session_id"] == 42


class TestContextTokens:
    def test_context_is_the_sum_of_all_three_input_buckets(self, tmp_path):
        """input_tokens=2 is true and useless; 2+20000+30000 is the real context."""
        transcript = tmp_path / "t.jsonl"
        _write_transcript(transcript, [_turn("2026-09-06T16:30:00Z", ["Read"])])
        row = extract_token_rows(str(transcript), 1)[0]
        assert row["input_tokens"] == 2
        assert row["context_tokens"] == 2 + 30000 + 20000

    def test_context_splits_across_tools_with_the_remainder_on_the_last(self, tmp_path):
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _turn(
                    "2026-09-06T16:30:00Z",
                    ["Read", "Grep", "Glob"],
                    usage={"input_tokens": 1, "output_tokens": 9, "cache_read_input_tokens": 99},
                )
            ],
        )
        rows = extract_token_rows(str(transcript), 1)
        assert [r["context_tokens"] for r in rows] == [33, 33, 34]
        assert sum(r["context_tokens"] for r in rows) == 100

    def test_usage_without_any_input_bucket_yields_absence_not_zero(self, tmp_path):
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript, [_turn("2026-09-06T16:30:00Z", ["Read"], usage={"output_tokens": 50})]
        )
        rows = extract_token_rows(str(transcript), 1)
        assert rows[0]["context_tokens"] is None
        assert rows[0]["output_tokens"] == 50

    def test_absent_cache_bucket_is_a_real_zero_not_absence(self, tmp_path):
        """An uncached call genuinely read no cache — that is 0, not unmeasured."""
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                _turn(
                    "2026-09-06T16:30:00Z",
                    ["Read"],
                    usage={"input_tokens": 4000, "output_tokens": 50},
                )
            ],
        )
        assert extract_token_rows(str(transcript), 1)[0]["context_tokens"] == 4000


class TestReportRefusesToPrintZeroForAbsence:
    def _ledger(self, tmp_path, rows):
        tausik = tmp_path / ".tausik"
        tausik.mkdir(exist_ok=True)
        (tausik / "token_metrics.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
        )

    def test_rows_without_context_report_not_measured_never_zero(self, tmp_path):
        self._ledger(
            tmp_path,
            [
                {"ts": "1", "session_id": 1, "tool_name": "Read", "input_tokens": 2},
                {"ts": "2", "session_id": 1, "tool_name": "Edit", "input_tokens": 2},
            ],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["totals"]["context"] is None
        assert agg["totals"]["context_missing_events"] == 2
        table = format_table(agg)
        assert "не измерено" in table
        assert "context=0" not in table
        assert "n/a" in table

    def test_partial_context_totals_only_what_was_measured(self, tmp_path):
        self._ledger(
            tmp_path,
            [
                {"ts": "1", "session_id": 1, "tool_name": "Read", "context_tokens": 500},
                {"ts": "2", "session_id": 1, "tool_name": "Read"},
            ],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["totals"]["context"] == 500
        assert agg["totals"]["context_measured_events"] == 1
        assert agg["totals"]["context_missing_events"] == 1
        assert "не измерено for 1 of 2 event(s)" in format_table(agg)

    def test_unattributed_rows_are_counted_and_named_not_dropped(self, tmp_path):
        self._ledger(
            tmp_path,
            [
                {"ts": "1", "session_id": None, "tool_name": "Read", "context_tokens": 10},
                {"ts": "2", "session_id": 5, "tool_name": "Edit", "context_tokens": 20},
            ],
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["unattributed_events"] == 1
        assert agg["sessions_observed"] == 1
        assert "outside every session" in format_table(agg)

    def test_coverage_prints_the_denominator(self, tmp_path):
        _make_db(tmp_path)
        self._ledger(
            tmp_path, [{"ts": "1", "session_id": 1, "tool_name": "Read", "context_tokens": 10}]
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["sessions_in_db"] == 3
        table = format_table(agg)
        assert "1 of 3 session(s)" in table
        assert "33.3% of the project's history" in table

    def test_unreadable_db_reports_denominator_as_unmeasured(self, tmp_path):
        self._ledger(
            tmp_path, [{"ts": "1", "session_id": 1, "tool_name": "Read", "context_tokens": 10}]
        )
        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["sessions_in_db"] is None
        assert "не измерено" in format_table(agg)


class TestLedgerCarriesNothingButNumbers:
    """AC8. The transcript holds arbitrary user input; the ledger must not."""

    def test_secrets_in_arguments_results_and_text_never_reach_a_row(self, tmp_path):
        secret = "sk-ant-SUPERSECRET-do-not-leak"
        transcript = tmp_path / "t.jsonl"
        _write_transcript(
            transcript,
            [
                {
                    "type": "assistant",
                    "timestamp": "2026-09-06T16:30:00Z",
                    "model": "claude-opus-5",
                    "content": [
                        {"type": "text", "text": f"I will use {secret} now"},
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": f"curl -H 'x: {secret}' https://example.test"},
                        },
                    ],
                    "usage": {"input_tokens": 2, "output_tokens": 5},
                },
                {
                    "type": "user",
                    "content": [{"type": "tool_result", "content": f"leaked {secret}"}],
                },
            ],
        )
        rows = extract_token_rows(str(transcript), 1)
        assert len(rows) == 1
        serialized = json.dumps(rows, ensure_ascii=False)
        assert secret not in serialized
        assert "curl" not in serialized
        assert set(rows[0]) == {
            "ts",
            "session_id",
            "tool_name",
            "input_tokens",
            "output_tokens",
            "cache_read",
            "cache_create",
            "context_tokens",
            "model",
            "source",
        }

    def test_source_is_the_transcript_id_not_its_path(self, tmp_path):
        nested = tmp_path / "secret-dir-name"
        nested.mkdir()
        transcript = nested / "b1946ac9-2c8f-4f2a-9c3e-000000000000.jsonl"
        _write_transcript(transcript, [_turn("2026-09-06T16:30:00Z", ["Read"])])
        row = extract_token_rows(str(transcript), 1)[0]
        assert row["source"] == "b1946ac9-2c8f-4f2a-9c3e-000000000000"
        assert "secret-dir-name" not in json.dumps(row)
        assert os.sep not in row["source"]


class TestRebuildFromEveryTranscript:
    def test_rebuild_covers_transcripts_the_incremental_writer_never_saw(self, tmp_path):
        """7 of 227 sessions had rows while 42 transcripts sat unread on disk."""
        _make_db(tmp_path)
        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        _write_transcript(transcripts / "old.jsonl", [_turn("2026-09-06T16:30:00Z", ["Read"])])
        _write_transcript(transcripts / "mid.jsonl", [_turn("2026-09-06T17:30:00Z", ["Grep"])])
        _write_transcript(transcripts / "new.jsonl", [_turn("2026-09-06T18:30:00Z", ["Edit"])])

        receipt = rebuild_ledger(project_dir=str(tmp_path), transcript_dir=str(transcripts))
        assert receipt["transcripts"] == 3
        assert receipt["rows"] == 3
        assert receipt["sessions"] == 3
        assert receipt["unattributed"] == 0

        agg = aggregate(project_dir=str(tmp_path), last_n=10)
        assert agg["sessions_observed"] == 3
        assert agg["sessions_in_db"] == 3
        assert agg["totals"]["context"] == 3 * 50002

    def test_rebuild_is_idempotent(self, tmp_path):
        _make_db(tmp_path)
        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        _write_transcript(transcripts / "a.jsonl", [_turn("2026-09-06T16:30:00Z", ["Read"])])
        first = rebuild_ledger(project_dir=str(tmp_path), transcript_dir=str(transcripts))
        second = rebuild_ledger(project_dir=str(tmp_path), transcript_dir=str(transcripts))
        assert first["rows"] == second["rows"] == 1
        ledger = (tmp_path / ".tausik" / "token_metrics.jsonl").read_text(encoding="utf-8")
        assert len([ln for ln in ledger.splitlines() if ln.strip()]) == 1

    def test_rebuild_without_transcripts_reports_an_error_not_an_empty_success(self, tmp_path):
        _make_db(tmp_path)
        empty = tmp_path / "none"
        empty.mkdir()
        receipt = rebuild_ledger(project_dir=str(tmp_path), transcript_dir=str(empty))
        assert receipt["error"] == "no transcripts found"
        assert receipt["rows"] == 0

    def test_two_transcripts_of_one_session_both_survive(self, tmp_path):
        """Replace-by-session used to let the newest transcript erase the rest."""
        from token_rows import replace_session_token_rows

        _make_db(tmp_path)
        transcripts = tmp_path / "transcripts"
        transcripts.mkdir()
        _write_transcript(transcripts / "one.jsonl", [_turn("2026-09-06T16:10:00Z", ["Read"])])
        _write_transcript(transcripts / "two.jsonl", [_turn("2026-09-06T16:50:00Z", ["Edit"])])
        resolver = make_session_resolver(str(tmp_path))
        for name in ("one.jsonl", "two.jsonl"):
            replace_session_token_rows(
                extract_token_rows(str(transcripts / name), resolver), project_dir=str(tmp_path)
            )
        rows = [
            json.loads(ln)
            for ln in (tmp_path / ".tausik" / "token_metrics.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if ln.strip()
        ]
        assert {r["tool_name"] for r in rows} == {"Read", "Edit"}
        assert {r["session_id"] for r in rows} == {1}


class TestLiveLedgerIsClean:
    """A fixture cannot prove the real file is clean. This runs on the live one.

    Skips when the ledger is absent — it is gitignored, so a fresh checkout has
    none. The skip is loud on purpose: it says the live check did not run, which
    is not the same as saying it passed.
    """

    def _live_rows(self):
        path = Path(__file__).resolve().parents[1] / ".tausik" / "token_metrics.jsonl"
        if not path.is_file():
            return None
        rows = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def test_no_row_identity_appears_under_two_sessions(self):
        rows = self._live_rows()
        if rows is None:
            import pytest

            pytest.skip(".tausik/token_metrics.jsonl absent (gitignored) — live check not run")
        seen: dict[tuple, set] = {}
        for row in rows:
            key = (row.get("ts"), row.get("tool_name"), row.get("output_tokens"))
            seen.setdefault(key, set()).add(row.get("session_id"))
        duplicated = {k: v for k, v in seen.items() if len(v) > 1}
        assert not duplicated, (
            f"{len(duplicated)} row identities appear under more than one session — "
            "the attribution defect is back. Re-derive with "
            "`tausik metrics tokens --rebuild`."
        )

    def test_no_row_carries_a_session_the_db_does_not_have(self):
        rows = self._live_rows()
        if rows is None:
            import pytest

            pytest.skip(".tausik/token_metrics.jsonl absent (gitignored) — live check not run")
        root = str(Path(__file__).resolve().parents[1])
        known = {w[2] for w in load_session_windows(root)}
        if not known:
            import pytest

            pytest.skip("sessions table unreadable — live check not run")
        unknown = {r.get("session_id") for r in rows} - known - {None}
        assert not unknown, f"ledger references sessions that do not exist: {sorted(unknown)}"


class TestTranscriptLocatorMatchesOnEvidence:
    r"""The locator must prove a transcript is ours, never guess from a name.

    The old rule derived a directory name from the CWD and, on no match, fell
    back to "the most recently touched project anywhere on this machine". On
    Windows it NEVER matched — Claude Code writes `c--Projects-…` for `C:\Projects\…`
    while the derived slug was `C-Projects-…` — so the fallback was the normal path.
    Three consecutive rebuilds in session #227 read 42, 32 and 10 transcripts
    from three different projects before this was found.
    """

    def _fake_home(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        (home / ".claude" / "projects").mkdir(parents=True)
        monkeypatch.setattr(os.path, "expanduser", lambda p: str(home) if p == "~" else p)
        return home / ".claude" / "projects"

    def _project_transcript(self, root, dir_name, cwd, stem="a"):
        d = root / dir_name
        d.mkdir(exist_ok=True)
        entry = {"type": "user", "cwd": cwd, "content": "hi"}
        turn = _turn("2026-09-06T16:30:00Z", ["Read"])
        (d / f"{stem}.jsonl").write_text(
            json.dumps(entry) + "\n" + json.dumps(turn) + "\n", encoding="utf-8"
        )
        return d

    def test_windows_style_mangled_directory_is_matched(self, tmp_path, monkeypatch):
        import transcript_locator

        root = self._fake_home(tmp_path, monkeypatch)
        mine = tmp_path / "proj"
        mine.mkdir()
        self._project_transcript(root, "d--fake-mangled-name", str(mine))
        assert transcript_locator.project_transcript_dirs(str(mine)) == [str(root / "d--fake-mangled-name")]

    def test_another_projects_transcript_is_never_returned(self, tmp_path, monkeypatch):
        """THE defect: a foreign, more recently touched transcript used to win."""
        import transcript_locator

        root = self._fake_home(tmp_path, monkeypatch)
        mine = tmp_path / "proj"
        mine.mkdir()
        theirs = tmp_path / "other"
        theirs.mkdir()
        self._project_transcript(root, "theirs", str(theirs))
        assert transcript_locator.project_transcript_dirs(str(mine)) == []
        assert transcript_locator.latest_project_transcript(str(mine)) is None
        assert transcript_locator.project_transcripts(str(mine)) == []

    def test_result_is_stable_across_repeated_calls(self, tmp_path, monkeypatch):
        """Non-determinism was the symptom: 42, then 32, then 10 transcripts."""
        import transcript_locator

        root = self._fake_home(tmp_path, monkeypatch)
        mine = tmp_path / "proj"
        mine.mkdir()
        self._project_transcript(root, "mine", str(mine), stem="a")
        self._project_transcript(root, "mine", str(mine), stem="b")
        self._project_transcript(root, "loud", str(tmp_path / "other"), stem="c")
        answers = {tuple(transcript_locator.project_transcripts(str(mine))) for _ in range(5)}
        assert len(answers) == 1
        assert len(next(iter(answers))) == 2

    def test_a_transcript_without_a_cwd_is_not_claimed(self, tmp_path, monkeypatch):
        import transcript_locator

        root = self._fake_home(tmp_path, monkeypatch)
        mine = tmp_path / "proj"
        mine.mkdir()
        d = root / "unknown"
        d.mkdir()
        (d / "a.jsonl").write_text(json.dumps(_turn("2026-09-06T16:30:00Z", ["Read"])) + "\n", encoding="utf-8")
        assert transcript_locator.project_transcript_dirs(str(mine)) == []

    def test_separator_and_case_differences_do_not_break_the_match(self, tmp_path, monkeypatch):
        import transcript_locator

        root = self._fake_home(tmp_path, monkeypatch)
        mine = tmp_path / "proj"
        mine.mkdir()
        recorded = str(mine).replace("/", os.sep).upper()
        self._project_transcript(root, "mine", recorded)
        assert transcript_locator.project_transcript_dirs(str(mine)) == [str(root / "mine")]
