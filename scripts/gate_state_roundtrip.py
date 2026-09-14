"""State round-trip gate — fails a commit when the durable `tausik/` projection
does not match a fresh export of the DB.

state-git-roundtrip-gate. The DB (`.tausik/tausik.db`) is the working cache; the
NON-dotted `tausik/` markdown tree is the branch-coupled source of truth. A
git-native state that silently drifts from the DB is a promise, not a guarantee —
so this gate re-serializes the live DB and byte-compares it to what is on disk.
It catches the three drift modes state-git-roundtrip-gate was written for:
forgot to `tausik state export` before committing; hand-edited a file past the
DB; a non-deterministic serializer.

Runs on the COMMIT trigger, not task-done: closing a task mutates the DB (and can
auto-close its parent story/epic), so a task-done-time check would flag its own
in-flight write as drift. The commit boundary is where "the files that enter git
must equal the DB" actually matters, and the auto-export triggers
(state_triggers) keep the tree current between commits.

Read-only and opt-in: a project that never ran `tausik state export` has no tree
to check and the gate SKIPS (passes) rather than inventing a red — a fresh clone
or a project that has not adopted git-native state must not be blocked. Extracted
to its own module (gate_bootstrap_drift / gate_renar_drift pattern) so gate_runner
stays under the filesize cap.
"""

from __future__ import annotations

import os

import gate_outcome

# What a reader of a CANNOT-RUN row is supposed to DO. Both non-execution paths
# owe the same answer; a refusal without a next action is a dead end wearing a
# better name (#182).
_CANNOT_RUN_REMEDY = (
    "This gate produced no evidence, so it certifies nothing. Re-run once the "
    "fault above is gone; if it persists, the round-trip is unknown, not clean."
)


def run_state_roundtrip_gate_for(gate: dict, files: list[str]) -> gate_outcome.GateOutcome:
    """Registry-uniform ``(gate, files)`` entrypoint (gate-registry-single-source).

    Both arguments are ignored: the check compares the WHOLE `tausik/` tree
    against a full DB export, and narrowing it to the task's declared files would
    let drift outside that scope enter git silently.
    """
    return run_state_roundtrip_gate()


