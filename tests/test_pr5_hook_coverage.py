"""Guards see every tool their action is reachable with — GitHub PR #5 (Okianiwa), ported.

The PR measured, on Claude Code 2.1.215, that four hooks kept four private
copies of "which tools write" and that two live write paths — NotebookEdit
and the MCP file editors — reached no guard at all. Four of its six claims
were already closed in 1.8 (PowerShell on the shell matchers, NotebookEdit in
task_gate and scope_write_gate, shell_channel, mcp<2 pinned); the fail-secure
flip went into 1.9 with credit. This file holds the rest:

* one list of write tools and payload path fields (`hooks/write_tools`),
  restated by the bootstrap matchers and pinned against them here;
* NotebookEdit and the MCP editors in front of secret_scan,
  memory_pretool_block and memory_posttool_audit; MultiEdit in auto_format;
  the windows-mcp shell on every shell gate;
* the NEGATIVE that matters: a write through a tool the old matcher never
  saw is REFUSED without a task. "The hook ran" is not evidence — a hook that
  never saw the call also exits 0 — the refusal is. Which tests are red on the
  OLD code, stated plainly: the ledger (task_gate's body was already
  tool-agnostic — what it lacked was the REGISTRATION, and only the ledger
  sees that), secret_scan on a NotebookEdit cell (the old tuple returned 0
  without looking), memory_pretool_block on a NotebookEdit into the memory
  dir (same), and the FileSystem move tests (the first cut judged the
  destination alone);
* the interception ledger (tool, hook) taken from the old registration only
  GROWS: nothing that fired before stops firing;
* what is NOT ported and why: anchoring `^(?:...)$`. The PR measured that a
  matcher of [A-Za-z0-9_|] is compared exactly and anything else runs as an
  unanchored regex; Qwen Code and Codex read the same dict with unmeasured
  semantics, so anchoring could silently disable every hook on a host. The
  fact is pinned instead: built-in lines stay pure alternations, and every
  regex-branch alternative is a name no other tool contains.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (os.path.join(_ROOT, "scripts", "hooks"), os.path.join(_ROOT, "bootstrap")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bootstrap_hooks as bh  # noqa: E402
import shell_channel  # noqa: E402
import write_tools as wt  # noqa: E402

CROSSCUTTING_SCOPE = [
    "scripts/hooks/write_tools.py",
    "scripts/hooks/shell_channel.py",
    "bootstrap/bootstrap_hooks.py",
    "bootstrap/bootstrap_qwen.py",
]

_HOOKS = os.path.join(_ROOT, "scripts", "hooks")

#: The registration as it stood before the port (bootstrap_hooks at 340c8cf4),
#: as (tool, hook) pairs. The ledger after the port must be a superset.
_OLD_LEDGER = {
    ("Write", "task_gate.py"),
    ("Edit", "task_gate.py"),
    ("MultiEdit", "task_gate.py"),
    ("NotebookEdit", "task_gate.py"),
    ("Write", "scope_write_gate.py"),
    ("NotebookEdit", "scope_write_gate.py"),
    ("Write", "memory_pretool_block.py"),
    ("MultiEdit", "memory_pretool_block.py"),
    ("Bash", "memory_pretool_block.py"),
    ("PowerShell", "memory_pretool_block.py"),
    ("Write", "secret_scan.py"),
    ("Bash", "secret_scan.py"),
    ("Bash", "bash_firewall.py"),
    ("PowerShell", "bash_firewall.py"),
    ("Bash", "bash_write_gate.py"),
    ("PowerShell", "bash_write_gate.py"),
    ("Bash", "git_push_gate.py"),
    ("PowerShell", "git_push_gate.py"),
    ("Write", "auto_format.py"),
    ("Edit", "auto_format.py"),
    ("Write", "memory_posttool_audit.py"),
    ("MultiEdit", "memory_posttool_audit.py"),
    ("Read", "activity_event.py"),
    ("Bash", "task_call_counter.py"),
}

#: Every tool name a Claude Code 2.1.x session can hand a hook, plus the MCP
#: names this project registers — the universe an unanchored regex could
#: over-match inside. TodoWrite/BashOutput are the two that a substring
#: search on "Write"/"Bash" would catch.
_TOOL_UNIVERSE = {
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Bash",
    "PowerShell",
    "BashOutput",
    "KillShell",
    "Grep",
    "Glob",
    "Task",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "AskUserQuestion",
    "ExitPlanMode",
    "EnterPlanMode",
    "mcp__tausik-project__tausik_task_done",
    "mcp__tausik-project__tausik_task_start",
    *wt.MCP_WRITE_TOOLS,
    *wt.MCP_SHELL_TOOLS,
}

_EXACT_BRANCH = re.compile(r"^[A-Za-z0-9_|]+$")


def _ledger(hooks: dict) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for entries in hooks.values():
        for entry in entries:
            for hook in entry["hooks"]:
                script = os.path.basename(hook["command"].split()[-1])
                for tool in str(entry["matcher"]).split("|"):
                    if tool:
                        out.add((tool, script))
    return out


def _claude_hooks() -> dict:
    return bh.build_hooks_dict(lambda s, suffix="": f"python /hooks/{s}{suffix}")


class TestOneListOfWriteTools:
    def test_bootstrap_restates_the_hooks_package_lists_exactly(self):
        assert set(bh.BUILTIN_WRITE_MATCHER.split("|")) == set(wt.BUILTIN_WRITE_TOOLS)
        assert set(bh.MCP_WRITE_MATCHER.split("|")) == set(wt.MCP_WRITE_TOOLS)
        assert set(bh.MCP_SHELL_MATCHER.split("|")) == set(wt.MCP_SHELL_TOOLS)
        assert set(wt.MCP_SHELL_TOOLS) <= set(shell_channel.SHELL_TOOLS)

    def test_no_hook_keeps_a_private_copy_of_the_write_tool_list(self):
        """The four literal tuples the PR found — gone, each reads write_tools."""
        for name in (
            "scope_write_gate",
            "memory_pretool_block",
            "memory_posttool_audit",
            "secret_scan",
        ):
            src = open(os.path.join(_HOOKS, f"{name}.py"), encoding="utf-8").read()
            assert "from write_tools import" in src, name
            assert '("Write", "Edit", "MultiEdit")' not in src, f"{name} still spells its own list"

    def test_edited_paths_reads_every_field_and_a_move_names_its_destination(self):
        assert wt.edited_paths({"file_path": "a.py"}) == ["a.py"]
        assert wt.edited_paths({"notebook_path": "n.ipynb"}) == ["n.ipynb"]
        assert wt.edited_paths({"relative_path": "src/x.py"}) == ["src/x.py"]
        assert wt.edited_paths({"path": "a", "destination": "b"}) == ["a", "b"]
        assert wt.edited_path({"path": "a", "destination": "b"}) == "b"
        assert wt.edited_path({"command": "ls"}) is None
        assert wt.edited_paths("not a dict") == []


class TestTheRefusalIsTheEvidence:
    """NEGATIVE: a write through a tool the old matcher never saw is refused."""

    def _project(self, tmp_path, *, active: bool):
        (tmp_path / ".tausik").mkdir()
        conn = sqlite3.connect(str(tmp_path / ".tausik" / "tausik.db"))
        conn.execute("CREATE TABLE tasks (slug TEXT PRIMARY KEY, status TEXT)")
        conn.execute("INSERT INTO tasks VALUES (?, ?)", ("t", "active" if active else "planning"))
        conn.commit()
        conn.close()
        return tmp_path

    def _hook(self, script: str, payload: dict, cwd, env_extra: dict | None = None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(cwd)}
        for k in ("TAUSIK_SKIP_HOOKS", "TAUSIK_HOOK_FAIL_SECURE", "TAUSIK_SECRET_SCAN_STRICT"):
            env.pop(k, None)
        env.update(env_extra or {})
        return subprocess.run(
            [sys.executable, os.path.join(_HOOKS, script)],
            input=json.dumps(payload),
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=env,
            cwd=str(cwd),
            timeout=15,
        )

    @pytest.mark.parametrize(
        "tool,field",
        [("mcp__serena__replace_symbol_body", "relative_path"), ("NotebookEdit", "notebook_path")],
    )
    def test_task_gate_refuses_the_write_without_a_task_and_allows_it_with_one(
        self, tmp_path, tool, field
    ):
        proj = self._project(tmp_path, active=False)
        res = self._hook(
            "task_gate.py", {"tool_name": tool, "tool_input": {field: "src/x.py"}}, proj
        )
        assert res.returncode == 2 and "BLOCKED" in res.stderr, (res.returncode, res.stderr)
        # With a task the same call passes — the refusal above was the gate, not a crash.
        conn = sqlite3.connect(str(proj / ".tausik" / "tausik.db"))
        conn.execute("UPDATE tasks SET status='active'")
        conn.commit()
        conn.close()
        res2 = self._hook(
            "task_gate.py", {"tool_name": tool, "tool_input": {field: "src/x.py"}}, proj
        )
        assert res2.returncode == 0, res2.stderr

    def test_a_move_out_of_the_project_is_gated_by_its_source(self, tmp_path):
        """NEGATIVE (review, session #259): a FileSystem move with the source inside
        the project and the destination outside must not pass as 'foreign'."""
        proj = self._project(tmp_path, active=False)
        (tmp_path / "src").mkdir()
        outside = str(tmp_path.parent / "elsewhere" / "x.py")
        res = self._hook(
            "task_gate.py",
            {
                "tool_name": "mcp__windows-mcp__FileSystem",
                "tool_input": {"path": "src/x.py", "destination": outside},
            },
            proj,
        )
        assert res.returncode == 2 and "BLOCKED" in res.stderr, (res.returncode, res.stderr)

    def test_scope_acl_judges_the_source_of_a_move_too(self, tmp_path):
        """NEGATIVE (review, session #259): a task scoped to src/a/** must not be able
        to move .tausik/tausik.db INTO src/a/ — the destination alone was judged."""
        proj = self._project(tmp_path, active=True)
        conn = sqlite3.connect(str(proj / ".tausik" / "tausik.db"))
        conn.execute("ALTER TABLE tasks ADD COLUMN scope_paths TEXT")
        conn.execute("ALTER TABLE tasks ADD COLUMN delegated_to TEXT")
        conn.execute("UPDATE tasks SET scope_paths=?", (json.dumps(["src/a/**"]),))
        conn.commit()
        conn.close()
        res = self._hook(
            "scope_write_gate.py",
            {
                "tool_name": "mcp__windows-mcp__FileSystem",
                "tool_input": {"path": ".tausik/tausik.db", "destination": "src/a/db.sqlite"},
            },
            proj,
        )
        assert res.returncode == 2 and "outside the declared scope" in res.stderr, (
            res.returncode,
            res.stderr,
        )
        ok = self._hook(
            "scope_write_gate.py",
            {
                "tool_name": "mcp__windows-mcp__FileSystem",
                "tool_input": {"path": "src/a/old.py", "destination": "src/a/new.py"},
            },
            proj,
        )
        assert ok.returncode == 0, ok.stderr

    def test_a_relative_path_that_climbs_out_of_the_project_is_still_gated(self, tmp_path):
        """serena speaks relative paths; `..` must not make the write look foreign."""
        (tmp_path / "p").mkdir()
        proj = self._project(tmp_path / "p", active=False)
        res = self._hook(
            "task_gate.py",
            {
                "tool_name": "mcp__serena__insert_after_symbol",
                "tool_input": {"relative_path": "../p/x.py"},
            },
            proj,
        )
        assert res.returncode == 2, res.stderr

    def test_secret_scan_sees_a_notebook_cell_in_strict_mode(self, tmp_path):
        """Before the port secret_scan returned 0 on NotebookEdit without looking."""
        res = self._hook(
            "secret_scan.py",
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"notebook_path": "n.ipynb", "new_source": "AKIAIOSFODNN7EXAMPLE"},
            },
            tmp_path,
            {"TAUSIK_SECRET_SCAN_STRICT": "1"},
        )
        assert res.returncode == 2, (res.returncode, res.stderr)
        res_prose = self._hook(
            "secret_scan.py",
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"notebook_path": "n.ipynb", "new_source": "print(1)"},
            },
            tmp_path,
            {"TAUSIK_SECRET_SCAN_STRICT": "1"},
        )
        assert res_prose.returncode == 0

    def test_memory_pretool_block_refuses_a_notebook_into_the_claude_memory_dir(self, tmp_path):
        """The hook judges the REAL home's sink dirs (memory_sinks expands `~`); the
        project is the temp one — the shape tests/test_memory_pretool_block_hook uses."""
        self._project(tmp_path, active=True)
        home = os.path.expanduser("~").replace("\\", "/")
        target = f"{home}/.claude/projects/test-proj/memory/n.ipynb"
        res = self._hook(
            "memory_pretool_block.py",
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"notebook_path": target, "new_source": "TAUSIK gotcha"},
                "transcript_path": "",
            },
            tmp_path,
        )
        assert res.returncode == 2 and "BLOCKED" in res.stderr, (res.returncode, res.stderr)


class TestNothingStopsFiring:
    """NEGATIVE: the ledger of (tool, hook) interceptions only grows."""

    def test_the_old_ledger_is_a_subset_of_the_new_one(self):
        new = _ledger(_claude_hooks())
        lost = _OLD_LEDGER - new
        assert not lost, f"interceptions that fired before and no longer do: {sorted(lost)}"
        gained = new - _OLD_LEDGER
        assert {("NotebookEdit", "secret_scan.py"), ("MultiEdit", "auto_format.py")} <= gained
        assert {(t, "task_gate.py") for t in wt.MCP_WRITE_TOOLS} <= gained
        assert {(t, "bash_firewall.py") for t in wt.MCP_SHELL_TOOLS} <= gained

    def test_a_wildcard_entry_gets_no_second_line_so_nothing_fires_twice(self, tmp_path):
        """Qwen registers the counters on "*"; a narrower MCP line beside it would
        count every MCP write twice (review, session #259)."""
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        tool = wt.MCP_WRITE_TOOLS[0]
        firings: dict[str, int] = {}
        for entries in cfg["hooks"].values():
            for entry in entries:
                names = str(entry["matcher"]).split("|")
                if entry["matcher"] in ("", "*") or tool in names:
                    for hook in entry["hooks"]:
                        script = os.path.basename(hook["command"].split()[-1])
                        firings[script] = firings.get(script, 0) + 1
        doubled = {s: n for s, n in firings.items() if n > 1}
        assert not doubled, f"hooks that would fire twice on {tool}: {doubled}"

    def test_qwen_mirror_gains_the_same_mcp_lines(self, tmp_path):
        from bootstrap_qwen import generate_settings_qwen

        target = tmp_path / ".qwen"
        target.mkdir()
        generate_settings_qwen(str(target), str(tmp_path), venv_python=sys.executable)
        cfg = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        qwen = _ledger(cfg["hooks"])
        wide = {script for tool, script in qwen if tool == "*"}
        for script, matcher in bh.MCP_COVERAGE.items():
            if script in wide:
                continue  # Qwen registers it for every tool already
            for tool in matcher.split("|"):
                assert (tool, script) in qwen, (tool, script)


class TestTheMatcherSemanticsArePinnedNotAnchored:
    """Measured by PR #5 on Claude Code 2.1.215; carried here with its source."""

    def test_built_in_lines_stay_on_the_exact_match_branch(self):
        for entries in _claude_hooks().values():
            for entry in entries:
                m = str(entry["matcher"])
                if not m or m == "*" or m.startswith("mcp__"):
                    continue
                assert _EXACT_BRANCH.match(m), (
                    f"{m!r} carries a regex character: the whole line would switch to an "
                    "unanchored search, and 'Write' would then match TodoWrite"
                )

    def test_every_regex_branch_alternative_is_a_name_no_other_tool_contains(self):
        for entries in _claude_hooks().values():
            for entry in entries:
                m = str(entry["matcher"])
                if not m or _EXACT_BRANCH.match(m):
                    continue
                for alt in m.split("|"):
                    swallowed = {t for t in _TOOL_UNIVERSE if alt in t and t != alt}
                    assert not swallowed, f"{alt!r} would also match {sorted(swallowed)}"

    def test_the_universe_shows_why_a_regex_branch_built_in_line_would_over_match(self):
        """The guard above is not vacuous: 'Write' and 'Bash' DO have superstrings."""
        assert {t for t in _TOOL_UNIVERSE if "Write" in t and t != "Write"} == {"TodoWrite"}
        assert {t for t in _TOOL_UNIVERSE if "Bash" in t and t != "Bash"} == {"BashOutput"}

    def test_anchoring_is_declined_in_writing(self):
        src = open(os.path.join(_ROOT, "bootstrap", "bootstrap_hooks.py"), encoding="utf-8").read()
        assert "That is NOT ported" in src and "unmeasured" in src
        assert "^(?:" not in bh.BUILTIN_WRITE_MATCHER + bh.SHELL_MATCHER + bh.MCP_WRITE_MATCHER
