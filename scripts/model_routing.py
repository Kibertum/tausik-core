"""Model routing suggestions — match Claude model to task complexity.

Claude Code does NOT accept programmatic model switches mid-session; the user
picks the model via /fast or settings. This module produces a *recommendation*
that TAUSIK surfaces in task output, so the user can apply it manually.

Principle (oh-my-claudecode cost optimisation): 30–50% token savings when
simple work runs on Haiku instead of Opus.
"""

from __future__ import annotations


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
