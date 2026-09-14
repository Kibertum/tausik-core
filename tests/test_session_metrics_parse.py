"""Tests for scripts/hooks/session_metrics.py::parse_transcript.

v14b-defect-session-metrics-opus-fallback regression guard: parse_transcript
used to default to "opus" pricing when the transcript had no `model` field,
silently 5×/19× over-attributing Sonnet/Haiku transcripts at Opus rates.
The fix: emit a stderr warning and return cost_usd=0.0 instead.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_HOOK_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks", "session_metrics.py")


def _import_module():
    """Direct in-process import for unit testing parse_transcript."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))
    import importlib
    import session_metrics  # type: ignore[import-not-found]

    importlib.reload(session_metrics)
    return session_metrics


def _write_transcript(tmp_path: Path, lines: list[dict]) -> str:
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    return str(path)


class TestParseTranscriptModelHandling:
    def test_known_model_yields_nonzero_cost(self, tmp_path):
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-opus-4-7",
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert m["model"] == "claude-opus-4-7"
        assert m["cost_usd"] > 0.0

    def test_missing_model_returns_absent_cost_not_opus_rates(self, tmp_path, capsys):
        """NEGATIVE: it once fell back to 'opus' rates, then to 0.0. Both were
        wrong in the same way — a number nobody derived. Now the cost is ABSENT
        and the tokens, which WERE observed, are kept."""
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert m["model"] == ""
        assert m["cost_usd"] is None
        assert m["tokens_total"] == 1500, "the tokens were observed and must survive"
        captured = capsys.readouterr()
        assert "session_metrics" in captured.err
        assert "missing 'model'" in captured.err

    def test_empty_model_string_returns_absent_cost(self, tmp_path):
        """NEGATIVE: empty string model is treated as missing, not as alias 'opus'."""
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "",
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert m["model"] == ""
        assert m["cost_usd"] is None

    def test_zero_tokens_no_warning_emitted(self, tmp_path, capsys):
        """If transcript is empty (no tokens), no warning fires — nothing was
        going to be billed anyway. Avoid noise on /end with empty sessions.
        """
        sm = _import_module()
        path = _write_transcript(tmp_path, [])
        m = sm.parse_transcript(path)
        assert m["cost_usd"] is None
        # 0 here is a real sum over an empty transcript, not a stand-in for the
        # unknown: every row was read and none carried usage.
        assert m["tokens_total"] == 0
        captured = capsys.readouterr()
        assert "missing 'model'" not in captured.err

    def test_sonnet_transcript_no_longer_attributed_to_opus(self, tmp_path):
        """The original H2 failure mode: a Sonnet transcript with model
        explicitly set must use Sonnet rates, not Opus.
        """
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
                }
            ],
        )
        m = sm.parse_transcript(path)
        # Sonnet input at $3/M → $3.0; opus rate would have been $15.0.
        assert m["cost_usd"] == 3.0

    def test_invalid_path_raises_or_handled(self, tmp_path):
        """NEGATIVE: nonexistent file path should not silently succeed with cost > 0."""
        sm = _import_module()
        bad = str(tmp_path / "does_not_exist.jsonl")
        try:
            sm.parse_transcript(bad)
        except (FileNotFoundError, OSError):
            return  # acceptable
        # If it returned, cost must be 0.0
        # Actually call again and assert
        try:
            result = sm.parse_transcript(bad)
        except (FileNotFoundError, OSError):
            return
        assert result["cost_usd"] == 0.0


class TestParseTranscriptSessionAttribution:
    """The database rollup must use the same containment rule as token rows."""

    def test_one_transcript_is_split_by_the_target_session(self, tmp_path):
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "timestamp": "2026-09-11T10:10:00Z",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                },
                {
                    "type": "assistant",
                    "timestamp": "2026-09-11T11:10:00Z",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 200, "output_tokens": 20},
                },
            ],
        )
        by_timestamp = {
            "2026-09-11T10:10:00Z": 11,
            "2026-09-11T11:10:00Z": 12,
        }

        first = sm.parse_transcript(path, session_resolver=by_timestamp.get, session_id=11)
        second = sm.parse_transcript(path, session_resolver=by_timestamp.get, session_id=12)

        assert first["tokens_total"] == 110
        assert second["tokens_total"] == 220

    def test_unattributable_timestamp_is_excluded_not_guessed(self, tmp_path):
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-sonnet-4-6",
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                },
            ],
        )

        metrics = sm.parse_transcript(path, session_resolver=lambda _timestamp: None, session_id=12)

        assert metrics["tokens_total"] == 0
        assert metrics["messages"] == 0


