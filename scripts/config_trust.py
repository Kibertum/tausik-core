"""Trust tiers for TAUSIK configuration — a project may only TIGHTEN enforcement.

``.tausik/config.json`` is an ordinary file inside the repository, and the
enforcement switches used to live in it: ``qg0.scope_hard_gate``,
``risk.l3_block_on_high``, ``task_done.auto_verify``, and per-gate ``enabled``,
``severity``, ``trigger`` and ``file_extensions``. An agent — or anyone opening
a pull request — could disable its own supervision with one write to a tracked
file. The premise was already recorded in one spot (``bootstrap_opencode.py``:
*".tausik/config.json travels with the repo, so the override is UNTRUSTED"*);
this module generalizes it.

THE RULE. Config is read from three tiers, least to most trusted: project
(``.tausik/config.json``, travels with the repo), user (``~/.tausik/config.json``),
managed (``$TAUSIK_MANAGED_CONFIG``). Higher tiers win on merge, EXCEPT that on a
guarded key the stricter value wins in both directions — a project may tighten
freely and may not weaken, and a tightening it already earned is not undone by a
trusted tier that merely restates a default.

Guarding ``enabled`` alone would be decorative: a gate that keeps its switch on
while losing every trigger never fires, and one whose ``file_extensions`` is
narrowed to nothing never receives input. Both are "off" spelled differently, so
those keys are guarded as sets the project may extend but not shrink.

THREAT SURFACE. Closed: **a repository cannot grant itself authority.**
``.tausik/config.json`` arrives with every clone, fork and PR;
``~/.tausik/config.json`` does not. NOT closed, stated plainly rather than
implied: an agent that can run shell commands can write the user tier or export
``TAUSIK_MANAGED_CONFIG`` itself. Tiers are **not a sandbox**. What they buy is a
raised bar and, above all, visibility — weakening must now happen outside the
repository, so it can no longer hide in a diff that looks like a config tweak.

Deliberately unguarded (decision #137): ``gates.filesize.exempt_files`` and
``verify_cache_ttl_seconds`` scope or tune supervision rather than switch it off.
Still open and named rather than implied: a gate ``command`` can be reduced to an
ALLOWED but inert one (``l26-gate-command-neutering``).

Full rationale, migration notes and the reader/writer contract:
``docs/en/config-trust-tiers.md``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, NamedTuple

logger = logging.getLogger(__name__)

USER_CONFIG_ENV = "TAUSIK_USER_CONFIG"
MANAGED_CONFIG_ENV = "TAUSIK_MANAGED_CONFIG"

# A trusted layer is operator-authored and small. Anything larger is either a
# mistake or an attempt to stall the loader; refuse it rather than parse it.
MAX_TRUSTED_LAYER_BYTES = 1_000_000


class Rejection(NamedTuple):
    """One guarded key the project tier tried to weaken."""

    key: str
    rejected: Any
    applied: Any
    reason: str

    def describe(self) -> str:
        return (
            f"{self.key}: project value {self.rejected!r} rejected "
            f"({self.reason}); {self.applied!r} applied"
        )


# --- Strictness comparators -------------------------------------------------
#
# Each returns True when `candidate` is WEAKER than `baseline` and must be
# dropped. Baseline is the value already established by the trusted tiers (or
# the framework default when they are silent).


def _weaker_when_false(candidate: Any, baseline: Any) -> bool:
    """Guard is on by default; turning it off is the weakening move."""
    return bool(baseline) and not bool(candidate)


def _weaker_when_true(candidate: Any, baseline: Any) -> bool:
    """Switch whose SAFE position is off (e.g. auto_verify bypasses the receipt)."""
    return bool(candidate) and not bool(baseline)


_SEVERITY_RANK = {"warn": 0, "block": 1}


def _weaker_severity(candidate: Any, baseline: Any) -> bool:
    """``warn`` < ``block``. An unknown string ranks below every known level, so
    a typo is rejected rather than silently outranking ``block``."""
    return _SEVERITY_RANK.get(str(candidate), -1) < _SEVERITY_RANK.get(str(baseline), -1)


def _removes_baseline_entries(candidate: Any, baseline: Any) -> bool:
    """Set-valued key the project may extend but not shrink.

    Guarding `enabled` alone is decorative: a gate that stays enabled while
    losing every trigger never runs. Same for narrowing `file_extensions` until
    nothing matches. Both are "off" by another spelling.
    """
    if not isinstance(baseline, (list, tuple, set)):
        return False  # nothing concrete to preserve
    if not isinstance(candidate, (list, tuple, set)):
        return True  # a non-list where a list belongs is not a legible tightening
    return bool(set(baseline) - set(candidate))


class Guard(NamedTuple):
    path: tuple[str, ...]  # dotted location; "*" matches any single key
    is_weaker: Callable[[Any, Any], bool]
    default: Any  # framework default, used when no trusted tier speaks
    note: str


# The guarded set. A key belongs here only if it TURNS OFF supervision. Keys
# that merely scope supervision (`gates.filesize.exempt_files`) or tune one of
# its parameters (`verify_cache_ttl_seconds`) are deliberately left out: their
# legitimate values are project-specific with no sensible home in a per-machine
# user tier, so guarding them costs working projects and buys little. See
# decision #137.
#
# The two ``gates`` entries carry ``default=None``: their real
# baseline is per-gate and lives in DEFAULT_GATES, resolved in `_baseline_for`.
# Keeping that lookup out of the table avoids importing default_gates at module
# import time.
GUARDS: tuple[Guard, ...] = (
    Guard(
        ("qg0", "scope_hard_gate"),
        _weaker_when_false,
        True,
        "scope hard gate (blocks edits outside a task's declared scope)",
    ),
    Guard(
        ("risk", "l3_block_on_high"),
        _weaker_when_false,
        True,
        "L3 external review requirement on high-risk closures",
    ),
    Guard(
        ("task_done", "auto_verify"),
        _weaker_when_true,
        False,
        "auto_verify closes a task on an inline run, skipping the signed receipt",
    ),
    Guard(
        ("gates", "*", "enabled"),
        _weaker_when_false,
        None,
        "gate on/off switch",
    ),
    Guard(
        ("gates", "*", "severity"),
        _weaker_severity,
        None,
        "gate severity (warn < block)",
    ),
    Guard(
        ("gates", "*", "trigger"),
        _removes_baseline_entries,
        None,
        "gate trigger list (dropping a trigger silences the gate on that event)",
    ),
    Guard(
        ("gates", "*", "file_extensions"),
        _removes_baseline_entries,
        None,
        "gate file-extension filter (narrowing it starves the gate of inputs)",
    ),
)


# --- Layer loading ----------------------------------------------------------


def _read_layer(path: str, tier: str) -> dict:
    """Read one trusted layer. Any problem degrades to ``{}`` with a warning —
    never to elevated privilege and never to a crash."""
    if not path:
        return {}
    try:
        if not os.path.isfile(path):
            return {}
        size = os.path.getsize(path)
        if size > MAX_TRUSTED_LAYER_BYTES:
            logger.warning(
                "%s config %s is %d bytes (limit %d) — layer ignored",
                tier,
                path,
                size,
                MAX_TRUSTED_LAYER_BYTES,
            )
            return {}
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("%s config unreadable (%s): %s — layer ignored", tier, path, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("%s config root must be an object (%s) — layer ignored", tier, path)
        return {}
    return data


def user_config_path() -> str:
    """``~/.tausik/config.json``, or ``$TAUSIK_USER_CONFIG`` when set.

    The env override exists so tests (and multi-account boxes) never have to
    touch a real home directory.
    """
    from tausik_utils import tausik_config_path

    override = os.environ.get(USER_CONFIG_ENV)
    if override:
        return os.path.abspath(os.path.expanduser(override))
    # Same `.tausik/config.json` layout as a project, rooted at home instead.
    return tausik_config_path(os.path.expanduser("~"))


def managed_config_path() -> str:
    override = os.environ.get(MANAGED_CONFIG_ENV)
    return os.path.abspath(os.path.expanduser(override)) if override else ""


def load_trusted_layers() -> dict:
    """Merge user and managed tiers (managed wins). Absent tiers → ``{}``."""
    return deep_merge(
        _read_layer(user_config_path(), "user"),
        _read_layer(managed_config_path(), "managed"),
    )


# --- Merge + enforcement ----------------------------------------------------


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursive dict merge; ``overlay`` wins. Non-dict values replace wholesale."""
    out = dict(base)
    for k, v in overlay.items():
        cur = out.get(k)
        out[k] = deep_merge(cur, v) if isinstance(cur, dict) and isinstance(v, dict) else v
    return out


