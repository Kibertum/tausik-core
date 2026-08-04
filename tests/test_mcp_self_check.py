"""Tests for the MCP project server's self-check diagnostic.

Covers v14b-mcp-stale-module-detector — detection of stale in-memory
modules that cause silent hangs in `tausik_verify` / `tausik_task_done`
(gotchas #77 / #79 / #80; the rename in v14b-task-done-rename-drop-v2
consolidated `tausik_task_done_v2` back into `tausik_task_done`).
"""

from __future__ import annotations

import importlib
import os
import sys

import pytest


@pytest.fixture
def self_check_mod():
    """Import self_check fresh, with the MCP project dir on sys.path."""
    mcp_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "harness",
            "claude",
            "mcp",
            "project",
        )
    )
    if mcp_dir not in sys.path:
        sys.path.insert(0, mcp_dir)
    if "self_check" in sys.modules:
        mod = importlib.reload(sys.modules["self_check"])
    else:
        import self_check as mod  # type: ignore[import-not-found]
    return mod


def test_startup_snapshot_populated(self_check_mod):
    """Eager-import + snapshot must run at module import.

    The snapshot dict can be empty in stripped environments, but the
    startup-time string MUST be set the first time the module loads.
    """
    assert self_check_mod._STARTUP_TIME_ISO
    assert isinstance(self_check_mod._MODULE_MTIMES_AT_STARTUP, dict)
    # In a healthy dev env at least one of the watched modules resolves
    # to a real file under scripts/. Allow zero only if the dev tree is
    # incomplete (CI-stripped tarball) — but the dict shape is required.
    for path, mtime in self_check_mod._MODULE_MTIMES_AT_STARTUP.items():
        assert os.path.isabs(path)
        assert isinstance(mtime, float)


def test_no_drift_when_files_unchanged(self_check_mod):
    """`collect()` reports drift_detected=False when nothing has moved."""
    report = self_check_mod.collect()
    assert report["server"] == "tausik-project"
    assert report["drift_detected"] is False
    assert report["stale_modules"] == []
    assert isinstance(report["sibling_mcp_count"], int)
    assert report["watched_modules_count"] == len(report["watched_modules"])


def test_drift_detected_when_mtime_advances(self_check_mod, tmp_path, monkeypatch):
    """Bump a snapshot file's mtime and confirm drift surfaces."""
    fake = tmp_path / "fake_module.py"
    fake.write_text("# placeholder\n", encoding="utf-8")
    snap = os.path.getmtime(fake)
    fake_path = str(fake)
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {fake_path: snap},
    )
    # Advance the on-disk mtime by 30s — well beyond float-precision noise.
    os.utime(fake, (snap + 30, snap + 30))

    report = self_check_mod.collect()

    assert report["drift_detected"] is True
    stale = report["stale_modules"]
    assert len(stale) == 1
    assert stale[0]["path"] == fake_path
    assert stale[0]["module"] == "fake_module.py"
    assert stale[0]["delta_seconds"] >= 30
    assert "Restart your IDE" in report["remediation"]


def test_collect_handles_missing_file_gracefully(self_check_mod, tmp_path, monkeypatch):
    """A snapshotted path that vanishes on disk must not crash collect()."""
    ghost = str(tmp_path / "deleted.py")
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {ghost: 1700000000.0},
    )
    # Path never existed — getmtime raises OSError, the loop skips it.
    report = self_check_mod.collect()
    assert report["drift_detected"] is False
    assert report["stale_modules"] == []


def test_sibling_count_is_safe_int(self_check_mod):
    """Sibling enumeration returns an int (or -1) without raising."""
    report = self_check_mod.collect()
    assert isinstance(report["sibling_mcp_count"], int)
    assert report["sibling_mcp_count"] >= -1
    assert isinstance(report["sibling_mcp_pids"], list)


def test_remediation_silent_when_count_unknown(self_check_mod, monkeypatch):
    """When sibling introspection failed (count=-1) and no drift, the
    remediation must NOT contain 'Restart your IDE' — that would be a
    false positive on hosts where wmic/PowerShell aren't usable.
    """
    # Force unknown-sibling state and zero drift.
    monkeypatch.setattr(self_check_mod, "_MODULE_MTIMES_AT_STARTUP", {})
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {
            "count": -1,
            "pids": [],
            "error": "wmic and powershell both missing: stub",
        },
    )
    report = self_check_mod.collect()
    assert report["drift_detected"] is False
    assert report["sibling_mcp_count"] == -1
    assert "Restart your IDE" not in report["remediation"]
    assert "drift check" in report["remediation"].lower()


