"""`tausik publish` parser — the public snapshot (decision #368)."""

from __future__ import annotations

import argparse


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def add_publish(sub: argparse._SubParsersAction) -> None:
    """Add public-snapshot build, audit, and exact-SHA CI commands."""
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
    rc = ps.add_parser(
        "recovery", help="Build a filtered root commit after public-line contamination"
    )
    rc.add_argument("--from", dest="source", default="HEAD", help="Source revision")
    rc.add_argument("--message", default=None, help="Commit message for the recovery object")
    rc.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help="Report only; write no commit"
    )
    ra = ps.add_parser(
        "remote-audit", help="Audit one exact remote ref without credentials or ref mutation"
    )
    ra.add_argument("--remote", required=True, help="Anonymous git URL or local bare remote")
    ra.add_argument("--ref", required=True, help="Exact ref, e.g. refs/heads/main")
    ra.add_argument("--from", dest="source", default="HEAD", help="Local source revision")
    nt = ps.add_parser(
        "notes", help="Refuse a release body that does not link both whats-new pages"
    )
    nt.add_argument("--version", required=True, help="Release version, e.g. 1.10.0")
    nt.add_argument("--body-file", required=True, dest="body_file", help="The release body")
    ps.add_parser(
        "senar-check",
        help="Refuse a release while GitHub Kibertum/SENAR lacks the claimed edition",
    )
    vf = ps.add_parser("verify", help="Snapshot tree equals the filtered tree of --from")
    vf.add_argument("--snapshot", required=True, help="Snapshot commit to check")
    vf.add_argument("--from", dest="source", default="HEAD", help="Source revision (default HEAD)")
    ci = ps.add_parser("ci-check", help="Wait for Tests success on the exact public SHA")
    ci.add_argument("--snapshot", required=True, help="Public snapshot commit to check")
    ci.add_argument("--from", dest="source", default="HEAD", help="Development source revision")
    ci.add_argument("--tag", required=True, help="Existing local release tag")
    ci.add_argument(
        "--timeout", type=_positive_int, default=90 * 60, help="Maximum wait in seconds"
    )
    ci.add_argument(
        "--poll-interval", type=_positive_int, default=15, help="Polling interval in seconds"
    )