class TestParseTranscriptCompactionBilling:
    """Compaction billed under usage.iterations is counted ONCE, not twice.

    This class used to assert `1000 + 300 = 1300`, on the belief that
    `iterations` held only the extra passes. It holds ALL of them, the first
    included, so the top level is a view of the list rather than a separate
    quantity — and the old rule doubled every message. Measured over 23,836
    live messages in session #227: 99.92% carry one iteration identical to the
    top level, and the inflation was 1.9999x on tokens and therefore on cost.
    """

    def test_a_lone_iteration_is_not_added_to_the_top_level(self, tmp_path):
        """The shape that covers 99.92% of real messages."""
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-opus-4-8",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        # The API repeats the message here; it is not an extra pass.
                        "iterations": [{"input_tokens": 1000, "output_tokens": 500}],
                    },
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert (m["tokens_input"], m["tokens_output"]) == (1000, 500)
        assert m["tokens_total"] == 1500  # 3000 under the superseded rule

    def test_extra_compaction_passes_are_still_counted(self, tmp_path):
        """The original intent survives: two passes bill for two passes."""
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-opus-4-8",
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "iterations": [
                            {"input_tokens": 1000, "output_tokens": 500},
                            {"input_tokens": 300, "output_tokens": 100},
                        ],
                    },
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert (m["tokens_input"], m["tokens_output"]) == (1300, 600)
        assert m["tokens_total"] == 1900

    def test_no_iterations_unchanged(self, tmp_path):
        """Regression guard: a plain usage block still sums exactly as before."""
        sm = _import_module()
        path = _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-opus-4-8",
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert (m["tokens_input"], m["tokens_output"]) == (1000, 500)


class TestParseTranscriptViaCLI:
    """End-to-end smoke through the CLI entrypoint — exercises the real path."""

    def test_cli_no_model_emits_stderr_warning(self, tmp_path):
        path = tmp_path / "transcript.jsonl"
        path.write_text(
            json.dumps({"type": "assistant", "usage": {"input_tokens": 100, "output_tokens": 50}})
            + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, _HOOK_PATH, str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, result.stderr
        # Stderr should contain the warning
        assert "missing 'model'" in result.stderr


class TestRecordToDbSelfLocation:
    """engine-claude-literals-followup: record_to_db located project.py via a
    miscounted dirname chain that pointed at the *profile* dir. The dead first
    candidate `<profile>/.claude/scripts/project.py` never matched, and
    `cwd=<profile>` made project.py resolve `.tausik/` under the profile — a
    silent DB-record miss. It now self-locates and runs with the real root cwd.
    """

    def _stub_run(self, monkeypatch, captured):
        import subprocess as _sub

        def fake_run(cmd, **kw):
            captured["cmd"] = cmd
            captured["cwd"] = kw.get("cwd")

            class _R:
                returncode = 0
                stdout = "ok"
                stderr = ""

            return _R()

        monkeypatch.setattr(_sub, "run", fake_run)

    def test_deployed_layout_uses_profile_script_and_root_cwd(self, tmp_path, monkeypatch):
        sm = _import_module()
        import _common  # type: ignore[import-not-found]

        root = tmp_path / "proj"
        profile = root / ".claude"
        (profile / "scripts").mkdir(parents=True)
        (profile / "scripts" / "project.py").write_text("# stub\n", encoding="utf-8")

        monkeypatch.setattr(_common, "profile_dir", lambda: str(profile))
        monkeypatch.setattr(_common, "project_root", lambda: str(root))
        captured: dict = {}
        self._stub_run(monkeypatch, captured)

        ok = sm.record_to_db({"tokens_input": 1, "tokens_output": 2, "tokens_total": 3})

        assert ok is True
        assert captured["cmd"][1] == str(profile / "scripts" / "project.py")
        # cwd is the true project root (parent of the profile), NOT the profile.
        assert captured["cwd"] == str(root)

    def test_source_layout_uses_root_script(self, tmp_path, monkeypatch):
        """NEGATIVE/boundary (a): no profile marker → root scripts/project.py, cwd=root."""
        sm = _import_module()
        import _common  # type: ignore[import-not-found]

        root = tmp_path / "src"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "project.py").write_text("# stub\n", encoding="utf-8")

        monkeypatch.setattr(_common, "profile_dir", lambda: None)
        monkeypatch.setattr(_common, "project_root", lambda: str(root))
        captured: dict = {}
        self._stub_run(monkeypatch, captured)

        ok = sm.record_to_db({"tokens_input": 0})

        assert ok is True
        assert captured["cmd"][1] == str(root / "scripts" / "project.py")
        assert captured["cwd"] == str(root)

    def test_missing_project_py_returns_false_without_crash(self, tmp_path, monkeypatch, capsys):
        """NEGATIVE/boundary (b): project.py nowhere → False + stderr, never raises."""
        sm = _import_module()
        import _common  # type: ignore[import-not-found]

        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.setattr(_common, "profile_dir", lambda: None)
        monkeypatch.setattr(_common, "project_root", lambda: str(empty))

        ok = sm.record_to_db({"tokens_input": 0})

        assert ok is False
        assert "project.py not found" in capsys.readouterr().err

    def test_explicit_session_id_is_forwarded_to_the_cli(self, tmp_path, monkeypatch):
        sm = _import_module()
        import _common  # type: ignore[import-not-found]

        root = tmp_path / "src"
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "project.py").write_text("# stub\n", encoding="utf-8")
        monkeypatch.setattr(_common, "profile_dir", lambda: None)
        monkeypatch.setattr(_common, "project_root", lambda: str(root))
        captured: dict = {}
        self._stub_run(monkeypatch, captured)

        assert sm.record_to_db({"tokens_input": 1}, session_id=42) is True
        pos = captured["cmd"].index("--session-id")
        assert captured["cmd"][pos + 1] == "42"

    def test_no_hardcoded_profile_in_deployed_script_join(self):
        """The dead `<profile>/.claude/scripts/project.py` join must be gone.

        The only `.claude` the file may still carry is the HOME transcript
        store `os.path.join(home, ".claude", "projects")` — not a project
        profile, so it is out of scope for the ide_utils generalisation.
        """
        text = open(_HOOK_PATH, encoding="utf-8").read()
        assert 'os.path.join(project_root, ".claude"' not in text


