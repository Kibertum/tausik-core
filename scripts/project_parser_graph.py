"""`tausik graph` — the artifact graph gets a way to be called.

WHY THIS FILE EXISTS AT ALL. The graph was built (`service_artifact_graph`,
`backend_crud_graph`, a schema, 234 lines of tests) and then had no surface: no
CLI command, no MCP tool, and — measured a day after it shipped — zero rows in
all three of its tables, in the repository that authored it. A capability that
cannot be invoked is not a capability the framework offers; it is code the
framework carries.

Its own subparser module rather than a section of `project_parser_ops`, which
sits at 461 lines against a 500-line limit. Splitting on a boundary is cheaper
than splitting under one.
"""

from __future__ import annotations

import argparse


def add_graph(sub: argparse._SubParsersAction) -> None:
    """`graph build`, `graph show`, `graph status` — fill it, then ask it."""
    g_p = sub.add_parser(
        "graph",
        help="Artifact graph: what changes with what, and on what evidence",
    )
    g_sub = g_p.add_subparsers(dest="graph_cmd")

    build = g_sub.add_parser(
        "build",
        help="Index the tree and build the edges. Prints what it stored.",
    )
    build.add_argument(
        "--layer",
        choices=("all", "cochange", "declared", "observed"),
        default="all",
        help=(
            "Which layer to build. `cochange` reads git history and works for any "
            "language; `declared` reads what this project already stated in its "
            "tasks; `observed` ingests what a test run actually reached — record "
            "it first with `TAUSIK_OBSERVE_COVERAGE=1 pytest`. Default: all three."
        ),
    )
    build.add_argument(
        "--window",
        type=int,
        default=None,
        help="How many commits the co-change layer reads (default: the service's own).",
    )
    build.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop what is stored first. Use after a rename that moved many files at once.",
    )

    show = g_sub.add_parser(
        "show",
        help="What the graph says about one path, WITH what it can no longer vouch for",
    )
    show.add_argument("path", help="Repo-relative path, e.g. scripts/symbol_index.py")
    show.add_argument(
        "--json",
        action="store_true",
        help="Emit the answer as JSON, including the staleness flags.",
    )

    read = g_sub.add_parser(
        "read",
        help="What to read to change a file — ranked by evidence, cut to a budget",
    )
    read.add_argument("path", help="Repo-relative path, e.g. scripts/symbol_index.py")
    read.add_argument(
        "--affects",
        action="store_true",
        help="Ask the other direction instead: what changing this file may affect.",
    )
    read.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "How many links to list before stating the remainder. The default is "
            "deliberately small: an unranked answer on this repository names up to 42 "
            "files totalling 2.8 MB, which costs more than the grep it replaces."
        ),
    )

    snap = g_sub.add_parser(
        "snapshot",
        help="Store the current relations under a label, compressed",
    )
    snap.add_argument("label", help="Usually a release tag, e.g. v1.9.0")

    diff_p = g_sub.add_parser(
        "diff",
        help="What CHANGED IN THE RELATIONS between two snapshots",
    )
    diff_p.add_argument("before", help="The earlier snapshot's label")
    diff_p.add_argument("after", help="The later snapshot's label, or `now` for the live graph")

    g_sub.add_parser(
        "status",
        help="How much is stored, how much is stale, and which roots were indexed",
    )
