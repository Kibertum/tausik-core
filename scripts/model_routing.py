"""Model routing suggestions — match Claude model to task complexity.

Claude Code does NOT accept programmatic model switches mid-session; the user
picks the model via the IDE model picker. (Note: `/fast` toggles faster output
on Opus 4.6 and does NOT downgrade to a smaller model — it is not a switch.)
This module produces a *recommendation* that TAUSIK surfaces in task output,
so the user can apply it manually, plus a persist hint via
`tausik config set model_profile <slug>` for the next session.

Principle (oh-my-claudecode cost optimisation): 30–50% token savings when
simple work runs on Haiku instead of Opus.
"""

from __future__ import annotations

import json
import os
import re


_ROUTING = {
    "simple": {
        "model": "claude-haiku-4-5",
        "display": "Haiku 4.5",
        "rationale": "Simple tasks (1 SP): single-file edits, doc tweaks, lint fixes. Haiku is 10-20× cheaper than Opus with similar quality for this tier.",
    },
    "medium": {
        "model": "claude-sonnet-4-6",
        "display": "Sonnet 4.6",
        "rationale": "Medium tasks (3 SP): multi-file changes, refactors, new features within one module. Sonnet balances cost and capability.",
    },
    "complex": {
        "model": "claude-opus-4-7",
        "display": "Opus 4.7",
        "rationale": "Complex tasks (8 SP): cross-module refactors, architecture, ambiguous requirements. Opus earns its cost on hard reasoning.",
    },
}

_DEFAULT = dict(_ROUTING["medium"])
_DEFAULT["rationale"] = (
    "Complexity not specified — defaulting to Sonnet. Set task complexity "
    "(`tausik task update <slug> --complexity simple|medium|complex`) for a targeted pick."
)


def suggest_model(complexity: str | None) -> dict[str, str]:
    """Return {model, display, rationale} for the given complexity.

    Case-insensitive. Unknown values fall back to Sonnet with a warning rationale.
    """
    if complexity is None:
        return dict(_DEFAULT)
    key = str(complexity).strip().lower()
    if key in _ROUTING:
        return dict(_ROUTING[key])
    fallback = dict(_DEFAULT)
    fallback["rationale"] = (
        f"Unknown complexity '{complexity}'. Expected one of: simple, medium, complex. "
        "Defaulting to Sonnet; run `tausik task update --complexity <value>` to refine."
    )
    return fallback


def format_suggestion(complexity: str | None) -> str:
    """One-line formatted suggestion for CLI output."""
    s = suggest_model(complexity)
    return f"{s['display']} ({s['model']}): {s['rationale']}"


_BRACKET_SUFFIX = re.compile(r"\[[^\[\]]+\]\s*$")

# Tier ordering for the mismatch verdict. Higher = more capable (and costly).
# Verdicts compare by FAMILY token (haiku/sonnet/opus/fable), never the exact
# version — so a point-release bump (claude-opus-4-7 -> claude-opus-4-8) never
# reads as a mismatch, and a brand-new top tier (fable) is recognised rather
# than triggering a false "MODEL MISMATCH" against every recommendation.
_TIER_ORDER: dict[str, int] = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}


def _normalize_model_id(raw: str | None) -> str:
    """Strip 1M-context [Nm] (and similar) suffixes for comparison."""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    return _BRACKET_SUFFIX.sub("", s).strip()


def _model_family(model_id: str | None) -> str | None:
    """Return the tier family (haiku/sonnet/opus/fable) in a model id, or None.

    None means the id is unrecognised — callers must treat that as an
    info-class verdict, never a mismatch warning.
    """
    norm = _normalize_model_id(model_id)
    if not norm:
        return None
    for family in _TIER_ORDER:
        if family in norm:
            return family
    return None


def _model_tier(model_id: str | None) -> int | None:
    """Return the tier rank for a model id, or None when unrecognised."""
    family = _model_family(model_id)
    return _TIER_ORDER[family] if family is not None else None


def read_active_model_from_transcript(transcript_path: str | None) -> str | None:
    """Return the most-recent assistant model id from a JSONL transcript.

    Walks the transcript backwards and returns the first non-empty `model`
    field encountered (under top-level or nested `message`). Returns None
    when the path is missing/unreadable, the file is empty, or no model
    field is present — callers must treat None as "unknown".
    """
    if not transcript_path or not os.path.isfile(transcript_path):
        return None
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return None
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        model = entry.get("model")
        if not model:
            inner = entry.get("message")
            if isinstance(inner, dict):
                model = inner.get("model")
        if model:
            return str(model).strip()
    return None


