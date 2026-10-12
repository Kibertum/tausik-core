"""argparse builder for `tausik actz` subcommands.

RENAR ACTZ artifacts (Sec5A). ``role`` (signatures), ``status`` and
``target_type`` (links) are CLOSED lists -- argparse ``choices`` gives a
friendly upfront rejection; the service + DB CHECK are the hard guard.
"""

from __future__ import annotations

from typing import Any

from service_actz import ACTZ_STATUSES, SIGNATURE_ROLES

SIGNATURE_ROLE_CHOICES = list(SIGNATURE_ROLES)
LINK_TARGET_CHOICES = ["task", "spec"]
ACTZ_STATUS_CHOICES = list(ACTZ_STATUSES)


def build_actz_subparsers(sub: Any) -> None:
    """Attach `actz` subparser tree."""
    actz_p = sub.add_parser(
        "actz",
        help="RENAR ACTZ artifacts (Sec5A) — create/point/sign/verify/delta/link/show",
    )
    z_sub = actz_p.add_subparsers(dest="actz_cmd")

    zc = z_sub.add_parser(
        "create",
        help="Create an ACTZ header",
        epilog="Example: tausik actz create actz-001 'Сроки приёмки' --tz-ref TZ-2026-001",
    )
    zc.add_argument("slug")
    zc.add_argument("title")
    zc.add_argument("--tz-ref", dest="tz_ref", required=True, help="Source TZ id (Sec5A)")

    zp = z_sub.add_parser("point", help="Add a numbered point to a draft ACTZ")
    zp.add_argument("actz_slug")
    zp.add_argument("point_no", type=int)
    zp.add_argument("--tz-ref", dest="tz_ref", required=True, help="Which ТЗ clause this clarifies")
    zp.add_argument("text")

    zsg = z_sub.add_parser(
        "sign",
        help="Record a signature (Sec5.5.3) — architect: ed25519 over the body; "
        "client: signed_by+signed_at only",
    )
    zsg.add_argument("actz_slug")
    zsg.add_argument("role", choices=SIGNATURE_ROLE_CHOICES)
    zsg.add_argument("--by", dest="signed_by", required=True, help="Signer identity")

    zv = z_sub.add_parser("verify", help="Verify the architect ed25519 signature")
    zv.add_argument("slug")

    zsh = z_sub.add_parser("show", help="Show an ACTZ (points + signatures + links)")
    zsh.add_argument("slug")

    zl = z_sub.add_parser("list", help="List ACTZ headers (optionally by status)")
    zl.add_argument("--status", choices=ACTZ_STATUS_CHOICES, default=None)

    zd = z_sub.add_parser("delta", help="Create a delta-ACTZ, supersede the parent")
    zd.add_argument("parent_slug")
    zd.add_argument("new_slug")
    zd.add_argument("title")
    zd.add_argument("--tz-ref", dest="tz_ref", required=True, help="delta-TZ id")
    zd.add_argument(
        "--supersession-rationale",
        dest="supersession_rationale",
        required=True,
        help="Why the parent is superseded (mandatory)",
    )

    zlk = z_sub.add_parser("link", help="Link an ACTZ to a task/spec")
    zlk.add_argument("actz_slug")
    zlk.add_argument("target_type", choices=LINK_TARGET_CHOICES)
    zlk.add_argument("target_slug")

    zuk = z_sub.add_parser("unlink", help="Remove an ACTZ<->task/spec link")
    zuk.add_argument("actz_slug")
    zuk.add_argument("target_type", choices=LINK_TARGET_CHOICES)
    zuk.add_argument("target_slug")

    zde = z_sub.add_parser("delete", help="Delete an ACTZ (cascades points/sigs/links)")
    zde.add_argument("slug")

    zse = z_sub.add_parser("search", help="FTS5 search over ACTZ headers")
    zse.add_argument("query")
    zse.add_argument("--limit", type=int, default=20)

    zdi = z_sub.add_parser(
        "decided-in", help="Record: an ADAPT finding was decided-in a SIGNED ACTZ point"
    )
    zdi.add_argument("adapt_slug")
    zdi.add_argument("finding_id", type=int)
    zdi.add_argument("actz_slug")
    zdi.add_argument("actz_point_no", type=int)
    zdi.add_argument("--by", dest="linked_by", required=True, help="Who recorded this edge")

    zdr = z_sub.add_parser("decided-in-remove", help="Remove a decided-in edge")
    zdr.add_argument("adapt_slug")
    zdr.add_argument("finding_id", type=int)
    zdr.add_argument("actz_slug")
    zdr.add_argument("actz_point_no", type=int)

    zft = z_sub.add_parser(
        "final-tz",
        help="The derived acceptance reference (§5A.4): per ТЗ clause, the latest "
        "signed ACTZ point, naming what it overrode",
    )
    zft.add_argument(
        "--as-of", dest="as_of", default=None, help="ISO-8601: show it at this past moment"
    )

    z_sub.add_parser(
        "orphans",
        help="Signed ACTZ points no ADAPT reflects — an obligation outside requirements (§5A.4, fatal)",
    )
