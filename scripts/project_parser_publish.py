"""`tausik publish` parser — the public snapshot (decision #368)."""

from __future__ import annotations

import argparse


def add_publish(sub: argparse._SubParsersAction) -> None:
    """`tausik publish snapshot|verify` — the public snapshot (decision #368)."""
    pp = sub.add_parser(
        "publish",
        help="Build / verify the public release snapshot (filtered tree, decision #368)",
    )
    ps = pp.add_subparsers(dest="publish_cmd")
    sn = ps.add_parser("snapshot", help="Commit the filtered tree of --from on top of --parent")
    sn.add_argument("--from", dest="source", default="HEAD", help="Source revision (default HEAD)")
    sn.add_argument("--parent", required=True, help="The public head the snapshot goes on top of")
    sn.add_argument("--message", default=None, help="Commit message for the snapshot")
    sn.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help="Report only; write no commit"
    )
    vf = ps.add_parser("verify", help="Snapshot tree equals the filtered tree of --from")
    vf.add_argument("--snapshot", required=True, help="Snapshot commit to check")
    vf.add_argument("--from", dest="source", default="HEAD", help="Source revision (default HEAD)")