def test_remediation_fires_on_real_drift(self_check_mod, tmp_path, monkeypatch):
    """With real drift, the remediation MUST tell the user to restart.

    Pinpoints the regression: previously, count=-1 also fired this path.
    """
    fake = tmp_path / "drifted.py"
    fake.write_text("# x\n", encoding="utf-8")
    snap = os.path.getmtime(fake)
    monkeypatch.setattr(
        self_check_mod,
        "_MODULE_MTIMES_AT_STARTUP",
        {str(fake): snap},
    )
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 0, "pids": [], "error": None},
    )
    os.utime(fake, (snap + 30, snap + 30))

    report = self_check_mod.collect()
    assert report["drift_detected"] is True
    assert "Restart your IDE" in report["remediation"]


def test_handler_returns_json_envelope(self_check_mod):
    """The MCP `_handle_self_check` dispatch wraps `collect()` in JSON.

    Not strictly necessary — but documents the integration surface for
    the agent so the JSON shape stays stable.
    """
    import json

    handlers_dir = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "harness",
            "claude",
            "mcp",
            "project",
        )
    )
    if handlers_dir not in sys.path:
        sys.path.insert(0, handlers_dir)
    # `_handle_self_check` moved into the status domain module by
    # mcp-handlers-god-module-split; handlers.py now only dispatches.
    if "handlers_status" in sys.modules:
        importlib.reload(sys.modules["handlers_status"])
    import handlers_status as handlers_mod  # type: ignore[import-not-found]

    raw = handlers_mod._handle_self_check()
    parsed = json.loads(raw)
    assert parsed["server"] == "tausik-project"
    assert "drift_detected" in parsed


# ==========================================================================
# mcp-self-check-watches-eleven-modules-of-a-hundred
# The watch set must come from the PRODUCER (sys.modules under the server
# tree), not a hand-maintained list that goes blind to everything outside it.
# ==========================================================================


import types  # noqa: E402


def _fake_module(name: str, file_path: str) -> types.ModuleType:
    m = types.ModuleType(name)
    m.__file__ = file_path
    return m


def test_watch_set_comes_from_producer_not_hand_list(self_check_mod, tmp_path, monkeypatch):
    """AC1: the observed set is derived from sys.modules filtered to the
    server roots — NOT enumerated in `_EAGER_IMPORT_MODULES`."""
    scripts_root = tmp_path / "scripts"
    mcp_root = tmp_path / "mcp"
    scripts_root.mkdir()
    mcp_root.mkdir()
    roots = (
        os.path.normcase(str(scripts_root)),
        os.path.normcase(str(mcp_root)),
    )
    monkeypatch.setattr(self_check_mod, "_server_roots", lambda: roots)

    f = scripts_root / "some_service.py"
    f.write_text("# x\n", encoding="utf-8")
    fake = _fake_module("some_service_xyz", str(f))
    monkeypatch.setitem(sys.modules, "some_service_xyz", fake)

    loaded = self_check_mod._loaded_our_module_paths()
    assert os.path.normcase(str(f)) in {os.path.normcase(p) for p in loaded.values()}


