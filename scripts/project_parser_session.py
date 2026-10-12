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
    ss = sess_sub.add_parser("start")
    _host = "The host's own session id (Claude Code hook payload `session_id`): the TAUSIK session IS that host session (decision #376)."
    ss.add_argument("--host-id", default=None, help=_host)
    se = sess_sub.add_parser("end")
    se.add_argument("--summary", default=None)
    se.add_argument("--host-id", default=None, help=_host + " Ends exactly that session.")
    sess_sub.add_parser("current")
    ssl = sess_sub.add_parser("list")
    ssl.add_argument("--limit", type=int, default=10)
    sh = sess_sub.add_parser("handoff")
    sh.add_argument(
        "json_data",
        nargs="?",
        default=None,
        help="Authored fields (next_steps, warnings, in_progress[].state) as JSON; "
        "without it the handoff is generated from the journal",
    )
    sh.add_argument("--host-id", default=None, help="Write into this host session's row")
    slh = sess_sub.add_parser("last-handoff")
    slh.add_argument(
        "--session",
        type=int,
        default=None,
        help="Read the handoff of session N instead of the live one",
    )
    sext = sess_sub.add_parser("extend", help="Extend session duration by N minutes")
    sext.add_argument("--minutes", type=int, default=60, help="Minutes to extend (default: 60)")
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
