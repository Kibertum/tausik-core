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
        except Exception:
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
        skills = [
            d
            for d in os.listdir(skills_dir)
            if os.path.isdir(os.path.join(skills_dir, d))
        ]
        critical = {
            "start",
            "end",
            "task",
            "plan",
            "review",
            "brain",
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
            f"{md_drift} static section(s) differ — run: tausik update-claudemd --dry-run",
        )
        warnings += 1
    else:
        _print_ok(
            "CLAUDE.md drift", "none — static sections match bootstrap_templates"
        )

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
    except Exception as e:
        _print_warn("Config knobs", f"load failed: {e}")
        warnings += 1

    try:
        from default_gates import DEFAULT_GATES

        gate_names = sorted(DEFAULT_GATES.keys())
        _print_ok("Quality gates", f"{len(gate_names)} registered")
    except Exception as e:
        _print_fail("Quality gates", f"registry load failed: {e}")
        failures += 1

    try:
        active = svc.session_active_minutes()
        wall = svc.session_wall_minutes()
        if wall > 0:
            _print_ok("Session", f"{active}m active / {wall}m wall")
        else:
            _print_ok("Session", "no active session")
    except Exception as e:
        _print_warn("Session", f"could not read: {e}")
        warnings += 1

    print("=" * 40)
    if failures:
        print(
            f"{RED} {failures} FAIL, {warnings} WARN — fix above before running tasks."
        )
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


def _check_claudemd_drift(project_dir: str) -> int | None:
    """Compare static (non-DYNAMIC) sections of CLAUDE.md against the live
    bootstrap_templates.build_full_body output.

    Returns the number of sections that differ, or None when comparison is
    not possible (file missing, project name unknown, template import failed).
    The CLAUDE.md head + DYNAMIC block + user-customised tail are ignored —
    we hash the static body sections individually so cosmetic edits
    (e.g. an extra newline at the end of file) don't trigger a false drift.
    """
    md_path = os.path.join(project_dir, "CLAUDE.md")
    if not os.path.isfile(md_path):
        return None
    try:
        sys.path.insert(0, os.path.join(project_dir, ".tausik-lib", "bootstrap"))
        sys.path.insert(0, os.path.join(project_dir, "bootstrap"))
        import importlib  # noqa: PLC0415

        try:
            bt = importlib.import_module("bootstrap_templates")
            build_full_body = bt.build_full_body
        except Exception:
            return None
    except Exception:
        return None
    try:
        from project_config import load_config, resolve_context_tier  # noqa: PLC0415

        cfg = load_config() or {}
        project_name = cfg.get("project_name") or os.path.basename(project_dir)
        stacks = cfg.get("stacks") or []
        tier = resolve_context_tier(cfg)
        expected = build_full_body(
            project_name,
            stacks,
            "an AI agent (Claude Code)",
            ".claude",
            ide="claude",
            context_tier=tier,
        )
    except Exception:
        return None
    try:
        with open(md_path, encoding="utf-8") as f:
            current = f.read()
    except OSError:
        return None
    # Compare per H2 block (## …). Sections present in expected but altered
    # or missing in current count as drift. New sections in current that
    # don't exist in expected are not flagged — those are user customisations.
    import re as _re

    def _split(text: str) -> dict[str, str]:
        sections: dict[str, str] = {}
        # Skip everything before the first H2 (header / project metadata
        # which is rendered uniquely per file).
        parts = _re.split(r"^(## [^\n]+)$", text, flags=_re.MULTILINE)
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            lower_h = heading.lower()
            # Drop sections whose heading is itself dynamic per project.
            if lower_h.startswith("## project:"):
                continue
            if "DYNAMIC:START" in body or lower_h.startswith("## current state"):
                continue
            sections[heading] = body.strip()
        return sections

    expected_sections = _split(expected)
    current_sections = _split(current)
    differ = 0
    for heading, body in expected_sections.items():
        if current_sections.get(heading, "").strip() != body.strip():
            differ += 1
    return differ


def _check_scripts_drift(project_dir: str) -> int | None:
    src = os.path.join(project_dir, "scripts")
    dst = os.path.join(project_dir, ".claude", "scripts")
    if not os.path.isdir(src) or not os.path.isdir(dst):
        return None
    differ = 0
    for name in os.listdir(src):
        if not name.endswith(".py"):
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if not os.path.isfile(d):
            differ += 1
            continue
        try:
            with open(s, "rb") as f1, open(d, "rb") as f2:
                if f1.read().replace(b"\r\n", b"\n") != f2.read().replace(
                    b"\r\n", b"\n"
                ):
                    differ += 1
        except OSError:
            pass
    return differ
