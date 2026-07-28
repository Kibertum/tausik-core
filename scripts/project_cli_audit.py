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
    else:
        # Default and "check" -- same behavior
        warning = svc.audit_check()
        if warning:
            print(f"WARNING: {warning}")
        else:
            print("Audit is up to date.")
