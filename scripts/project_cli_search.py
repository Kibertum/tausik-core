"""Searching the project's own record, and the index that makes it fast.

Small on purpose. `search` and `fts` are two commands over one store, and the
family's convention is a module named after the command rather than a drawer
named after what would not fit elsewhere.
"""

from __future__ import annotations

from typing import Any
from project_service import ProjectService


def cmd_search(svc: ProjectService, args: Any) -> None:
    from render_status import SEARCH_LIMIT, search_lines

    limit = getattr(args, "limit", SEARCH_LIMIT)
    print("\n".join(search_lines(svc, args.query, args.scope, limit)))


def cmd_fts(svc: ProjectService, args: Any) -> None:
    c = getattr(args, "fts_cmd", None)
    if c == "optimize":
        results = svc.fts_optimize()
        for table, status in results.items():
            print(f"  {table}: {status}")
        print("FTS5 optimization complete.")
    else:
        print("Usage: tausik fts optimize")


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
