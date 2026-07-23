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

    A name may carry forward slashes (`hooks/x.py`) — that is how the
    hooks/providers subtrees, invisible to the pre-recursion comparator, are
    modelled.
    """

    def _write(base, name, body):
        target = base.joinpath(*name.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    src = tmp_path / "scripts"
    src.mkdir()
    for name, body in source.items():
        _write(src, name, body)
    for ide, files in profiles.items():
        pdir = tmp_path / f".{ide}" / "scripts"
        pdir.mkdir(parents=True)
        for name, body in files.items():
            _write(pdir, name, body)
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


def test_a_stale_non_py_file_is_drift(tmp_path):
    # This test previously asserted the OPPOSITE — that a drifting `notes.txt`
    # must NOT be reported "because it is not a .py deploy target". It is one:
    # `bootstrap_copy.copy_dir` deploys the whole tree, `scripts/hooks/pre-commit`
    # among it. A comparator judging only Python files applies a narrower rule
    # than the copier it exists to check — the second-copy-of-the-rule defect
    # (conv #266) one layer down, and the old assertion locked it in.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n", "notes.txt": "SOURCE"},
        profiles={"claude": {"a.py": "x\n", "notes.txt": "STALE"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/notes.txt"]


def test_drift_inside_hooks_subdir_is_found(tmp_path):
    # THE hole this task closes. `os.listdir` saw only the top level, so a stale
    # deployed hook — the file class that takes down every tool call with a
    # module-level ImportError when half-landed — read as clean.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n", "hooks/_common.py": "NEW\n"},
        profiles={"claude": {"a.py": "x\n", "hooks/_common.py": "OLD\n"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/hooks/_common.py"]


def test_missing_file_inside_a_subdir_is_found(tmp_path):
    # The live hazard named in the task: `_common.py` landed, the module it
    # imports did not. Every hook then dies on import until a redeploy.
    proj = _mkproject(
        tmp_path,
        source={
            "hooks/_common.py": "import hook_supervision\n",
            "hooks/hook_supervision.py": "x\n",
        },
        profiles={"claude": {"hooks/_common.py": "import hook_supervision\n"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/hooks/hook_supervision.py"]


def test_nested_providers_subdir_is_covered(tmp_path):
    proj = _mkproject(
        tmp_path,
        source={"providers/deep/p.py": "NEW\n"},
        profiles={"claude": {"providers/deep/p.py": "OLD\n"}},
    )
    assert scripts_drift_names(proj) == [".claude/scripts/providers/deep/p.py"]


def test_pycache_and_git_are_not_compared(tmp_path):
    # copy_dir never deploys them, so demanding them in the profile would be a
    # permanent false positive on any machine that ran the source once.
    proj = _mkproject(
        tmp_path,
        source={
            "a.py": "x\n",
            "__pycache__/a.cpython-311.pyc": "junk",
            "hooks/__pycache__/b.pyc": "junk",
            "b.pyc": "junk",
            ".git/config": "junk",
        },
        profiles={"claude": {"a.py": "x\n"}},
    )
    assert scripts_drift_names(proj) == []


def test_profile_only_file_is_not_drift(tmp_path):
    # `vendor_seo/` and leftover .pyc live in the profile and nowhere in source.
    # The gate asks "did a source edit fail to land"; an extra file in the
    # destination is not an answer to that question.
    proj = _mkproject(
        tmp_path,
        source={"a.py": "x\n"},
        profiles={"claude": {"a.py": "x\n", "vendor_seo/z.py": "extra\n"}},
    )
    assert scripts_drift_names(proj) == []


def test_comparator_ignore_rules_match_the_real_copier(tmp_path):
    # Behavioural tie, not a string comparison: run bootstrap's OWN copy_dir into
    # a temp target and assert the comparator's file set is exactly what landed.
    # If copy_dir's ignore rules ever change, this fails here instead of in an
    # incident where the gate silently stopped checking a subtree.
    boot = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
    if boot not in sys.path:
        sys.path.insert(0, boot)
    from bootstrap_copy import copy_dir

    from service_doctor_drift import _deployed_relpaths

    src = tmp_path / "scripts"
    for rel, body in {
        "a.py": "x\n",
        "README.md": "docs\n",
        "hooks/pre-commit": "#!/bin/bash\n",
        "hooks/h.py": "y\n",
        "providers/deep/p.py": "z\n",
        "__pycache__/a.pyc": "junk",
        "hooks/__pycache__/h.pyc": "junk",
        ".git/config": "junk",
        "stale.pyc": "junk",
    }.items():
        t = src.joinpath(*rel.split("/"))
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text(body, encoding="utf-8")

    dst = tmp_path / "deployed"
    copy_dir(str(src), str(dst))
    landed = {
        os.path.relpath(os.path.join(r, f), str(dst)).replace(os.sep, "/")
        for r, _d, fs in os.walk(str(dst))
        for f in fs
    }
    assert set(_deployed_relpaths(str(src))) == landed


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
