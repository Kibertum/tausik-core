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
from collections.abc import Callable
from glob import glob

# Own directory FIRST: the siblings below are imported by bare name, and
# scripts/hooks reaches sys.path only when this file is RUN as a script. Imported
# as `hooks.<name>` — which model_routing does — those names did not resolve, and
# the caller's except swallowed the ImportError into a silent None.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cost_pricing import calculate_cost_usd  # noqa: E402
from token_accounting import sum_usage_tokens  # noqa: E402


def parse_transcript(
    path: str,
    tool_rows_out: list | None = None,
    session_resolver: Callable[[object], int | None] | None = None,
    session_id: int | None = None,
) -> dict:
    """Parse JSONL transcript and extract metrics.

    Returns:
        {tokens_input, tokens_output, tokens_total, cost_usd,
         tool_calls, model, messages, duration_sec}

    ``tool_rows_out``, when a list is passed, is FILLED with one row per tool
    use — the material for the optional OTLP child spans. An out-parameter
    rather than another key in the returned dict, because that dict is written
    to the metrics file and recorded to the database, and a telemetry
    extension has no business changing the shape of either. Absent, nothing is
    collected and the walk is exactly as before.
    """
    if (session_resolver is None) != (session_id is None):
        raise ValueError("session_resolver and session_id must be supplied together")

    tool_rows = tool_rows_out if tool_rows_out is not None else []
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

            # A Claude transcript can span several TAUSIK sessions.  The
            # session rollup therefore filters before it counts *anything*;
            # otherwise the newest session receives a copy of the whole file.
            # No timestamp is not evidence of ownership, so the resolver's
            # None is deliberately excluded rather than assigned by proximity.
            if (
                session_id is not None
                and session_resolver is not None
                and session_resolver(entry.get("timestamp")) != session_id
            ):
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

            # Extract usage from API response. sum_usage_tokens folds in
            # server-side compaction billed under usage.iterations[*], which the
            # top-level input/output_tokens omit — a top-level-only sum here
            # understated the real (billed) token count (l26-tokenizer-calibration).
            usage = entry.get("usage") or entry.get("message", {}).get("usage") or {}
            if usage:
                ti, to = sum_usage_tokens(usage)
                tokens_input += ti
                tokens_output += to

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
                        # Names for the optional OTLP child spans. Collected
                        # here because the walk is already happening; kept out
                        # of `metrics` (see below) so the metrics file and the
                        # usage row keep the shape everything else expects.
                        name = str(block.get("name") or "").strip()
                        if name:
                            tool_rows.append(
                                {"id": len(tool_rows) + 1, "tool_name": name, "model_id": model}
                            )

    tokens_total = tokens_input + tokens_output

    cost_usd: float | None
    if not model:
        # No silent Opus fallback — Sonnet/Haiku transcripts would be 5×–19×
        # over-attributed. And no 0.0 either: a cost that cannot be computed is
        # ABSENT, not nought (decision #334). Reporting zero here is what let
        # 55,471 rows claim work had been free; downstream now sees None and
        # says "not measured" instead of printing a price nobody derived.
        if tokens_total > 0:
            print(
                "session_metrics: transcript missing 'model' field; "
                f"cost is NOT MEASURED for {tokens_total} tokens",
                file=sys.stderr,
            )
        cost_usd = None
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
        "cost_usd": None if cost_usd is None else round(cost_usd, 4),
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
    """Newest transcript that PROVABLY belongs to the current project, or None.

    This used to derive a directory name from the CWD and, when that failed to
    match, return the most recently touched project ANYWHERE on the machine. On
    Windows the match never succeeded — Claude Code writes `c--Projects-…` for
    `C:\\Projects\\…` while the derived slug was `C-Projects-…` — so the fallback was the
    normal path, and this function routinely returned another project's
    conversation to the session-metrics parser, the token ledger and the model
    detector. Matching is now on the `cwd` a transcript records about itself;
    when nothing matches the answer is None, because a wrong transcript is
    indistinguishable from a right one to every caller here.
    """
    found: str | None = latest_project_transcript()
    return found


