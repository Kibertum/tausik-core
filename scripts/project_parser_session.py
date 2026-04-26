"""argparse builder for `tausik session` subcommands.

Extracted from project_parser.py to keep the main parser under the
400-line filesize gate.
"""

from __future__ import annotations

from typing import Any


def build_session_subparsers(sub: Any) -> None:
    """Attach `session` subparser tree to the top-level subparser."""
    sess_p = sub.add_parser("session", help="Session management")
    sess_sub = sess_p.add_subparsers(dest="session_cmd")
    sess_sub.add_parser("start")
    se = sess_sub.add_parser("end")
    se.add_argument("--summary", default=None)
    sess_sub.add_parser("current")
    ssl = sess_sub.add_parser("list")
    ssl.add_argument("--limit", type=int, default=10)
    sh = sess_sub.add_parser("handoff")
    sh.add_argument("json_data", help="Handoff JSON string")
    sess_sub.add_parser("last-handoff")
    sext = sess_sub.add_parser("extend", help="Extend session duration by N minutes")
    sext.add_argument(
        "--minutes", type=int, default=60, help="Minutes to extend (default: 60)"
    )
    srec = sess_sub.add_parser(
        "recompute",
        help="Compare wall-clock vs active (gap-based) minutes for past sessions",
    )
    srec.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="Idle gap threshold in minutes (default: from config or 10)",
    )
    srec.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Show only the last N sessions (default: all)",
    )
    srec.add_argument("--json", action="store_true", help="Emit JSON instead of table")
