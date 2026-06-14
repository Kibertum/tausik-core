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

    mcp_project = os.path.join(project_dir, ".claude", "mcp", "project", "server.py")
    mcp_brain = os.path.join(project_dir, ".claude", "mcp", "brain", "server.py")
    if os.path.isfile(mcp_project):
        _print_ok("MCP server (project)", ".claude/mcp/project/server.py")
    else:
        _print_fail("MCP server (project)", "missing — re-run bootstrap")
        failures += 1
    if os.path.isfile(mcp_brain):
        _print_ok("MCP server (brain)", ".claude/mcp/brain/server.py")
    else:
        _print_warn("MCP server (brain)", "missing — bootstrap may have skipped it")
        warnings += 1

    skills_dir = os.path.join(project_dir, ".claude", "skills")
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
        # brain skill is opt-in: only required when brain.enabled=true.
        # Mirrors bootstrap_copy gating so disabling brain doesn't FAIL doctor.
        try:
            from project_config import load_config  # noqa: PLC0415

            _cfg = load_config() or {}
            if bool((_cfg.get("brain") or {}).get("enabled", False)):
                critical.add("brain")
        except Exception:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
            critical.add("brain")  # default-on when config unreadable
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
        _print_fail("Core skills", "no .claude/skills/ — run bootstrap")
        failures += 1

    drift = _check_scripts_drift(project_dir)
    if drift is None:
        _print_warn("Bootstrap drift", "could not compare scripts/ vs .claude/scripts/")
        warnings += 1
    elif drift:
        _print_warn(
            "Bootstrap drift",
            f"{drift} script(s) differ — restart MCP server or re-bootstrap",
        )
        warnings += 1
    else:
        _print_ok("Bootstrap drift", "none — deployed scripts match source")

    md_drift = _check_claudemd_drift(project_dir)
    if md_drift is None:
        _print_warn(
            "CLAUDE.md drift",
            "could not compare CLAUDE.md vs bootstrap_templates output",
        )
        warnings += 1
    elif md_drift:
        _print_warn(
            "CLAUDE.md drift",
            f"{md_drift} static section(s) differ from bootstrap template "
            "(likely project customisation; re-run bootstrap to reset). "
            "`tausik update-claudemd` only refreshes the DYNAMIC block.",
        )
        warnings += 1
    else:
        _print_ok("CLAUDE.md drift", "none — static sections match bootstrap_templates")

    try:
        from project_config import (
            DEFAULT_SESSION_CAPACITY_CALLS,
            DEFAULT_SESSION_MAX_MINUTES,
            load_config,
        )

        cfg = load_config()
        cap = cfg.get("session_capacity_calls", DEFAULT_SESSION_CAPACITY_CALLS)
        max_min = cfg.get("session_max_minutes", DEFAULT_SESSION_MAX_MINUTES)
        warn_th = cfg.get("session_warn_threshold_minutes", 150)
        idle_th = cfg.get("session_idle_threshold_minutes", 10)
        ttl = cfg.get("verify_cache_ttl_seconds", 600)
        _print_ok(
            "Config knobs",
            f"max={max_min}m warn={warn_th}m idle={idle_th}m capacity={cap} cache_ttl={ttl}s",
        )
        av_hint = auto_verify_interactive_warning_detail(cfg, dict(os.environ))
        if av_hint:
            _print_warn("Verify-First profile", av_hint)
            warnings += 1
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        _print_warn("Config knobs", f"load failed: {e}")
        warnings += 1

    try:
        from default_gates import DEFAULT_GATES

        gate_names = sorted(DEFAULT_GATES.keys())
        _print_ok("Quality gates", f"{len(gate_names)} registered")
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        _print_fail("Quality gates", f"registry load failed: {e}")
        failures += 1

    # Brain config — surfaces "enabled but misconfigured" before the user
    # accumulates local-only decisions/gotchas that should reach Notion.
    # See defect v14b-defect-brain-decisions-empty.
    try:
        from brain_config import is_brain_enabled, validate_brain

        if is_brain_enabled():
            brain_errors = validate_brain()
            if brain_errors:
                first = brain_errors[0]
                more = f" (+{len(brain_errors) - 1} more)" if len(brain_errors) > 1 else ""
                _print_warn(
                    "Brain config",
                    f"enabled but misconfigured: {first}{more} — "
                    f"run `tausik brain init` or set `brain.enabled=false`",
                )
                warnings += 1
            else:
                _print_ok("Brain config", "enabled, all 4 database_ids + token set")
        else:
            _print_ok("Brain config", "disabled (opt-in)")
    except Exception as e:  # noqa: BLE001 — best-effort: non-fatal, keeps the surrounding flow alive
        _print_warn("Brain config", f"could not validate: {e}")
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
    is_trimmed_baseline as _is_trimmed_baseline,
)
