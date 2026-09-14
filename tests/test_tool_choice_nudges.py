"""A tool TAUSIK ships is named at the moment an alternative was chosen.

a-tool-is-chosen-at-the-moment-the-alternative-appears. Measured over this
project's own transcripts before any of this existed (session #233, 5,966 tool
calls, 735 user turns):

    dead-end        0 uses. NONE — while that same window's journals carry at
                    least four refuted hypotheses.
    tausik symbol   2 uses against 226 greps for a definition. Built an hour
                    earlier and not being chosen.
    checkpoint      no mechanism at all; the rule asks for one every 30-50 calls,
                    so roughly 149 were due.
    task log        222 uses — one per 26 tool calls, against a rule that says
                    "after every meaningful step".

FOUR RULES, ONE DEFECT: the tool exists, the rule demands it, and nothing joins
them at the moment of choice. Those numbers are what "joined by memory alone"
measures to.

WHAT IS ASSERTED HERE is behaviour, driven through the real hook as a subprocess
with a real payload. And the negative half carries equal weight: a nudge that
fires on ordinary work is one the reader learns to skip, and a skipped notice
costs the attention the next real warning needs (convention #291).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_HOOK = _REPO / "scripts" / "hooks" / "tool_choice_nudge.py"
for _p in (str(_REPO / "scripts"), str(_REPO / "scripts" / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tool_choice_nudge as nudge  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/hooks/", "bootstrap/"]


def _fire(tmp_path: Path, command: str, session: str = "t") -> str:
    payload = {"tool_name": "Bash", "session_id": session, "tool_input": {"command": command}}
    result = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"},
    )
    assert result.returncode == 0, "a nudge must never fail the call it follows"
    return result.stderr


class TestAGrepForADefinitionIsAnsweredWithTheTool:
    @pytest.mark.parametrize(
        "command,name",
        [
            pytest.param('grep -n "def tags_unmoved" scripts/x.py', "tags_unmoved", id="def"),
            pytest.param("grep -rn 'class Symbol' scripts/", "Symbol", id="class"),
            pytest.param('rg "def build_index"', "build_index", id="another_grep_flavour"),
        ],
    )
    def test_it_names_the_exact_command_to_run_instead(self, tmp_path, command, name):
        out = _fire(tmp_path, command)
        assert f"tausik symbol {name}" in out, out

    def test_it_says_why_in_calls_rather_than_asserting_a_saving(self, tmp_path):
        """The measured result was half the CALLS, not fewer characters. A note
        claiming a token saving would be quoting a number we did not get."""
        out = _fire(tmp_path, 'grep -n "def target" a.py')
        assert "2 calls" in out and "1" in out


class TestOrdinaryWorkIsLeftAlone:
    """AC6. The half that decides whether anybody keeps reading these."""

    @pytest.mark.parametrize(
        "command",
        [
            pytest.param('grep -rn "definition" docs/', id="a_word_that_contains_def"),
            pytest.param("grep -rn 'the default' README.md", id="prose"),
            pytest.param("ls scripts/defaults/", id="a_path_containing_def"),
            pytest.param("pytest -q", id="unrelated"),
            pytest.param("git commit -m 'define the route'", id="the_word_in_a_message"),
        ],
    )
    def test_no_note_is_produced(self, tmp_path, command):
        assert _fire(tmp_path, command) == "", command


class TestEachSubjectSpeaksOncePerSession:
    def test_a_second_definition_grep_is_silent(self, tmp_path):
        first = _fire(tmp_path, 'grep -n "def one" a.py')
        second = _fire(tmp_path, 'grep -n "def two" b.py')
        assert "tausik symbol one" in first
        assert second == "", "the same subject spoke twice in one session"

    def test_the_two_subjects_do_not_silence_each_other(self, tmp_path):
        """A single mark for both would let whichever came first hide the other."""
        _fire(tmp_path, 'grep -n "def one" a.py')
        out = _fire(tmp_path, ".tausik/tausik task done x")
        assert "tausik_task_done" in out

    def test_a_new_session_starts_over(self, tmp_path):
        _fire(tmp_path, 'grep -n "def one" a.py', session="s1")
        again = _fire(tmp_path, 'grep -n "def one" a.py', session="s2")
        assert "tausik symbol one" in again


class TestTheDetectorReadsTheSearchAndNotTheLine:
    @pytest.mark.parametrize(
        "command,expected",
        [
            pytest.param('grep -n "def build_index" x.py', ["build_index"], id="one_definition"),
            pytest.param(
                'grep "def a" x.py; grep "class B" y.py',
                ["B", "a"],
                id="two_searches_in_one_line",
            ),
            pytest.param('grep -rn "define" docs/', [], id="prose_yields_nothing"),
            pytest.param("grep -rn 'the default' README.md", [], id="a_word_containing_def"),
        ],
    )
    def test_it_reads_the_search_and_not_the_line(self, command, expected):
        """The detector's whole value is telling a definition search from a text
        search: firing on the second would make it noise, and noise is skipped."""
        assert nudge.symbols_in(command) == expected


class TestClosureNamesDeadEndWhenTheJournalShowsOne:
    """AC1. `dead-end` was used 0 times in 5,966 calls while journals in that
    same window recorded refuted hypotheses. The general 'no knowledge captured'
    warning lists three options, and a reader satisfies it with the cheapest."""

    def _warns(self, notes: str) -> bool:
        from service_task_done import _journal_shows_a_refutation

        return _journal_shows_a_refutation(notes)

    @pytest.mark.parametrize(
        "notes",
        [
            pytest.param("Замер ОПРОВЕРГ гипотезу таймаута", id="ru_refuted"),
            pytest.param("the timeout hypothesis was refuted by measurement", id="en_refuted"),
            pytest.param("подход не сработал, откатили", id="ru_did_not_work"),
            pytest.param("this turned out to be wrong", id="en_wrong"),
        ],
    )
    def test_a_refutation_in_the_journal_is_recognised(self, notes):
        assert self._warns(notes)

    @pytest.mark.parametrize(
        "notes",
        [
            pytest.param("AC verified: 1. ok 2. ok", id="a_plain_checklist"),
            pytest.param("added the index and the tests", id="ordinary_work"),
            pytest.param("", id="empty"),
        ],
    )
    def test_an_ordinary_journal_is_not(self, notes):
        assert not self._warns(notes)


class TestTheCommandSectionCarriesItsOwnCount:
    """AC4. Eighteen of fifty-two commands were named nowhere an agent reads, and
    listing all fifty-two would cost that budget on every turn instead."""

    def test_the_number_comes_from_the_parser(self):
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_templates import build_commands_section
        from route_map import cli_commands

        text = build_commands_section()
        assert f"{len(cli_commands())} commands" in text

    def test_it_points_at_help_rather_than_listing_everything(self):
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_templates import build_commands_section

        text = build_commands_section()
        assert "--help" in text
        assert text.count(".tausik/tausik ") < 15, "the section is turning into the full list"

    def test_the_tool_this_release_shipped_is_in_the_nine(self):
        """A command nobody is told about is one nobody uses — measured at 2 uses
        against 226 greps."""
        sys.path.insert(0, str(_REPO / "bootstrap"))
        from bootstrap_templates import build_commands_section

        assert "tausik symbol" in build_commands_section()


class TestTheRenamedHookReachesBothHostsAndTheOldNameStillWorks:
    @pytest.mark.parametrize("ide", ["claude", "qwen"])
    def test_bootstrap_deploys_the_new_name(self, tmp_path, ide):
        sys.path.insert(0, str(_REPO / "bootstrap"))
        target = tmp_path / ide
        target.mkdir()
        if ide == "claude":
            from bootstrap_generate import generate_settings_claude

            generate_settings_claude(str(target), str(tmp_path), lib_dir=str(_REPO))
        else:
            from bootstrap_qwen import generate_settings_qwen

            generate_settings_qwen(
                str(target), str(tmp_path), venv_python=sys.executable, lib_dir=str(_REPO)
            )
        data = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        commands = [
            hook.get("command", "")
            for entries in data["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks") or []
        ]
        assert any("tool_choice_nudge" in c for c in commands), f"{ide} lost the nudge"
        assert not any("mcp_first_nudge" in c for c in commands), (
            f"{ide} still points at the old name"
        )

    def test_the_old_path_still_runs(self, tmp_path):
        """A host reads settings at session start, so a running session keeps the
        old path after an upgrade. Found by the rename breaking this very
        session — the shim is why nobody else's does."""
        payload = {
            "tool_name": "Bash",
            "session_id": "shim",
            "tool_input": {"command": 'grep -n "def shimmed" a.py'},
        }
        result = subprocess.run(
            [sys.executable, str(_REPO / "scripts" / "hooks" / "mcp_first_nudge.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"},
        )
        assert result.returncode == 0
        assert "tausik symbol shimmed" in result.stderr
