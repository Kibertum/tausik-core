"""TAUSIK CLI handler for `tausik doctor` — health diagnostic.

Single-pass check: venv + DB + MCP servers + core skills + bootstrap drift +
session capacity + gates loadable. Surfaces actionable next steps for any FAIL.
Exit code 0 on all-clean, 1 on any FAIL (so CI can gate on it).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from typing import Any

from project_service import ProjectService

_CI_ENV_MARKERS = frozenset(
    {
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "BUILDKITE",
        "CIRCLECI",
        "TF_BUILD",
        "JENKINS_URL",
        "TRAVIS",
    }
)


def _env_truthy(environ: Mapping[str, str], key: str) -> bool:
    val = environ.get(key)
    if val is None:
        return False
    return str(val).strip().lower() not in ("", "0", "false", "no", "off")


def looks_like_ci_environment(environ: Mapping[str, str]) -> bool:
    """True when common CI/CD vars suggest an automated runner (not local IDE)."""

    return any(_env_truthy(environ, k) for k in _CI_ENV_MARKERS)


def auto_verify_interactive_warning_detail(
    cfg: dict,
    environ: Mapping[str, str],
) -> str | None:
    """Warning text when legacy inline verify is enabled outside CI; else None."""

    td_raw = cfg.get("task_done")
    td = td_raw if isinstance(td_raw, dict) else {}
    if not bool(td.get("auto_verify")):
        return None
    if looks_like_ci_environment(environ):
        return None
    return (
        "task_done.auto_verify=true — heavy gates inline on `task done` (legacy). "
        "Prefer `verify` then `task done` for interactive agents; CI may keep "
        "`auto_verify` for single-step pipelines."
    )


def _supports_utf8() -> bool:
    if sys.platform == "win32":
        if os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"):
            return True
        try:
            import ctypes

            cp = ctypes.windll.kernel32.GetConsoleOutputCP()
            return bool(cp == 65001)
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            return False
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in enc


GREEN = "✓" if _supports_utf8() else "OK"
YELLOW = "!" if _supports_utf8() else "WARN"
RED = "✗" if _supports_utf8() else "FAIL"

_DB_PRE_SVC_EXISTS: bool | None = None


def _capture_db_state() -> None:
    """Snapshot DB existence BEFORE get_service auto-creates it."""
    global _DB_PRE_SVC_EXISTS
    if _DB_PRE_SVC_EXISTS is None:
        db = os.path.join(os.getcwd(), ".tausik", "tausik.db")
        _DB_PRE_SVC_EXISTS = os.path.isfile(db)


# The optional checks (Kilo, OpenCode, caveman, backlog, commit hooks, enforcement
# coverage) live next door: this file is held at 490 lines with headroom, and the
# six of them were the same block six times over.
from service_doctor_external import run_optional_checks  # noqa: E402


def cmd_doctor(svc: ProjectService, args: Any) -> None:
    failures = 0
    warnings = 0
    project_dir = os.getcwd()

    print("TAUSIK doctor — health check")
    print("=" * 40)

    venv_dir = os.path.join(project_dir, ".tausik", "venv")
    if os.path.isdir(venv_dir):
        _print_ok("Python venv", venv_dir)
    else:
        _print_fail(
            "Python venv",
            "not found at .tausik/venv — run: python bootstrap/bootstrap.py",
        )
        failures += 1

    db = os.path.join(project_dir, ".tausik", "tausik.db")
    if _DB_PRE_SVC_EXISTS is False:
        _print_warn(
            "Project DB",
            "was MISSING before doctor — auto-created. Run: tausik init for full setup",
        )
        warnings += 1
    elif os.path.isfile(db):
        size_kb = os.path.getsize(db) // 1024
        _print_ok("Project DB", f".tausik/tausik.db ({size_kb} KB)")
    else:
        _print_fail("Project DB", "not found — run: tausik init")
        failures += 1

    # Which profile directory this project actually runs from. Hardcoding
    # `.claude` here made `doctor` FAIL and exit 1 on every Cursor / Qwen /
    # Kilo / OpenCode install — bootstrap deploys `.cursor/mcp`, `.qwen/mcp`
    # and friends, and the health check declared them missing. A health check
    # that fails healthy projects trains people to ignore it.
    from ide_utils import missing_profile_hint, resolve_profile

    ide, ide_rel = resolve_profile(project_dir)
    mcp_project = os.path.join(project_dir, ide_rel, "mcp", "project", "server.py")
    if os.path.isfile(mcp_project):
        _print_ok("MCP server (project)", f"{ide_rel}/mcp/project/server.py")
    else:
        hint = missing_profile_hint(project_dir, ide)
        _print_fail("MCP server (project)", f"{ide_rel}/mcp/project/server.py {hint}")
        failures += 1

    _f, _w = run_optional_checks(project_dir, svc, _print_ok, _print_warn, _print_fail)
    failures += _f
    warnings += _w

    skills_dir = os.path.join(project_dir, ide_rel, "skills")
    if os.path.isdir(skills_dir):
        skills = [d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))]
        critical = {
            "start",
            "end",
            "task",
            "plan",
            "review",
            "ship",
            "checkpoint",
        }
        missing = critical - set(skills)
        if not missing:
            _print_ok("Core skills", f"{len(skills)} deployed (all critical present)")
        else:
            _print_fail(
                "Core skills",
                f"missing critical: {sorted(missing)} — re-run bootstrap",
            )
            failures += 1
    else:
        _print_fail("Core skills", f"no {ide_rel}/skills/ — run bootstrap")
        failures += 1

    d_is_warn, d_detail = _format_scripts_drift_line(_scripts_drift_names(project_dir))
    (_print_warn if d_is_warn else _print_ok)("Bootstrap drift", d_detail)
    warnings += int(d_is_warn)

    from pyc_hygiene import doctor_section  # a .pyc that names another tree lies in tracebacks

    fix_pyc = getattr(args, "fix_bytecode", False)  # tests call cmd_doctor with bare namespaces
    warnings += doctor_section(project_dir, fix_pyc, _print_ok, _print_warn)
    md_is_warn, md_detail = _format_claudemd_drift_line(_claudemd_drift_report(project_dir))
    if md_is_warn:
        _print_warn("CLAUDE.md drift", md_detail)
        warnings += 1
    else:
        _print_ok("CLAUDE.md drift", md_detail)

    try:
        from project_config import (
            DEFAULT_SESSION_CAPACITY_CALLS,
            DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES,
            DEFAULT_SESSION_MAX_MINUTES,
            DEFAULT_SESSION_WARN_THRESHOLD_MINUTES,
            load_config_with_rejections,
        )
        from verify_constants import DEFAULT_CACHE_TTL_S

        cfg, trust_rejections = load_config_with_rejections()
        cap = cfg.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
        # DELIBERATELY the configured base, not the extended limit `tausik status`
        # shows. This line reports CONFIGURATION, not the state of whichever
        # session happens to be open — a `session extend` is a fact about one
        # session, and folding it in here would make doctor describe a knob nobody
        # set. The divergence from `status` is intended; do not "fix" it.
        max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
        warn_th = cfg.get("session_warn_threshold_minutes", DEFAULT_SESSION_WARN_THRESHOLD_MINUTES)
        idle_th = cfg.get("session_idle_threshold_minutes", DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES)
        ttl = cfg.get("verify_cache_ttl_seconds", DEFAULT_CACHE_TTL_S)
        _print_ok(
            "Config knobs",
            f"max={max_min}m warn={warn_th}m idle={idle_th}m capacity={cap} cache_ttl={ttl}s",
        )
        av_hint = auto_verify_interactive_warning_detail(cfg, dict(os.environ))
        if av_hint:
            _print_warn("Verify-First profile", av_hint)
            warnings += 1
        # THREE states, not two. A project-scope key that tried to weaken
        # enforcement is dropped on read, and silent dropping would look like the
        # setting works — so every rejection is named. A key a TRUSTED tier holds
        # weaker is NOT dropped; saying nothing of it let the OK line read as
        # "nothing is weakened" while QG-2 was being bypassed. WARN and never
        # FAIL: those tiers are the operator's word, and doctor owes visibility
        # here, not a verdict.
        from config_trust_weakening import summary

        weak_lines, weak_ok = summary(cfg, project_dir)
        for r in trust_rejections:
            _print_warn("Config trust tier", r.describe())
        for line in weak_lines:
            _print_warn("Config trust tier", line)
        warnings += len(trust_rejections) + len(weak_lines)
        if not trust_rejections and weak_ok:
            _print_ok("Config trust tier", weak_ok)
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        _print_warn("Config knobs", f"load failed: {e}")
        warnings += 1

    try:
        from default_gates import DEFAULT_GATES

        gate_names = sorted(DEFAULT_GATES.keys())
        # Resolve the gates the project will ACTUALLY run, not just the registry
        # count. Counting DEFAULT_GATES alone cannot fail, so it reported a
        # clean bill of health while a malformed `gates` entry crashed
        # `load_gates` and silently disabled Verify-First enforcement.
        from project_config import get_gates_for_trigger, load_gates

        effective = load_gates()
        verify_gates = get_gates_for_trigger("verify")
        _print_ok(
            "Quality gates",
            f"{len(gate_names)} registered, {len(effective)} resolved, "
            f"{len(verify_gates)} on verify",
        )
    except Exception as e:  # noqa: BLE001 — a gate config that cannot resolve is a FAIL, not a warning
        _print_fail("Quality gates", f"config failed to resolve: {type(e).__name__}: {e}")
        failures += 1

        warnings += 1

    try:
        active = svc.session_active_minutes()
        wall = svc.session_wall_minutes()
        if wall > 0:
            _print_ok("Session", f"{active}m active / {wall}m wall")
        else:
            _print_ok("Session", "no active session")
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        _print_warn("Session", f"could not read: {e}")
        warnings += 1

    print("=" * 40)
    if failures:
        print(f"{RED} {failures} FAIL, {warnings} WARN — fix above before running tasks.")
        sys.exit(1)
    elif warnings:
        print(f"{YELLOW} OK with {warnings} warning(s).")
    else:
        print(f"{GREEN} All clean.")


def _print_ok(label: str, detail: str) -> None:
    print(f"  {GREEN}  {label:<25} {detail}")


def _print_warn(label: str, detail: str) -> None:
    print(f"  {YELLOW}  {label:<25} {detail}")


def _print_fail(label: str, detail: str) -> None:
    print(f"  {RED}  {label:<25} {detail}")


# Drift checks moved to service_doctor_drift.py (filesize gate). Re-exported
# here under the legacy underscore-prefixed names so existing tests + callers
# continue to work without import surgery.
from service_doctor_drift import (  # noqa: E402,F401
    check_claudemd_drift as _check_claudemd_drift,
    check_scripts_drift as _check_scripts_drift,
    claudemd_drift_report as _claudemd_drift_report,
    format_claudemd_drift_line as _format_claudemd_drift_line,
    format_scripts_drift_line as _format_scripts_drift_line,
    scripts_drift_names as _scripts_drift_names,
)


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
