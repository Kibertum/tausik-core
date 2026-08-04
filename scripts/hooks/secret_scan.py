#!/usr/bin/env python3
"""PreToolUse hook — scan tool_input for likely secrets, on both write and
shell channels.

SENAR Rule 10.12 (Context Hygiene): keep credentials and project-specific
secrets out of agent context and out of files the agent writes. Brain
already enforces this on the write path; this hook closes the gap on
local Write/Edit/MultiEdit AND on the shell tools (Bash / PowerShell).

secret-scan-covers-no-shell-channel (Decision #178). The hole this closes:
the hook was registered only on `Write|Edit|MultiEdit`, so a secret written
by a shell — `cat > .env <<EOF` with an AWS key in the body, or
`Set-Content -Path .env -Value 'AKIA...'` — reached exactly the content the
Write path would have warned on, and this hook never ran. That is a gap in
BOTH shells equally; closing it on one would re-split the channels, which was
the root defect of the PowerShell-firewall task. So it is closed on both, via
`shell_channel.is_shell_tool` (the producer of the shell-tool set, not a
literal list here — convention #289: a second copy of that list is how the
PowerShell tool went ungated).

Whole-command, not written-value: the shell command STRING is scanned in full
rather than the extracted write value (heredoc body / `-Value` / `Out-File`
input). That is a strict superset — it catches those plus `export KEY=AKIA...`
and `aws configure set ... AKIA...`, all of which are the secret literal in
context that Rule 10.12 also covers — and adds zero new shell parsing, the one
thing that has produced every regression in this directory. The detectors are
specific enough (`AKIA[0-9A-Z]{16}`, `sk-ant-...`, PEM headers) that a match on
ordinary command text is almost always a real literal. Residual, stated: a
secret passed by VARIABLE or env (`--token "$TOKEN"`) is not a literal anywhere
and is not resolved — the same boundary the write parsers document for paths.

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

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from shell_channel import is_shell_tool  # noqa: E402

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
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
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
    # Make stderr UTF-8 regardless of how this hook was launched: the warning
    # can carry a non-ASCII em dash or a non-ASCII byte from a scanned sample,
    # and on a non-UTF-8 launcher that turns the reader's stderr into None
    # (hook-stderr-encoding-locale-dependent). Production passes `-X utf8`, but a
    # test or manual run does not — so the hook does it itself.
    from _common import force_utf8_io

    force_utf8_io()

    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        from _common import emit_supervision_bypass

        emit_supervision_bypass(
            os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "skip_hooks", "secret_scan"
        )
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError, EOFError):
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_name = payload.get("tool_name") or ""
    # The write tools carry the content in `content`/`new_string`; the shell
    # tools carry it in `command`. `_walk` scans every string field of either,
    # so admitting both here is all it takes. `is_shell_tool` is asked rather
    # than a literal ("Bash","PowerShell") list so a third shell added to
    # `shell_channel` is covered without editing this line (convention #289).
    if tool_name not in ("Write", "Edit", "MultiEdit") and not is_shell_tool(tool_name):
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
        f"[TAUSIK secret-scan] Possible secrets detected in pending {tool_name} input:\n"
        + "\n".join(lines)
        + "\nRotate the credential and remove the literal — pass it via an env var or "
        "a file read at runtime, not as a literal in the command or file.\n"
        "  Strict mode: set TAUSIK_SECRET_SCAN_STRICT=1 to block instead of warn.",
        file=sys.stderr,
    )
    if os.environ.get("TAUSIK_SECRET_SCAN_STRICT"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
