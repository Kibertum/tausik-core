"""The MCP/CLI surface parity ratchet â€” declared pairs, no silent losses.

ratchet-for-mcp-cli-surface-parity (github#122): three eye-caught divergences
of one class (verify gate names, update_claudemd memory tail, task_show hidden
fields) instead of a fourth point fix. scripts/mcp_cli_parity.py declares every
MCP tool's CLI twin; this test drives both surfaces of the read spine on one
planted project and fails on any FIELD LABEL the CLI shows and the MCP tool
does not -- unless that loss is declared in the ledger with a reason, in which
case the ledger entry must still be a live loss. The ledger only shrinks.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project")
)

import handlers
import mcp_cli_parity as parity
import tools
from project_backend import SQLiteBackend
from project_parser import build_parser
from project_service import ProjectService

PROJECT_PY = os.path.join(os.path.dirname(__file__), "..", "scripts", "project.py")


# --- The registry is the contract ------------------------------------------------


def test_registry_covers_the_live_surface_exactly():
    """AC2: a tool missing from the pair map is a silent absence; a dead entry is a lie."""
    live = {t["name"] for t in tools.TOOLS}
    declared = set(parity.PARITY)
    assert live - declared == set(), f"silent absences: {sorted(live - declared)}"
    assert declared - live == set(), f"dead entries: {sorted(declared - live)}"


def test_every_no_twin_exception_carries_a_reason_and_the_written_count():
    """AC6: exceptions are recorded as a number with reasons, not left implicit."""
    no_twin = {t for t, cli in parity.PARITY.items() if cli is None}
    assert set(parity.NO_TWIN_REASONS) == no_twin, "every None pair needs a reason, none else"
    for tool, reason in parity.NO_TWIN_REASONS.items():
        assert reason.strip(), f"{tool}: empty reason"
    assert len(no_twin) == parity.NO_TWIN_COUNT, "count literal drifted; update it consciously"


def test_the_read_surface_is_driven_or_excused_by_number():
    """AC6 for the loss ratchet: read tools are driven or excused, exactly and counted."""
    driven = {m for m, _, _ in parity.COMPARABLE}
    assert driven <= parity.READ_TOOLS
    assert parity.READ_TOOLS - driven == set(parity.NOT_DRIVEN_REASONS)
    for tool, reason in parity.NOT_DRIVEN_REASONS.items():
        assert reason.strip(), f"{tool}: empty reason"
    assert len(parity.NOT_DRIVEN_REASONS) == parity.NOT_DRIVEN_COUNT
    # no tool is both driven and excused
    assert not driven & set(parity.NOT_DRIVEN_REASONS)


def test_declared_cli_twins_resolve_in_the_live_parser():
    """A declared pair whose CLI command does not exist is worse than no list."""
    parser = build_parser()
    bad: list[tuple[str, tuple[str, ...]]] = []
    for tool, cli in parity.PARITY.items():
        if cli is None:
            continue
        argv = [a for a in cli if not a.startswith("<")] + ["--help"]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                parser.parse_args(argv)
            except SystemExit as exc:
                if exc.code not in (0, None):
                    bad.append((tool, cli))
    assert not bad, f"declared twins the live CLI parser rejects: {bad}"


def test_known_loss_ledger_entries_carry_reasons():
    for (tool, label), reason in parity.KNOWN_LOSSES.items():
        assert tool in parity.PARITY, f"ledger names unknown tool {tool}"
        assert label and reason.strip(), f"({tool}, {label}): empty label or reason"


# --- The loss driver ---------------------------------------------------------------


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    """One planted project; the CLI seeds it, both surfaces read the same DB."""
    tmp_path = tmp_path_factory.mktemp("parity")
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    (tausik_dir / "config.json").write_text(json.dumps({"project": "parity-ratchet"}))
    managed = tmp_path / "managed-config.json"
    managed.write_text(
        json.dumps({"gates": {"pytest": {"enabled": False}, "ruff": {"enabled": False}}})
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["TAUSIK_DIR"] = str(tausik_dir)
    env["TAUSIK_MANAGED_CONFIG"] = str(managed)

    def run_cli(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, PROJECT_PY, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(tmp_path),
            timeout=60,
        )

    seed = [
        ("epic", "add", "e1", "Epic One"),
        ("story", "add", "e1", "s1", "Story One"),
        ("task", "add", "Parity task", "--group", "s1", "--slug", "parity-task"),
        (
            "task",
            "update",
            "parity-task",
            "--goal",
            "measure parity",
            "--acceptance-criteria",
            "1. labels reach mcp",
            "--scope-paths",
            "scripts/x.py",
            "--rollback-plan",
            "git revert",
        ),
        ("task", "log", "parity-task", "journal line for the logs view"),
        ("memory", "add", "pattern", "Needle title", "needle content body"),
        ("decide", "Use SQLite", "--rationale", "Simple and single-file"),
        ("session", "start"),
        ("session", "end", "--summary", "parity seed done"),
    ]
    for args in seed:
        r = run_cli(*args)
        assert r.returncode == 0, f"seed failed: {args}\nstdout={r.stdout}\nstderr={r.stderr}"

    db_path = tausik_dir / "tausik.db"
    assert db_path.exists(), f"planted DB missing at {db_path}"
    return run_cli, str(db_path)


@pytest.mark.parametrize("mcp_tool,cli_argv,mcp_args", parity.COMPARABLE)
def test_cli_labels_reach_the_mcp_surface(planted, mcp_tool, cli_argv, mcp_args):
    """AC3: a label the CLI prints and the MCP tool does not is a loss; richer MCP is fine."""
    run_cli, db_path = planted
    r = run_cli(*cli_argv)
    assert r.returncode == 0, f"CLI side failed: {cli_argv}\nstderr={r.stderr}"

    svc = ProjectService(SQLiteBackend(db_path))
    try:
        mcp_out = handlers.handle_tool(svc, mcp_tool, dict(mcp_args))
    finally:
        svc.be.close()
    assert not mcp_out.lower().startswith("error"), (
        f"pair mis-declared, MCP refused: {mcp_tool} {mcp_args} -> {mcp_out[:200]}"
    )

    cli_labels = parity.labels_from_text(r.stdout)
    mcp_labels = parity.labels_from_text(mcp_out)
    losses = cli_labels - mcp_labels
    known = {lab for (t, lab) in parity.KNOWN_LOSSES if t == mcp_tool}

    undeclared = losses - known
    assert not undeclared, (
        f"{mcp_tool}: NEW losses vs CLI twin {cli_argv}: {sorted(undeclared)}\n"
        f"mcp output was:\n{mcp_out[:600]}"
    )
    healed = known - losses
    assert not healed, f"{mcp_tool}: ledger entries that healed, delete them: {sorted(healed)}"


def test_label_extraction_normalises_headers_and_noise():
    text = (
        "Relevant memory (8):\nscope_paths: ['scripts/x.py']\nStarted at: 2026-10-07\nplain line\n"
    )
    assert parity.labels_from_text(text) == {"scope_paths", "started_at"}
