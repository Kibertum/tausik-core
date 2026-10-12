"""argparse builder for `tausik at` subcommands.

RENAR AT (Acceptance Test) artifacts (Sec8A). See docs/en/at-generation-procedure.md
for the isolated-generation procedure this CLI records the result of -- it
does not generate anything itself.
"""

from __future__ import annotations

from typing import Any


def build_at_subparsers(sub: Any) -> None:
    """Attach `at` subparser tree."""
    at_p = sub.add_parser(
        "at",
        help="RENAR AT (Acceptance Test) artifacts (Sec8A) — create/show/list/check-freshness",
    )
    a_sub = at_p.add_subparsers(dest="at_cmd")

    ac = a_sub.add_parser(
        "create",
        help="Record an AT (result of the isolated-generation procedure, see docs/en/at-generation-procedure.md)",
        epilog=(
            "Example: tausik at create at-001 TZ-3.1 'Верно: клиент видит статус заказа "
            "в реальном времени.' 'Открыть заказ, ожидать обновления статуса < 2с' "
            "--as-of 2026-02-01T00:00:00Z --by isolated-session-42"
        ),
    )
    ac.add_argument("slug")
    ac.add_argument("tz_ref")
    ac.add_argument("tz_text", help="Verbatim quote of the contract clause (§8A property 3)")
    ac.add_argument("scenario", help="The acceptance check itself")
    ac.add_argument(
        "--as-of",
        dest="source_as_of",
        required=True,
        help="Which final-TZ moment (completed_at) this AT was derived from",
    )
    ac.add_argument(
        "--by", dest="generated_by", required=True, help="Who recorded this (orchestrator identity)"
    )

    ash = a_sub.add_parser("show", help="Show an AT record")
    ash.add_argument("slug")

    al = a_sub.add_parser("list", help="List AT records, optionally by tz_ref")
    al.add_argument("--tz-ref", dest="tz_ref", default=None)

    ade = a_sub.add_parser("delete", help="Delete an AT record")
    ade.add_argument("slug")

    ase = a_sub.add_parser("search", help="FTS5 search over AT records")
    ase.add_argument("query")
    ase.add_argument("--limit", type=int, default=20)

    acf = a_sub.add_parser(
        "check-freshness",
        help="Which AT records are stale against the CURRENT final-TZ (§8A property 2)",
    )
    acf.add_argument("slug", nargs="?", default=None, help="Check one AT; omit to check all")

    arr = a_sub.add_parser("record-result", help="Record one observed trial of an AT")
    arr.add_argument("slug")
    arr.add_argument("outcome", choices=["red", "green"])
    arr.add_argument("--note", default=None)

    adi = a_sub.add_parser(
        "diagnose",
        help="Route an AT's latest outcome against a caller-supplied tc_outcome (§8A.4/§10.4.3)",
    )
    adi.add_argument("slug")
    adi.add_argument(
        "--tc-outcome",
        dest="tc_outcome",
        required=True,
        choices=["red", "green"],
        help="TC has no first-class artifact yet — supply the observed state explicitly",
    )

    a_sub.add_parser(
        "release-readiness",
        help="Sec8A.4 release gate: ready only when every AT is green and fresh (not QG-4)",
    )
