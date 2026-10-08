"""Hierarchy-level pooled verification and atomic closure (Track A, 1.11.3).

`verify --story <slug>` / `verify --epic <slug>` resolve the exact non-done
descendant set, refuse anything but a real cohort, demand review-ready
members (plan complete, AC evidence logged), and delegate to
`verify_cohort.run_cohort_verify`. `story done --verify-handle` /
`epic done --verify-handle` then close every member plus the parent in ONE
transaction on that exact receipt — membership drift, member edits,
reopenings or blocks after verify make the handle stale, and a partial
closure rolls back whole.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import verify_cohort as vc


def resolve_descendants(be: Any, parent_slug: str, kind: str) -> list[str]:
    """The exact non-done task set under a story or epic, sorted."""
    if kind == "story":
        rows = be._q(
            "SELECT slug FROM tasks WHERE story_id="
            "(SELECT id FROM stories WHERE slug=?) AND status != 'done' "
            "ORDER BY slug",
            (parent_slug,),
        )
    else:
        rows = be._q(
            "SELECT slug FROM tasks WHERE story_id IN "
            "(SELECT id FROM stories WHERE epic_id=(SELECT id FROM epics WHERE slug=?)) "
            "AND status != 'done' ORDER BY slug",
            (parent_slug,),
        )
    return [r["slug"] for r in rows]


def review_ready_reasons(be: Any, slugs: list[str]) -> list[str]:
    """AC-2: every member plan-complete with numbered AC evidence logged."""
    reasons: list[str] = []
    for slug in slugs:
        row = be._q1("SELECT plan, acceptance_criteria FROM tasks WHERE slug=?", (slug,))
        if not row:
            reasons.append(f"{slug}: task missing")
            continue
        try:
            steps = json.loads(row["plan"]) if row["plan"] else []
        except (TypeError, ValueError):
            steps = []
        if steps and not all(s.get("done") for s in steps):
            reasons.append(f"{slug}: plan incomplete")
        if not (row["acceptance_criteria"] or "").strip():
            reasons.append(f"{slug}: no acceptance criteria")
        log_row = be._q1(
            "SELECT 1 AS ok FROM task_logs WHERE task_slug=? AND message LIKE '%AC-%' LIMIT 1",
            (slug,),
        )
        if not log_row:
            reasons.append(f"{slug}: no numbered AC evidence logged")
    return reasons


def hierarchy_summary(out: dict[str, Any]) -> str:
    """The one rendering of a hierarchy pooled run — CLI and MCP share it."""
    if out.get("refused"):
        return str(out["refused"])
    h = out.get("hierarchy", {})
    lines = [
        f"Cohort {'green' if out['passed'] else 'RED'} for "
        f"{h.get('kind', '?')} '{h.get('parent', '?')}': "
        f"identity {out['identity'][:16]}, {len(out['members'])} member(s), "
        f"union scope {len(out['union_scope'])} file(s) run ONCE. "
        f"Denominator: members={len(out['members'])}, "
        f"test_files={len(out['union_scope'])}."
    ]
    lines.extend(out.get("prepared") or [])
    lines.extend(out.get("widened") or [])
    lines.extend(vc.pooled_handle_lines(out.get("report"), h.get("parent"), h.get("kind")))
    return "\n".join(lines)


def run_hierarchy_verify(
    svc: Any,
    parent_slug: str,
    kind: str,
    scope: str = "manual",
    prepare: bool = True,
    _runner=None,
) -> dict[str, Any]:
    """Resolve → refuse degenerate pools → demand review-ready → cohort run."""
    if kind not in ("story", "epic"):
        return {"refused": f"kind must be story or epic, got {kind}"}
    members = resolve_descendants(svc.be, parent_slug, kind)
    if not members:
        return {
            "refused": f"{kind} '{parent_slug}' has no non-done tasks — nothing "
            f"to pool; an empty cohort is not a cohort"
        }
    if len(members) < 2:
        return {
            "refused": f"only one non-done task under '{parent_slug}' — that is "
            f"an ordinary `verify --task {members[0]}`, not a cohort"
        }
    not_ready = review_ready_reasons(svc.be, members)
    if not_ready:
        return {"refused": "cohort not review-ready: " + "; ".join(not_ready)}
    out = vc.run_cohort_verify(svc, members, scope=scope, prepare=prepare, _runner=_runner)
    out["hierarchy"] = {"kind": kind, "parent": parent_slug}
    return out


def hierarchy_done_with_handle(
    svc: Any,
    parent_slug: str,
    kind: str,
    handle: str,
) -> str:
    """Atomic close of the whole hierarchy on one exact cohort receipt.

    Redemption reuses the single-task lane's own machinery (`verify_handle`):
    shape-validated parse, constant-time nonce compare, single-use spend with
    the predicate inside the UPDATE, and the same TTL. The stale check (AC-4)
    recomputes identity over the CURRENT members with the SAME root source the
    mint used (`root_from_service`) — a `None` root here once made every
    production receipt permanently stale while the tests, fabricating receipts
    with the same `None`, stayed green.
    """
    import hmac

    from project_root import root_from_service
    from verify_handle import load_run_for_handle, parse_handle, parse_iso, redeem

    be = svc.be
    parsed = parse_handle(handle)
    if parsed is None:
        return f"REFUSED: unknown or malformed handle {handle}"
    run_id, nonce = parsed
    row = load_run_for_handle(be._conn, run_id)
    if row is None:
        return (
            f"REFUSED: no verify run #{run_id} in this project's database — "
            "the handle was minted elsewhere or the row is gone; re-run pooled verify."
        )
    stored = row.get("handle_nonce")
    if not stored or not hmac.compare_digest(str(stored), nonce):
        return (
            f"REFUSED: nonce does not match verify run #{run_id}; handles are "
            "single-use and replaced by each new verify — present the one the "
            "LAST pooled verify printed."
        )
    if row.get("handle_redeemed_at"):
        return "REFUSED: handle already redeemed (single use)"
    # SPEC §5: same redemption rules as the single-task lane — an expiry that
    # cannot be read is not treated as absent, and a past one is a refusal.
    expiry = parse_iso(row.get("handle_expires_at"))
    if expiry is None:
        return (
            f"REFUSED: run #{run_id} carries no readable expiry "
            f"({row.get('handle_expires_at')!r}) — re-run pooled verify."
        )
    if datetime.now(timezone.utc) > expiry:
        return (
            f"REFUSED: handle expired at {row['handle_expires_at']} (run #{run_id}); "
            "re-run pooled verify."
        )
    if row["exit_code"] != 0 or not row.get("cohort_identity"):
        return "REFUSED: handle belongs to no green cohort receipt"

    members = resolve_descendants(be, parent_slug, kind)
    if len(members) < 2:
        return (
            f"REFUSED: {kind} '{parent_slug}' no longer holds a cohort-sized "
            f"non-done set — resolve it by hand"
        )

    # The stale check (AC-4): recompute identity over the CURRENT members and
    # demand the exact receipt. Add/remove/edit/reopen/block all change either
    # membership or a fingerprint, so the handle goes stale instead of green.
    # The root MUST be resolved the way the mint resolved it — see docstring.
    inputs = vc.collect_identity_inputs(be, members, vc.gate_signature(be), root_from_service(svc))
    if vc.canonical_identity(inputs) != row["cohort_identity"]:
        return (
            "REFUSED: handle is stale — the cohort changed after verify "
            "(membership, a member's plan/AC, or gates); re-run verify"
        )

    now = datetime.now(timezone.utc).isoformat()
    try:
        # `be.transaction()` keeps the task writes, the story/epic writes, the
        # single-use spend AND the projection queue in ONE commit: a partial
        # closure rolls back whole, and the git-native state files can never
        # end up behind the DB (the projection flush hangs off commit_tx).
        with be.transaction():
            for slug in members:
                changed = be.task_update(slug, status="done", completed_at=now)
                if changed != 1:
                    raise RuntimeError(f"{slug}: expected exactly one open row, got {changed}")
            if kind == "epic":
                # Stories close with their epic: leaving them open under a
                # done epic is the inverse of the doctor's open-epic check.
                open_stories = be._q(
                    "SELECT slug FROM stories WHERE epic_id="
                    "(SELECT id FROM epics WHERE slug=?) AND status != 'done'",
                    (parent_slug,),
                )
                for srow in open_stories:
                    be.story_update(srow["slug"], status="done")
            (be.story_update if kind == "story" else be.epic_update)(parent_slug, status="done")
            if not redeem(be._conn, run_id, nonce):
                raise RuntimeError("handle was spent concurrently (single use)")
            be._ex(
                "UPDATE verification_cohorts SET state='green', updated_at=? WHERE identity=?",
                (now, row["cohort_identity"]),
            )
    except Exception as exc:  # noqa: BLE001 — AC-4: partial closure rolls back whole
        return (
            f"REFUSED: transaction rolled back — nothing closed ({exc}); "
            f"{kind} members must all be closable in one pass"
        )
    return (
        f"Closed atomically: {len(members)} task(s) + {kind} '{parent_slug}' "
        f"on cohort receipt run #{row['id']}; handle redeemed."
    )
