"""Argparse subparser for `tausik review` (SENAR Rule 10.15).

Moved out of project_parser_ops.py when the L3 model flags (github#157) took
that file past the 500-line filesize gate.
"""

from __future__ import annotations

import argparse


def add_review(sub: argparse._SubParsersAction) -> None:
    """SENAR Rule 10.15: track L1/L2/L3 review runs + ADR metric."""
    rev_p = sub.add_parser("review", help="Track L1/L2/L3 review runs (SENAR Rule 10.15)")
    rev_sub = rev_p.add_subparsers(dest="review_cmd")

    rec = rev_sub.add_parser("record", help="Record a review run")
    rec.add_argument("--task", required=True, help="Task slug being reviewed")
    rec.add_argument(
        "--type",
        dest="run_type",
        required=True,
        choices=["L1", "L2", "L3"],
        help="L1=author, L2=peer, L3=adversarial/external",
    )
    rec.add_argument("--critical", type=int, default=0, help="Number of critical findings")
    rec.add_argument("--warnings", type=int, default=0, help="Number of warnings")
    rec.add_argument("--high", type=int, default=0, help="Number of HIGH findings")
    rec.add_argument("--notes", default=None, help="Free-form notes (links, summary)")
    rec.add_argument(
        "--reason",
        default=None,
        help="Why the findings are CRITICAL; required when --critical > 0 (docs/en/severity-scale.md)",
    )
    rec.add_argument(
        "--reviewer-model",
        default=None,
        help="L3: the model that ran the review; required, refused when it is the author's family",
    )
    rec.add_argument(
        "--author-model",
        default=None,
        help="L3: the model that wrote the code; default: the model of this session",
    )
    rec.add_argument(
        "--reviewer-context",
        choices=["author", "fresh", "different-model"],
        default=None,
        help="Actual context used; L3 requires different-model",
    )
    rec.add_argument(
        "--reviewer-invocations",
        type=int,
        default=None,
        help="Actual reviewer calls (route default when omitted)",
    )
    rec.add_argument("--deep", action="store_true", help="Record an explicitly forced deep audit")

    route = rev_sub.add_parser("route", help="Preview the canonical residual-assurance route")
    route.add_argument("--task", required=True, help="Task slug to route")
    route.add_argument("--deep", action="store_true", help="Force the explicit L3-deep audit route")
    route.add_argument("--json", action="store_true", help="Output JSON")

    ls = rev_sub.add_parser("list", help="List recent reviews")
    ls.add_argument("--task", default=None, help="Filter by task slug")
    ls.add_argument("--type", dest="run_type", default=None, choices=["L1", "L2", "L3"])
    ls.add_argument("--limit", type=int, default=20)
    ls.add_argument("--json", action="store_true", help="Output as JSON")

    rev_sub.add_parser("metrics", help="Show ADR metric")
