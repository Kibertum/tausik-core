#!/usr/bin/env python3
"""Validate Anthropic prompt caching in Claude Code transcripts.

Reads a transcript JSONL, parses each `usage` block, and reports whether
Anthropic prompt caching is active. The two telemetry fields that prove a
cache breakpoint was honoured are `cache_creation_input_tokens` (first time
the prefix was seen) and `cache_read_input_tokens` (subsequent hit).

Usage:
    python scripts/validate_prompt_caching.py <transcript.jsonl>
    python scripts/validate_prompt_caching.py --auto

Exit codes:
    0  prompt caching active (cache_read_input_tokens > 0 in at least one usage block)
    1  cache fields present but no reads (every prompt is a miss — fix prefix stability)
    2  no cache_creation/cache_read fields anywhere (caching not enabled by the API)
   64  bad CLI invocation / file not found
"""

from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from hooks.session_metrics import auto_find_transcript
except ImportError:
    auto_find_transcript = None  # type: ignore[assignment]


def parse_caching(path: str) -> dict:
    """Sum cache_creation + cache_read tokens across a transcript.

    Returns a dict with input/output token totals, cache totals, hit rate,
    and counts of usage blocks (overall and those carrying cache fields).
    """
    input_tokens = 0
    output_tokens = 0
    cache_creation = 0
    cache_read = 0
    entries_with_cache_fields = 0
    total_entries_with_usage = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = entry.get("usage") or entry.get("message", {}).get("usage") or {}
            if not usage:
                continue
            total_entries_with_usage += 1
            input_tokens += int(usage.get("input_tokens", 0))
            output_tokens += int(usage.get("output_tokens", 0))
            cc = int(usage.get("cache_creation_input_tokens", 0))
            cr = int(usage.get("cache_read_input_tokens", 0))
            if "cache_creation_input_tokens" in usage or "cache_read_input_tokens" in usage:
                entries_with_cache_fields += 1
            cache_creation += cc
            cache_read += cr

    cached_input = cache_creation + cache_read
    hit_rate = (cache_read / cached_input * 100) if cached_input else 0.0
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "cache_hit_rate_pct": round(hit_rate, 2),
        "entries_with_cache_fields": entries_with_cache_fields,
        "total_entries_with_usage": total_entries_with_usage,
    }


def classify(stats: dict) -> tuple[int, str]:
    """Map parsed stats to (exit_code, human message)."""
    if stats.get("entries_with_cache_fields", 0) == 0:
        return (
            2,
            "FAIL: no cache_creation_input_tokens / cache_read_input_tokens fields "
            "in any usage block — Anthropic prompt caching not active in this transcript.",
        )
    if stats.get("cache_read_input_tokens", 0) == 0:
        return (
            1,
            "WARN: cache_creation > 0 but cache_read_input_tokens = 0 — "
            "every prompt is a cache miss. Check stable-prefix structure (CLAUDE.md, "
            "system prompt, MCP tool descriptions should not change between turns).",
        )
    return (0, "OK: prompt caching active — cache_read_input_tokens > 0.")


def format_report(stats: dict) -> str:
    return (
        f"input_tokens:                {stats['input_tokens']:>12,}\n"
        f"output_tokens:               {stats['output_tokens']:>12,}\n"
        f"cache_creation_input_tokens: {stats['cache_creation_input_tokens']:>12,}\n"
        f"cache_read_input_tokens:     {stats['cache_read_input_tokens']:>12,}\n"
        f"cache_hit_rate:              {stats['cache_hit_rate_pct']:>11.2f}%\n"
        f"entries_with_cache_fields:   {stats['entries_with_cache_fields']:>12} "
        f"/ {stats['total_entries_with_usage']} usage blocks\n"
    )


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: validate_prompt_caching.py <transcript.jsonl>\n"
            "       validate_prompt_caching.py --auto",
            file=sys.stderr,
        )
        return 64

    arg = sys.argv[1]
    if arg == "--auto":
        if auto_find_transcript is None:
            print(
                "--auto requires scripts/hooks/session_metrics.py to be importable",
                file=sys.stderr,
            )
            return 64
        path = auto_find_transcript()
        if not path:
            print("No transcript found via --auto", file=sys.stderr)
            return 64
    else:
        path = arg

    if not os.path.isfile(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 64

    stats = parse_caching(path)
    print(format_report(stats))
    code, msg = classify(stats)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
