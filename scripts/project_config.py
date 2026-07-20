"""TAUSIK config loader — find .tausik/ dir, create service, gates config."""

from __future__ import annotations

import json
import logging
import os

from project_backend import SQLiteBackend
from project_service import ProjectService

logger = logging.getLogger(__name__)

# Data lives in .tausik/ (IDE-agnostic)
TAUSIK_DIR = ".tausik"
DB_NAME = "tausik.db"
CONFIG_NAME = "config.json"

# --- Gate defaults ---

# Custom-gate command security lives in `gate_command_policy` (split out at the
# 400-line cap). Re-exported here because callers and tests import it from this
# module.
from gate_command_policy import (  # noqa: E402,F401
    ALLOWED_GATE_EXECUTABLES,
    VALID_GATE_SEVERITIES,
    VALID_GATE_TRIGGERS,
    _validate_custom_gate,
    validate_default_gate_command,
)

# --- Agent rule pack size (bootstrap templates: CLAUDE.md / AGENTS.md / .cursorrules) ---
CONTEXT_TIER_VALUES = frozenset({"minimal", "standard", "full"})
DEFAULT_CONTEXT_TIER = "standard"


def resolve_context_tier(cfg: dict | None) -> str:
    """Return normalized ``context_tier`` from the root of ``.tausik/config.json``.

    Missing or null → ``standard``. Invalid string → ``ValueError``.
    """

    if not cfg:
        return DEFAULT_CONTEXT_TIER
    raw = cfg.get("context_tier", DEFAULT_CONTEXT_TIER)
    if raw is None or raw == "":
        return DEFAULT_CONTEXT_TIER
    if not isinstance(raw, str):
        raise ValueError("context_tier must be a string")
    t = raw.strip().lower()
    if t not in CONTEXT_TIER_VALUES:
        raise ValueError(
            f"Invalid context_tier {raw!r}; expected one of {sorted(CONTEXT_TIER_VALUES)}"
        )
    return t


def is_task_next_model_hint_enabled(cfg: dict | None = None) -> bool:
    """Whether to append non-blocking Claude model hints to ``task next`` / ``hud``.

    Opt-in via root ``.tausik/config.json``::

        "task_next": { "model_hint": true }

    Missing ``task_next``, wrong type, or ``model_hint: false`` → ``False`` (unchanged behavior).
    """
    if cfg is None:
        cfg = load_config()
    tn = cfg.get("task_next")
    if not isinstance(tn, dict):
        return False
    return bool(tn.get("model_hint"))


def is_task_start_model_banner_enabled(cfg: dict | None = None) -> bool:
    """Whether ``task start`` prints the model recommendation banner.

    Default: True (v1.4 polish). Opt-out for headless/CI runs via root
    ``.tausik/config.json``::

        "task_start": { "model_banner": false }

    Missing ``task_start`` key or wrong type → True (default-on). Explicit
    ``false`` disables. Any other truthy value enables.
    """
    if cfg is None:
        cfg = load_config()
    ts = cfg.get("task_start")
    if not isinstance(ts, dict):
        return True
    flag = ts.get("model_banner")
    if flag is False:
        return False
    return True


def normalize_llm_pricing_config(cfg: dict | None) -> dict:
    """Validate ``llm_pricing_usd_per_million``: map ``model_id`` → USD per 1M tokens."""

    if not cfg:
        return {}
    out = dict(cfg)
    raw = out.get("llm_pricing_usd_per_million")
    if raw is None:
        return out
    if not isinstance(raw, dict):
        logger.warning(
            "llm_pricing_usd_per_million must be a JSON object (model → price) — dropped"
        )
        del out["llm_pricing_usd_per_million"]
        return out
    clean: dict[str, float] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if not key:
            continue
        try:
            val = float(v)
        except (TypeError, ValueError):
            logger.warning("Skipping llm_pricing_usd_per_million entry %r — not numeric", k)
            continue
        if val != val:  # NaN
            continue
        if val < 0:
            logger.warning(
                "Skipping llm_pricing_usd_per_million for %r — negative price not allowed",
                key,
            )
            continue
        clean[key] = val
    out["llm_pricing_usd_per_million"] = clean
    return out


def lookup_llm_usd_per_million_tokens(cfg: dict | None, model_id: str | None) -> float | None:
    """USD per million tokens for *exact* ``model_id`` match, else ``None`` (unknown tariff)."""

    if not cfg or model_id is None:
        return None
    tbl = cfg.get("llm_pricing_usd_per_million")
    if not isinstance(tbl, dict):
        return None
    key = model_id.strip()
    if not key or key not in tbl:
        return None
    return float(tbl[key])