class TestToolRowsForTheOptionalTrace:
    """The names the OTLP child spans are built from, collected on the walk.

    An OUT-PARAMETER, not another key in the metrics dict: that dict is written
    to the metrics file and recorded to the database, and telemetry has no
    business changing the shape of either.
    """

    def _transcript(self, tmp_path):
        return _write_transcript(
            tmp_path,
            [
                {
                    "type": "assistant",
                    "model": "claude-opus-4-7",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "content": [
                        {"type": "tool_use", "name": "Read"},
                        {"type": "tool_use", "name": "Bash"},
                        {"type": "text", "text": "not a tool"},
                        {"type": "tool_use"},  # nameless — counted, never named
                    ],
                }
            ],
        )

    def test_rows_carry_the_tool_names_and_the_model(self, tmp_path):
        sm = _import_module()
        rows: list = []
        metrics = sm.parse_transcript(self._transcript(tmp_path), rows)
        assert metrics["tool_calls"] == 3, "the count includes the nameless block"
        assert [r["tool_name"] for r in rows] == ["Read", "Bash"], "only named ones become spans"
        assert {r["model_id"] for r in rows} == {"claude-opus-4-7"}
        assert [r["id"] for r in rows] == [1, 2], "ids are positional and stable"

    def test_the_metrics_dict_is_unchanged_by_the_collection(self, tmp_path):
        """NEGATIVE SCENARIO: the extension must not alter what everything else reads."""
        sm = _import_module()
        path = self._transcript(tmp_path)
        without = sm.parse_transcript(path)
        with_rows = sm.parse_transcript(path, [])
        assert without == with_rows
        assert "tool_spans" not in without and "tool_rows" not in without

    def test_omitting_the_list_collects_nothing_and_still_parses(self, tmp_path):
        sm = _import_module()
        assert sm.parse_transcript(self._transcript(tmp_path))["tool_calls"] == 3


class TestProfileDirAgreement:
    """AC-3: self-location lives once in _common; session_start delegates to it."""

    def test_common_and_session_start_agree(self):
        _import_module()  # ensures scripts/ + scripts/hooks/ are on sys.path
        import _common  # type: ignore[import-not-found]
        import session_start  # type: ignore[import-not-found]

        assert session_start._profile_dir() == _common.profile_dir()
