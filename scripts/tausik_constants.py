"""TAUSIK leaf constants + pure config-value helpers (project-config-god-module-split).

Extracted from ``project_config`` so the config LOADER no longer has to carry — and
be imported alongside — the session-duration constants, the context-tier enum, and
the LLM-pricing normaliser. Dependency-light: this module imports only stdlib, so
anything (a hook, a future standalone package) can read these values without
dragging the config/trust/DB machinery. ``project_config`` re-exports every name
here, so existing ``from project_config import X`` call sites are unchanged.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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
# Warn threshold (minutes): a duration nudge fires before the hard cap above.
DEFAULT_SESSION_WARN_THRESHOLD_MINUTES = 150
# Gap (minutes) above which a pause is treated as AFK, excluded from active time.
# Tunable via .tausik/config.json "session_idle_threshold_minutes".
DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES = 10

# --- Agent-native session capacity (tool calls, not minutes) ---
DEFAULT_SESSION_CAPACITY_CALLS = 200
