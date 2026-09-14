"""TAUSIK CLI handler for `tausik audit` — the command and its subcommands.

`cmd_audit` moved here from project_cli_ops.py: the subcommands already
lived in this file while the command they belong to did not, which split one
domain across two modules (filesize-rejoin-cap-deformed-wrappers,
decision #199). Renamed off `_audit_extra` — nothing here is extra.
"""

from __future__ import annotations

import json as _json
import os as _os
from typing import Any

from project_service import ProjectService


def cmd_audit_vendors(args: Any) -> None:
    """`tausik audit vendors [--json]` — classify vendor repos for cleanup."""
    from audit_vendor_usage import audit_vendor_usage
    from tausik_utils import tausik_config_path

    project_dir = _os.getcwd()
    vendor_dir = _os.path.join(project_dir, ".tausik", "vendor")
    config_path = tausik_config_path(project_dir)
    result = audit_vendor_usage(vendor_dir, config_path)

    if getattr(args, "as_json", False):
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Vendor audit (dir: {vendor_dir}):")
    print(f"  installed:        {len(result['installed'])}")
    print(f"  vendored_unused:  {len(result['vendored_unused'])} (cleanup candidates)")
    print(f"  unknown (errors): {len(result['unknown'])}")
    if result["vendored_unused"]:
        print("\n  Cleanup candidates (not in installed_skills):")
        for v in result["vendored_unused"]:
            skills = ", ".join(v["skills"]) or "(no skills)"
            print(f"    - {v['name']}  skills=[{skills}]  cloned_at={v['cloned_at_iso'] or '?'}")
        print(
            "\n  To remove: tausik skill repo remove <name>  "
            "(after manual review — this audit never deletes)"
        )


def cmd_audit_research(args: Any) -> None:
    """`tausik audit research [--min-age-days N] [--json]` — surface stale unreferenced research files."""
    from audit_research_dump import audit_research_dump

    project_dir = _os.getcwd()
    min_age = int(getattr(args, "min_age_days", 30) or 30)
    result = audit_research_dump(project_dir, min_age_days=min_age)

    if getattr(args, "as_json", False):
        print(_json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Research dump audit (min_age_days={min_age}):")
    print(f"  scanned:            {result['scanned']}")
    print(f"  candidates:         {len(result['candidates'])}  (stale + unreferenced)")
    print(f"  skipped recent:     {result['skipped_recent']}")
    print(f"  skipped referenced: {result['skipped_referenced']}")
    if result["candidates"]:
        print("\n  Cleanup candidates (move to docs/_archive/research/):")
        for c in result["candidates"]:
            print(f"    - {c['path']}  ({c['age_days']} days old)")
        print("\n  Audit is read-only — review manually before moving.")


def cmd_audit_evidence(svc: ProjectService, args: Any) -> None:
    """`tausik audit evidence [--json] [--no-git]` — do closure citations still resolve?

    Read-only and NON-BLOCKING by construction: it neither fails nor returns a
    non-zero status on findings. Renaming a test is legitimate; the point is
    that the decay is visible, not that refactoring is punished.
    """
    from audit_closure_evidence import (
        ILLUSTRATIVE,
        NEVER_EXISTED,
        ROTTED,
        UNKNOWN_HISTORY,
        audit_closure_evidence,
        default_probe,
    )

    # --no-git is not a speed switch: without history the audit CANNOT tell a
    # rename from a path that never existed, so it withholds the verdict rather
    # than picking the likelier one.
    probe = None if getattr(args, "no_git", False) else default_probe
    report = audit_closure_evidence(_os.getcwd(), svc.task_list(status="done"), probe=probe)

    if getattr(args, "as_json", False):
        print(_json.dumps(report, ensure_ascii=False, indent=2))
        return

    print("Closure-evidence audit (read-only, never blocks):")
    print(f"  closed tasks scanned:   {report['tasks_scanned']}")
    print(f"  tasks citing a test:    {report['tasks_with_refs']}")
    print(f"  citations / unique:     {report['refs_total']} / {report['refs_unique']}")
    print(f"  resolve today:          {report['resolved_unique']}")
    counts = report["counts"]
    print(f"  ROTTED (was in git history, gone now):  {counts[ROTTED]}")
    print(f"  NEVER_EXISTED (git never had it):       {counts[NEVER_EXISTED]}")
    print(f"  UNKNOWN_HISTORY (git could not answer): {counts[UNKNOWN_HISTORY]}")
    # Printed with the others, not folded away: the three counts above are only
    # trustworthy while a reader can see how many refs were set aside and why.
    print(f"  ILLUSTRATIVE (an example quoted, not a citation): {counts[ILLUSTRATIVE]}")
    for verdict, blurb in (
        (
            ROTTED,
            "renamed or deleted AFTER closure — the reference decayed, coverage may be intact",
        ),
        (NEVER_EXISTED, "never in git: a synthetic path quoted on purpose, or invented at closure"),
        (UNKNOWN_HISTORY, "git refused to answer — verdict withheld, not guessed"),
        (
            ILLUSTRATIVE,
            "a conventional example name, quoted by a task whose subject IS the citation form",
        ),
    ):
        rows = [f for f in report["findings"] if f["verdict"] == verdict]
        if not rows:
            continue
        print(f"\n  {verdict} ({blurb}):")
        for f in rows:
            near = f["successor_candidate"]
            hint = f"  ~ CANDIDATE, not a verdict: {near}" if near else ""
            amb = "  [ambiguous file name]" if f["ambiguous"] else ""
            why = f.get("illustrative_reason")
            reason = f"  <- {why}" if why else ""
            print(f"    - {f['ref']}{amb}{hint}{reason}")
            print(f"        cited by: {', '.join(f['tasks'])}")
    print("\n  A successor is a suggestion from name similarity. Confirm it by reading the")
    print("  test before treating it as the same check under a new name.")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)


def cmd_audit(svc: ProjectService, args: Any) -> None:
    c = getattr(args, "audit_cmd", None)
    if c == "mark":
        print(svc.audit_mark())
    elif c == "vendors":
        cmd_audit_vendors(args)
    elif c == "research":
        cmd_audit_research(args)
    elif c == "evidence":
        cmd_audit_evidence(svc, args)
    else:
        # Default and "check" -- same behavior
        warning = svc.audit_check()
        if warning:
            print(f"WARNING: {warning}")
        else:
            print("Audit is up to date.")
