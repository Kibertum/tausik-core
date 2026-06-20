"""Tests for claudemd_writer — AGENTS.md/CLAUDE.md dynamic sync (v15p-agents-md-bootstrap)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from claudemd_writer import apply_dynamic_section, resolve_sibling_targets  # noqa: E402

_DOC = (
    "# CLAUDE.md\n\nStatic stuff.\n\n"
    "<!-- DYNAMIC:START -->\nOLD STATE\n<!-- DYNAMIC:END -->\n\nMore static.\n"
)


class TestApplyDynamicSection:
    def test_replaces_between_markers(self, tmp_path):
        p = tmp_path / "CLAUDE.md"
        p.write_text(_DOC, encoding="utf-8")
        msg, changed = apply_dynamic_section(str(p), "NEW STATE", dry_run=False)
        assert changed is True
        out = p.read_text(encoding="utf-8")
        assert "NEW STATE" in out
        assert "OLD STATE" not in out
        assert "Static stuff." in out and "More static." in out  # outside untouched

    def test_no_marker_is_skipped_not_error(self, tmp_path):
        p = tmp_path / "AGENTS.md"
        p.write_text("# AGENTS.md\n\nno markers here\n", encoding="utf-8")
        msg, changed = apply_dynamic_section(str(p), "X", dry_run=False)
        assert changed is False
        assert "marker not found" in msg
        assert p.read_text(encoding="utf-8") == "# AGENTS.md\n\nno markers here\n"

    def test_missing_end_marker_appends_end(self, tmp_path):
        p = tmp_path / "CLAUDE.md"
        p.write_text("# C\n<!-- DYNAMIC:START -->\nold\n", encoding="utf-8")
        _, changed = apply_dynamic_section(str(p), "fresh", dry_run=False)
        assert changed is True
        out = p.read_text(encoding="utf-8")
        assert "fresh" in out and "<!-- DYNAMIC:END -->" in out

    def test_up_to_date_no_change(self, tmp_path):
        p = tmp_path / "CLAUDE.md"
        p.write_text(_DOC, encoding="utf-8")
        apply_dynamic_section(str(p), "NEW", dry_run=False)
        _, changed = apply_dynamic_section(str(p), "NEW", dry_run=False)
        assert changed is False

    def test_dry_run_does_not_write(self, tmp_path, capsys):
        p = tmp_path / "CLAUDE.md"
        p.write_text(_DOC, encoding="utf-8")
        _, changed = apply_dynamic_section(str(p), "NEW STATE", dry_run=True)
        assert changed is True  # would change
        assert p.read_text(encoding="utf-8") == _DOC  # untouched
        assert "NEW STATE" in capsys.readouterr().out  # diff printed

    def test_end_marker_in_prose_before_section_not_corrupted(self, tmp_path):
        # An END marker mentioned in body text BEFORE the real section must not
        # mis-slice — END is located strictly after START.
        doc = (
            "# C\n\nDocs mention <!-- DYNAMIC:END --> in prose.\n\n"
            "<!-- DYNAMIC:START -->\nold\n<!-- DYNAMIC:END -->\n\ntail\n"
        )
        p = tmp_path / "CLAUDE.md"
        p.write_text(doc, encoding="utf-8")
        _, changed = apply_dynamic_section(str(p), "NEW", dry_run=False)
        out = p.read_text(encoding="utf-8")
        assert changed is True
        assert "Docs mention" in out and "tail" in out  # nothing dropped
        assert "NEW" in out and "old" not in out

    def test_missing_file_returns_error_tuple(self, tmp_path):
        msg, changed = apply_dynamic_section(str(tmp_path / "nope.md"), "X", dry_run=False)
        assert changed is False
        assert "Error reading" in msg


class TestResolveSiblingTargets:
    def test_includes_agents_md_sibling(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("x", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("y", encoding="utf-8")
        targets = resolve_sibling_targets(str(tmp_path / "CLAUDE.md"))
        assert any(t.endswith("AGENTS.md") for t in targets)
        assert len(targets) == 2

    def test_no_agents_md_returns_only_primary(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("x", encoding="utf-8")
        targets = resolve_sibling_targets(str(tmp_path / "CLAUDE.md"))
        assert targets == [str(tmp_path / "CLAUDE.md")]

    def test_does_not_pick_cwd_agents_md_for_other_dir_primary(self, tmp_path, monkeypatch):
        # primary lives in a subdir without AGENTS.md; an AGENTS.md in cwd must NOT
        # be picked up (would corrupt an unrelated file under MCP cwd).
        sub = tmp_path / "proj"
        sub.mkdir()
        (sub / "CLAUDE.md").write_text("x", encoding="utf-8")
        (tmp_path / "AGENTS.md").write_text("unrelated", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        targets = resolve_sibling_targets(str(sub / "CLAUDE.md"))
        assert targets == [str(sub / "CLAUDE.md")]  # cwd AGENTS.md excluded
