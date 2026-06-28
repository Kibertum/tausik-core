"""argparse builder for `tausik adapt` subcommands (v16r-adapt).

RENAR ADAPT artifacts (§7). ``category`` (findings) and ``role`` (signatures)
are CLOSED lists — argparse ``choices`` gives a friendly upfront rejection; the
service + DB CHECK are the hard guard.
"""

from __future__ import annotations

from typing import Any

from service_adapts import ADAPT_STATUSES

FINDING_CATEGORY_CHOICES = [
    "contradiction",
    "gap",
    "hidden-assumption",
    "feasibility",
    "regulatory",
    "terminology",
    "scope",
]
SIGNATURE_ROLE_CHOICES = ["client", "architect"]
LINK_TARGET_CHOICES = ["task", "spec"]
# Derived from the service-layer source of truth (no independent literal here).
# Drift is impossible: tests/test_enum_single_source.py pins this to ADAPT_STATUSES.
ADAPT_STATUS_CHOICES = list(ADAPT_STATUSES)


def build_adapt_subparsers(sub: Any) -> None:
    """Attach `adapt` subparser tree."""
    adapt_p = sub.add_parser(
        "adapt",
        help="RENAR ADAPT artifacts — create/interpret/finding/sign/delta/link/show",
    )
    a_sub = adapt_p.add_subparsers(dest="adapt_cmd")

    ac = a_sub.add_parser(
        "create",
        help="Create an ADAPT header",
        epilog="Example: tausik adapt create adapt-001 'Auth ADAPT' --tz-ref TZ-2026-001",
    )
    ac.add_argument("slug")
    ac.add_argument("title")
    ac.add_argument("--tz-ref", dest="tz_ref", required=True, help="Source TZ id (§7.4.3)")

    ai = a_sub.add_parser("interpret", help="Add a forward-interpretation entry (§7.4.3)")
    ai.add_argument("adapt_slug")
    ai.add_argument("--tz-ref", dest="tz_ref", required=True, help="'ТЗ§N.N' (mandatory)")
    ai.add_argument("--citation", required=True, help="Verbatim/paraphrased TZ text (mandatory)")
    ai.add_argument(
        "--interpretation",
        dest="engineering_interpretation",
        required=True,
        help="Engineering interpretation (mandatory)",
    )
    ai.add_argument("--scope-in", dest="scope_in", required=True, help="In-scope boundary")
    ai.add_argument("--scope-out", dest="scope_out", required=True, help="Out-of-scope boundary")
    ai.add_argument(
        "--term-mapping", dest="term_mapping", default=None, help="client→engineer terms"
    )
    ai.add_argument("--scenarios", default=None, help="Built-in/implied scenarios")

    af = a_sub.add_parser("finding", help="Add a backward finding (closed-7 §7)")
    af.add_argument("adapt_slug")
    af.add_argument("category", choices=FINDING_CATEGORY_CHOICES)
    af.add_argument("description")
    af.add_argument("--tz-ref", dest="tz_ref", default=None)
    af.add_argument("--resolution", default=None)

    asg = a_sub.add_parser("sign", help="Record a dual signature (§7.5); architect → ed25519")
    asg.add_argument("adapt_slug")
    asg.add_argument("role", choices=SIGNATURE_ROLE_CHOICES)
    asg.add_argument("--by", dest="signed_by", required=True, help="Signer identity")

    av = a_sub.add_parser("verify", help="Verify the architect ed25519 signature")
    av.add_argument("slug")

    ash = a_sub.add_parser("show", help="Show an ADAPT (body + signatures + links)")
    ash.add_argument("slug")

    al = a_sub.add_parser("list", help="List ADAPTs (optionally by status)")
    al.add_argument("--status", choices=ADAPT_STATUS_CHOICES, default=None)

    ad = a_sub.add_parser("delta", help="Create a delta-ADAPT, supersede the parent (§7.6)")
    ad.add_argument("parent_slug")
    ad.add_argument("new_slug")
    ad.add_argument("title")
    ad.add_argument("--tz-ref", dest="tz_ref", required=True, help="delta-TZ id")

    alk = a_sub.add_parser("link", help="Link an ADAPT to a task/spec")
    alk.add_argument("adapt_slug")
    alk.add_argument("target_type", choices=LINK_TARGET_CHOICES)
    alk.add_argument("target_slug")

    auk = a_sub.add_parser("unlink", help="Remove an ADAPT↔task/spec link")
    auk.add_argument("adapt_slug")
    auk.add_argument("target_type", choices=LINK_TARGET_CHOICES)
    auk.add_argument("target_slug")

    ade = a_sub.add_parser("delete", help="Delete an ADAPT (cascades body/sigs/links)")
    ade.add_argument("slug")

    ase = a_sub.add_parser("search", help="FTS5 search over ADAPTs")
    ase.add_argument("query")
    ase.add_argument("--limit", type=int, default=20)
