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


def _price_pair(value: object, key: str) -> dict[str, float] | None:
    """One config price as ``{input, output}``, or None if it is not usable.

    TWO ACCEPTED SHAPES, and the second one is the point. A bare number is the
    original schema and still works, but it necessarily prices input and output
    THE SAME — no real tariff does that, so every model priced through this
    config was wrong by construction, in a direction nobody could see. An object
    ``{"input": x, "output": y}`` states the real thing. A bare number is read as
    "both directions at this rate", which is what it always meant; it is kept for
    compatibility, not because it can express a tariff.
    """

    def _num(raw: object) -> float | None:
        try:
            val = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if val != val or val < 0:  # NaN or negative
            return None
        return val

    if isinstance(value, dict):
        got_in, got_out = _num(value.get("input")), _num(value.get("output"))
        if got_in is None or got_out is None:
            logger.warning(
                "Skipping llm_pricing_usd_per_million for %r — an object price needs "
                "non-negative numeric 'input' and 'output'",
                key,
            )
            return None
        return {"input": got_in, "output": got_out}
    flat = _num(value)
    if flat is None:
        # Two different mistakes, two different messages: a number that is out
        # of range is not the same error as a value that is not a number, and
        # collapsing them makes the log useless for fixing the config.
        try:
            float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            logger.warning(
                "Skipping llm_pricing_usd_per_million entry %r — not a number and not "
                "an {'input': x, 'output': y} object",
                key,
            )
        else:
            logger.warning(
                "Skipping llm_pricing_usd_per_million for %r — negative price not allowed",
                key,
            )
        return None
    return {"input": flat, "output": flat}


def normalize_llm_pricing_config(cfg: dict | None) -> dict:
    """Validate ``llm_pricing_usd_per_million``: ``model_id`` → USD per 1M tokens.

    A value is either a number (both directions at that rate) or an object with
    ``input`` and ``output``. Normalized to the object form either way, so every
    consumer sees one shape.
    """

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
    clean: dict[str, dict[str, float]] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if not key:
            continue
        pair = _price_pair(v, key)
        if pair is not None:
            clean[key] = pair
    out["llm_pricing_usd_per_million"] = clean
    return out


def lookup_llm_pricing_pair(cfg: dict | None, model_id: str | None) -> dict[str, float] | None:
    """``{input, output}`` USD per 1M tokens for *exact* ``model_id``, else None.

    Tolerates a config that never went through :func:`normalize_llm_pricing_config`
    — a caller-supplied dict may still carry the raw number form.
    """
    if not cfg or model_id is None:
        return None
    tbl = cfg.get("llm_pricing_usd_per_million")
    if not isinstance(tbl, dict):
        return None
    key = model_id.strip()
    if not key or key not in tbl:
        return None
    return _price_pair(tbl[key], key)


def lookup_llm_usd_per_million_tokens(cfg: dict | None, model_id: str | None) -> float | None:
    """USD per million tokens for *exact* ``model_id`` match, else ``None``.

    Retained for compatibility; returns the INPUT rate. Prefer
    :func:`lookup_llm_pricing_pair`, which distinguishes input from output —
    this one cannot, and a single number is not a tariff.
    """

    pair = lookup_llm_pricing_pair(cfg, model_id)
    return None if pair is None else pair["input"]


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