# --- SENAR Rule 9.2: Session duration limit (minutes) ---
# SENAR v1.3: sessions exceeding 180 min show diminishing returns.
# Measured against ACTIVE minutes (gap-based), not wall clock — AFK breaks
# don't count. See backend_session_metrics.compute_active_minutes.
DEFAULT_SESSION_MAX_MINUTES = 180

# Gap (in minutes) above which a pause between events is treated as AFK
# and excluded from active-time totals. Tunable via .tausik/config.json
# under "session_idle_threshold_minutes".
DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES = 10

# --- Agent-native session capacity (tool calls, not minutes) ---
DEFAULT_SESSION_CAPACITY_CALLS = 200

from default_gates import DEFAULT_GATES  # noqa: E402


def _build_stack_gate_map() -> dict[str, list[str]]:
    """Build mapping: stack -> list of gates to auto-enable."""
    result: dict[str, list[str]] = {}
    for gate_name, gate_cfg in DEFAULT_GATES.items():
        for stack in gate_cfg.get("stacks", []):
            result.setdefault(stack, []).append(gate_name)
    return result


STACK_GATE_MAP: dict[str, list[str]] = _build_stack_gate_map()


def auto_enable_gates_for_stacks(cfg: dict, stacks: list[str]) -> list[str]:
    """Auto-enable gates for detected stacks. Returns list of newly enabled gate names.

    Only enables gates that are not already explicitly configured by the user.
    Writes changes to config under "gates" key.
    """
    user_gates = cfg.setdefault("gates", {})
    newly_enabled: list[str] = []
    for stack in stacks:
        for gate_name in STACK_GATE_MAP.get(stack, []):
            # Skip if user already configured this gate explicitly
            if gate_name in user_gates:
                continue
            user_gates[gate_name] = {"enabled": True}
            newly_enabled.append(gate_name)
    return list(dict.fromkeys(newly_enabled))  # deduplicate preserving order


def find_tausik_dir() -> str:
    """Find .tausik/ directory, searching up from cwd. Env override: TAUSIK_DIR."""
    override = os.environ.get("TAUSIK_DIR")
    if override:
        return override
    d = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(d, TAUSIK_DIR)
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # Default to cwd
    return os.path.join(os.getcwd(), TAUSIK_DIR)


def get_db_path() -> str:
    return os.path.join(find_tausik_dir(), DB_NAME)


def get_config_path() -> str:
    return os.path.join(find_tausik_dir(), CONFIG_NAME)


def load_project_config() -> dict:
    """Raw ``.tausik/config.json`` — the project tier alone, no trusted layers.

    This is what config *writers* must read: `save_config` persists whatever it
    is handed, so round-tripping the effective config (`load_config`) would
    copy the user's and the operator's settings into the repository file.
    Readers want `load_config` instead.
    """
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    logging.getLogger("tausik.config").warning(
                        "Config root must be an object (%s)", path
                    )
                    return {}
                return normalize_llm_pricing_config(data)
        except (json.JSONDecodeError, OSError) as e:
            logging.getLogger("tausik.config").warning(
                "Config corrupted (%s): %s — using defaults", path, e
            )
    return {}


def load_config_with_rejections() -> tuple[dict, list]:
    """Effective config plus the guarded keys the project tier tried to weaken.

    Layers merge project < user < managed; on top of that a project-tier value
    for a guarded key applies only if it is at least as strict as what the
    trusted tiers (or the framework default) already establish. See
    `config_trust` for the rule and its honest threat boundary.
    """
    from config_trust import resolve

    cfg, rejections = resolve(load_project_config())
    for r in rejections:
        logger.warning("Config trust tier: %s", r.describe())
    return cfg, rejections


def load_config() -> dict:
    """Effective config for readers. Rejections are logged, not returned —
    use `load_config_with_rejections` when you need to surface them."""
    return load_config_with_rejections()[0]


