"""r14-claudemd-drift: tausik doctor + update-claudemd --dry-run.

The audit found that bootstrap_generate.py never overwrites an existing
CLAUDE.md, so the static body section can drift behind the template
definition silently. v1.4 closes the gap with two affordances:

1. `tausik doctor` runs `_check_claudemd_drift` which compares H2 blocks
   between the live CLAUDE.md and what `build_full_body` would emit. Any
   difference is reported as a non-fatal warning (no surprises on existing
   projects, but the user is told to look at it).
2. `tausik update-claudemd --dry-run` shows a unified diff and exits
   non-zero when drift exists, so CI / pre-commit can gate on it.

These tests pin both behaviours.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


@pytest.fixture
def temp_project(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".tausik").mkdir()
    monkeypatch.chdir(proj)
    return proj


def test_drift_zero_on_freshly_generated_claudemd(temp_project):
    sys.path.insert(0, str(REPO / "bootstrap"))
    from bootstrap_templates import build_full_body

    body = build_full_body(
        "temp-project", ["python"], "an AI agent (Claude Code)", ".claude", ide="claude"
    )
    (temp_project / "CLAUDE.md").write_text(f"# CLAUDE.md\n\n{body}", encoding="utf-8")

    from project_cli_doctor import _check_claudemd_drift

    drift = _check_claudemd_drift(str(temp_project))
    assert drift == 0, f"expected zero drift on freshly generated CLAUDE.md, got {drift}"


def test_drift_detected_when_section_edited(temp_project):
    sys.path.insert(0, str(REPO / "bootstrap"))
    from bootstrap_templates import build_full_body

    body = build_full_body(
        "temp-project", ["python"], "an AI agent (Claude Code)", ".claude", ide="claude"
    )
    (temp_project / "CLAUDE.md").write_text(f"# CLAUDE.md\n\n{body}", encoding="utf-8")

    md = (temp_project / "CLAUDE.md").read_text(encoding="utf-8")
    md = md.replace("## Workflow", "## Workflow\n\nINTENTIONALLY EDITED LOCALLY", 1)
    (temp_project / "CLAUDE.md").write_text(md, encoding="utf-8")

    from project_cli_doctor import _check_claudemd_drift

    drift = _check_claudemd_drift(str(temp_project))
    assert drift is not None and drift >= 1


def test_drift_returns_none_when_claudemd_missing(temp_project):
    from project_cli_doctor import _check_claudemd_drift

    assert _check_claudemd_drift(str(temp_project)) is None


def test_dry_run_flag_exists_in_parser():
    """update-claudemd parser exposes --dry-run after r14-claudemd-drift."""
    from project_parser import build_parser

    parser = build_parser()
    args = parser.parse_args(["update-claudemd", "--dry-run", "--claudemd", "X"])
    assert args.dry_run is True
    assert args.claudemd == "X"


def test_dry_run_exits_nonzero_when_drift(temp_project, monkeypatch):
    """`tausik update-claudemd --dry-run` should exit 1 when drift is detected."""
    sys.path.insert(0, str(REPO / "bootstrap"))
    sys.path.insert(0, str(REPO / "scripts"))
    from bootstrap_templates import build_full_body

    body = build_full_body("temp", ["python"], "an AI agent (Claude Code)", ".claude", ide="claude")
    (temp_project / "CLAUDE.md").write_text(
        f"# CLAUDE.md\n\n{body}\n<!-- DYNAMIC:START -->\n## Current State\nold\n<!-- DYNAMIC:END -->\n",
        encoding="utf-8",
    )

    venv_py = (
        REPO / ".tausik" / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not venv_py.exists():
        pytest.skip("venv python not available; skipping subprocess dry-run check")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    # Run via the same module path the CLI uses.
    code = textwrap.dedent(
        """
        import sys, os
        sys.path.insert(0, r'{scripts}')
        sys.path.insert(0, r'{bootstrap}')
        from project_cli_extra import cmd_update_claudemd
        from types import SimpleNamespace

        class _Svc:
            def task_list(self): return []
            def session_current(self): return None

        try:
            cmd_update_claudemd(_Svc(), SimpleNamespace(claudemd='CLAUDE.md', dry_run=True))
            print('NO_EXIT')
        except SystemExit as e:
            print(f'EXIT={{e.code}}')
        """
    ).format(scripts=str(REPO / "scripts"), bootstrap=str(REPO / "bootstrap"))
    res = subprocess.run(
        [str(venv_py), "-c", code], capture_output=True, text=True, cwd=str(temp_project), env=env
    )
    assert "EXIT=1" in res.stdout, (res.stdout, res.stderr)


# --- Memory tail injection (A4 — update-claudemd-memory-tail) ----------


class _BeStub:
    """Minimal backend stub for _build_memory_tail tests."""

    def __init__(self, *, decisions=None, conventions=None, deadends=None, raise_on=False):
        self._decisions = decisions or []
        self._conventions = conventions or []
        self._deadends = deadends or []
        self._raise = raise_on

    def decision_list(self, limit):
        if self._raise:
            raise RuntimeError("db down")
        return self._decisions[:limit]

    def memory_list(self, mtype, limit):
        if self._raise:
            raise RuntimeError("db down")
        if mtype == "convention":
            return self._conventions[:limit]
        if mtype == "dead_end":
            return self._deadends[:limit]
        return []


class _SvcStub:
    def __init__(self, be):
        self.be = be


def test_memory_tail_empty_db_returns_empty_list():
    from service_knowledge_aggregates import build_compact_memory_tail as _build_memory_tail

    assert _build_memory_tail(_BeStub()) == []


def test_memory_tail_renders_decisions_conventions_deadends():
    from service_knowledge_aggregates import build_compact_memory_tail as _build_memory_tail

    be = _BeStub(
        decisions=[{"id": 1, "decision": "Use SQLite for local"}],
        conventions=[{"id": 2, "title": "kebab-case slugs"}],
        deadends=[{"id": 3, "title": "Tried bcrypt — incompatible"}],
    )
    out = _build_memory_tail(be)
    text = "\n".join(out)
    assert "### Memory tail" in text
    assert "Use SQLite" in text
    assert "kebab-case slugs" in text
    assert "Tried bcrypt" in text
    assert "Decisions (1)" in text
    assert "Conventions (1)" in text
    assert "Dead ends (1)" in text


def test_memory_tail_db_failure_returns_empty_no_crash():
    from service_knowledge_aggregates import build_compact_memory_tail as _build_memory_tail

    # Must not raise — update_claudemd should still produce a valid CLAUDE.md
    # even if the memory subsystem is broken.
    assert _build_memory_tail(_BeStub(raise_on=True)) == []


def test_memory_tail_truncates_long_text():
    from service_knowledge_aggregates import build_compact_memory_tail as _build_memory_tail

    be = _BeStub(decisions=[{"id": 1, "decision": "x" * 500}])
    out = _build_memory_tail(be)
    long_line = next(line for line in out if "x" in line)
    assert len(long_line) < 200, "decision lines must be truncated to ~120 chars"


def test_memory_tail_only_decisions_no_conventions_or_deadends():
    from service_knowledge_aggregates import build_compact_memory_tail as _build_memory_tail

    be = _BeStub(decisions=[{"id": 1, "decision": "Solo decision"}])
    out = _build_memory_tail(be)
    text = "\n".join(out)
    assert "### Memory tail" in text
    assert "Solo decision" in text
    assert "Conventions" not in text
    assert "Dead ends" not in text
