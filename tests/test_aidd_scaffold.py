"""Tests for scripts/project_cli_aidd.py — AIDD scaffold."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_cli_aidd import (  # noqa: E402
    AIDD_FILES,
    _resolve_choice,
    cmd_init_template,
    is_known_template,
    scaffold_aidd,
)


def _captured_log():
    buf: list[str] = []
    return buf, lambda msg: buf.append(msg)


class TestResolveChoice:
    def test_empty_defaults_to_skip(self):
        assert _resolve_choice("") == "skip"
        assert _resolve_choice("   ") == "skip"

    def test_first_letter_match(self):
        assert _resolve_choice("o") == "overwrite"
        assert _resolve_choice("overwrite") == "overwrite"
        assert _resolve_choice("M") == "merge-append"
        assert _resolve_choice("Skip") == "skip"
        assert _resolve_choice("a") == "abort-all"

    def test_unknown_falls_back_to_skip(self):
        assert _resolve_choice("xyz") == "skip"


class TestIsKnownTemplate:
    def test_aidd_known(self):
        assert is_known_template("aidd") is True

    def test_unknown_returns_false(self):
        assert is_known_template("bogus") is False
        assert is_known_template("") is False


class TestScaffoldAidd:
    def test_clean_dir_creates_all_three(self, tmp_path):
        log, log_fn = _captured_log()
        result = scaffold_aidd(str(tmp_path), log=log_fn)
        assert sorted(result["created"]) == sorted(AIDD_FILES)
        assert result["overwritten"] == []
        assert result["merged"] == []
        assert result["skipped"] == []
        assert result["aborted"] is False
        for f in AIDD_FILES:
            assert os.path.isfile(tmp_path / f)
            assert (tmp_path / f).read_text(encoding="utf-8")  # non-empty

    def test_partial_conflict_default_skip_keeps_existing(self, tmp_path):
        # Pre-populate vision.md with a sentinel.
        (tmp_path / "vision.md").write_text("MY EXISTING VISION", encoding="utf-8")
        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            prompt=lambda _: "",  # empty → skip
            log=log_fn,
        )
        assert sorted(result["created"]) == sorted(["idea.md", "conventions.md"])
        assert result["skipped"] == ["vision.md"]
        assert (tmp_path / "vision.md").read_text(encoding="utf-8") == "MY EXISTING VISION"
        assert any("Conflict: vision.md" in line for line in log)

    def test_full_conflict_default_skip_keeps_all_existing(self, tmp_path):
        sentinels: dict[str, str] = {}
        for f in AIDD_FILES:
            content = f"sentinel-{f}"
            (tmp_path / f).write_text(content, encoding="utf-8")
            sentinels[f] = content
        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            prompt=lambda _: "",
            log=log_fn,
        )
        assert result["created"] == []
        assert sorted(result["skipped"]) == sorted(AIDD_FILES)
        for f in AIDD_FILES:
            assert (tmp_path / f).read_text(encoding="utf-8") == sentinels[f]

    def test_force_overwrites_without_prompt(self, tmp_path):
        for f in AIDD_FILES:
            (tmp_path / f).write_text(f"sentinel-{f}", encoding="utf-8")
        prompt_calls: list[str] = []

        def _prompt(p: str) -> str:
            prompt_calls.append(p)
            return "should-not-be-asked"

        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            force=True,
            prompt=_prompt,
            log=log_fn,
        )
        assert sorted(result["overwritten"]) == sorted(AIDD_FILES)
        assert prompt_calls == [], "prompt must not run with --force"
        for f in AIDD_FILES:
            content = (tmp_path / f).read_text(encoding="utf-8")
            assert "sentinel" not in content
            assert content  # template content present

    def test_overwrite_choice_replaces_file(self, tmp_path):
        (tmp_path / "idea.md").write_text("old", encoding="utf-8")
        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            prompt=lambda _: "o",
            log=log_fn,
        )
        assert "idea.md" in result["overwritten"]
        assert (tmp_path / "idea.md").read_text(encoding="utf-8") != "old"

    def test_merge_append_keeps_existing_and_appends_template(self, tmp_path):
        (tmp_path / "vision.md").write_text("user vision text", encoding="utf-8")
        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            prompt=lambda _: "m",
            log=log_fn,
        )
        assert "vision.md" in result["merged"]
        merged = (tmp_path / "vision.md").read_text(encoding="utf-8")
        assert merged.startswith("user vision text")
        assert "merged from AIDD template" in merged

    def test_abort_all_skips_remaining_in_batch(self, tmp_path):
        # All three files exist so each one would conflict.
        for f in AIDD_FILES:
            (tmp_path / f).write_text(f"sentinel-{f}", encoding="utf-8")
        log, log_fn = _captured_log()
        result = scaffold_aidd(
            str(tmp_path),
            prompt=lambda _: "a",  # first prompt aborts
            log=log_fn,
        )
        assert result["aborted"] is True
        assert sorted(result["skipped"]) == sorted(AIDD_FILES)
        assert result["created"] == []
        assert result["overwritten"] == []


class TestCmdInitTemplate:
    def test_unknown_template_returns_2(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = cmd_init_template("bogus")
        assert rc == 2
        err = capsys.readouterr().err
        assert "Unknown template: bogus" in err
        # No files leaked into the working dir.
        assert not any((tmp_path / f).exists() for f in AIDD_FILES)

    def test_aidd_clean_dir_returns_0(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = cmd_init_template("aidd")
        assert rc == 0
        out = capsys.readouterr().out
        assert "AIDD scaffold (aidd)" in out
        assert "3 created" in out
        for f in AIDD_FILES:
            assert (tmp_path / f).is_file()
