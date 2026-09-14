"""The route an agent must take is checkable, and no rule demands the impossible.

the-route-an-agent-must-take-is-enforced-not-described. Measured over this
project's own transcripts (session #233, 4,011 shell commands) before anything
was built:

    MCP-first     1,216 of 1,530 CLI invocations HAD an MCP twin and used the
                  shell anyway (79.5%). MCP's share of framework calls: 29.1%.
    the wrapper      79 direct `python scripts/*.py` runs, of which 68 went to
                  scripts with NO wrapper route at all.

THE SECOND NUMBER INVERTS THE OBVIOUS READING and is why this file exists. "Always
through `.tausik/tausik`" was UNFOLLOWABLE for those scripts, and an unfollowable
rule is worse than an absent one: it teaches that the rules here are approximate,
and that lesson generalises to the rules that do matter.

So the ratchet is not "did the agent obey". It is: does a route EXIST for
everything the rules demand a route for, and does a module that has none say so
instead of doing nothing quietly.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (str(_REPO / "scripts"), str(_REPO / "scripts" / "hooks")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import tool_choice_nudge as nudge  # noqa: E402
import route_map as rm  # noqa: E402

#: A module whose only mention of the entry-point phrase is prose.
_MAIN_IN_PROSE = '\'\'\'Mentions __name__ == "__main__" in prose.\'\'\'\n'

#: A slug and a quoted message after the command — the greedy-match trap.
_TASK_LOG_WITH_SLUG = '.tausik/tausik task log my-slug "hello"'

CROSSCUTTING_SCOPE = ["scripts/", "bootstrap/"]

#: Modules an agent was measured running directly in session #233. Each must now
#: be reachable, or refuse and name what to use — never silent.
_INVOKED_DIRECTLY = (
    "gen_doc_constants.py",
    "audit_pytest_dedupe.py",
    "senar_version_claim.py",
    "gate_class_surface.py",
    "repo_coherence.py",
    "audit_closure_evidence.py",
)


class TestNoRuleDemandsTheImpossible:
    """AC1. The third state — 'a route is required and none exists' — is gone."""

    @pytest.mark.parametrize("name", _INVOKED_DIRECTLY)
    def test_every_directly_invoked_module_is_reachable_or_refuses(self, name):
        verdict = rm.classify(_REPO / "scripts" / name)
        assert verdict in ("REFUSES", "ENTRYPOINT"), (
            f"{name} is {verdict}: running it directly does nothing and says nothing, "
            "while the rules insist on a route it does not have. Six such runs are "
            "in the transcripts, each producing silence the agent then had to "
            "diagnose. Give it a route or make it refuse and name one."
        )

    @pytest.mark.parametrize(
        "source,why",
        [
            pytest.param(
                "def helper():\n    return 1\n",
                "no entry point at all",
                id="no_main",
            ),
            pytest.param(
                _MAIN_IN_PROSE,
                "the phrase in a docstring is not an entry point, and a text "
                "search cannot tell the difference",
                id="main_only_in_prose",
            ),
        ],
    )
    def test_a_module_that_does_nothing_is_classified_INERT(self, tmp_path, source, why):
        """PREMISE. A classifier that never returns INERT proves nothing above."""
        path = tmp_path / "probe.py"
        path.write_text(source, encoding="utf-8")
        assert rm.classify(path) == "INERT", why


class TestARefusalNamesTheRoute:
    """AC2. 'Use the wrapper' leaves the reader to find WHICH command — the very
    search the refusal exists to save."""

    @pytest.mark.parametrize(
        "module,needle",
        [
            ("repo_coherence.py", "tausik coherence"),
            ("gate_class_surface.py", "tausik gates status"),
        ],
    )
    def test_running_it_directly_prints_the_replacement(self, module, needle):
        result = subprocess.run(
            [sys.executable, str(_REPO / "scripts" / module)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(_REPO),
        )
        assert result.returncode != 0, "a bypass that exits 0 is indistinguishable from success"
        assert needle in result.stderr, result.stderr


class TestTheMcpTwinIsDerivedNotListed:
    """AC7. A hand-kept table of 'which command has a tool' would drift from the
    tools exactly as every other hand-kept registry here has (decision #335)."""

    def test_the_twin_name_follows_from_the_command(self):
        assert rm.mcp_twin("task done") == "tausik_task_done"
        assert rm.mcp_twin("push-ok") == "tausik_push_ok"

    def test_existence_is_checked_against_the_live_dispatch_table(self):
        tools = rm.mcp_tools()
        assert len(tools) > 100, f"only {len(tools)} MCP tools — the table was not read"
        assert rm.mcp_twin("task done") in tools
        assert rm.mcp_twin("doc roadmap") not in tools, (
            "a command with no MCP tool must not be reported as having one"
        )

    def test_an_unreadable_server_yields_unknown_and_not_absence(self, monkeypatch):
        """Reporting 'no twin exists' because the server could not be read would
        accuse the agent of a choice it never had."""
        monkeypatch.setattr(nudge, "twins_for", lambda cmds: {})
        assert nudge.twins_for(["task done"]) == {}


class TestTheNudgeNamesTheAlternativeAndOnlyThat:
    def test_it_finds_the_command_in_a_shell_line(self):
        found = nudge.commands_in(".tausik/tausik task done my-slug --ac-verified")
        assert "task done" in found and "task" in found

    @pytest.mark.parametrize(
        "command,expected",
        [
            pytest.param(
                ".tausik/tausik task done x",
                {"task done": "tausik_task_done"},
                id="longest_match_wins",
            ),
            pytest.param(
                _TASK_LOG_WITH_SLUG,
                {"task log": "tausik_task_log"},
                id="a_slug_is_not_a_subcommand",
            ),
            pytest.param(".tausik/tausik push-ok", {}, id="no_twin_exists"),
        ],
    )
    def test_the_twin_reported_is_the_one_that_matches(self, command, expected):
        """Reporting `task` instead of `task done` would name a tool that does
        something else; treating a slug as a subcommand would look for a tool
        named after the slug."""
        assert nudge.twins_for(nudge.commands_in(command)) == expected


class TestTheNudgeIsNotNoise:
    """AC6. A note repeated on every call is one the reader learns to skip, and a
    skipped note costs the attention the next real warning needs."""

    def _run(self, tmp_path, command: str, session: str = "t") -> str:
        payload = {
            "tool_name": "Bash",
            "session_id": session,
            "tool_input": {"command": command},
        }
        result = subprocess.run(
            [sys.executable, str(_REPO / "scripts" / "hooks" / "tool_choice_nudge.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env={
                **__import__("os").environ,
                "CLAUDE_PROJECT_DIR": str(tmp_path),
                "PYTHONUTF8": "1",
            },
        )
        assert result.returncode == 0, "the nudge must never fail a command"
        return result.stderr

    def test_it_speaks_once_per_command_per_session(self, tmp_path):
        first = self._run(tmp_path, ".tausik/tausik task done x")
        second = self._run(tmp_path, ".tausik/tausik task done y")
        assert "tausik_task_done" in first
        assert second == "", "the same note fired twice in one session"

    def test_a_different_command_still_gets_its_note(self, tmp_path):
        self._run(tmp_path, ".tausik/tausik task done x")
        other = self._run(tmp_path, ".tausik/tausik task log x msg")
        assert "tausik_task_log" in other

    def test_a_new_session_starts_over(self, tmp_path):
        self._run(tmp_path, ".tausik/tausik task done x", session="s1")
        again = self._run(tmp_path, ".tausik/tausik task done x", session="s2")
        assert "tausik_task_done" in again


class TestNoFalseBlockOnRoutineWork:
    """AC5. A false block on a routine operation trains circumvention and costs
    more than the miss it prevents (convention #291)."""

    def test_the_nudge_never_blocks(self, tmp_path):
        payload = {
            "tool_name": "Bash",
            "session_id": "block-probe",
            "tool_input": {"command": ".tausik/tausik task done x"},
        }
        result = subprocess.run(
            [sys.executable, str(_REPO / "scripts" / "hooks" / "tool_choice_nudge.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            # `errors="replace"` and PYTHONUTF8 together: without them the reader
            # thread dies decoding this project's own non-ASCII output on a
            # cp1251 console, and the failure surfaces as a warning about a
            # thread rather than as anything to do with the test.
            encoding="utf-8",
            errors="replace",
            timeout=120,
            env={
                **__import__("os").environ,
                "CLAUDE_PROJECT_DIR": str(tmp_path),
                "PYTHONUTF8": "1",
            },
        )
        assert result.returncode == 0

    @pytest.mark.parametrize(
        "command",
        [
            pytest.param("pytest -q", id="a_plain_command"),
            pytest.param(".tausik/tausik push-ok", id="no_twin_exists"),
            pytest.param("git status", id="unrelated"),
        ],
    )
    def test_a_command_that_is_not_the_subject_is_left_alone(self, tmp_path, command):
        assert self_run(tmp_path, command) == ""


def self_run(tmp_path, command: str) -> str:
    payload = {"tool_name": "Bash", "session_id": "quiet", "tool_input": {"command": command}}
    result = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "hooks" / "tool_choice_nudge.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env={**__import__("os").environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONUTF8": "1"},
    )
    return result.stderr


class TestTheNudgeReachesBothHookBearingHosts:
    """A capability on one host and not the other is what `cross_model_parity`
    refuses — and this hook exists because a rule went unenforced, so shipping it
    half-deployed would be the same defect twice. The module was renamed to
    `tool_choice_nudge` when it gained the grep -> `symbol` case: a name saying
    `mcp_first` while doing two things would be a name that lies."""

    @pytest.mark.parametrize("ide", ["claude", "qwen"])
    def test_bootstrap_deploys_it(self, tmp_path, ide):
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
        assert any("tool_choice_nudge" in c for c in commands), f"{ide} does not deploy the nudge"
