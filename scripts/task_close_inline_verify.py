"""Closing in one call: `task done --verify` runs the check itself.

MEASURED. Closing a task costs the agent four to six calls — `verify`, then `task done`,
then a refusal from a gate that only fires at close, then `verify` again, then `task done`
again. At the measured 482 000 tokens of prefix re-sent on every call, each extra call
costs about half a million tokens, and this is the most frequent ceremony in the framework:
1240 closures carry a recorded call count.

WHAT THIS IS NOT. It is not a way around QG-2. The inline run is the same
`run_verify_for_task` the separate command calls, it records the same receipt, and it mints
the same single-use handle — which is then presented to `task_done` exactly as a
hand-driven close presents it. A red run refuses the close and leaves the task open, and
the receipt of that red run stays: a run that happened is evidence whichever way it went.

WHY IT REFUSES ALONGSIDE `--verify-handle`. Two sources of verification in one call means
one of them is not the one that gets redeemed, and the caller cannot tell which from the
output. The refusal names both and asks for one.

WHY IT REFUSES AN EMPTY SCOPE. A verify over an undeclared scope skips the scoped gates and
still signs a receipt. Requiring the declaration is what keeps the single call from being a
cheaper way to certify nothing; `--no-file-changes` remains the honest way to say a task
changed no files, and it is accepted here.
"""

from __future__ import annotations

import json
from typing import Any, Callable

#: Printed by the refusals so a caller reads back the wrapper it types.
_CLI = ".tausik/tausik"


def refuse_two_sources(args: Any) -> None:
    """`--verify` and `--verify-handle` together name two runs; only one is redeemed."""
    if getattr(args, "verify", False) and getattr(args, "verify_handle", None):
        from project_service import ServiceError

        raise ServiceError(
            "task done: --verify and --verify-handle both name a verification run, and "
            "only one of them can be the one redeemed. Drop --verify to present the handle "
            "you already hold, or drop --verify-handle to let this call run the check: "
            f"`{_CLI} task done <slug> --ac-verified --verify`."
        )


def declared_scope(svc: Any, slug: str) -> list[str]:
    """The task's own relevant_files, as a list; [] when it declared none.

    A service that cannot answer gives [] rather than raising. This is asked on the way to
    an OPTIONAL step — preparing the tree before the gates — and a helper reaching for
    optional information must never be the reason the run it serves does not happen.
    """
    try:
        row = svc.task_show(slug) or {}
    except Exception:  # noqa: BLE001 - see above: optional information, never fatal
        return []
    raw = row.get("relevant_files")
    if not raw:
        return []
    if isinstance(raw, list):
        return list(raw)
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return list(parsed) if isinstance(parsed, list) else []


def post_close_advisory(svc: Any, slug: str) -> list[str]:
    """What the post-scope gates will demand at close, said BEFORE the close is paid for.

    These gates run only at `task done`, so an agent meets them AFTER the ceremony has
    already cost a call — the changelog one alone cost two extra calls in the session that
    filed this. The real gate is asked and its verdict reported; re-implementing the check
    here would be a second copy of the rule, and a second copy is one that drifts.

    Advisory, never a refusal: mid-task the entry legitimately does not exist yet, and a
    gate that goes red on the normal case is a gate people learn to skip.
    """
    from gate_changelog import enforce_changelog

    probe: dict[str, Any] = {"passed": True, "blocking_failures": []}
    try:
        enforce_changelog(svc, probe, slug)
    except Exception:  # noqa: BLE001 - an advisory must never break the run it advises
        return []
    lines = []
    for failure in probe["blocking_failures"]:
        lines.append(
            f"AT CLOSE, NOT NOW: gate '{failure['gate']}' will refuse this close. "
            f"{failure.get('remediation') or ''}".rstrip()
        )
    return lines


def handle_for_close(
    svc: Any,
    args: Any,
    *,
    echo: Callable[[str], None] = print,
) -> str:
    """Run the scoped check and return the handle `task done` must present.

    Raises SystemExit(1) on a red run, after printing the same report the separate command
    prints — the agent's next action depends on WHICH gate went red, not on the fact that
    one did, and a one-call close that swallowed the report would trade four cheap calls
    for one blind one.

    Returns "" when the run passed but earned no handle: that happens when the receipt
    could not be signed, and `task_done` still has its freshness lookup for that case.
    Inventing a handle there would be the hidden server state the handle exists to replace.
    """
    from project_service import ServiceError
    from render_verify import verify_lines

    slug = args.slug
    passed_files = list(getattr(args, "relevant_files", None) or [])
    if not passed_files and not declared_scope(svc, slug):
        if not getattr(args, "no_file_changes", False):
            raise ServiceError(
                f"task done --verify: '{slug}' declares no relevant_files. A verify over an "
                "undeclared scope skips the scoped gates and still signs a receipt, so the "
                "one call would certify nothing. Declare the scope — "
                f"`{_CLI} verify --task {slug} --relevant-files <paths>` — or, if the task "
                "really changed no files, say so with --no-file-changes."
            )
    if passed_files:
        svc.task_update(slug, relevant_files=json.dumps(passed_files))
        echo(f"Scope declared for '{slug}': {len(passed_files)} file(s).")

    report = svc.run_verify_for_task(
        slug,
        scope="manual",
        trigger="verify",
        no_tests_expected=bool(getattr(args, "no_tests_expected", False)),
    )
    echo("\n".join(verify_lines(svc, report, slug, "manual")))
    if not report.get("passed"):
        raise SystemExit(1)
    return str(report.get("verify_handle") or "")


if __name__ == "__main__":  # pragma: no cover - exercised via the CLI
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(__file__)