def test_reproduces_todays_case_module_outside_old_eleven(self_check_mod, tmp_path, monkeypatch):
    """AC2: reproduce the session #135 case — a module that was NOT in the old
    hard list of eleven (e.g. `complexity_understatement`) is edited after
    startup and MUST surface as drift, named in stale_modules.

    Proof the hole existed: the same module name is NOT in
    `_EAGER_IMPORT_MODULES` (the old watch-set definition), so the old
    list-driven check could never have seen it.
    """
    # The hole: this module drove a false calibration event yet was invisible.
    assert "complexity_understatement" not in self_check_mod._EAGER_IMPORT_MODULES
    assert "service_task_done" not in self_check_mod._EAGER_IMPORT_MODULES

    scripts_root = tmp_path / "scripts"
    scripts_root.mkdir()
    roots = (os.path.normcase(str(scripts_root)), os.path.normcase(str(tmp_path / "mcp")))
    monkeypatch.setattr(self_check_mod, "_server_roots", lambda: roots)

    victim = scripts_root / "complexity_understatement.py"
    victim.write_text("# real code\n", encoding="utf-8")
    snap = os.path.getmtime(str(victim))
    fake = _fake_module("complexity_understatement", str(victim))
    monkeypatch.setitem(sys.modules, "complexity_understatement", fake)

    # Snapshot taken at "startup" — module present, unchanged.
    monkeypatch.setattr(self_check_mod, "_MODULE_MTIMES_AT_STARTUP", {str(victim): snap})
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 0, "pids": [], "error": None},
    )
    # Edit lands AFTER startup.
    os.utime(str(victim), (snap + 30, snap + 30))

    report = self_check_mod.collect()

    assert report["drift_detected"] is True
    names = [s["module"] for s in report["stale_modules"]]
    assert "complexity_understatement.py" in names


def test_old_list_would_have_missed_it(self_check_mod, tmp_path, monkeypatch):
    """AC2 (companion): with the OLD list-as-watch-set semantics, editing a
    module outside the eleven yields NO drift — proving the defect. We emulate
    the old behaviour by driving the pure core with an EMPTY startup snapshot
    and an EMPTY loaded set (the old code never looked past its 11 names, none
    of which is our victim), and confirm it reports clean."""
    victim = tmp_path / "complexity_understatement.py"
    victim.write_text("# x\n", encoding="utf-8")
    os.utime(str(victim), (2_000_000_000, 2_000_000_000))  # far future mtime
    # Old semantics: victim is not in the 11-name snapshot and the old code
    # never enumerated sys.modules → it is invisible.
    drift, _cur = self_check_mod._compute_drift({}, 1_000_000_000.0, {}, os.path.getmtime)
    assert drift == []  # the hole: a future-dated edit produced no drift


def test_lazy_loaded_after_startup_is_drift(self_check_mod, tmp_path):
    """AC3: a module imported LAZILY after startup (absent from the snapshot)
    whose file mtime is later than the boot time is treated as drift."""
    late = tmp_path / "lazy_mod.py"
    late.write_text("# x\n", encoding="utf-8")
    boot = 1_000_000_000.0
    os.utime(str(late), (boot + 500, boot + 500))  # edited after boot
    drift, cur = self_check_mod._compute_drift({}, boot, {"lazy_mod": str(late)}, os.path.getmtime)
    assert len(drift) == 1
    assert drift[0]["module"] == "lazy_mod.py"
    assert drift[0]["reason"] == "lazy-loaded-after-edit"


def test_lazy_loaded_before_boot_is_not_drift(self_check_mod, tmp_path):
    """AC3 negative: a lazily-loaded module whose file predates boot is fresh
    (it was read off disk after the edit) — NOT drift."""
    early = tmp_path / "early_mod.py"
    early.write_text("# x\n", encoding="utf-8")
    boot = 2_000_000_000.0
    os.utime(str(early), (boot - 500, boot - 500))  # file older than boot
    drift, _cur = self_check_mod._compute_drift(
        {}, boot, {"early_mod": str(early)}, os.path.getmtime
    )
    assert drift == []


def test_stdlib_and_site_packages_not_watched(self_check_mod):
    """AC5: stdlib / site-packages modules fall outside the server roots, so a
    `pip install` (which bumps their mtime) can never read as MCP drift."""
    loaded = self_check_mod._loaded_our_module_paths()
    watched = {os.path.normcase(p) for p in loaded.values()}
    # `os` and `json` are always loaded and always stdlib.
    for stdlib_name in ("os", "json", "sys"):
        mod = sys.modules.get(stdlib_name)
        f = getattr(mod, "__file__", None)
        if f:
            assert os.path.normcase(os.path.abspath(f)) not in watched


def test_file_not_imported_by_server_is_not_drift(self_check_mod, tmp_path):
    """AC5: a file the server never imported is not in the loaded set, so an
    edit to it cannot be drift — the check speaks only about loaded code."""
    stranger = tmp_path / "never_imported.py"
    stranger.write_text("# x\n", encoding="utf-8")
    os.utime(str(stranger), (2_000_000_000, 2_000_000_000))
    # Not in snapshot, not in loaded set → no drift.
    drift, _cur = self_check_mod._compute_drift({}, 1_000_000_000.0, {}, os.path.getmtime)
    assert drift == []


