"""bootstrap-drift-not-gated-stale-runtime — the gate that catches a source edit
that never reached the executable copy.

Tests the COMPARISON FUNCTION and the gate runner on a SYNTHETIC project under
tmp_path, deliberately NOT against the repo's real `.claude/`/`.cursor/` etc.:
those profiles are gitignored, so a test that read them would find nothing on a
fresh clone or in CI and degrade to an eternal skip — precisely the dead test
this whole task exists to prevent (memory #229). A synthetic project runs
identically everywhere.
"""

from __future__ import annotations

import os
import sys


SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from service_doctor_drift import scripts_drift_names  # noqa: E402


def _mkproject(tmp_path, *, source: dict[str, str], profiles: dict[str, dict[str, str]]):
    """Build a fake project: source scripts/ plus deployed .{ide}/scripts/ trees.

    ``source`` maps filename → content. ``profiles`` maps ide → {filename: content}.
    A profile whose filename is absent models "missing-in-profile"; a differing
    content models a stale copy.
    """
    src = tmp_path / "scripts"
    src.mkdir()
    for name, body in source.items():
        (src / name).write_text(body, encoding="utf-8")
    for ide, files in profiles.items():
        pdir = tmp_path / f".{ide}" / "scripts"
        pdir.mkdir(parents=True)
        for name, body in files.items():
            (pdir / name).write_text(body, encoding="utf-8")
    return str(tmp_path)


def test_in_sync_reports_no_drift(tmp_path):
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x = 1\n", "b.py": "y = 2\n"},
        profiles={"claude": {"a.py": "x = 1\n", "b.py": "y = 2\n"}},
    )
    assert scripts_drift_names(proj) == []


def test_a_differing_file_is_named(tmp_path):
    proj = _mkproject(
        tmp_path,
        source={"a.py": "NEW body\n"},
        profiles={"claude": {"a.py": "OLD body\n"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/a.py"]


def test_missing_in_profile_is_named(tmp_path):
    # The exact defect shape: a new source file that a redeploy never carried over.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n", "new.py": "z\n"},
        profiles={"claude": {"a.py": "x\n"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/new.py"]


def test_crlf_normalisation_is_not_drift(tmp_path):
    # A CRLF checkout of the same bytes must not false-positive.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x = 1\n"},
        profiles={"claude": {}},
    )
    (tmp_path / ".claude" / "scripts" / "a.py").write_bytes(b"x = 1\r\n")
    assert scripts_drift_names(proj) == []


def test_every_present_profile_is_checked(tmp_path):
    proj = _mkproject(
        tmp_path,
        source={"a.py": "src\n"},
        profiles={"claude": {"a.py": "src\n"}, "cursor": {"a.py": "stale\n"}},
    )
    assert scripts_drift_names(proj) == [".cursor/scripts/a.py"]


def test_absent_profile_is_not_drift(tmp_path):
    # Only .claude installed; the four other IDEs are simply not on disk. A gate
    # that demanded them would fail on every machine without all five IDEs.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n"},
        profiles={"claude": {"a.py": "x\n"}},
    )
    assert scripts_drift_names(proj) == []


def test_no_profiles_at_all_is_clean_not_none(tmp_path):
    # Fresh clone / CI: source present, zero profiles deployed. This is CLEAN
    # (empty list), NOT "cannot compare" (None) — the gate must PASS here.
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("x\n", encoding="utf-8")
    assert scripts_drift_names(str(tmp_path)) == []


def test_missing_source_dir_is_none(tmp_path):
    # No scripts/ source at all — genuinely cannot compare, distinct from clean.
    assert scripts_drift_names(str(tmp_path)) is None


def test_non_py_files_are_ignored(tmp_path):
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n", "notes.txt": "SOURCE"},
        profiles={"claude": {"a.py": "x\n", "notes.txt": "STALE"}},
    )
    # notes.txt drifts but is not a .py deploy target — must not be reported.
    assert scripts_drift_names(proj) == []


class TestGateRunner:
    """The registered task-done gate wrapper: pass/fail + actionable message."""

    def _point_gate_at(self, tmp_path, monkeypatch):
        (tmp_path / ".tausik").mkdir()
        monkeypatch.setenv("TAUSIK_DIR", str(tmp_path / ".tausik"))

    def test_passes_and_is_silent_when_in_sync(self, tmp_path, monkeypatch):
        _mkproject(tmp_path, source={"a.py": "x\n"}, profiles={"claude": {"a.py": "x\n"}})
        self._point_gate_at(tmp_path, monkeypatch)
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is True and "no bootstrap drift" in msg.lower()

    def test_fails_and_names_the_file_and_command_on_drift(self, tmp_path, monkeypatch):
        _mkproject(tmp_path, source={"a.py": "NEW\n"}, profiles={"claude": {"a.py": "OLD\n"}})
        self._point_gate_at(tmp_path, monkeypatch)
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is False
        assert ".claude/scripts/a.py" in msg
        assert "bootstrap.py --ide all" in msg

    def test_passes_when_no_profiles_present(self, tmp_path, monkeypatch):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "a.py").write_text("x\n", encoding="utf-8")
        self._point_gate_at(tmp_path, monkeypatch)
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, _msg = run_bootstrap_drift_gate()
        assert passed is True

    def test_passes_when_source_dir_missing(self, tmp_path, monkeypatch):
        self._point_gate_at(tmp_path, monkeypatch)
        from gate_bootstrap_drift import run_bootstrap_drift_gate

        passed, msg = run_bootstrap_drift_gate()
        assert passed is True and "skipped" in msg.lower()
