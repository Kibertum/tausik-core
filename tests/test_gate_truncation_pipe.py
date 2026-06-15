"""v15p-fix-hadolint-windows-head: unix truncation pipes in gate commands.

Stack gates ended with `2>&1 | head -30` / `| tail -30`; on Windows
shell=True is cmd.exe, which has no head/tail, so every such gate failed
with "'head' is not recognized". The runner now strips the trailing pipe
and truncates in Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gate_command_runner import (  # noqa: E402
    _apply_line_filter,
    _extract_truncation_filter,
    run_command_gate,
)


class TestExtractTruncationFilter:
    def test_head_with_redirect(self):
        cmd, f = _extract_truncation_filter("hadolint a.df 2>&1 | head -30")
        assert cmd == "hadolint a.df"
        assert f == ("head", 30)

    def test_tail_with_redirect(self):
        cmd, f = _extract_truncation_filter("vendor/bin/phpunit 2>&1 | tail -30")
        assert cmd == "vendor/bin/phpunit"
        assert f == ("tail", 30)

    def test_pipe_without_redirect(self):
        cmd, f = _extract_truncation_filter("tool x | head -5")
        assert cmd == "tool x"
        assert f == ("head", 5)

    def test_dash_n_form(self):
        cmd, f = _extract_truncation_filter("tool 2>&1 | head -n 20")
        assert cmd == "tool"
        assert f == ("head", 20)

    def test_compound_command_keeps_prefix(self):
        cmd, f = _extract_truncation_filter(
            "terraform fmt -check && terraform validate 2>&1 | head -30"
        )
        assert cmd == "terraform fmt -check && terraform validate"
        assert f == ("head", 30)

    def test_no_pipe_passthrough(self):
        cmd, f = _extract_truncation_filter("ruff check {files}")
        assert cmd == "ruff check {files}"
        assert f is None

    def test_mid_command_pipe_untouched(self):
        original = "foo | grep bar && baz"
        cmd, f = _extract_truncation_filter(original)
        assert cmd == original
        assert f is None


class TestApplyLineFilter:
    def test_head_keeps_first_n(self):
        out = _apply_line_filter("a\nb\nc\nd", ("head", 2))
        assert out.splitlines()[:2] == ["a", "b"]
        assert "truncated" in out

    def test_tail_keeps_last_n(self):
        out = _apply_line_filter("a\nb\nc\nd", ("tail", 2))
        assert out.splitlines()[-2:] == ["c", "d"]
        assert "truncated" in out

    def test_short_output_unchanged(self):
        assert _apply_line_filter("a\nb", ("head", 30)) == "a\nb"


class TestRunCommandGateCrossPlatform:
    def test_head_pipe_runs_without_shell_head(self):
        """The exact failing shape: pipe to head on a 40-line producer."""
        py = sys.executable.replace("\\", "/")
        gate = {
            "command": f'"{py}" -c "import sys; [print(i) for i in range(40)]" 2>&1 | head -10',
            "timeout": 30,
        }
        passed, output = run_command_gate(gate, [])
        assert passed, output
        assert "'head' is not recognized" not in output
        lines = output.splitlines()
        assert lines[0] == "0"
        assert "truncated" in lines[-1]
        assert len(lines) == 11  # 10 + marker

    def test_tail_pipe_keeps_last_lines(self):
        py = sys.executable.replace("\\", "/")
        gate = {
            "command": f'"{py}" -c "import sys; [print(i) for i in range(40)]" 2>&1 | tail -10',
            "timeout": 30,
        }
        passed, output = run_command_gate(gate, [])
        assert passed, output
        assert output.splitlines()[-1] == "39"


class TestFilePatterns:
    """Gate-level filename scoping (Dockerfile has no extension)."""

    GATE = {
        "command": "hadolint {files} 2>&1 | head -30",
        "file_patterns": ["Dockerfile", "Containerfile", "*.dockerfile"],
        "timeout": 30,
    }

    def test_skips_when_no_matching_files(self):
        passed, output = run_command_gate(self.GATE, ["scripts/foo.py"])
        assert passed
        assert "skipped" in output

    def test_skips_on_empty_files_instead_of_dot(self):
        """The `hadolint .` permission-denied shape: empty files must skip,
        not fall through to '.'."""
        passed, output = run_command_gate(self.GATE, [])
        assert passed
        assert "skipped" in output

    def test_matches_dockerfile_basename_case_insensitive(self):
        gate = dict(self.GATE)
        py = sys.executable.replace("\\", "/")
        gate["command"] = f'"{py}" -c "import sys; print(sys.argv[1:])" {{files}}'
        passed, output = run_command_gate(
            gate, ["sub/dir/Dockerfile", "x/app.dockerfile", "y/readme.md"]
        )
        assert passed
        assert "Dockerfile" in output
        assert "app.dockerfile" in output
        assert "readme.md" not in output


def test_no_stack_gate_uses_unhandled_unix_utility():
    """Every pipe in a stack gate command must be a supported truncation
    pipe (head/tail) — no grep/awk/sed/xargs/cut sneaking in."""
    stacks_dir = ROOT / "stacks"
    offenders = []
    for sj in stacks_dir.glob("*/stack.json"):
        data = json.loads(sj.read_text(encoding="utf-8"))
        for gate_name, gate in (data.get("gates") or {}).items():
            cmd = gate.get("command") or ""
            if "|" not in cmd:
                continue
            stripped, line_filter = _extract_truncation_filter(cmd)
            if line_filter is None or "|" in stripped:
                offenders.append(f"{sj.parent.name}/{gate_name}: {cmd}")
    assert not offenders, (
        "Gate commands with unix-only pipes the runner cannot neutralize:\n" + "\n".join(offenders)
    )
