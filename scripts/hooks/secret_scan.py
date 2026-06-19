#!/usr/bin/env python3
"""PreToolUse Write/Edit hook — scan tool_input for likely secrets.

SENAR Rule 10.12 (Context Hygiene): keep credentials and project-specific
secrets out of agent context and out of files the agent writes. Brain
already enforces this on the write path; this hook closes the gap on
local Edit/Write/MultiEdit calls.

Behaviour:
  - Read JSON payload from stdin (Claude Code hook contract).
  - Walk tool_input string fields for known-bad regex patterns: AWS keys,
    Slack/Stripe/GitHub/OpenAI/Anthropic tokens, JWT-like tokens,
    private-key headers.
  - On match — print a stderr **warning** listing the detector(s) and exit 0
    (non-blocking). Set `TAUSIK_SECRET_SCAN_STRICT=1` to upgrade to a
    hard block (exit 2).
  - Skipped via TAUSIK_SKIP_HOOKS=1.

Designed to be cheap (≤1 ms per call on a 4 KB input) and zero-deps.
"""

from __future__ import annotations

import json
import os
import re
import sys

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"\baws_secret(?:_access)?_key\b\s*[:=]\s*[A-Za-z0-9/+]{40}")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")),
    ("github_oauth", re.compile(r"\bgho_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[abp]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{24,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{32,}\b")),
    ("notion_secret", re.compile(r"\b(?:secret|ntn)_[A-Za-z0-9]{32,}\b")),
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"
        ),
    ),
    ("jwt_token", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    (
        "generic_secret_assignment",
        re.compile(
            r"\b(?:api_key|apikey|secret|token|password|passwd)\s*[:=]\s*['\"][A-Za-z0-9/+_=\-]{20,}['\"]",
            re.IGNORECASE,
        ),
    ),
]

_MAX_FIELD = 50_000


def _walk(value, hits: list[tuple[str, str]]) -> None:
    if isinstance(value, str):
        if len(value) > _MAX_FIELD:
            value = value[:_MAX_FIELD]
        for name, pat in _PATTERNS:
            m = pat.search(value)
            if m:
                hits.append((name, m.group(0)[:80]))
        return
    if isinstance(value, dict):
        for v in value.values():
            _walk(v, hits)
        return
    if isinstance(value, (list, tuple)):
        for v in value:
            _walk(v, hits)


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, EOFError):
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_name = payload.get("tool_name") or ""
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0
    tool_input = payload.get("tool_input") or {}
    hits: list[tuple[str, str]] = []
    _walk(tool_input, hits)
    if not hits:
        return 0

    seen: set[str] = set()
    lines: list[str] = []
    for name, sample in hits:
        key = f"{name}:{sample}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  - {name}: {sample!r}")
    print(
        "[TAUSIK secret-scan] Possible secrets detected in pending Write/Edit:\n"
        + "\n".join(lines)
        + "\nRotate the credential and remove the literal from your changes.\n"
        "  Strict mode: set TAUSIK_SECRET_SCAN_STRICT=1 to block instead of warn.",
        file=sys.stderr,
    )
    if os.environ.get("TAUSIK_SECRET_SCAN_STRICT"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
