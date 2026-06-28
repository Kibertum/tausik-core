"""Phase x complexity -> Claude model recommendation (v15mr-phase-matrix).

Leaf module: the routing *data* (matrix, tier specs, family detection) plus the
pure `suggest_model` / `format_suggestion` API. `model_routing` re-exports these
and adds the task_start banner on top. Split out to keep both files under the
400-line filesize gate (Decision #112).

Claude Code does NOT switch models programmatically — the user applies the pick
via the IDE model picker. This module only produces a *recommendation*.
"""

from __future__ import annotations

import model_profiles


# --- Tier family detection (version-agnostic) --------------------------------

# Tier ordering for the mismatch verdict. Higher = more capable (and costly).
# Verdicts compare by FAMILY token (haiku/sonnet/opus/fable), never the exact
# version — so a point-release bump (opus-4-7 -> opus-4-8) never reads as a
# mismatch, and a brand-new top tier (fable) is recognised.
_TIER_ORDER: dict[str, int] = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}


# Single source of truth for id normalization lives in model_profiles. Alias
# keeps the historical private name used across this module and re-exported by
# model_routing (lowercase + strip a trailing ``[Nm]`` context-window suffix).
_normalize_model_id = model_profiles.normalize_model_id


def _model_family(model_id: str | None) -> str | None:
    """Return the tier family (haiku/sonnet/opus/fable) in a model id, or None.

    None means the id is unrecognised — callers must treat that as an
    info-class verdict, never a mismatch warning. An id containing more than
    one family token (e.g. a contrived "claude-sonnet-opus-x") is ambiguous and
    also returns None rather than silently guessing the first match.
    """
    norm = _normalize_model_id(model_id)
    if not norm:
        return None
    hits = [family for family in _TIER_ORDER if family in norm]
    return hits[0] if len(hits) == 1 else None


def _model_tier(
    model_id: str | None,
    families: dict[str, dict[str, dict[str, str]]] | None = None,
) -> int | None:
    """Return the capability tier rank for a model id, or None when unrecognised.

    Claude ids resolve via the family token (haiku/sonnet/opus/fable). When that
    fails and ``families`` is supplied, the id is looked up in the model_profiles
    reverse index — so a GLM id (which carries no Claude token) still gets a rank
    and the banner verdict no longer treats it as 'unknown'.
    """
    family = _model_family(model_id)
    if family is not None:
        return _TIER_ORDER[family]
    if families is not None:
        rank = model_profiles.rank_of(model_id, families)
        if rank is not None:
            return _TIER_ORDER.get(rank)
    return None


_PROFILE_SLUG_BY_MODEL_ID: dict[str, str] = {
    "claude-haiku-4-5": "haiku",
    "claude-sonnet-4-6": "sonnet",
    "claude-opus-4-7": "opus",
    "claude-opus-4-8": "opus",
    "claude-fable-5": "fable",
}


def _model_id_to_profile_slug(model_id: str) -> str | None:
    """Return the model_profile slug `tausik config set` accepts, or None.

    Explicit registry first (the four Claude tiers), then a family fallback so
    a future point-release id (e.g. claude-opus-4-9) still resolves.
    """
    slug = _PROFILE_SLUG_BY_MODEL_ID.get(_normalize_model_id(model_id))
    return slug if slug is not None else _model_family(model_id)


# --- Phase x complexity routing matrix (Decision #112) -----------------------
# Routing depends on BOTH complexity AND SDLC phase. Per-cell justification lives
# in docs/ru/research/model-routing-matrix.md (AC4 source of truth). Key shift
# from the v1.4 complexity-only table: Haiku is too weak for implementation, so
# the implement floor is Sonnet; Haiku is reserved for research-simple (read-only
# discovery). Planning always uses a strong planner — plan quality compounds.

# Claude tier specs — single source of truth lives in model_profiles
# (DEFAULT_FAMILIES["claude"]) so the matrix and the profile data never drift.
_TIER_SPEC: dict[str, dict[str, str]] = model_profiles.DEFAULT_FAMILIES["claude"]

DEFAULT_PHASE = "implement"
_VALID_TIERS = ("simple", "medium", "complex")

# (phase, tier) -> (primary_tier, alt_tier|None, rationale). alt_tier is the ТЗ
# "fable|opus" second choice — surfaced in rationale, never a separate return key.
_PLAN = (
    "fable",
    "opus",
    "Plan quality compounds; strong planner regardless of tier (Opus 4.8 alt).",
)
_MATRIX: dict[str, dict[str, tuple[str, str | None, str]]] = {
    "planning": {tier: _PLAN for tier in _VALID_TIERS},
    "implement": {
        "simple": ("sonnet", None, "Implementation floor — Haiku too weak for production code."),
        "medium": (
            "sonnet",
            None,
            "Multi-file changes within one module — Sonnet balances cost/capability.",
        ),
        "complex": (
            "opus",
            "fable",
            "Cross-module / architecture work — Opus earns its cost (Fable 5 alt).",
        ),
    },
    "research": {
        "simple": (
            "haiku",
            None,
            "Read-only discovery (where-is-X, symbol search) — Haiku is 10-20x cheaper.",
        ),
        "medium": ("sonnet", None, "Deeper cross-subsystem investigation — Sonnet for synthesis."),
        "complex": (
            "sonnet",
            "opus",
            "Deep multi-source research — Sonnet; escalate to Opus manually if stalled.",
        ),
    },
}

# Single source of truth for valid phases — derived from the matrix so the two
# can never drift (M2 review fix).
VALID_PHASES = tuple(_MATRIX.keys())