def save_config(cfg: dict) -> None:
    """Persist config.json atomically: write to .tmp + os.replace.

    Atomicity guards against partial writes if the process is killed mid-write.
    """
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_gates(cfg: dict | None = None) -> dict[str, dict]:
    """Load gates config: merge user overrides on top of defaults.

    Returns dict of gate_name -> gate_config.
    User can override any field per gate in config.json under "gates" key.
    """
    if cfg is None:
        cfg = load_config()
    user_gates = cfg.get("gates", {})
    if not isinstance(user_gates, dict):
        logger.warning("Config `gates` must be an object — user overrides ignored")
        user_gates = {}
    merged: dict[str, dict] = {}
    # Start with defaults
    for name, defaults in DEFAULT_GATES.items():
        gate = dict(defaults)
        override = user_gates.get(name)
        if isinstance(override, dict):
            # An override that swaps a built-in gate's command used to skip the
            # allowed-executable check entirely — it only ran for gate names
            # absent from DEFAULT_GATES. `.tausik/config.json` travels with the
            # repo, so that let a cloned project point `ruff.command` at any
            # binary and have the runner execute it. Validate every command an
            # override supplies, built-in or not; on refusal keep the default.
            if "command" in override:
                # Two independent checks: allow-list ("is this binary
                # tolerable at all?"), then identity ("is it still this
                # gate's tool?"). Rationale in gate_command_policy.
                error = _validate_custom_gate(name, override) or validate_default_gate_command(
                    name, override.get("command"), defaults.get("command")
                )
                if error:
                    logger.warning("Ignoring command override: %s", error)
                    override = {k: v for k, v in override.items() if k != "command"}
            gate.update(override)
        elif override is not None:
            logger.warning("Gate '%s' override must be an object — ignored", name)
        merged[name] = gate
    # Add custom user gates (not in defaults) — with security validation
    for name, ucfg in user_gates.items():
        if name not in merged:
            error = _validate_custom_gate(name, ucfg)
            if error:
                logger.warning("Skipping gate: %s", error)
                continue
            merged[name] = ucfg
    return merged


def get_gates_for_trigger(trigger: str, cfg: dict | None = None) -> list[dict]:
    """Return enabled gates matching a specific trigger.

    Each returned dict includes a 'name' key.
    """
    all_gates = load_gates(cfg)
    result = []
    for name, gate in all_gates.items():
        if not gate.get("enabled", True):
            continue
        triggers = gate.get("trigger", [])
        if trigger in triggers:
            result.append({**gate, "name": name})
    return result


def set_gate_enabled(name: str, enable: bool) -> str:
    """Toggle a gate in the project tier and report what actually took effect.

    The write always lands in the project file, but it does not always take
    effect: the trust policy refuses a project-scope disable of a guarded gate,
    and a trusted tier can hold the opposite value outright. Reporting success
    in either case would be the silent lie this whole mechanism exists to
    remove, so the answer is derived from the EFFECTIVE config rather than from
    the write — in both directions. Shared by the CLI and the MCP handler.
    """
    from config_trust import resolve

    cfg = load_project_config()
    cfg.setdefault("gates", {}).setdefault(name, {})["enabled"] = enable
    save_config(cfg)

    effective, rejections = resolve(cfg)
    gate = effective.get("gates", {})
    gate = gate.get(name, {}) if isinstance(gate, dict) else {}
    actual = gate.get("enabled") if isinstance(gate, dict) else None
    if actual is None:
        actual = DEFAULT_GATES.get(name, {}).get("enabled", True)

    if bool(actual) == bool(enable):
        return f"Gate '{name}' {'enabled' if enable else 'disabled'}."

    verb = "enabled" if enable else "disabled"
    for r in rejections:
        if r.key == f"gates.{name}.enabled":
            return (
                f"Gate '{name}' NOT {verb} — {r.reason}. The key was written to "
                f"{get_config_path()} but the effective config keeps {r.applied!r}. "
                f"To change it for real, set it in the user tier "
                f"(~/.tausik/config.json) or in $TAUSIK_MANAGED_CONFIG."
            )
    # Backstop. With the present guard set this is unreachable: a project
    # DISABLE that a trusted tier contradicts produces a rejection above, and a
    # project ENABLE always wins because tightening wins. It stays because the
    # answer is derived from the effective config rather than from the guard
    # table — so if the table grows a case this function has not anticipated,
    # it reports the truth instead of asserting its own assumptions.
    return (
        f"Gate '{name}' NOT {verb} — a trusted config tier sets it to {actual!r} "
        f"and outranks {get_config_path()}. Change it in ~/.tausik/config.json "
        f"or in $TAUSIK_MANAGED_CONFIG."
    )


def get_service() -> ProjectService:
    """Create ProjectService with SQLite backend."""
    db_path = get_db_path()
    be = SQLiteBackend(db_path)
    return ProjectService(be)
