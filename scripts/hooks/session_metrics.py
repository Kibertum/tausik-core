#!/usr/bin/env python3
"""Parse Claude Code transcript JSONL and extract session metrics.

Reads a conversation transcript (JSONL), sums token usage from API responses,
computes estimated cost, and writes results to .claude-project/session-metrics.json.

Usage:
    python scripts/hooks/session_metrics.py <transcript_path>
    python scripts/hooks/session_metrics.py --session-dir <dir>  # latest .jsonl

Can be used as a Claude Code hook (PostSessionEnd) or called from /end skill.
"""

import json
import os
import sys
from glob import glob

# Model pricing (USD per 1M tokens) — updated for Claude 4.x
MODEL_PRICING = {
    "claude-opus-4-6":     {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6":   {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5":    {"input": 0.80, "output": 4.0},
    # Aliases
    "opus":                {"input": 15.0, "output": 75.0},
    "sonnet":              {"input": 3.0,  "output": 15.0},
    "haiku":               {"input": 0.80, "output": 4.0},
}


def parse_transcript(path: str) -> dict:
    """Parse JSONL transcript and extract metrics.

    Returns:
        {tokens_input, tokens_output, tokens_total, cost_usd,
         tool_calls, model, messages, duration_sec}
    """
    tokens_input = 0
    tokens_output = 0
    tool_calls = 0
    model = ""
    messages = 0
    first_ts = None
    last_ts = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract timestamp
            ts = entry.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            # Count messages
            msg_type = entry.get("type", "")
            if msg_type in ("human", "assistant"):
                messages += 1

            # Extract usage from API response
            usage = entry.get("usage") or entry.get("message", {}).get("usage") or {}
            if usage:
                tokens_input += usage.get("input_tokens", 0)
                tokens_output += usage.get("output_tokens", 0)

            # Extract model
            entry_model = entry.get("model") or entry.get("message", {}).get("model") or ""
            if entry_model and not model:
                model = entry_model

            # Count tool use
            content = entry.get("content") or entry.get("message", {}).get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls += 1

    tokens_total = tokens_input + tokens_output

    # Calculate cost
    cost_usd = 0.0
    pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("opus"))
    if pricing:
        cost_usd = (tokens_input * pricing["input"] / 1_000_000 +
                    tokens_output * pricing["output"] / 1_000_000)

    # Duration
    duration_sec = 0
    if first_ts and last_ts:
        try:
            from datetime import datetime
            t1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            duration_sec = int((t2 - t1).total_seconds())
        except (ValueError, TypeError):
            pass

    return {
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_total": tokens_total,
        "cost_usd": round(cost_usd, 4),
        "tool_calls": tool_calls,
        "model": model,
        "messages": messages,
        "duration_sec": duration_sec,
    }


def find_latest_transcript(session_dir: str) -> str | None:
    """Find the most recent .jsonl transcript in a directory."""
    pattern = os.path.join(session_dir, "*.jsonl")
    files = sorted(glob(pattern), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def auto_find_transcript() -> str | None:
    """Auto-detect Claude Code transcript for current project.

    Checks ~/.claude/projects/<project-slug>/*.jsonl
    Project slug is derived from CWD by replacing path separators with dashes.
    """
    home = os.path.expanduser("~")
    projects_dir = os.path.join(home, ".claude", "projects")
    if not os.path.isdir(projects_dir):
        return None

    # Build slug from CWD (Claude Code convention: drive-letter--path--components)
    cwd = os.getcwd()
    # Try to find matching project dir
    cwd_normalized = cwd.replace("\\", "/").replace(":", "")
    slug_candidate = cwd_normalized.replace("/", "-")

    # Search for matching directory
    for entry in os.listdir(projects_dir):
        entry_lower = entry.lower()
        if slug_candidate.lower() in entry_lower or entry_lower in slug_candidate.lower():
            project_dir = os.path.join(projects_dir, entry)
            if os.path.isdir(project_dir):
                return find_latest_transcript(project_dir)

    # Fallback: find any project dir with recent transcript
    all_transcripts = []
    for entry in os.listdir(projects_dir):
        project_dir = os.path.join(projects_dir, entry)
        if os.path.isdir(project_dir):
            t = find_latest_transcript(project_dir)
            if t:
                all_transcripts.append(t)
    if all_transcripts:
        return max(all_transcripts, key=os.path.getmtime)
    return None


def write_metrics(metrics: dict, output_path: str | None = None) -> str:
    """Write metrics to JSON file. Returns path written."""
    if not output_path:
        output_path = os.path.join(os.getcwd(), ".claude-project", "session-metrics.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    return output_path


def record_to_db(metrics: dict, project_root: str | None = None) -> bool:
    """Call project.py metrics record-session to write metrics to CouchDB.

    Returns True on success, False on failure.
    """
    import subprocess
    if not project_root:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
    script = os.path.join(project_root, ".claude", "scripts", "project.py")
    if not os.path.isfile(script):
        # Try root scripts/ (source layout)
        script = os.path.join(project_root, "scripts", "project.py")
    if not os.path.isfile(script):
        print("project.py not found, skipping DB record", file=sys.stderr)
        return False

    cmd = [
        sys.executable, script, "metrics", "record-session",
        "--tokens-input", str(metrics.get("tokens_input", 0)),
        "--tokens-output", str(metrics.get("tokens_output", 0)),
        "--tokens-total", str(metrics.get("tokens_total", 0)),
        "--cost-usd", str(metrics.get("cost_usd", 0.0)),
        "--tool-calls", str(metrics.get("tool_calls", 0)),
        "--model", metrics.get("model", ""),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                cwd=project_root)
        if result.returncode == 0:
            print(f"DB: {result.stdout.strip()}")
            return True
        else:
            print(f"DB record failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"DB record error: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: session_metrics.py <transcript.jsonl>", file=sys.stderr)
        print("       session_metrics.py --session-dir <dir>", file=sys.stderr)
        print("       session_metrics.py --auto", file=sys.stderr)
        print("  --record  Also write metrics to DB via project.py", file=sys.stderr)
        sys.exit(1)

    record = "--record" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--record"]

    if not args:
        print("Error: no transcript path provided", file=sys.stderr)
        sys.exit(1)

    path = None
    if args[0] == "--auto":
        path = auto_find_transcript()
        if not path:
            print("No transcript found (--auto). Skipping metrics.", file=sys.stderr)
            sys.exit(0)
    elif args[0] == "--session-dir":
        if len(args) < 2:
            print("Error: --session-dir requires a path", file=sys.stderr)
            sys.exit(1)
        path = find_latest_transcript(args[1])
        if not path:
            print(f"No .jsonl files found in {args[1]}", file=sys.stderr)
            sys.exit(1)
    else:
        path = args[0]

    if not path or not os.path.isfile(path):
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    metrics = parse_transcript(path)
    output = write_metrics(metrics)
    print(f"Metrics: {metrics['tokens_total']:,} tokens, ${metrics['cost_usd']:.2f}, "
          f"{metrics['tool_calls']} tool calls, model={metrics['model']}")
    print(f"Written to: {output}")

    if record:
        record_to_db(metrics)


if __name__ == "__main__":
    main()