def _auto_find_transcript() -> str | None:
    """Best-effort discovery of the active Claude Code transcript.

    Reuses session_metrics.auto_find_transcript when available; returns None
    if that helper isn't importable (e.g. minimal install). Errors are
    swallowed so a missing transcript never breaks task_start.
    """
    try:
        # Lazy import — keeps model_routing free of hooks/* import chains
        # for callers that only want suggest_model.
        import importlib

        sm = importlib.import_module("hooks.session_metrics")
        finder = getattr(sm, "auto_find_transcript", None)
        if callable(finder):
            return finder()  # type: ignore[no-any-return]
    except Exception:
        return None
    return None


def format_task_start_banner(
    complexity: str | None,
    transcript_path: str | None = None,
    active_model: str | None = None,
) -> str:
    """Multi-line banner shown by task_start.

    Output shape (3-5 lines): recommended, active, verdict, [+ mismatch hints].
    - When active_model is supplied (test path) it is used directly.
    - When transcript_path is supplied (or None — auto-discovery) the active
      model is read via read_active_model_from_transcript.
    - When the active model can't be determined the verdict line reads
      "ⓘ active model unknown — recommendation only".
    - When normalized active_model differs from the recommendation, verdict
      is a loud "⚠ MODEL MISMATCH" line followed by two actionable hints:
      manual switch via the IDE model picker, and persist via
      `tausik config set model_profile <slug>`. Note: `/fast` is NOT a switch —
      it only toggles fast-output on Opus 4.6.
    """
    s = suggest_model(complexity)
    rec_id = s["model"]
    rec_display = s["display"]
    if active_model is None:
        path = transcript_path if transcript_path is not None else _auto_find_transcript()
        active_model = read_active_model_from_transcript(path)
    rec_tier = _model_tier(rec_id)
    active_tier = _model_tier(active_model)
    line_recommended = (
        f"  recommended: {rec_display} ({rec_id}) — {complexity or 'no complexity set'}"
    )
    extra_lines: list[str] = []
    _PICKER = (
        "  ⓘ Mid-session switch: use the IDE model picker "
        "(Claude Code has no programmatic switch — `/fast` toggles fast-output on Opus only)"
    )
    slug = _model_id_to_profile_slug(rec_id)
    if not active_model:
        line_active = "  active:      unknown (no transcript readable)"
        verdict = "  ⓘ active model unknown — recommendation only"
    elif active_tier is None:
        # Present but unrecognised family — never a false warning (AC3).
        line_active = f"  active:      {active_model}"
        verdict = f"  ⓘ active model '{active_model}' unrecognized — recommendation only"
    else:
        line_active = f"  active:      {active_model}"
        if rec_tier is None or active_tier == rec_tier:
            verdict = "  ✓ model match"
        elif active_tier > rec_tier:
            # Higher tier than needed: quality surplus, not a defect. Nudge
            # toward the cheaper recommended tier instead of a loud warning.
            verdict = (
                f"  ⓘ quality surplus — active exceeds recommended {rec_display}; "
                "switch down to save cost"
            )
            extra_lines.append(_PICKER.replace("Mid-session switch", "Switch down"))
            if slug:
                extra_lines.append(
                    f"  ↪ Persist cheaper tier next session: `tausik config set model_profile {slug}`"
                )
        else:
            # Genuinely under-powered for this tier — the real mismatch (AC2).
            verdict = f"  ⚠ MODEL MISMATCH — recommended {rec_display} (active under-powered)"
            extra_lines.append(_PICKER)
            if slug:
                extra_lines.append(
                    f"  ↪ Persist for next session: `tausik config set model_profile {slug}`"
                )
    lines = [line_recommended, line_active, verdict, *extra_lines]
    return "Model recommendation:\n" + "\n".join(lines)


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
    a future point-release id (e.g. claude-opus-4-9) still resolves. Other
    model ids (GPT/Qwen overlays) come from upstream profile work and aren't
    reachable from suggest_model today.
    """
    slug = _PROFILE_SLUG_BY_MODEL_ID.get(_normalize_model_id(model_id))
    return slug if slug is not None else _model_family(model_id)
