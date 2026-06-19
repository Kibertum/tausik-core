"""fix-risk-compute-stdin-hang: MCP task_done stdin-hang regression.

risk_compute runs `git ... --numstat` on every task_done to score closure
risk. Without stdin=DEVNULL the git child inherits the MCP server's stdin
(a JSON-RPC pipe); on Windows git probes it (paginator / credential) and
blocks, hanging task_done — a reintroduction of the v14b defect that
verify_git_diff.py already guards. These tests pin the guard and add a
class-level scan so it cannot silently return a third time.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import risk_compute  # noqa: E402

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"


class TestRiskComputeGitStdin:
    def test_git_call_passes_stdin_devnull(self, monkeypatch):
        captured: dict = {}

        def fake_check_output(cmd, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return b"1\t2\tscripts/x.py\n"

        monkeypatch.setattr(subprocess, "check_output", fake_check_output)
        risk_compute._git_numstat_lines(["diff", "--numstat", "HEAD"], set(), ".")
        assert captured["kwargs"].get("stdin") is subprocess.DEVNULL

    def test_git_failure_returns_none(self, monkeypatch):
        # Negative/boundary (AC4): git missing or timing out → None, no raise.
        def boom(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 10)

        monkeypatch.setattr(subprocess, "check_output", boom)
        assert risk_compute._factor_code_churn(["scripts/x.py"], None, ".") is None


_SUBPROCESS_FUNCS = {"run", "check_output", "check_call", "call", "Popen"}


def _unguarded_subprocess_calls(path: pathlib.Path) -> list[int]:
    """Lines of subprocess.<run/check_output/Popen/...> calls lacking a stdin kwarg."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in _SUBPROCESS_FUNCS
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            if "stdin" not in {kw.arg for kw in node.keywords}:
                bad.append(node.lineno)
    return bad


class TestNoUnguardedSubprocessInMcpPath:
    """Class-guard: every subprocess call in scripts/ top-level (all MCP-reachable
    via the project server) must set stdin — else it can inherit the JSON-RPC
    pipe and hang. scripts/hooks/ run as standalone harness processes and are
    excluded. This is the anti-regression net for this defect class."""

    def test_all_top_level_subprocess_calls_set_stdin(self):
        offenders: list[str] = []
        for py in sorted(_SCRIPTS.glob("*.py")):  # top-level only — excludes hooks/
            for lineno in _unguarded_subprocess_calls(py):
                offenders.append(f"{py.name}:{lineno}")
        assert not offenders, (
            "subprocess calls without stdin=DEVNULL in MCP-reachable modules "
            f"(stdin-hang risk): {offenders}"
        )