def _resolve_tier(complexity: str | None) -> tuple[str, str | None]:
    """Map a raw complexity to a matrix tier key.

    Returns (tier_key, note): note is None for an exact match, else an
    explanatory string. None / unrecognised complexity falls back to 'medium'.
    """
    if complexity is None:
        return "medium", (
            "Complexity not specified — defaulting to the medium tier. Set it "
            "(`tausik task update <slug> --complexity simple|medium|complex`) for a targeted pick."
        )
    key = str(complexity).strip().lower()
    if key in _VALID_TIERS:
        return key, None
    return "medium", (
        f"Unknown complexity '{complexity}'. Expected one of: simple, medium, complex. "
        "Defaulting to the medium tier; run `tausik task update --complexity <value>` to refine."
    )


def _normalize_phase(phase: str | None) -> str:
    """Validate + normalise a phase. Unknown -> ValueError listing valid phases."""
    if phase is None:
        return DEFAULT_PHASE
    key = str(phase).strip().lower()
    if key not in _MATRIX:
        raise ValueError(f"Unknown phase '{phase}'. Expected one of: {', '.join(VALID_PHASES)}.")
    return key


def _spec_from_tier(
    tier: str,
    rationale: str,
    *,
    family: str | None = None,
    config: dict | None = None,
) -> dict[str, str]:
    """Resolve a capability tier to a concrete {model, display} for ``family``.

    family None/'claude' keeps the canonical Claude spec (back-compat — callers
    that don't pass family get identical output). Any other family resolves via
    model_profiles, falling back to the Claude spec for ranks it doesn't define.
    """
    if family is None or family.strip().lower() == "claude":
        base = _TIER_SPEC[tier]
        return {"model": base["model"], "display": base["display"], "rationale": rationale}
    families = model_profiles.load_families(config)
    spec = model_profiles.spec_for(family, tier, families)
    if spec is None:
        base = _TIER_SPEC[tier]
        return {"model": base["model"], "display": base["display"], "rationale": rationale}
    return {"model": spec["model"], "display": spec["display"], "rationale": rationale}


def _override_model_id(config: dict | None, phase: str, tier: str) -> str | None:
    """Resolve a config override model id for (phase, tier), or None.

    Schema under root `.tausik/config.json` "model_routing":
        {"<phase>": "<model_id>"}                       # one model for all tiers
        {"<phase>": {"<tier>": "<model_id>", ...}}       # per-tier override
    Malformed / missing entries return None (base matrix wins) — never raises.
    """
    if not config:
        return None
    mr = config.get("model_routing")
    if not isinstance(mr, dict):
        return None
    cell = mr.get(phase)
    if isinstance(cell, str):
        return cell.strip() or None
    if isinstance(cell, dict):
        val = cell.get(tier)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def _spec_from_model_id(model_id: str, rationale: str) -> dict[str, str]:
    # Honest display (H2 review fix): only use the registered tier label when the
    # id EXACTLY matches that tier's canonical model. A same-family but different
    # version (e.g. an override of claude-opus-4-9) must show its own id, not lie
    # as "Opus 4.8".
    family = _model_family(model_id)
    norm = _normalize_model_id(model_id)
    if family in _TIER_SPEC and norm == _TIER_SPEC[family]["model"]:
        display = _TIER_SPEC[family]["display"]
    else:
        display = model_id
    return {"model": model_id, "display": display, "rationale": rationale}


def _load_config_safe() -> dict:
    """Best-effort load of `.tausik/config.json`; {} on any failure."""
    try:
        import importlib

        pc = importlib.import_module("project_config")
        loader = getattr(pc, "load_config", None)
        if callable(loader):
            cfg = loader()
            return cfg if isinstance(cfg, dict) else {}
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return {}
    return {}


def suggest_model(
    complexity: str | None,
    phase: str | None = DEFAULT_PHASE,
    *,
    config: dict | None = None,
    family: str | None = None,
) -> dict[str, str]:
    """Return {model, display, rationale} for a (complexity, phase) cell.

    - `phase` defaults to 'implement' (single-arg callers are unchanged).
      Case-insensitive; unknown phase raises ValueError listing valid phases.
    - `complexity` is case-insensitive; None or an unrecognised value falls
      back to the phase's 'medium' column with an explanatory rationale.
    - `config` (root `.tausik/config.json` dict) may override a cell via the
      "model_routing" section. When None, NO override is applied (pure call);
      user-facing surfaces auto-load it (see `format_suggestion`).
    """
    ph = _normalize_phase(phase)
    tier, note = _resolve_tier(complexity)
    primary_tier, _alt, base_rationale = _MATRIX[ph][tier]

    override = _override_model_id(config, ph, tier)
    if override is not None:
        rationale = f"Config override (.tausik/config.json model_routing.{ph}). {base_rationale}"
        return _spec_from_model_id(override, rationale)

    rationale = base_rationale if note is None else f"{note} {base_rationale}"
    return _spec_from_tier(primary_tier, rationale, family=family, config=config)


def format_suggestion(
    complexity: str | None,
    phase: str | None = DEFAULT_PHASE,
    *,
    config: dict | None = None,
) -> str:
    """One-line formatted suggestion for CLI output.

    Auto-loads config via `project_config.load_config()` when `config` is not
    passed explicitly, so the CLI honours user model_routing overrides. Pass
    `config={}` to suppress all overrides (and avoid the file read — important
    for hermetic tests).
    """
    cfg = config if config is not None else _load_config_safe()
    s = suggest_model(complexity, phase, config=cfg)
    return f"{s['display']} ({s['model']}): {s['rationale']}"