def test_module_without_file_is_skipped_not_crash(self_check_mod, tmp_path, monkeypatch):
    """AC5: a module with no `__file__` (builtin, namespace package) yields no
    entry and no exception."""
    roots = (os.path.normcase(str(tmp_path / "scripts")), os.path.normcase(str(tmp_path / "mcp")))
    monkeypatch.setattr(self_check_mod, "_server_roots", lambda: roots)
    nofile = types.ModuleType("no_file_mod")  # no __file__ attribute
    monkeypatch.setitem(sys.modules, "no_file_mod", nofile)
    loaded = self_check_mod._loaded_our_module_paths()  # must not raise
    assert "no_file_mod" not in loaded


def test_deleted_file_getmtime_error_swallowed(self_check_mod):
    """AC5: a snapshotted module whose file was deleted after startup raises
    OSError inside getmtime — the core swallows it and returns a report."""
    drift, cur = self_check_mod._compute_drift(
        {"/nonexistent/ghost.py": 1_000_000_000.0},
        1_000_000_000.0,
        {},
        os.path.getmtime,
    )
    assert drift == []
    assert "/nonexistent/ghost.py" not in cur


def test_any_getmtime_exception_does_not_crash_collect(self_check_mod, monkeypatch):
    """AC5: ANY error inside the check must not crash the MCP server. Patch
    os.path.getmtime to raise a non-OSError; collect() must still return a
    report dict, not propagate."""
    monkeypatch.setattr(self_check_mod, "_MODULE_MTIMES_AT_STARTUP", {"/x/y.py": 1.0})

    def boom(_path):
        raise RuntimeError("simulated getmtime failure")

    monkeypatch.setattr(self_check_mod.os.path, "getmtime", boom)
    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 0, "pids": [], "error": None},
    )
    report = self_check_mod.collect()  # must not raise
    assert report["server"] == "tausik-project"
    assert report["drift_detected"] is False


def test_self_check_module_walk_cost_under_budget(self_check_mod):
    """AC4: the sys.modules walk (the added cost) must be cheap. Measure the
    producer walk + snapshot over the REAL loaded module set and assert it is
    well under the 100 ms budget the task named."""
    import time

    n = 20
    t0 = time.perf_counter()
    for _ in range(n):
        loaded = self_check_mod._loaded_our_module_paths()
        self_check_mod._compute_drift(
            self_check_mod._snapshot_module_mtimes(),
            self_check_mod._STARTUP_TIME_EPOCH,
            loaded,
            os.path.getmtime,
        )
    elapsed_ms = (time.perf_counter() - t0) / n * 1000
    # Print so the AC4 measurement is captured in test output.
    print(
        f"\n[AC4] self_check module walk: {elapsed_ms:.2f} ms/call "
        f"over {len(sys.modules)} sys.modules"
    )
    assert elapsed_ms < 100, f"module walk too slow: {elapsed_ms:.2f} ms"


def test_enumerate_excludes_parent_pid_venv_launcher(self_check_mod, monkeypatch, tmp_path):
    """Regression for v14b-defect-mcp-self-check-venv-launcher.

    On Windows, `venv\\Scripts\\python.exe` is a launcher shim that re-execs
    the real interpreter as a child while keeping the same command line. The
    parent therefore matches the same `mcp/project/server.py` + project
    needle as the child and would otherwise count as a "sibling MCP",
    producing a chronic +1 false-positive after every IDE restart. Fix:
    `_enumerate_sibling_mcps` must exclude `os.getppid()` from the candidate
    set on every introspection backend (wmic, PowerShell, /proc, ps).
    """
    import subprocess

    self_pid = 47332
    parent_pid = 30968
    real_sibling_pid = 99999
    project_str = str(tmp_path).replace("\\", "/")

    monkeypatch.setattr(self_check_mod.os, "getpid", lambda: self_pid)
    monkeypatch.setattr(self_check_mod.os, "getppid", lambda: parent_pid)
    # Force the PowerShell branch (modern Windows) by making wmic appear absent.
    cmd_line = f"python.exe .claude/mcp/project/server.py --project {project_str}"
    ps_stdout = "\n".join(
        [
            f"{parent_pid}|{cmd_line}",  # venv shim parent — must be skipped
            f"{self_pid}|{cmd_line}",  # self — must be skipped
            f"{real_sibling_pid}|{cmd_line}",  # actual leak — must be counted
        ]
    )

    def fake_run(cmd, *args, **kwargs):
        first = cmd[0] if cmd else ""
        if first == "wmic":
            raise FileNotFoundError("wmic absent (simulated)")
        if first == "powershell":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=ps_stdout, stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(self_check_mod.sys, "platform", "win32")
    monkeypatch.setattr("subprocess.run", fake_run)

    out = self_check_mod._enumerate_sibling_mcps(self_pid, str(tmp_path))

    assert out["error"] is None
    assert parent_pid not in out["pids"], (
        "venv launcher shim parent PID leaked into sibling list — "
        "v14b-defect-mcp-self-check-venv-launcher regressed."
    )
    assert self_pid not in out["pids"]
    assert real_sibling_pid in out["pids"]
    assert out["count"] == 1