def _dig(cfg: Any, path: tuple[str, ...]) -> tuple[bool, Any]:
    """(found, value) for a dotted path; missing or wrong-shaped → (False, None)."""
    node = cfg
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _overwrite(cfg: dict, path: tuple[str, ...], value: Any) -> None:
    """Replace the value at a dotted path, leaving intermediate dicts in place.

    Deleting the key instead would also work today, because every consumer
    happens to default to the strict value. That is an invisible coupling: it
    breaks the moment someone writes `cfg["gates"]["x"]["enabled"]` without a
    default, and it makes the effective config disagree with the rejection
    message, which promises a concrete `applied` value. Write it down.
    """
    node: Any = cfg
    for part in path[:-1]:
        if not isinstance(node, dict) or part not in node:
            return
        node = node[part]
    if isinstance(node, dict):
        node[path[-1]] = value


def _expand(guard: Guard, project: dict) -> list[tuple[str, ...]]:
    """Resolve a ``*`` wildcard against the keys the project tier actually sets.

    Only project keys matter: a guard exists to police what the project asks
    for, and a trusted tier needs no policing.
    """
    if "*" not in guard.path:
        return [guard.path]
    idx = guard.path.index("*")
    prefix, suffix = guard.path[:idx], guard.path[idx + 1 :]
    found, node = _dig(project, prefix)
    if not found or not isinstance(node, dict):
        return []
    return [prefix + (name,) + suffix for name in node]


