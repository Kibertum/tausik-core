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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cost_pricing import calculate_cost_usd  # noqa: E402


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

    if not model:
        # No silent Opus fallback — Sonnet/Haiku transcripts would be 5×–19×
        # over-attributed. Emit a stderr warning (parity with posttool_usage)
        # and report cost_usd=0.0 so downstream telemetry can flag the gap.
        if tokens_total > 0:
            print(
                "session_metrics: transcript missing 'model' field; "
                f"reporting cost_usd=0.0 for {tokens_total} tokens",
                file=sys.stderr,
            )
        cost_usd = 0.0
    else:
        cost_usd = calculate_cost_usd(model, tokens_input, tokens_output)

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

    def _auto_find_in_projects_root(projects_dir: str) -> str | None:
        if not os.path.isdir(projects_dir):
            return None
        # Build slug from CWD (shared across IDEs: path separators -> dashes)
        cwd = os.getcwd()
        cwd_normalized = cwd.replace("\\", "/").replace(":", "")
        slug_candidate = cwd_normalized.replace("/", "-")

        # Search for matching directory first
        for entry in os.listdir(projects_dir):
            entry_lower = entry.lower()
            if slug_candidate.lower() in entry_lower or entry_lower in slug_candidate.lower():
                project_dir = os.path.join(projects_dir, entry)
                if os.path.isdir(project_dir):
                    t = find_latest_transcript(project_dir)
                    if t:
                        return t

        # Fallback: most recent transcript in this projects root
        all_transcripts: list[str] = []
        for entry in os.listdir(projects_dir):
            project_dir = os.path.join(projects_dir, entry)
            if os.path.isdir(project_dir):
                t = find_latest_transcript(project_dir)
                if t:
                    all_transcripts.append(t)
        if all_transcripts:
            return max(all_transcripts, key=os.path.getmtime)
        return None

    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".claude", "projects"),
        os.path.join(home, ".cursor", "projects"),
    ]
    for projects_dir in candidates:
        found = _auto_find_in_projects_root(projects_dir)
        if found:
            return found
    return None


def write_metrics(metrics: dict, output_path: str | None = None) -> str:
    """Write metrics to JSON file. Returns path written."""
    if not output_path:
        output_path = os.path.join(os.getcwd(), ".claude-project", "session-metrics.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    return output_path


def extract_token_rows(path: str, session_id: int) -> list[dict]:
    """Walk transcript JSONL, emit one row per tool_use occurrence.

    Schema matches service_token_metrics.aggregate(): ts, session_id, tool_name,
    input_tokens, output_tokens, cache_read, cache_create, model. API usage is
    message-level, so per-tool attribution divides input/output/cache_* equally
    across tool_use blocks in the same assistant entry; the last block absorbs
    the integer-division remainder so totals stay exact. Pure-text turns and
    entries without tool_use blocks emit no rows.
    """
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message") if isinstance(entry.get("message"), dict) else {}
            usage = entry.get("usage") or msg.get("usage") or {}
            if not isinstance(usage, dict) or not usage:
                continue
            content = entry.get("content") or msg.get("content") or []
            if not isinstance(content, list):
                continue
            tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
            if not tool_uses:
                continue
            n = len(tool_uses)
            ts = entry.get("timestamp") or ""
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            cache_read = int(usage.get("cache_read_input_tokens") or 0)
            cache_create = int(usage.get("cache_creation_input_tokens") or 0)
            entry_model = entry.get("model") or msg.get("model") or None
            if not isinstance(entry_model, str) or not entry_model.strip():
                entry_model = None

            def _split(total: int, idx: int) -> int:
                base = total // n
                if idx == n - 1:
                    return total - base * (n - 1)
                return base

            for i, tu in enumerate(tool_uses):
                rows.append(
                    {
                        "ts": ts,
                        "session_id": session_id,
                        "tool_name": tu.get("name") or "(unknown)",
                        "input_tokens": _split(input_tokens, i),
                        "output_tokens": _split(output_tokens, i),
                        "cache_read": _split(cache_read, i),
                        "cache_create": _split(cache_create, i),
                        "model": entry_model,
                    }
                )
    return rows


def append_token_rows(rows: list[dict], project_dir: str | None = None) -> str | None:
    """Append rows to .tausik/token_metrics.jsonl. Returns path or None on no-op."""
    if not rows:
        return None
    proj = project_dir or os.getcwd()
    tausik_dir = os.path.join(proj, ".tausik")
    if not os.path.isdir(tausik_dir):
        return None
    path = os.path.join(tausik_dir, "token_metrics.jsonl")
    try:
        with open(path, "a", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"token_metrics.jsonl append failed: {exc}", file=sys.stderr)
        return None
    return path


def resolve_session_id(project_dir: str | None = None) -> int | None:
    """Most-recent session id from .tausik/tausik.db. None when DB missing/empty."""
    proj = project_dir or os.getcwd()
    db = os.path.join(proj, ".tausik", "tausik.db")
    if not os.path.exists(db):
        return None
    try:
        import sqlite3

        conn = sqlite3.connect(db, timeout=2)
        try:
            row = conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
            return int(row[0]) if row else None
        finally:
            conn.close()
    except sqlite3.Error:
        return None


def record_to_db(metrics: dict, project_root: str | None = None) -> bool:
    """Call project.py metrics record-session to write metrics to CouchDB.

    Returns True on success, False on failure.
    """
    import subprocess

    if not project_root:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(project_root, ".claude", "scripts", "project.py")
    if not os.path.isfile(script):
        # Try root scripts/ (source layout)
        script = os.path.join(project_root, "scripts", "project.py")
    if not os.path.isfile(script):
        print("project.py not found, skipping DB record", file=sys.stderr)
        return False

    cmd = [
        sys.executable,
        script,
        "metrics",
        "record-session",
        "--tokens-input",
        str(metrics.get("tokens_input", 0)),
        "--tokens-output",
        str(metrics.get("tokens_output", 0)),
        "--tokens-total",
        str(metrics.get("tokens_total", 0)),
        "--cost-usd",
        str(metrics.get("cost_usd", 0.0)),
        "--tool-calls",
        str(metrics.get("tool_calls", 0)),
        "--model",
        metrics.get("model", ""),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=project_root)
        if result.returncode == 0:
            print(f"DB: {result.stdout.strip()}")
            return True
        else:
            print(f"DB record failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    except Exception as e:  # noqa: BLE001 — best-effort: a hook must never break the tool call it guards
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
    print(
        f"Metrics: {metrics['tokens_total']:,} tokens, ${metrics['cost_usd']:.2f}, "
        f"{metrics['tool_calls']} tool calls, model={metrics['model']}"
    )
    print(f"Written to: {output}")

    if record:
        record_to_db(metrics)

    sid = resolve_session_id()
    if sid is not None:
        rows = extract_token_rows(path, sid)
        jsonl = append_token_rows(rows)
        if jsonl:
            print(f"token_metrics.jsonl: appended {len(rows)} row(s) to {jsonl}")


if __name__ == "__main__":
    main()
