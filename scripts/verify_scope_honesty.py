"""Honest scope description for verification receipts.

l26-verify-git-diff-wire. `verify_git_diff.is_declared_consistent_with_git_diff`
has been wired since v1.3.4, but its answer gated exactly one thing: whether
the verify cache could be reused. On a mismatch the cache was refused, a WARN
landed in the task notes, `cache_status` became "git-mismatch" — and then the
gates ran against the SAME narrow declared list, after which `record_run`
signed a receipt for that narrow scope. The divergence was detected and left
out of the artifact of proof. An agent declaring `relevant_files=[README.md]`
during a broad edit still received a cryptographically signed green receipt
for README.md.

This module turns that transient boolean into a recordable property.

Two deliberate departures from the old boolean (Decision #139):

1. **Tri-state, not boolean.** "Declared scope is provably complete" and "we
   could not check" are different claims and must not collapse into one. No
   git, no `task_created_at`, empty `relevant_files`, or a failed git call all
   yield `unknown` — never `complete`. Legacy rows with NULL read as `unknown`
   for the same reason. Conflating the two is precisely the silent green this
   task exists to remove (memory #221: a check that could not be computed must
   not report success).

2. **Divergence itself never blocks.** Both closures of session #112 diverged
   from git and both were honest — CHANGELOG, docs, generated constants,
   README badges and five IDE mirrors edited beyond the declared set. A rule
   firing on ~100% of honest work would be disabled first (Decision #138,
   memory #223). Only the intersection of the *undeclared* set with the
   security predicate blocks, because that is the half of the original v1.3.4
   hole which refusing the cache never closed: undeclared `scripts/auth.py`
   is skipped by the scoped gates entirely.
"""

from __future__ import annotations

import subprocess
from typing import Any, Callable

import verify_git_diff
from security_pattern import is_security_sensitive
from verify_git_diff import _normalize_repo_path

STATUS_COMPLETE = "complete"
STATUS_UNDER_DECLARED = "under-declared"
STATUS_UNKNOWN = "unknown"

# Receipts must stay small and canonically stable. The full count is always
# recorded; the listing is capped and sorted so the signed bytes are
# deterministic regardless of git output order or filesystem locale.
MAX_LISTED_UNDECLARED = 50


def describe_declared_scope(
    declared_files: list[str] | None,
    task_created_at: str | None,
    *,
    root: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> dict[str, Any]:
    """Describe how the declared file set relates to what git says changed.

    Returns a dict that is safe to persist and to embed in a signed receipt::

        {
          "status": "complete" | "under-declared" | "unknown",
          "reason": str,                # why, for notes/debugging — not signed
          "undeclared": [str, ...],     # sorted, capped at MAX_LISTED_UNDECLARED
          "undeclared_count": int,      # full count, never capped
          "security_undeclared": [str], # subset that trips is_security_sensitive
        }

    `status` is `unknown` — never `complete` — whenever the comparison could
    not actually be made. `undeclared` is empty for every status except
    `under-declared`.
    """
    empty: dict[str, Any] = {
        "undeclared": [],
        "undeclared_count": 0,
        "security_undeclared": [],
    }
    if not task_created_at:
        return {"status": STATUS_UNKNOWN, "reason": "no task_created_at", **empty}
    declared_set = {_normalize_repo_path(s) for s in (declared_files or []) if s}
    declared_set.discard("")
    if not declared_set:
        return {"status": STATUS_UNKNOWN, "reason": "no declared files", **empty}

    # Called through the module, not via a from-import binding: the git lookup
    # is the seam tests substitute, and a direct name binding would silently
    # ignore `monkeypatch.setattr(verify_git_diff, "changed_files_since", ...)`
    # — the check would then pass while measuring nothing.
    actual = verify_git_diff.changed_files_since(task_created_at, root=root, runner=runner)
    if actual is None:
        # changed_files_since collapses "not a git repo", "git missing from
        # PATH" and "git call failed" into None. All three mean the same to us:
        # unverifiable, therefore unknown.
        return {"status": STATUS_UNKNOWN, "reason": "git unavailable", **empty}
    if not actual:
        return {
            "status": STATUS_COMPLETE,
            "reason": "no git-visible changes since task start",
            **empty,
        }

    undeclared = sorted(actual - declared_set)
    if not undeclared:
        return {
            "status": STATUS_COMPLETE,
            "reason": f"declared set covers all {len(actual)} changed file(s)",
            **empty,
        }
    return {
        "status": STATUS_UNDER_DECLARED,
        "reason": f"{len(undeclared)} file(s) changed per git but not declared",
        "undeclared": undeclared[:MAX_LISTED_UNDECLARED],
        "undeclared_count": len(undeclared),
        "security_undeclared": [p for p in undeclared if is_security_sensitive([p])],
    }


def security_block_reason(description: dict[str, Any] | None) -> str | None:
    """Message to block on, or None when the run may proceed.

    Blocks only when a file that git says changed was left out of
    `relevant_files` AND that file is security-sensitive. Refusing the verify
    cache (the v1.3.4 behaviour) does not cover this case: the gates that run
    afterwards still see only the declared list, so an undeclared auth file is
    never gated at all.

    Everything else — including a plain under-declaration of docs, changelogs
    or generated files — returns None by design (Decision #139).
    """
    if not description:
        return None
    offenders = list(description.get("security_undeclared") or [])
    if not offenders:
        return None
    shown = ", ".join(offenders[:10])
    more = "" if len(offenders) <= 10 else f" (+{len(offenders) - 10} more)"
    return (
        f"FAIL: security-sensitive file(s) changed since task start but absent "
        f"from relevant_files: {shown}{more}. Scoped gates run against the "
        f"declared list only, so these files would be verified by nothing. "
        f"Add them to relevant_files and re-run."
    )