def run_state_roundtrip_gate() -> gate_outcome.GateOutcome:
    """Fail iff the on-disk `tausik/` tree differs from a fresh DB export.

    Returns a ``GateOutcome``, which still unpacks as the historical
    ``(passed, message)`` pair for call sites that destructure it.

    NOT_APPLICABLE (passes) when there is no tree to check — no `.tausik/`, or
    the projection was never materialized. A slug-less entity that cannot be
    serialized is a real, actionable FAILED (block).

    Any other unexpected fault is COULD_NOT_RUN and BLOCKS — it does NOT fail
    open (three-more-gates-sign-non-execution-as-a-pass). The exception is still
    caught, because a gate must never crash the commit it guards; what changed
    is that a check which produced no evidence stops being counted as one that
    found nothing wrong.
    """
    try:
        from project_config import find_tausik_dir

        tausik_dir = os.path.abspath(find_tausik_dir())
        project_root = os.path.dirname(tausik_dir)
        tree_root = os.path.join(project_root, "tausik")
        if not os.path.isdir(tree_root):
            return gate_outcome.not_applicable(
                gate_outcome.REASON_NO_PROJECTION,
                "No tausik/ projection — state round-trip check skipped "
                "(run `tausik state export` to adopt git-native state).",
            )
        db_path = os.path.join(tausik_dir, "tausik.db")
        if not os.path.isfile(db_path):
            return gate_outcome.not_applicable(
                gate_outcome.REASON_NO_DATABASE,
                "No tausik.db — state round-trip check skipped.",
            )
    except Exception as e:  # noqa: BLE001 — caught, but recorded as non-execution, not as a pass
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            f"State round-trip check unavailable ({type(e).__name__}: {e}).",
            remedy=_CANNOT_RUN_REMEDY,
        )

    be = None
    try:
        # ExportError is imported HERE, inside the guarded block — a broken
        # state_export import chain must be CAUGHT, not propagate out of
        # gate_runner (which calls impl() with no try/except) and crash the whole
        # commit-gate run. Caught is not the same as passed: it is recorded as
        # COULD_NOT_RUN and blocks, since a broken import means the round-trip is
        # unknown, not clean.
        from project_backend import SQLiteBackend
        from project_service import ProjectService
        from state_export import ENTITY_DIRS, ExportError, build_tree
        from state_serialize import check_tree

        be = SQLiteBackend(db_path)
        svc = ProjectService(be)
        try:
            tree, _warnings = build_tree(svc)
        except ExportError as e:
            # A slug-less/unserializable entity is a genuine defect, not noise —
            # the export refuses loudly, so must the gate (block, with the fix).
            return gate_outcome.failed(
                f"State export refused — the DB cannot be serialized: {e}\n"
                "Fix the entity (usually a missing stable slug), then `tausik state export`."
            )
        drift = check_tree(tree_root, tree, managed_dirs=set(ENTITY_DIRS))
    except Exception as e:  # noqa: BLE001 — caught, but recorded as non-execution, not as a pass
        return gate_outcome.could_not_run(
            gate_outcome.REASON_RUNNER_ERROR,
            f"State round-trip check unavailable ({type(e).__name__}: {e}).",
            remedy=_CANNOT_RUN_REMEDY,
        )
    finally:
        if be is not None:
            try:
                be.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass

    if drift:
        shown = "\n  ".join(drift[:20])
        more = f"\n  … (+{len(drift) - 20} more)" if len(drift) > 20 else ""
        return gate_outcome.failed(
            f"State drift: tausik/ does NOT match the live DB ({len(drift)} issue(s)) — "
            "the files that would enter git disagree with the source of truth "
            "(forgot to export, a hand-edit past the DB, or a non-deterministic "
            f"serializer):\n  {shown}{more}\n"
            "Fix: tausik state export   (re-serializes the DB, then re-stage the tree)."
        )

    # The working tree matches the DB — but a commit carries the INDEX, not the
    # working tree, and the commit flow stages SPECIFIC files (not `git add -A`).
    # If the export is on disk yet not staged (`git add tausik/` forgotten), those
    # DB-matching files never enter the commit, and a working-tree-only check
    # would green-light a commit that omits them. Require the tree to be fully
    # staged. Fail-open when git is unavailable (not a repo / no git binary).
    unstaged = _unstaged_managed_paths(project_root)
    if unstaged:
        shown = "\n  ".join(unstaged[:20])
        more = f"\n  … (+{len(unstaged) - 20} more)" if len(unstaged) > 20 else ""
        return gate_outcome.failed(
            f"State not staged: tausik/ matches the DB, but {len(unstaged)} change(s) "
            "are unstaged/untracked — the commit would omit them:\n  "
            f"{shown}{more}\n"
            "Fix: git add tausik/   (stage the exported tree before committing)."
        )
    return gate_outcome.passed(
        f"No state drift — tausik/ matches the DB export ({len(tree)} file(s))."
    )


def _unstaged_managed_paths(project_root: str) -> list[str]:
    """`tausik/` paths present on disk but NOT fully staged — untracked, or with
    changes in the worktree column that the index will not commit.

    Returns ``[]`` when git is unavailable (no binary, not a repo, timeout): the
    staged-vs-index guarantee is best-effort and must never crash the commit.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", "tausik"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
    except Exception:  # noqa: BLE001 — git missing / timeout / OS error
        # Deliberately still permissive, and NOT the fail-open this task retired.
        # This is a HELPER, not a verdict: it answers "which managed paths are
        # unstaged", and its caller only ever turns a non-empty answer into a
        # failure. An empty list here says "no evidence of unstaged files", which
        # is what an absent git honestly gives — the gate's own verdict, and the
        # blocking decision, are made above and are unaffected.
        return []
    if proc.returncode != 0:
        return []
    dirty: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        path = line[3:]
        # Untracked ("??"), or any non-space in the WORKTREE column (index 1):
        # the on-disk (DB-matching) content differs from what the index commits.
        if xy == "??" or xy[1] != " ":
            dirty.append(path)
    return dirty
