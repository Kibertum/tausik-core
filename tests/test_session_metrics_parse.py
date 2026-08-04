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

    def test_missing_model_returns_zero_cost_not_opus_rates(self, tmp_path, capsys):
        """NEGATIVE: previously fell back to 'opus' rates; now returns 0.0 + stderr warn."""
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
        assert m["cost_usd"] == 0.0
        captured = capsys.readouterr()
        assert "session_metrics" in captured.err
        assert "missing 'model'" in captured.err

    def test_empty_model_string_returns_zero_cost(self, tmp_path):
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
        assert m["cost_usd"] == 0.0

    def test_zero_tokens_no_warning_emitted(self, tmp_path, capsys):
        """If transcript is empty (no tokens), no warning fires — nothing was
        going to be billed anyway. Avoid noise on /end with empty sessions.
        """
        sm = _import_module()
        path = _write_transcript(tmp_path, [])
        m = sm.parse_transcript(path)
        assert m["cost_usd"] == 0.0
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


class TestParseTranscriptCompactionBilling:
    """AC4 (l26-tokenizer-calibration): server-side compaction billed under
    usage.iterations must be counted, not dropped by a top-level-only sum.
    """

    def test_iterations_are_added_to_top_level_tokens(self, tmp_path):
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
                        # Separately-billed compaction pass — omitted from the
                        # top-level counts; a naive sum would report 1000/500.
                        "iterations": [{"input_tokens": 300, "output_tokens": 100}],
                    },
                }
            ],
        )
        m = sm.parse_transcript(path)
        assert m["tokens_input"] == 1300
        assert m["tokens_output"] == 600
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

    def test_no_hardcoded_profile_in_deployed_script_join(self):
        """The dead `<profile>/.claude/scripts/project.py` join must be gone.

        The only `.claude` the file may still carry is the HOME transcript
        store `os.path.join(home, ".claude", "projects")` — not a project
        profile, so it is out of scope for the ide_utils generalisation.
        """
        text = open(_HOOK_PATH, encoding="utf-8").read()
        assert 'os.path.join(project_root, ".claude"' not in text


class TestProfileDirAgreement:
    """AC-3: self-location lives once in _common; session_start delegates to it."""

    def test_common_and_session_start_agree(self):
        _import_module()  # ensures scripts/ + scripts/hooks/ are on sys.path
        import _common  # type: ignore[import-not-found]
        import session_start  # type: ignore[import-not-found]

        assert session_start._profile_dir() == _common.profile_dir()
