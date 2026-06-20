"""argparse builder for `tausik spec` subcommands (v16r-spec-types).

RENAR SPEC artifacts. ``type`` is a CLOSED list of 9 — argparse ``choices``
gives a friendly upfront rejection; the service + DB CHECK are the hard guard.
"""

from __future__ import annotations

from typing import Any

from service_specs import SPEC_STATUSES, SPEC_TYPES

# Derived from the service-layer source of truth (no independent literal here).
# Drift is impossible: tests/test_enum_single_source.py pins these to SPEC_TYPES.
SPEC_TYPE_CHOICES = list(SPEC_TYPES)
SPEC_RELATION_CHOICES = ["implements", "constrained_by"]
SPEC_STATUS_CHOICES = list(SPEC_STATUSES)


def build_spec_subparsers(sub: Any) -> None:
    """Attach `spec` subparser tree."""
    spec_p = sub.add_parser(
        "spec",
        help="RENAR SPEC artifacts — add/list/show/update/delete/link/search",
    )
    spec_sub = spec_p.add_subparsers(dest="spec_cmd")

    sl = spec_sub.add_parser("list", help="List SPECs (optionally by type)")
    sl.add_argument("--type", choices=SPEC_TYPE_CHOICES, default=None)

    ssh = spec_sub.add_parser("show", help="Show a SPEC + its linked tasks")
    ssh.add_argument("slug")

    sa = spec_sub.add_parser(
        "add",
        help="Create a SPEC",
        epilog="Example: tausik spec add auth-arch ARCH 'Auth architecture' "
        "--version v1 --content-ref docs/specs/auth.md",
    )
    sa.add_argument("slug")
    sa.add_argument("type", choices=SPEC_TYPE_CHOICES, help="Closed list of 9 RENAR types")
    sa.add_argument("title")
    sa.add_argument("--version", required=True, help="SPEC version (e.g. v1, 1.0-draft)")
    sa.add_argument(
        "--content-ref", dest="content_ref", default=None, help="Pointer to the spec doc (path/URL)"
    )
    sa.add_argument("--status", choices=SPEC_STATUS_CHOICES, default="draft")

    su = spec_sub.add_parser("update", help="Patch mutable SPEC fields")
    su.add_argument("slug")
    su.add_argument("--title", default=None)
    su.add_argument("--version", default=None)
    su.add_argument("--content-ref", dest="content_ref", default=None)
    su.add_argument("--status", choices=SPEC_STATUS_CHOICES, default=None)

    sd = spec_sub.add_parser("delete", help="Delete a SPEC (cascades task links)")
    sd.add_argument("slug")

    sk = spec_sub.add_parser("link", help="Link a task to a SPEC")
    sk.add_argument("task_slug")
    sk.add_argument("spec_slug")
    sk.add_argument("--relation", choices=SPEC_RELATION_CHOICES, default="implements")

    suk = spec_sub.add_parser("unlink", help="Remove a task↔SPEC link")
    suk.add_argument("task_slug")
    suk.add_argument("spec_slug")
    suk.add_argument("--relation", choices=SPEC_RELATION_CHOICES, default="implements")

    sse = spec_sub.add_parser("search", help="FTS5 search over SPECs")
    sse.add_argument("query")
    sse.add_argument("--limit", type=int, default=20)
