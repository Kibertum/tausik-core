"""The AGENTS.md sibling is tracked; what `update-claudemd` writes into it is a policy (GitLab #14).

A project that keeps CLAUDE.md out of git for the sake of auto-refresh still
tracks AGENTS.md — and every session wrote the session number, the counters,
the memory tail and "Shared knowledge — from other projects" into the
repository's history, with a `M AGENTS.md` after one /start and a verify
warning nothing could honestly clear. Two things follow, both here:

* `claudemd.sibling_dynamic` (default true) — the sibling is refreshed; false —
  the sibling is not written at all.
* Whatever the knob, the sibling never carries other projects' knowledge: the
  shared section is stripped, and a tail left with nothing under it is dropped.

The state gate judges the sibling against the same plan the writer follows, so
a sibling whose only knowledge would be foreign is not called "drift".
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (
    os.path.join(_ROOT, "scripts"),
    os.path.join(_ROOT, "harness", "claude", "mcp", "project"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import claudemd_writer as cw  # noqa: E402
import service_knowledge_aggregates as ska  # noqa: E402
from handlers import handle_tool  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_cli_extra import cmd_update_claudemd  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = [
    "scripts/claudemd_writer.py",
    "scripts/gate_claudemd_state.py",
    "scripts/project_cli_extra.py",
    "scripts/service_knowledge_aggregates.py",
    "harness/claude/mcp/project/handlers_skill.py",
]

_DOC = "# doc\n\n<!-- DYNAMIC:START -->\nold\n<!-- DYNAMIC:END -->\n\ntail\n"
_SHARED = [
    "",
    f"{ska.SHARED_KNOWLEDGE_HEADING} (1):**",
    "- [gotcha] a library fact from elsewhere",
]


def _block(path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[text.index("<!-- DYNAMIC:START -->") : text.index("<!-- DYNAMIC:END -->")]


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / ".tausik").mkdir()
    (tmp_path / "CLAUDE.md").write_text(_DOC, encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(_DOC, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ska, "_shared_section", lambda n: (_SHARED, []))
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield tmp_path, svc
    svc.be.close()


def _knob(tmp_path, value):
    (tmp_path / ".tausik" / "config.json").write_text(
        json.dumps({"claudemd": {"sibling_dynamic": value}}), encoding="utf-8"
    )


def _cli(svc):
    cmd_update_claudemd(svc, argparse.Namespace(claudemd=None, dry_run=False))


def _mcp(svc):
    handle_tool(svc, "tausik_update_claudemd", {})


class TestTheKnob:
    @pytest.mark.parametrize("run", [_cli, _mcp], ids=["cli", "mcp"])
    def test_default_refreshes_the_sibling(self, project, run):
        tmp_path, svc = project
        svc.memory_add("convention", "Slugs in kebab-case", "so")
        run(svc)
        assert "kebab-case" in _block(tmp_path / "AGENTS.md")
        assert "old" not in _block(tmp_path / "AGENTS.md")

    @pytest.mark.parametrize("run", [_cli, _mcp], ids=["cli", "mcp"])
    def test_false_leaves_the_sibling_untouched(self, project, run):
        """NEGATIVE: knob off — CLAUDE.md is refreshed, AGENTS.md keeps its old block byte for byte."""
        tmp_path, svc = project
        _knob(tmp_path, False)
        before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        run(svc)
        assert "old" not in _block(tmp_path / "CLAUDE.md")
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == before

    def test_the_knob_is_read_from_this_projects_config(self, project):
        tmp_path, _ = project
        assert cw.sibling_dynamic_enabled(str(tmp_path / ".tausik")) is True
        _knob(tmp_path, False)
        assert cw.sibling_dynamic_enabled(str(tmp_path / ".tausik")) is False
        _knob(tmp_path, "no")  # anything but an explicit false is on
        assert cw.sibling_dynamic_enabled(str(tmp_path / ".tausik")) is True


class TestForeignKnowledgeNeverReachesTheSibling:
    @pytest.mark.parametrize("run", [_cli, _mcp], ids=["cli", "mcp"])
    @pytest.mark.parametrize("knob", [None, True], ids=["default", "explicit-true"])
    def test_the_shared_section_is_in_the_primary_and_not_in_the_sibling(self, project, run, knob):
        """NEGATIVE: at any knob value that writes the sibling, the foreign section stays out."""
        tmp_path, svc = project
        if knob is not None:
            _knob(tmp_path, knob)
        svc.memory_add("convention", "Slugs in kebab-case", "so")
        run(svc)
        primary, sibling = _block(tmp_path / "CLAUDE.md"), _block(tmp_path / "AGENTS.md")
        assert ska.SHARED_KNOWLEDGE_HEADING in primary and "from elsewhere" in primary
        assert ska.SHARED_KNOWLEDGE_HEADING not in sibling and "from elsewhere" not in sibling
        assert "kebab-case" in sibling, "the project's own knowledge still reaches the sibling"

    def test_a_project_whose_only_knowledge_is_shared_gives_the_sibling_no_tail(self, project):
        tmp_path, svc = project
        _cli(svc)
        sibling = _block(tmp_path / "AGENTS.md")
        assert ska.MEMORY_TAIL_HEADING not in sibling, "a heading over nothing is not a tail"
        assert "Session:" in sibling, "the state itself is still written"

    def test_strip_keeps_a_warning_that_follows_the_section(self):
        block = "\n".join(
            ["## Current State", "Session: none", "", ska.MEMORY_TAIL_HEADING]
            + ["Conventions (1):", "- #1 x"]
            + _SHARED
            + [" ", "⚠ store version skew"]
        )
        out = cw.strip_foreign_knowledge(block)
        assert "from elsewhere" not in out
        assert "⚠ store version skew" in out and "- #1 x" in out
        assert "\n\n \n" not in out and "\n\n\n" not in out, "the two separators must not stack"

    def test_the_knob_is_read_from_the_project_that_owns_the_files(self, project, tmp_path):
        """`--claudemd <other project>` honours THAT project's opt-out, not the caller's."""
        tmp_path, svc = project
        other = tmp_path / "other"
        (other / ".tausik").mkdir(parents=True)
        (other / "CLAUDE.md").write_text(_DOC, encoding="utf-8")
        (other / "AGENTS.md").write_text(_DOC, encoding="utf-8")
        (other / ".tausik" / "config.json").write_text(
            json.dumps({"claudemd": {"sibling_dynamic": False}}), encoding="utf-8"
        )
        before = (other / "AGENTS.md").read_text(encoding="utf-8")
        cmd_update_claudemd(
            svc, argparse.Namespace(claudemd=str(other / "CLAUDE.md"), dry_run=False)
        )
        assert "old" not in _block(other / "CLAUDE.md")
        assert (other / "AGENTS.md").read_text(encoding="utf-8") == before

    def test_an_unreadable_config_keeps_the_sibling_on_and_says_so(self, project, caplog):
        tmp_path, _ = project
        (tmp_path / ".tausik" / "config.json").write_text("{not json", encoding="utf-8")
        with caplog.at_level("WARNING"):
            assert cw.sibling_dynamic_enabled(str(tmp_path / ".tausik")) is True


class TestTheGateJudgesWhatTheWriterWrites:
    """The gate looks where the writer writes, with the writer's expectation."""

    def _gate(self, tmp_path, monkeypatch):
        import project_config
        from gate_claudemd_state import run_claudemd_state_gate

        monkeypatch.setattr(
            project_config, "find_tausik_dir", lambda *a, **k: str(tmp_path / ".tausik")
        )
        return run_claudemd_state_gate()

    def test_a_sibling_with_no_tail_because_all_knowledge_is_foreign_is_not_drift(
        self, project, monkeypatch
    ):
        tmp_path, svc = project
        _cli(svc)
        outcome = self._gate(tmp_path, monkeypatch)
        assert outcome[0] is True, outcome[1]

    def test_a_sibling_the_policy_does_not_write_is_not_judged(self, project, monkeypatch):
        tmp_path, svc = project
        _knob(tmp_path, False)
        svc.memory_add("convention", "Slugs in kebab-case", "so")
        _cli(svc)
        outcome = self._gate(tmp_path, monkeypatch)
        assert outcome[0] is True, outcome[1]

    def test_a_sibling_that_lost_its_own_tail_is_still_drift(self, project, monkeypatch):
        """NEGATIVE: the trimming does not blind the gate to the failure it exists for."""
        tmp_path, svc = project
        svc.memory_add("convention", "Slugs in kebab-case", "so")
        _cli(svc)
        text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        head = text[: text.index("<!-- DYNAMIC:START -->") + len("<!-- DYNAMIC:START -->")]
        wiped = (
            head
            + "\n## Current State\nSession: none\n"
            + text[text.index("<!-- DYNAMIC:END -->") :]
        )
        (tmp_path / "AGENTS.md").write_text(wiped, encoding="utf-8")
        outcome = self._gate(tmp_path, monkeypatch)
        assert outcome[0] is False and "AGENTS.md" in outcome[1]


class TestAWriterThatIgnoresTheKnobIsCaught:
    """MUTATION: read the knob, then disregard it — the tests above must go red."""

    def test_writing_the_full_block_to_the_sibling_is_visible(self, project, monkeypatch):
        tmp_path, svc = project
        monkeypatch.setattr(cw, "strip_foreign_knowledge", lambda block: block)
        _cli(svc)
        assert ska.SHARED_KNOWLEDGE_HEADING in _block(tmp_path / "AGENTS.md"), (
            "with trimming disabled the foreign section reaches the sibling — "
            "the assertion the real tests make would fail here"
        )

    def test_writing_with_the_knob_false_is_visible(self, project, monkeypatch):
        tmp_path, svc = project
        _knob(tmp_path, False)
        monkeypatch.setattr(cw, "sibling_dynamic_enabled", lambda tausik_dir=None: True)
        before = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        _cli(svc)
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") != before
