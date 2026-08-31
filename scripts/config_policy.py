"""Committed project policy — the half of the project tier that survives a clone.

WHY THIS EXISTS. `config_trust` says the project tier "travels with the repo",
and for a consumer project — where `.tausik/` is committed — that is true. In
THIS repository it is not: `.gitignore:25` ignores `.tausik/` wholesale, so the
one file carrying the project tier never leaves this working copy. Measured, not
argued: a fresh `git worktree` of HEAD, read against a user tier with
`task_done.auto_verify: true`, resolves `auto_verify` to **True** and
`gates.bootstrap_drift.enabled` to **False** — both of this repository's
tightenings gone, with zero rejections to show for it, because an absent project
tier has nothing to reject. A release whose thesis is evidence was enforcing its
own rules from a file no clone receives.

WHY NOT THE OTHER TWO REPAIRS. Making the strict values framework DEFAULTS
cannot work: `auto_verify: False` already IS the default (see `GUARDS`), and a
default loses to any trusted tier that speaks. Only the PROJECT tier is
compared, strictness-wise, against the trusted ones — so the fix has to keep the
values in the project tier and change only where they are stored. Un-ignoring
`.tausik/config.json` would store them in a GENERATED file: `_meta.generated_at`,
`_meta.lib_commit`, `installed_skills` and `brain.database_ids` would dirty the
tree on every bootstrap.

THE SHAPE. `tausik/policy.json` — the same non-dotted, branch-coupled projection
that already carries `tausik/gates.json`, whose own `_comment` states the
precedent verbatim: *"Lives in the non-dotted tausik/ projection (NOT the
gitignored .tausik/) so a fresh clone carries it."* This module generalizes that
one-off into the config loader instead of leaving a third gate to re-implement
it.

NO NEW AUTHORITY. `policy.json` is not a fourth tier. It is the project tier,
which is the UNTRUSTED one: everything in it is judged by the same guards and
may only tighten. A hostile clone that writes `auto_verify: true` here is
rejected exactly as it is when it writes the same key into `.tausik/config.json`.
What changes is reach, not power — a tightening now arrives with the repository
rather than living in one developer's checkout.

PRECEDENCE INSIDE THE TIER. `.tausik/config.json` wins on ordinary keys: it is
the machine-local file, and bootstrap metadata belongs to the machine. On a
GUARDED key the stricter of the two wins, so a local file cannot quietly undo a
committed tightening — that silent undo is the very defect this module was
opened to close, and re-admitting it one layer down would be a poor joke.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Explicit path override. Tests and CI need to point the loader at a policy file
# without owning the directory layout around it, exactly as `TAUSIK_GATES_CONFIG`
# does for `tausik/gates.json`.
POLICY_ENV = "TAUSIK_PROJECT_POLICY"

POLICY_DIRNAME = "tausik"
POLICY_NAME = "policy.json"

# Same ceiling as a trusted layer in `config_trust`: an operator-authored policy
# is small, and anything larger is a mistake or an attempt to stall the loader.
MAX_POLICY_BYTES = 1_000_000


def policy_path(tausik_dir: str) -> str:
    """Where the committed policy sits for the project rooted at *tausik_dir*.

    Derived from the caller's `.tausik/` handle rather than re-walking the tree.
    `gate_filesize._committed_gates_config_path` has to walk up from the cwd
    because a gate is handed files, not a project; the config loader is already
    holding the answer, and a second walk-up formula here would be one more copy
    of a rule that has to stay in step (convention #266). It also removes that
    walk's failure mode outright: there is no ancestor to adopt by accident.
    """
    override = os.environ.get(POLICY_ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    project_root = os.path.dirname(os.path.abspath(tausik_dir))
    return os.path.join(project_root, POLICY_DIRNAME, POLICY_NAME)


def load_policy(tausik_dir: str) -> dict[str, Any]:
    """Read the committed policy layer. Absent or broken → ``{}``.

    Best-effort by design, and the direction of the degradation is the point: a
    missing policy leaves the project tier exactly as it was before this module
    existed, so a consumer project whose generator never writes the file is
    untouched, and `tausik init` in an empty directory keeps working. A file
    this loader cannot read must not be able to hard-fail every command that
    reads config — that would take the whole CLI down for a reason unrelated to
    the command being run (convention #226).

    It also cannot degrade to elevated privilege: `{}` means "the project asks
    for no tightening", and the trusted tiers and framework defaults then decide
    on their own, which is the pre-existing behaviour rather than a bypass.
    """
    path = policy_path(tausik_dir)
    try:
        if not os.path.isfile(path):
            return {}
        size = os.path.getsize(path)
        if size > MAX_POLICY_BYTES:
            logger.warning(
                "project policy %s is %d bytes (limit %d) — layer ignored",
                path,
                size,
                MAX_POLICY_BYTES,
            )
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("project policy unreadable (%s): %s — layer ignored", path, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("project policy root must be an object (%s) — layer ignored", path)
        return {}
    return data


def compose_project_tier(policy: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """The project tier as one dict: committed policy under the local config.

    `local` wins the ordinary merge — it is the machine's own file and holds the
    bootstrap metadata that has no business in a committed policy. On a guarded
    key the STRICTER of the two is restored afterwards, reusing the very
    comparator set that polices this tier against the trusted ones, so "may only
    tighten" reads the same in both places instead of being spelled twice.

    Neither input is mutated.
    """
    from config_trust import deep_merge, restore_tightenings

    if not policy:
        return dict(local)
    merged = deep_merge(policy, local)
    restore_tightenings(merged, policy, local)
    return merged


def load_project_tier(tausik_dir: str, local: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper: compose *local* over the policy found for *tausik_dir*."""
    return compose_project_tier(load_policy(tausik_dir), local)
