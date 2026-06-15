"""Model routing — task_start banner over the phase x complexity matrix.

The routing *data* and the pure `suggest_model` / `format_suggestion` API live in
`model_routing_matrix` (kept separate for the 400-line filesize gate). This module
re-exports them for back-compat and adds the multi-line task_start banner, which
compares the recommendation against the transcript's active model.

Claude Code does NOT switch models programmatically; the user applies the pick via
the IDE model picker. (`/fast` toggles fast-output on Opus only — not a switch.)
"""

from __future__ import annotations

import json
import os

# Re-exported so existing importers (`from model_routing import ...`) keep working.
from model_routing_matrix import (  # noqa: F401
    DEFAULT_PHASE,
    VALID_PHASES,
    _load_config_safe,
    _model_family,
    _model_id_to_profile_slug,
    _model_tier,
    _normalize_model_id,
    format_suggestion,
    suggest_model,
)


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
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return None
    return None


def format_task_start_banner(
    complexity: str | None,
    transcript_path: str | None = None,
    active_model: str | None = None,
    phase: str | None = DEFAULT_PHASE,
    *,
    config: dict | None = None,
) -> str:
    """Multi-line banner shown by task_start.

    Output shape (3-5 lines): recommended, active, verdict, [+ mismatch hints].
    - `phase` defaults to 'implement'; it drives the recommendation via the
      phase x complexity matrix. (Surfaced through plan/explore by the
      v15mr-phase-surfaces follow-up.)
    - When active_model is supplied (test path) it is used directly.
    - When transcript_path is supplied (or None — auto-discovery) the active
      model is read via read_active_model_from_transcript.
    - When the active model can't be determined the verdict line reads
      "ⓘ active model unknown — recommendation only".
    - When normalized active_model differs from the recommendation, verdict
      is a loud "⚠ MODEL MISMATCH" line followed by two actionable hints:
      manual switch via the IDE model picker, and persist via
      `tausik config set model_profile <slug>`.
    """
    cfg = config if config is not None else _load_config_safe()
    s = suggest_model(complexity, phase, config=cfg)
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
        # Present but unrecognised family — never a false warning.
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
            # Genuinely under-powered for this tier — the real mismatch.
            verdict = f"  ⚠ MODEL MISMATCH — recommended {rec_display} (active under-powered)"
            extra_lines.append(_PICKER)
            if slug:
                extra_lines.append(
                    f"  ↪ Persist for next session: `tausik config set model_profile {slug}`"
                )
    lines = [line_recommended, line_active, verdict, *extra_lines]
    return "Model recommendation:\n" + "\n".join(lines)
