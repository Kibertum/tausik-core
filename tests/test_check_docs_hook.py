"""Tests for `scripts/hooks/check_docs.py` (v14-ci-doc-check).

Covers:
  AC-1 — exit 0 when constants are in sync (real repo + drift artificial test).
  AC-2 — developer README documents how to run locally.
  AC-3 (negative) — no pyproject.toml above cwd → SKIP, exit 0; never crashes
    a hook in an external checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    PYTHON = REPO / ".tausik" / "venv" / "bin" / "python"
HOOK = REPO / "scripts" / "hooks" / "check_docs.py"


def _run(cwd: Path, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if env_extra:
        env.update(env_extra)
    # Match the child's PYTHONIOENCODING so non-ASCII drift output (em-dashes,
    # arrows) doesn't crash decode on Windows where the parent's locale would
    # otherwise default to cp1252.
    return subprocess.run(
        [str(PYTHON), str(HOOK)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


class TestRealRepoSync:
    def test_exit_0_when_in_sync(self):
        # AC-1: live repo's constants.json should match — pre-checked by /start
        r = _run(REPO)
        assert r.returncode == 0, r.stderr


class TestDriftDetected:
    def test_drifted_json_returns_1(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Build a tiny TAUSIK-shaped tree with a stale constants.json."""
        # Layout
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "9.9.9"\n')
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        # Copy the real generator + helper so the hook can call them.
        # Both encoding= calls are required: the sources contain non-ASCII
        # (em-dashes, arrows) and Path.write_text without encoding defaults
        # to the locale codec on Windows (cp1252) and crashes.
        for name in ("gen_doc_constants.py", "mcp_tool_counts.py"):
            (scripts / name).write_text(
                (REPO / "scripts" / name).read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        # Stale constants.json (different version)
        gen_dir = tmp_path / "docs" / "_generated"
        gen_dir.mkdir(parents=True)
        (gen_dir / "constants.json").write_text(
            json.dumps({"tausik_version": "0.0.0", "schema_version": 1}, indent=2)
        )

        r = _run(tmp_path)
        assert r.returncode == 1
        assert "drift" in (r.stderr + r.stdout).lower()


class TestNegativeNoPyproject:
    def test_skip_when_no_pyproject_above(self, tmp_path: Path):
        # AC-3 negative: external checkout without pyproject.toml → exit 0 + skip msg
        r = _run(tmp_path)
        assert r.returncode == 0
        assert "skipping" in r.stderr.lower()


class TestDeveloperDocs:
    def test_dev_doc_checks_md_exists_en(self):
        # AC-2: developer-facing README in EN
        path = REPO / "docs" / "en" / "dev-doc-checks.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "gen_doc_constants.py --check" in text
        assert "scripts/hooks/check_docs.py" in text

    def test_dev_doc_checks_md_exists_ru(self):
        path = REPO / "docs" / "ru" / "dev-doc-checks.md"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "gen_doc_constants.py --check" in text


class TestCiWorkflow:
    def test_workflow_step_present(self):
        wf = REPO / ".github" / "workflows" / "tests.yml"
        assert wf.is_file()
        text = wf.read_text(encoding="utf-8")
        assert "Doc-constants drift check" in text
        assert "scripts/gen_doc_constants.py --check" in text
