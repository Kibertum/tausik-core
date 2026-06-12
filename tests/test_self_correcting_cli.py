"""v15p-self-correcting-cli (T1): arg errors must teach the right syntax.

CLI: SelfCorrectingParser.error() prints subcommand usage + known-good
examples. MCP: server error replies append a usage line generated from the
tool's inputSchema. Either way the agent recovers in one retry.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
MCP_PROJECT = ROOT / "harness" / "claude" / "mcp" / "project"
for p in (str(SCRIPTS),):
    if p not in sys.path:
        sys.path.insert(0, p)

from project_parser import build_parser  # noqa: E402
from project_parser_errors import EXAMPLES, find_examples  # noqa: E402


def _parse_error_output(argv: list[str], monkeypatch, capsys) -> str:
    """Run parser on bad argv, return combined out/err of the SystemExit."""
    monkeypatch.setattr(sys, "argv", ["project.py"] + argv)
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(argv)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    return captured.out + captured.err


class TestCliErrors:
    def test_epic_add_extra_positional_shows_example(self, monkeypatch, capsys):
        """The classic guess: epic add slug title DESCRIPTION (3rd positional)."""
        out = _parse_error_output(
            ["epic", "add", "my-epic", "Title", "Surplus description"],
            monkeypatch,
            capsys,
        )
        assert "error:" in out
        assert 'tausik epic add <slug> "Title"' in out

    def test_memory_add_missing_content_shows_example(self, monkeypatch, capsys):
        out = _parse_error_output(["memory", "add", "gotcha", "Only title"], monkeypatch, capsys)
        assert "usage:" in out
        assert "tausik memory add gotcha" in out

    def test_task_done_unknown_flag_shows_example(self, monkeypatch, capsys):
        out = _parse_error_output(["task", "done", "slug", "--акверифайд"], monkeypatch, capsys)
        assert "tausik task done <slug> --ac-verified" in out

    def test_unknown_command_still_exits_2_with_hint(self, monkeypatch, capsys):
        out = _parse_error_output(["задача", "старт"], monkeypatch, capsys)
        assert "hint:" in out

    def test_help_not_affected(self, capsys):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0


class TestFindExamples:
    def test_longest_prefix_wins(self):
        ex = find_examples(["task", "add", "a", "b"])
        assert ex == EXAMPLES["tausik task add"]

    def test_flags_ignored_in_matching(self):
        ex = find_examples(["task", "--weird", "done", "slug"])
        assert ex == EXAMPLES["tausik task done"]

    def test_no_match_returns_empty(self):
        assert find_examples(["completely", "unknown"]) == []


def test_cli_e2e_subprocess_error_contains_example(tmp_path):
    """Full binary path: scripts/project.py with wrong args."""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "project.py"), "epic", "add", "a", "b", "c"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(ROOT),
    )
    assert r.returncode == 2
    combined = r.stdout + r.stderr
    assert 'tausik epic add <slug> "Title"' in combined


class TestMcpUsageHint:
    @pytest.fixture()
    def usage_hint(self):
        # unique module name — bare `import server` collides with the
        # codebase-rag server module in other test files
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "tausik_project_server", MCP_PROJECT / "server.py"
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._usage_hint

    TOOLS = [
        {
            "name": "tausik_task_done",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "ac_verified": {"type": "boolean"},
                    "relevant_files": {"type": "array"},
                },
                "required": ["slug"],
            },
        },
        {"name": "tausik_status", "inputSchema": {"type": "object", "properties": {}}},
    ]

    def test_hint_lists_args_and_required_marker(self, usage_hint):
        hint = usage_hint(self.TOOLS, "tausik_task_done")
        assert hint.startswith("usage: tausik_task_done(")
        assert "slug*:string" in hint
        assert "ac_verified:boolean" in hint

    def test_unknown_tool_empty(self, usage_hint):
        assert usage_hint(self.TOOLS, "nope") == ""

    def test_no_props_empty(self, usage_hint):
        assert usage_hint(self.TOOLS, "tausik_status") == ""
