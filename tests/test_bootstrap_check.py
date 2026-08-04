"""bootstrap-drift-harness-tree-ungated — the harness/ fan-out drift oracle.

Where scripts/ is one-to-one (covered by scripts_drift_names), the harness/ tree
fans out: `harness/claude/mcp/*` → `.claude/mcp/*`, `harness/claude/subagents/*`
→ `.claude/agents/*`. bootstrap_check reuses bootstrap's OWN copy functions as the
oracle — it scaffolds the copy-only trees into a temp dir and byte-compares — so
there is no second, silently-diverging layout formula (#249).

Synthetic lib+project under tmp_path (never the repo's real gitignored profiles,
which would degrade to an eternal skip on a fresh clone — memory #229).
"""

from __future__ import annotations

import os
import sys
import tempfile


BOOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
for _p in (SCRIPTS, BOOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bootstrap_check import check_deployed_trees  # noqa: E402


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _lib(tmp_path, handlers: str = "v1") -> str:
    lib = str(tmp_path / "lib")
    _write(
        os.path.join(lib, "harness", "claude", "mcp", "project", "handlers.py"), f"# {handlers}\n"
    )
    return lib


def _project(tmp_path, *, deployed: str | None = "v1", extra: dict[str, str] | None = None) -> str:
    proj = str(tmp_path / "proj")
    if deployed is not None:
        _write(os.path.join(proj, ".claude", "mcp", "project", "handlers.py"), f"# {deployed}\n")
    for rel, body in (extra or {}).items():
        _write(os.path.join(proj, rel), body)
    return proj


class TestHarnessDrift:
    def test_in_sync_reports_nothing(self, tmp_path):
        assert (
            check_deployed_trees(
                _lib(tmp_path, "v1"), _project(tmp_path, deployed="v1"), ["claude"]
            )
            == []
        )

    def test_stale_deployed_copy_is_named(self, tmp_path):
        # AC4: the exact defect — source edited (v2), deployed copy still v1.
        drift = check_deployed_trees(
            _lib(tmp_path, "v2"), _project(tmp_path, deployed="v1"), ["claude"]
        )
        assert drift == [".claude/mcp/project/handlers.py"]

    def test_missing_in_profile_is_named(self, tmp_path):
        # Profile present (.claude exists) but the mcp file never landed.
        proj = _project(tmp_path, deployed=None, extra={".claude/marker": "x"})
        drift = check_deployed_trees(_lib(tmp_path, "v1"), proj, ["claude"])
        assert drift == [".claude/mcp/project/handlers.py"]

    def test_crlf_is_not_drift(self, tmp_path):
        lib = _lib(tmp_path, "v1")
        proj = str(tmp_path / "proj")
        # Same bytes, CRLF line ending — a cross-platform checkout must not flag.
        _write_bytes = os.path.join(proj, ".claude", "mcp", "project", "handlers.py")
        os.makedirs(os.path.dirname(_write_bytes), exist_ok=True)
        with open(_write_bytes, "wb") as f:
            f.write(b"# v1\r\n")
        assert check_deployed_trees(lib, proj, ["claude"]) == []


class TestInertness:
    def test_absent_profile_is_not_drift(self, tmp_path):
        # AC5: no .claude on disk (fresh clone / CI) → nothing deployed to fall
        # behind. Must be clean, not a demand for a profile that need not exist.
        assert check_deployed_trees(_lib(tmp_path, "v1"), str(tmp_path / "proj"), ["claude"]) == []

    def test_no_harness_source_is_empty(self, tmp_path):
        # AC5: no harness/ to scaffold from → clean (callers read [] as clean).
        proj = _project(tmp_path, deployed="v1")
        assert check_deployed_trees(str(tmp_path / "empty-lib"), proj, ["claude"]) == []


class TestGeneratedFilesNotFlagged:
    def test_generated_settings_is_ignored(self, tmp_path):
        # AC6: a generated file living in the profile is never scaffolded, so it
        # is never compared — no false positive even though it has no source twin.
        proj = _project(
            tmp_path, deployed="v1", extra={".claude/settings.json": '{"generated": true}'}
        )
        drift = check_deployed_trees(_lib(tmp_path, "v1"), proj, ["claude"])
        assert drift == []
        assert all(
            "settings.json" not in d
            for d in check_deployed_trees(_lib(tmp_path, "v2"), proj, ["claude"])
        )


class TestTempCleanup:
    def test_no_temp_dirs_left_behind(self, tmp_path):
        # AC7: the throwaway scaffold is removed even across a normal run.
        before = {n for n in os.listdir(tempfile.gettempdir()) if n.startswith("tausik-drift-")}
        check_deployed_trees(_lib(tmp_path, "v2"), _project(tmp_path, deployed="v1"), ["claude"])
        after = {n for n in os.listdir(tempfile.gettempdir()) if n.startswith("tausik-drift-")}
        assert after <= before  # nothing new left over


class TestGateWiring:
    """The task-done gate blocks on harness drift, names the file + command."""

    def test_gate_blocks_on_harness_drift(self, tmp_path, monkeypatch):
        import gate_bootstrap_drift as g

        monkeypatch.setattr(
            g, "_harness_drift_names", lambda _p: [".claude/mcp/project/handlers.py"]
        )
        monkeypatch.setattr("service_doctor_drift.scripts_drift_names", lambda _p: [])
        monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(tmp_path / ".tausik"))
        passed, msg = g.run_bootstrap_drift_gate()
        assert passed is False
        assert ".claude/mcp/project/handlers.py" in msg
        assert "bootstrap.py --ide all" in msg

    def test_gate_passes_when_both_comparators_clean(self, tmp_path, monkeypatch):
        import gate_bootstrap_drift as g

        monkeypatch.setattr(g, "_harness_drift_names", lambda _p: [])
        monkeypatch.setattr("service_doctor_drift.scripts_drift_names", lambda _p: [])
        monkeypatch.setattr("project_config.find_tausik_dir", lambda: str(tmp_path / ".tausik"))
        passed, msg = g.run_bootstrap_drift_gate()
        assert passed is True and "no bootstrap drift" in msg.lower()
