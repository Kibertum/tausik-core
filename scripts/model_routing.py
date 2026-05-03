"""Model routing suggestions — match Claude model to task complexity.

Claude Code does NOT accept programmatic model switches mid-session; the user
picks the model via /fast or settings. This module produces a *recommendation*
that TAUSIK surfaces in task output, so the user can apply it manually.

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


def _normalize_model_id(raw: str | None) -> str:
    """Strip 1M-context [Nm] (and similar) suffixes for comparison."""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    return _BRACKET_SUFFIX.sub("", s).strip()


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

    Output shape (3 lines): recommended, active, verdict.
    - When active_model is supplied (test path) it is used directly.
    - When transcript_path is supplied (or None — auto-discovery) the active
      model is read via read_active_model_from_transcript.
    - When the active model can't be determined the verdict line reads
      "ⓘ active model unknown — recommendation only".
    - When normalized active_model differs from the recommendation, verdict
      is a loud "⚠ MODEL MISMATCH" line; otherwise "✓ model match".
    """
    s = suggest_model(complexity)
    rec_id = s["model"]
    rec_display = s["display"]
    if active_model is None:
        path = transcript_path if transcript_path is not None else _auto_find_transcript()
        active_model = read_active_model_from_transcript(path)
    rec_norm = _normalize_model_id(rec_id)
    active_norm = _normalize_model_id(active_model)
    line_recommended = (
        f"  recommended: {rec_display} ({rec_id}) — {complexity or 'no complexity set'}"
    )
    if active_norm:
        line_active = f"  active:      {active_model}"
        if rec_norm == active_norm:
            verdict = "  ✓ model match"
        else:
            verdict = (
                f"  ⚠ MODEL MISMATCH — switch to {rec_display} via /fast or model picker "
                "for cost savings"
            )
    else:
        line_active = "  active:      unknown (no transcript readable)"
        verdict = "  ⓘ active model unknown — recommendation only"
    return "Model recommendation:\n" + "\n".join([line_recommended, line_active, verdict])