def _baseline_for(guard: Guard, path: tuple[str, ...], trusted: dict) -> Any:
    """The value a project override is measured against: what the trusted tiers
    say, else the framework default."""
    found, value = _dig(trusted, path)
    if found:
        return value
    if guard.default is not None:
        return guard.default
    # Per-gate guards: the default lives in DEFAULT_GATES.
    if path[:1] == ("gates",) and len(path) == 3:
        from default_gates import DEFAULT_GATES

        gate = DEFAULT_GATES.get(path[1])
        if isinstance(gate, dict) and path[2] in gate:
            return gate[path[2]]
        # No default means this is a custom gate the project itself defined —
        # there is nothing for it to weaken. Assuming `enabled: True` here
        # would reject a project's own opt-in gate the moment it ships
        # disabled.
        return None
    return None


def enforce_project_tier(project: dict, trusted: dict) -> tuple[dict, list[Rejection]]:
    """Return (project layer with weakening keys removed, rejections).

    The input is not mutated.
    """
    cleaned = json.loads(json.dumps(project)) if project else {}
    rejections: list[Rejection] = []
    for guard in GUARDS:
        for path in _expand(guard, cleaned):
            found, candidate = _dig(cleaned, path)
            if not found:
                continue
            baseline = _baseline_for(guard, path, trusted)
            if baseline is None:
                continue  # nothing to be stricter than
            if not guard.is_weaker(candidate, baseline):
                continue  # equal or tighter — the project may do this freely
            _overwrite(cleaned, path, baseline)
            rejections.append(
                Rejection(
                    key=".".join(path),
                    rejected=candidate,
                    applied=baseline,
                    reason=f"project scope may only tighten {guard.note}",
                )
            )
    return cleaned, rejections


def _restore_project_tightenings(merged: dict, cleaned: dict, trusted: dict) -> None:
    """Let a surviving project value stand where the merge made things laxer.

    `deep_merge` gives the trusted tier the last word on every key it names,
    which is right for unguarded settings but wrong for a guarded one the
    project legitimately tightened. An operator whose `~/.tausik/config.json`
    merely restates a default (`mypy.enabled: false`) would otherwise silently
    undo a project's `true` — a tightening the policy had already approved, with
    no rejection to show for it. "Project may only tighten" has to hold in this
    direction too: on guarded keys the STRICTER of the two wins.
    """
    for guard in GUARDS:
        for path in _expand(guard, cleaned):
            found, project_value = _dig(cleaned, path)
            if not found:
                continue
            in_trusted, _ = _dig(trusted, path)
            if not in_trusted:
                continue  # merge left the project value alone already
            found_m, merged_value = _dig(merged, path)
            if found_m and guard.is_weaker(merged_value, project_value):
                _overwrite(merged, path, project_value)


def resolve(project: dict, trusted: dict | None = None) -> tuple[dict, list[Rejection]]:
    """Effective config from a raw project layer. Trusted tiers are read from
    disk unless supplied (tests, callers that already loaded them)."""
    if trusted is None:
        trusted = load_trusted_layers()
    cleaned, rejections = enforce_project_tier(project, trusted)
    merged = deep_merge(cleaned, trusted)
    _restore_project_tightenings(merged, cleaned, trusted)
    return merged, rejections


def is_guarded(path: tuple[str, ...] | str) -> Guard | None:
    """The guard covering a dotted key, if any. Config writers use this to tell
    the caller their write will not take effect."""
    parts = tuple(path.split(".")) if isinstance(path, str) else tuple(path)
    for guard in GUARDS:
        if len(guard.path) != len(parts):
            continue
        if all(g == "*" or g == p for g, p in zip(guard.path, parts)):
            return guard
    return None