def write_metrics(metrics: dict, output_path: str | None = None) -> str:
    """Write metrics to JSON file. Returns path written."""
    if not output_path:
        output_path = os.path.join(os.getcwd(), ".claude-project", "session-metrics.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    return output_path


def _load_config_safe() -> dict | None:
    """Effective project config, or None. Best-effort — never raises."""
    try:
        from project_config import load_config

        return load_config()
    except Exception:  # noqa: BLE001 — no config just means "export stays off"
        return None


# Token-row extraction and the token_metrics.jsonl writer moved to
# `token_rows` at the 400-line cap. Re-exported so existing callers and
# tests keep importing them from here.
from session_windows import make_session_resolver  # noqa: E402
from token_rows import (  # noqa: E402,F401
    TOKEN_METRICS_MAX_BYTES,
    _surviving_lines,
    extract_token_rows,
    replace_session_token_rows,
)
from transcript_locator import latest_project_transcript  # noqa: E402


# `resolve_session_id()` — "the newest session in the DB" — used to stamp every
# row of a re-walked transcript. It is DELETED rather than deprecated: its only
# caller was the token-row emitter, and there it was the defect itself (one
# transcript spans several sessions, so each of them received a copy of the whole
# file). Attribution now goes through `session_windows.make_session_resolver`,
# which places a row by its own timestamp and answers None outside every session.
# A function kept "just in case" would be an invitation to reintroduce the bug.


def record_to_db(
    metrics: dict, project_root: str | None = None, session_id: int | None = None
) -> bool:
    """Call project.py metrics record-session to write metrics to CouchDB.

    Returns True on success, False on failure.
    """
    import subprocess

    # Locate project.py and the true project root by self-location, not a
    # miscounted dirname chain. `dirname×3(__file__)` actually yielded the
    # *profile* dir (…/.claude), so the old first candidate
    # `<profile>/.claude/scripts/project.py` doubled the profile segment and
    # never existed, and `cwd=<profile>` made project.py resolve `.tausik/`
    # under the profile instead of the project root — a silent DB-record miss
    # that only "worked" through the scripts/ fallback. The shared helper is
    # the single home for this logic (see _common.profile_dir).
    hooks_dir = os.path.dirname(os.path.abspath(__file__))
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from _common import profile_dir
    from _common import project_root as _detect_root

    profile = profile_dir()
    if not project_root:
        project_root = _detect_root()

    candidates: list[str] = []
    if profile:  # deployed: project.py ships under the profile's scripts/
        candidates.append(os.path.join(profile, "scripts", "project.py"))
    candidates.append(os.path.join(project_root, "scripts", "project.py"))  # source tree
    script = next((c for c in candidates if os.path.isfile(c)), None)
    if not script:
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
    if session_id is not None:
        cmd.extend(["--session-id", str(session_id)])
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=project_root,
        )
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

    session_id = None
    if "--session-id" in args:
        index = args.index("--session-id")
        if index + 1 >= len(args):
            print("Error: --session-id requires an integer", file=sys.stderr)
            sys.exit(1)
        try:
            session_id = int(args[index + 1])
        except ValueError:
            print("Error: --session-id requires an integer", file=sys.stderr)
            sys.exit(1)
        del args[index : index + 2]

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

    # The service closes its session before invoking this hook, and passes that
    # exact ID.  An IDE SessionEnd hook can instead still have one open TAUSIK
    # session; use it only when the window proves it is current.  With neither
    # proof, write the human-readable full transcript summary but refuse to
    # put an un-attributable total in the authoritative per-session table.
    if record and session_id is None:
        from session_windows import load_session_windows

        windows = load_session_windows()
        if windows and windows[-1][1] is None:
            session_id = windows[-1][2]
        else:
            print("No attributable TAUSIK session; skipping DB record", file=sys.stderr)

    tool_rows: list = []
    if record and session_id is not None:
        metrics = parse_transcript(
            path,
            tool_rows,
            session_resolver=make_session_resolver(),
            session_id=session_id,
        )
    else:
        metrics = parse_transcript(path, tool_rows)
    output = write_metrics(metrics)
    # `cost_usd` is None when it could not be computed — no model, or no price
    # for the one named. Printed as words, never as $0.00: the whole point of
    # storing absence is lost if the reader is shown a price anyway.
    cost = metrics["cost_usd"]
    cost_text = "cost NOT MEASURED" if cost is None else f"${cost:.2f}"
    print(
        f"Metrics: {metrics['tokens_total']:,} tokens, {cost_text}, "
        f"{metrics['tool_calls']} tool calls, model={metrics['model']}"
    )
    print(f"Written to: {output}")

    # Optional OTLP/JSON export — an ADDITIONAL output, off unless enabled. When
    # disabled session_otlp_document() returns {} and nothing here runs, so the
    # events/metrics path above is unchanged (l26-otel-export, AC1).
    from otel_export import session_otlp_document

    otlp = session_otlp_document(metrics, _load_config_safe(), tool_calls=tool_rows)
    if otlp:
        otlp_path = os.path.join(os.path.dirname(output), "session-otlp.json")
        with open(otlp_path, "w", encoding="utf-8") as f:
            json.dump(otlp, f, indent=2, ensure_ascii=False)
        print(f"OTLP trace: {otlp_path}")

    if record and session_id is not None:
        record_to_db(metrics, session_id=session_id)

    # Attribute each row to the session its OWN timestamp falls in. Stamping the
    # whole transcript with resolve_session_id() — the newest session in the DB —
    # gave three consecutive sessions a copy of the same transcript and made
    # 72.4% of this project's ledger duplicates (see session_windows).
    rows = extract_token_rows(path, make_session_resolver())
    jsonl = replace_session_token_rows(rows)
    if jsonl:
        attributed = sum(1 for r in rows if r.get("session_id") is not None)
        print(
            f"token_metrics.jsonl: {len(rows)} row(s) -> {jsonl} "
            f"({attributed} attributed, {len(rows) - attributed} outside any session)"
        )


if __name__ == "__main__":
    main()