# --- v2-stale-mcp-reaping: TTL-cached enumeration + report-only warning -------


def _put_scripts_on_path() -> None:
    """Make scripts/mcp_reaper.py importable (source tree has no
    harness/claude/scripts, so self_check's own path helper no-ops here)."""
    scripts = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


def test_sibling_enumeration_is_ttl_cached(self_check_mod, monkeypatch):
    """AC3: the expensive enumeration is not re-run on every collect() call.

    On Win11 26200 each enumeration spawns a fresh PowerShell Get-CimInstance
    (~1s); paying that on every self_check made /start look like a hang. Within
    the TTL window a second collect() must reuse the cached result.
    """
    _put_scripts_on_path()
    self_check_mod._SIBLING_ENUM_CACHE.clear()
    calls = {"n": 0}

    def counting_enum(pid, project):
        calls["n"] += 1
        return {"count": 0, "pids": [], "error": None}

    monkeypatch.setattr(self_check_mod, "_enumerate_sibling_mcps", counting_enum)

    self_check_mod.collect()
    self_check_mod.collect()
    assert calls["n"] == 1, "enumeration ran more than once inside the TTL window"


def test_sibling_count_over_threshold_reports_warning(self_check_mod, monkeypatch):
    """AC2: an accumulation above threshold surfaces a report-only warning that
    is prepended to remediation — and never claims the framework killed anything.
    """
    _put_scripts_on_path()
    self_check_mod._SIBLING_ENUM_CACHE.clear()

    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 5, "pids": [11, 22, 33, 44, 55], "error": None},
    )
    report = self_check_mod.collect()
    assert report["sibling_mcp_count"] == 5
    assert report["sibling_warning"], "count 5 (>3) should raise a warning"
    assert "5" in report["sibling_warning"]
    assert "will not kill" in report["sibling_warning"].lower()
    # The warning leads the remediation string the agent surfaces.
    assert report["remediation"].startswith(report["sibling_warning"])


def test_sibling_count_within_threshold_no_warning(self_check_mod, monkeypatch):
    """NEGATIVE (AC2): a normal sibling count raises no warning and leaves
    remediation untouched."""
    _put_scripts_on_path()
    self_check_mod._SIBLING_ENUM_CACHE.clear()

    monkeypatch.setattr(
        self_check_mod,
        "_enumerate_sibling_mcps",
        lambda pid, project: {"count": 2, "pids": [11, 22], "error": None},
    )
    report = self_check_mod.collect()
    assert report["sibling_mcp_count"] == 2
    assert report["sibling_warning"] == ""


def test_enumeration_exception_degrades_to_unknown(self_check_mod, monkeypatch):
    """s146 review LOW: if the cached enumeration itself raises, collect() must
    degrade to count == -1 (unknown), never crash the MCP diagnostic (AC5)."""
    _put_scripts_on_path()

    def boom(pid, project):
        raise RuntimeError("enumeration blew up")

    monkeypatch.setattr(self_check_mod, "_enumerate_sibling_mcps_cached", boom)
    report = self_check_mod.collect()
    assert report["sibling_mcp_count"] == -1
    assert report["drift_detected"] is False
