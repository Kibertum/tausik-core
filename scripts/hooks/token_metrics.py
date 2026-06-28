#!/usr/bin/env python3
"""Deprecated PostToolUse hook — replaced by SessionEnd transcript-parser.

The original v14b-baseline-token-metrics design assumed Claude Code's
PostToolUse payload carried per-tool API usage. It does not — usage is
message-level and only available in the transcript JSONL. The replacement
emitter lives in scripts/hooks/session_metrics.py (extract_token_rows /
append_token_rows / resolve_session_id) and runs at SessionEnd.

This file is kept as a silent no-op so live IDE instances with a stale
hooks config (still pointing here) don't error on every tool call until
the IDE is restarted and picks up the regenerated .claude/settings.json
(which no longer references this script). Safe to delete after restart.

See decision #61 + task v14b-defect-token-metrics-no-realworld-write.
"""

import sys

if __name__ == "__main__":
    sys.exit(0)
