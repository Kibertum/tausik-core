"""Model profiles — vendor families × capability ranks as DATA (Decision #119, axis-2).

The routing matrix produces an abstract *capability rank* (lowest→flagship). The
concrete model id that fills a rank depends on the active *vendor family*
(Claude, GLM/z.ai, …). Keeping that mapping as data — built-in defaults here,
overridable/extendable via ``.tausik/config.json`` ``model_profiles.families`` —
means adding or switching z.ai GLM models needs NO code change.

Ranks are named after Claude tiers (haiku/sonnet/opus/fable) for historical
continuity: the matrix already speaks those keys. Treat them as ABSTRACT ranks
(0=lightest … 3=flagship) that each family maps its own models onto.
"""

from __future__ import annotations

import re

# Capability ranks, lowest→flagship. The index IS the tier order used for
# under/over-powered verdicts.
RANKS: tuple[str, ...] = ("haiku", "sonnet", "opus", "fable")

_BRACKET_SUFFIX = re.compile(r"\[[^\[\]]+\]\s*$")

# Built-in defaults — zero-config UX. Claude mirrors the canonical tiers; GLM is
# a starter lineup (refined in the glm-profiles task / overridable via config).
DEFAULT_FAMILIES: dict[str, dict[str, dict[str, str]]] = {
    "claude": {
        "haiku": {"model": "claude-haiku-4-5", "display": "Haiku 4.5"},
        "sonnet": {"model": "claude-sonnet-4-6", "display": "Sonnet 4.6"},
        "opus": {"model": "claude-opus-4-8", "display": "Opus 4.8"},
        "fable": {"model": "claude-fable-5", "display": "Fable 5"},
    },
    "glm": {
        "haiku": {"model": "glm-4.5-air", "display": "GLM-4.5-Air"},
        "sonnet": {"model": "glm-4.6", "display": "GLM-4.6"},
        "opus": {"model": "glm-4.6", "display": "GLM-4.6"},
        "fable": {"model": "glm-4.6", "display": "GLM-4.6"},
    },
}

# Vendor token fallback when a model id is not found in the (merged) families
# reverse index — keeps detection working for point-release ids not yet listed.
_VENDOR_TOKENS: tuple[str, ...] = ("claude", "glm", "qwen")


def normalize_model_id(raw: str | None) -> str:
    """Lowercase + strip a trailing ``[Nm]`` context-window suffix for matching."""
    if not raw:
        return ""
    return _BRACKET_SUFFIX.sub("", str(raw).strip().lower()).strip()


def load_families(config: dict | None) -> dict[str, dict[str, dict[str, str]]]:
    """Merge ``config['model_profiles']['families']`` over the built-in defaults.

    Malformed entries are skipped (never raise): a family must be a dict of
    rank→{model[,display]}; unknown ranks and non-string/empty models are
    dropped. ``display`` defaults to the model id when absent.
    """
    fams: dict[str, dict[str, dict[str, str]]] = {
        f: {r: dict(spec) for r, spec in ranks.items()} for f, ranks in DEFAULT_FAMILIES.items()
    }
    if not isinstance(config, dict):
        return fams
    mp = config.get("model_profiles")
    if not isinstance(mp, dict):
        return fams
    cfg_fams = mp.get("families")
    if not isinstance(cfg_fams, dict):
        return fams
    for fam, ranks in cfg_fams.items():
        if not isinstance(ranks, dict):
            continue
        dst = fams.setdefault(str(fam).strip().lower(), {})
        for rank, spec in ranks.items():
            if rank not in RANKS or not isinstance(spec, dict):
                continue
            model = spec.get("model")
            if not isinstance(model, str) or not model.strip():
                continue
            display = spec.get("display")
            dst[rank] = {
                "model": model.strip(),
                "display": display.strip()
                if isinstance(display, str) and display.strip()
                else model.strip(),
            }
    return fams


def default_family(config: dict | None) -> str | None:
    """Optional ``model_profiles.default_family`` — the family to recommend for
    when the active model can't be detected (e.g. Kilo without KILO_MODEL)."""
    if not isinstance(config, dict):
        return None
    mp = config.get("model_profiles")
    if not isinstance(mp, dict):
        return None
    fam = mp.get("default_family")
    if isinstance(fam, str) and fam.strip():
        return fam.strip().lower()
    return None


def reverse_index(families: dict[str, dict[str, dict[str, str]]]) -> dict[str, tuple[str, str]]:
    """Map normalized model id → (family, highest rank it fills).

    Highest rank wins when one model fills several ranks (e.g. a single flagship
    GLM): its true capability is the top rank it satisfies.
    """
    idx: dict[str, tuple[str, str]] = {}
    for fam, ranks in families.items():
        for rank, spec in ranks.items():
            mid = normalize_model_id(spec.get("model"))
            if not mid:
                continue
            cur = idx.get(mid)
            if cur is None or RANKS.index(cur[1]) < RANKS.index(rank):
                idx[mid] = (fam, rank)
    return idx


def vendor_of(model_id: str | None, families: dict[str, dict[str, dict[str, str]]]) -> str | None:
    """Vendor family for a model id: reverse-index hit first, then token heuristic."""
    norm = normalize_model_id(model_id)
    if not norm:
        return None
    hit = reverse_index(families).get(norm)
    if hit is not None:
        return hit[0]
    for tok in _VENDOR_TOKENS:
        if tok in norm:
            return tok
    return None


def rank_of(model_id: str | None, families: dict[str, dict[str, dict[str, str]]]) -> str | None:
    """Capability rank (haiku/…/fable) for a model id, or None if unknown."""
    norm = normalize_model_id(model_id)
    if not norm:
        return None
    hit = reverse_index(families).get(norm)
    return hit[1] if hit is not None else None


def spec_for(
    family: str | None,
    rank: str,
    families: dict[str, dict[str, dict[str, str]]],
) -> dict[str, str] | None:
    """The {model, display} for (family, rank), falling back to the claude family
    when the requested family lacks that rank. None only if even claude lacks it."""
    fam = (family or "claude").strip().lower()
    ranks = families.get(fam)
    if isinstance(ranks, dict) and rank in ranks:
        return dict(ranks[rank])
    claude = families.get("claude", {})
    if rank in claude:
        return dict(claude[rank])
    return None
