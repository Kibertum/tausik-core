#!/usr/bin/env python3
"""PostToolUse coaching hook — nudge agent toward narrower scope on bloated output.

When a tool (Read / Grep / Bash) returns more than `threshold` lines, emit a
single stderr line so the agent reads it next turn and adjusts strategy. We
do NOT modify the tool result — built-in tool head_limits already truncate
content; this hook is a coaching signal, not a censor.

Threshold lookup order (first hit wins):
  1. .tausik/config.json key `tool_output_truncation_threshold` (int)
  2. Env var `TAUSIK_OUTPUT_TRUNCATION_THRESHOLD` (int)
  3. Hard default = 250 lines

Skipped via TAUSIK_SKIP_HOOKS=1. Best-effort throughout: malformed stdin,
missing tool_response, IO failure → silent exit 0 so the harness keeps going.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tausik_utils import tausik_config_path  # noqa: E402

DEFAULT_THRESHOLD = 250
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
    cfg_path = tausik_config_path(project_dir)
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                cfg = json.load(f)
            v = cfg.get("tool_output_truncation_threshold")
            if isinstance(v, int) and v > 0:
                return v
        except (OSError, json.JSONDecodeError, ValueError):
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


def main() -> int:
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

    threshold = _resolve_threshold(project_dir)
    if n_lines <= threshold:
        return 0

    excess = n_lines - threshold
    print(
        f"[TAUSIK truncation nudge] {tool_name} returned {n_lines} lines "
        f"(threshold {threshold}, +{excess} over). Prefer narrower scope: "
        f"`mcp__codebase-rag__search_code` for symbols, Grep with `glob`/`path`, "
        f"or Read with `offset`/`limit`. Configure threshold via "
        f".tausik/config.json key `tool_output_truncation_threshold`.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
