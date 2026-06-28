"""Heuristic snippet/pattern classifier for Shared Brain writes (v15-snippet).

Closes the v1 stub in brain_artifact_taxonomy.py: infer the optional
``artifact_taxonomy_kind`` from the record's text when the caller did not set
it. Pure stdlib, zero deps, never raises — a misclassification is advisory only
(the value is validated and stripped exactly like a caller-supplied one).

Heuristic (gated on the presence of code-ish content, then short + low-prose):
  * code-fence (```), or YAML/JSON/CLI cues  → there is reusable code/config
  * non-blank line count ≤ 20                → small enough to be an excerpt
  * high symbol ratio (low natural prose)    → it IS the code, not prose about it
A strong hit → 'snippet'; code present but long or prose-heavy → 'pattern';
no code-ish content → None.

Public API:
    detect_artifact_kind(fields: dict) -> 'snippet' | 'pattern' | None
    maybe_autofill_snippet_kind(category, work, cfg) -> str | None
"""

from __future__ import annotations

import re
from typing import Any

# Text fields that may carry code/config across brain categories. Order is
# irrelevant — all present values are concatenated for analysis.
_TEXT_KEYS = (
    "name",
    "title",
    "description",
    "when_to_use",
    "example",
    "wrong_way",
    "right_way",
    "content",
    "problem",
    "solution",
    "body",
    "code",
)

_SNIPPET_CATEGORIES = frozenset({"patterns", "gotchas"})
_MAX_SNIPPET_LINES = 20
# Code/config is symbol-dense; English prose is symbol-sparse. 0.18 sits well
# above typical prose (~0.05-0.10) and below typical code/config (~0.25+).
_SYMBOL_RATIO_THRESHOLD = 0.18

_FENCE_RE = re.compile(r"```")
# YAML: a lowercase identifier key followed by a SINGLE-token / quoted / numeric
# value. The single-token value requirement rejects prose like "Problem: the
# cache fails." (multi-word value) and the lowercase-start rejects "Solution:".
_YAML_LINE_RE = re.compile(r"""(?m)^\s*[a-z_][\w.-]*:\s+(?:"[^"]*"|'[^']*'|\S+)\s*$""")
# JSON-ish: an object with at least one "key": pair.
_JSON_RE = re.compile(r'\{[^{}]*"[^"]+"\s*:')
# CLI: an explicit `$ ` shell prompt, or a known tool invocation that also
# carries a -flag (so a prose sentence starting with "git is great" never hits).
_CLI_RE = re.compile(
    r"(?m)^\s*(?:\$\s+\S"
    r"|(?:npm|pip|pip3|git|docker|kubectl|curl|cargo|go|yarn|pnpm|make|node|python|python3)"
    r"\b[^\n]*\s-{1,2}\w)"
)


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_stringify(v) for v in value)
    return ""


def _gather_text(fields: dict[str, Any]) -> str:
    if not isinstance(fields, dict):
        return ""
    parts = [_stringify(fields.get(k)) for k in _TEXT_KEYS if fields.get(k)]
    return "\n".join(p for p in parts if p).strip()


def _symbol_ratio(text: str) -> float:
    """Fraction of non-space chars that are neither letters nor digits.

    Code/config (braces, colons, quotes, operators) scores high; prose scores
    low. Returns 0.0 for empty input.
    """
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return 0.0
    symbols = sum(1 for c in non_space if not c.isalnum())
    return symbols / len(non_space)


# A YAML value is "config-ish" (vs a bare English word) when it is numeric,
# quoted, bracketed, or carries a separator — this is what tells real config
# apart from prose metadata like "scope: global\nauthor: john".
_YAML_CONFIGISH_VALUE_RE = re.compile(r""":\s*(?:\d|["'\[\{]|\S*[-._/:]\S)""")


def _has_config_cues(text: str) -> bool:
    if _CLI_RE.search(text) or _JSON_RE.search(text):
        return True
    yaml_lines = _YAML_LINE_RE.findall(text)
    if len(yaml_lines) < 2:
        return False  # a single "key: token" line is not a config block
    # ≥3 lines reads as structured config on its own; for exactly 2, require at
    # least one config-ish value so two bare "word: word" prose lines don't fire.
    return len(yaml_lines) >= 3 or any(_YAML_CONFIGISH_VALUE_RE.search(ln) for ln in yaml_lines)


def detect_artifact_kind(fields: dict[str, Any]) -> str | None:
    """Infer 'snippet' | 'pattern' | None from a record's text. Never raises."""
    try:
        text = _gather_text(fields)
        if not text:
            return None

        has_fence = bool(_FENCE_RE.search(text))
        has_cues = _has_config_cues(text)
        if not (has_fence or has_cues):
            return None  # no reusable code/config → ordinary knowledge

        nonblank_lines = sum(1 for ln in text.splitlines() if ln.strip())
        if nonblank_lines > _MAX_SNIPPET_LINES:
            return "pattern"  # code present but too long to be a minimal excerpt
        if has_cues:
            return "snippet"  # short + structured config (YAML/JSON/CLI) → excerpt
        # Fenced but no config cues: require code density to tell a real code block
        # apart from prose that merely wraps a sentence in a fence.
        if _symbol_ratio(text) >= _SYMBOL_RATIO_THRESHOLD:
            return "snippet"
        return "pattern"
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return None


def maybe_autofill_snippet_kind(
    category: str, work: dict[str, Any], cfg: dict[str, Any]
) -> str | None:
    """Advisory auto-fill of ``artifact_taxonomy_kind`` on ``work`` in place.

    Only fills when ALL hold: category is patterns/gotchas, the caller did not
    already supply the key, the ``auto_detect_snippet_kind`` knob is on
    (default True), and the detector returns 'snippet'. Returns the inferred
    kind if it filled, else None. Never raises and never overwrites a
    caller-supplied value.
    """
    try:
        if category not in _SNIPPET_CATEGORIES:
            return None
        if not isinstance(work, dict):
            return None
        if work.get("artifact_taxonomy_kind") is not None:
            return None
        if not cfg.get("auto_detect_snippet_kind", True):
            return None
        if detect_artifact_kind(work) == "snippet":
            work["artifact_taxonomy_kind"] = "snippet"
            return "snippet"
    except Exception:  # noqa: BLE001 — best-effort: brain op is non-fatal to the local flow
        return None
    return None
