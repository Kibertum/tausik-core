#!/usr/bin/env python3
"""PostToolUse coaching hook — nudge agent toward narrower scope on bloated output.

Two thresholds, because ONE OF THEM CANNOT SEE THE OTHER'S DEFECT. A line count
does not notice a single enormous line — a minified file, JSON on one line, a log
without newlines — and that output enters the context in full while the line
counter reads "1". A byte count does not notice five hundred short lines. Both
are cheap; neither substitutes for the other.

The byte threshold is set from measurement, not taste. Session #229: the delta
from one call to the next, inside one session, over 9,844 Bash calls — median
848, p90 2,514, p99 6,386. The default below sits near that p99, so the nudge
speaks about the calls that actually cost something rather than about every
second command.

READ THAT DELTA CAREFULLY, because a first version of this note did not. It
contains TWO things: the tool's result AND the model's own output on that turn
(reasoning, text, the tool_use block). Split on the same 14,048 pairs: the
model's output is 12,895,606 of 18,009,761 tokens — 71.6% — and tool results
plus framing are 28.4%. Within Bash specifically, 60.4% of the delta is the
model writing and 39.6% is the command's result, so BASH RESULTS ARE 26.3% OF
ALL GROWTH, not the 66.4% the delta suggests. The threshold is unaffected: p99
was computed on the delta and the delta has not changed. What changes is the
claim — capping command output is worth 26.3%, and the larger lever is the shape
of the model's own answer.

That measurement also corrected the premise it was gathered under: the growth is
BROAD, not tail-heavy (the top 1% of Bash calls is only 6.8% of Bash growth), and
no catastrophic single result appears in the corpus — because the Claude Code
harness truncates tool output itself. On a host that does not, it would. The byte
threshold is therefore worth most exactly where the framework promises the least
today: on hosts other than this one.

We do NOT modify the tool result and we do NOT block the call. This is a coaching
signal, not a censor.

Threshold lookup order (first hit wins), independently for each threshold:
  1. .tausik/config.json key `tool_output_truncation_threshold` (lines, int)
     / `tool_output_truncation_bytes` (bytes, int)
  2. Env var `TAUSIK_OUTPUT_TRUNCATION_THRESHOLD` / `..._BYTES` (int)
  3. Hard defaults = 250 lines, 24000 bytes

Skipped via TAUSIK_SKIP_HOOKS=1. Best-effort throughout: malformed stdin,
missing tool_response, IO failure → silent exit 0 so the harness keeps going.
"""

from __future__ import annotations

import json
import os
import sys

# Own directory FIRST: `_common` below is a SIBLING imported by bare name, and
# scripts/hooks reaches sys.path only when this file is RUN as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _common import force_utf8_io  # noqa: E402
from tausik_utils import load_effective_config  # noqa: E402

DEFAULT_THRESHOLD = 250

#: ~6,000 tokens at 4 bytes/token — just above the measured p99 of Bash's
#: per-call context growth (6,386 tokens). Below this the nudge would fire on
#: ordinary work and be learned into invisibility; above it, the calls that
#: actually move the context would pass unremarked.
DEFAULT_BYTE_THRESHOLD = 24000

WATCHED_TOOLS = {"Read", "Grep", "Bash", "Glob"}


def _load_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_threshold(project_dir: str) -> int:
    # Was a raw json.load of the project file, ignoring the user/managed tiers
    # (hooks-bypass-config-trust-tiers). load_effective_config merges the tiers so
    # an operator's machine-wide threshold is honoured. Lookup order unchanged:
    # config key first, then env, then the hard default.
    try:
        cfg = load_effective_config(project_dir)
        v = cfg.get("tool_output_truncation_threshold")
        if isinstance(v, int) and v > 0:
            return v
    except (OSError, ValueError, TypeError):
        pass
    env = os.environ.get("TAUSIK_OUTPUT_TRUNCATION_THRESHOLD", "")
    if env.strip():
        try:
            n = int(env.strip())
            if n > 0:
                return n
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


