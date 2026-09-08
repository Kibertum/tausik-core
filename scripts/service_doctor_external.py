"""The optional doctor checks: each fires only where its subject is installed.

Lifted out of `project_cli_doctor` because that file is held at 490 lines with
headroom on purpose, and because the six blocks were the same shape six times
over — import a checker, print its rows, count them, and refuse to let a bug in
one of them take the whole command down.

Every check yields the same ``(severity, label, detail)`` rows. Nothing here
knows what any of them mean; the meaning lives in the check.
"""

from __future__ import annotations

from typing import Any

def run_optional_checks(
    project_dir: str,
    svc: Any,
    print_ok: Any,
    print_warn: Any,
    print_fail: Any,
) -> tuple[int, int]:
    """Run every optional check, print it, and return (failures, warnings).

    The printers are passed in rather than imported: they live in the CLI handler
    that owns the output format, and importing them back would make these two
    modules a cycle.
    """
    failures = warnings = 0

    def drain(rows: Any) -> None:
        """Print a check's rows and fold them into the running counts.

        Six copies of this dispatch used to sit inline. Six copies of a counter
        is six chances for one of them to quietly stop counting.
        """
        nonlocal failures, warnings
        for severity, label, detail in rows:
            if severity == "fail":
                print_fail(label, detail)
                failures += 1
            elif severity == "warn":
                print_warn(label, detail)
                warnings += 1
            else:
                print_ok(label, detail)

    # Kilo MCP config — only fires for Kilo installs (.kilo/.kilocode present).
    # Silent for non-Kilo projects so it adds no noise to the common path.
    try:
        from service_doctor_kilo import check_kilo_config

        drain(check_kilo_config(project_dir))
    except Exception as e:  # noqa: BLE001 — best-effort: a Kilo-check bug must not crash doctor
        print_warn("Kilo MCP config", f"could not validate: {e}")
        warnings += 1

    # OpenCode config + QG-0 plugin — only fires for OpenCode installs (.opencode/).
    # Catches the three failures that broke a user's host: a `tools` object
    # (ConfigInvalidError), a missing/singular-dir plugin (enforcement silently off),
    # and `instructions` pointing nowhere (rules silently never load).
    try:
        from service_doctor_opencode import check_opencode_config

        drain(check_opencode_config(project_dir))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("OpenCode config", f"could not validate: {e}")
        warnings += 1

    # caveman interop — silent unless a user-installed caveman is present alongside
    # TAUSIK's own output_mode. Surfaces coexistence + the .claude/settings.json overlap.
    try:
        from service_doctor_caveman import check_caveman_interop

        drain(check_caveman_interop(project_dir))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("caveman interop", f"could not validate: {e}")
        warnings += 1

    # Backlog hygiene — open tasks no epic can reach. The release boundary is a
    # mechanical "everything in epic X", so such a task is silently absent from
    # every scope count. Warn, never fail: a standalone task is legitimate.
    # Deferred AC — a criterion parked at closure inside work still in flight.
    # Scoped to open epics so the signal stays clearable; a warning that names
    # long-shipped history is one a reader learns to skip.
    try:
        from service_doctor_backlog import check_backlog_hygiene, check_deferred_acs

        for check in (check_backlog_hygiene, check_deferred_acs):
            drain(check(svc))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("Backlog hygiene", f"could not validate: {e}")
        warnings += 1

    # Commit hooks — alive, off by choice, or DEAD and silent. The third state
    # is the one this exists for: a `core.hooksPath` pointing nowhere makes git
    # run nothing and report nothing, so `memory_route` (blocking), mypy and the
    # RAG reindex skip every commit while `gates status` still prints them [ON].
    try:
        from service_doctor_hooks import check_commit_hooks

        drain(check_commit_hooks(project_dir))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("Commit hooks", f"could not validate: {e}")
        warnings += 1

    # Enforcement coverage — does each host's rules file still match the mechanism
    # deployed for it? The gap (cursor, kilo) is declared and is NOT a warning.
    try:
        from service_doctor_enforcement import check_enforcement_coverage

        drain(check_enforcement_coverage(project_dir))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("Enforcement coverage", f"could not validate: {e}")
        warnings += 1


    # Session model — did any source name the model running this session? The
    # pinning chain (RENAR 10.13) is dead without it, and a NULL column looks
    # exactly like a feature nobody wanted.
    try:
        from service_doctor_model_source import check_session_model

        drain(check_session_model(svc))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("Session model", f"could not validate: {e}")
        warnings += 1

    # Agent route — MCP versus the shell, reported as a number rather than
    # judged. The rules call MCP-first a hard constraint and nothing counted it.
    try:
        from service_doctor_route import check_agent_route

        drain(check_agent_route(svc))
    except Exception as e:  # noqa: BLE001 — best-effort: a check bug must not crash doctor
        print_warn("Agent route", f"could not validate: {e}")
        warnings += 1

    return failures, warnings