def _resolve_byte_threshold(project_dir: str) -> int:
    """Same lookup order as the line threshold, its own keys.

    Separate keys on purpose: a project that wants to hear about long files but
    not about wide ones (or the reverse) must be able to say so. One shared knob
    would force a single answer onto two different questions.
    """
    try:
        cfg = load_effective_config(project_dir)
        v = cfg.get("tool_output_truncation_bytes")
        if isinstance(v, int) and v > 0:
            return v
    except (OSError, ValueError, TypeError):
        pass
    env = os.environ.get("TAUSIK_OUTPUT_TRUNCATION_BYTES", "")
    if env.strip():
        try:
            n = int(env.strip())
            if n > 0:
                return n
        except ValueError:
            pass
    return DEFAULT_BYTE_THRESHOLD


def _extract_output_text(payload: dict) -> str:
    """Best-effort: pull the tool's textual output out of tool_response.

    Claude Code passes tool results in `tool_response`. The shape varies by
    tool — sometimes a plain string, sometimes a dict with `content` (list
    of {type, text} parts) or `output` / `text`. We collect any text we
    can find without raising.
    """
    response = payload.get("tool_response")
    if isinstance(response, str):
        return response
    if not isinstance(response, dict):
        return ""

    for key in ("output", "text", "stdout"):
        v = response.get(key)
        if isinstance(v, str):
            return v

    content = response.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(item, str):
                parts.append(item)
        if parts:
            return "\n".join(parts)
    return ""


def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def count_bytes(text: str) -> int:
    """UTF-8 bytes, not characters. Cyrillic output costs two bytes per letter,
    and a threshold that counted characters would be twice as loose on it."""
    if not text:
        return 0
    return len(text.encode("utf-8", "replace"))


def build_nudge(tool_name: str, n_lines: int, n_bytes: int, lines_max: int, bytes_max: int) -> str:
    """The advice line, or "" when neither threshold is exceeded.

    Says WHICH threshold tripped, because the two have different cures: too many
    lines means narrow the query, too many bytes on few lines means cap the
    output. Advice that does not say what to do is noise, and noise gets learned
    into invisibility.
    """
    over_lines = n_lines > lines_max
    over_bytes = n_bytes > bytes_max
    if not (over_lines or over_bytes):
        return ""
    parts = []
    if over_lines:
        parts.append(f"{n_lines} lines (threshold {lines_max}, +{n_lines - lines_max} over)")
    if over_bytes:
        parts.append(f"{n_bytes:,} bytes (threshold {bytes_max:,})")
    cure = (
        "Prefer narrower scope: `mcp__codebase-rag__search_code` for symbols, "
        "Grep with `glob`/`path`, or Read with `offset`/`limit`."
    )
    if over_bytes and not over_lines:
        cure = (
            "Few lines, many bytes — a line limit cannot see this. Cap the OUTPUT: "
            f"append `| head -c {bytes_max}` (or `cut -c1-200`) to a command whose "
            "result size you do not know in advance."
        )
    elif over_bytes:
        cure += (
            f" The byte threshold tripped too, so a line limit alone will not help: "
            f"cap with `| head -c {bytes_max}`."
        )
    return (
        f"[TAUSIK truncation nudge] {tool_name} returned " + " and ".join(parts) + ". "
        f"{cure} Configure via .tausik/config.json keys "
        "`tool_output_truncation_threshold` (lines) / `tool_output_truncation_bytes`."
    )


def main() -> int:
    # The advice line carries an em dash, so the stream must be UTF-8 before it
    # is written: on a cp1252 console the message would die, and a coaching hook
    # that crashes on the machine it is coaching is worse than no hook.
    force_utf8_io()
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    payload = _load_payload()

    tool_name = payload.get("tool_name") if isinstance(payload, dict) else None
    if not isinstance(tool_name, str) or tool_name not in WATCHED_TOOLS:
        return 0

    text = _extract_output_text(payload)
    n_lines = count_lines(text)
    if n_lines == 0:
        return 0

    message = build_nudge(
        tool_name,
        n_lines,
        count_bytes(text),
        _resolve_threshold(project_dir),
        _resolve_byte_threshold(project_dir),
    )
    if message:
        # Numbers and the tool's name only. The output itself is never echoed:
        # a hook that exists to save context has no business copying the very
        # content it is complaining about into the log.
        print(message, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
