#!/usr/bin/env python3
"""Per-tool token rows and the `.tausik/token_metrics.jsonl` writer.

Split out of `session_metrics` at the 400-line cap. One coherent concern:
walk a transcript, emit one row per tool_use, and persist the rows for a
session — separate from the session-level rollup that computes cost and
writes `session-metrics.json`.

The writer REPLACES what a transcript contributed rather than appending.
`extract_token_rows` re-derives a transcript's complete set on every call, so
appending duplicated every row on each SessionEnd re-run — the file reached
191 MB that way. Replacing by (session, transcript) is idempotent by
construction and, unlike the earlier replace-by-session, does not let the newest
transcript erase what earlier ones recorded for the same session.

Rows carry the session their OWN timestamp falls in (`session_windows`), or
None when it falls in none, and the full input context of the message
(`context_tokens`), which is what a token-economy claim is about — not
`input_tokens`, the uncached remainder that reads 2 on every cached call.

`rebuild_ledger` re-derives the whole file from every transcript on disk, for
when the incremental writer's coverage is narrower than the history that exists.

Names are re-exported from `session_metrics` for existing callers.
"""

import json
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Usage keys that together make up the input context of one message. The API
#: splits input into three DISJOINT buckets when prompt caching is on, and
#: `input_tokens` is only the uncached remainder — measured on this project it
#: is literally 2 for every one of 5301 rows, while cache_read carries ~30k and
#: cache_create ~20k. A report that calls `input_tokens` "the input" is naming
#: the smallest of three parts. Their sum is the quantity a token-economy claim
#: is actually about.
_CONTEXT_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _context_tokens(usage: dict) -> int | None:
    """Full input context of one message, or None when it is not measurable.

    None when the payload carries NONE of the three buckets — the size was not
    reported, and absence is reported as absence rather than as zero
    (decision #334). An absent cache bucket alongside a present `input_tokens`
    is a real zero: it means that call used no cache, not that nobody looked.
    """
    present = [k for k in _CONTEXT_KEYS if usage.get(k) is not None]
    if not present:
        return None
    total = 0
    for key in present:
        try:
            total += int(usage[key])
        except (TypeError, ValueError):
            return None
    return total


def extract_token_rows(path: str, session_id) -> list[dict]:
    """Walk transcript JSONL, emit one row per tool_use occurrence.

    Schema matches service_token_metrics.aggregate(): ts, session_id, tool_name,
    input_tokens, output_tokens, cache_read, cache_create, context_tokens,
    model. API usage is message-level, so per-tool attribution divides
    input/output/cache_*/context equally across tool_use blocks in the same
    assistant entry; the last block absorbs the integer-division remainder so
    totals stay exact. Pure-text turns and entries without tool_use blocks emit
    no rows.

    `session_id` is either a fixed id (a transcript known to belong to one
    session) or a CALLABLE `ts -> id | None`. The callable form is what the
    SessionEnd hook passes, because one Claude Code transcript spans several
    TAUSIK sessions and stamping them all with one id is what produced 72.4%
    duplicate rows in this project's own ledger — see `session_windows`. A row
    whose timestamp falls in no session gets `session_id: None`, not a guess.

    NOTHING but the tool NAME, the timestamp, numbers and the model id leaves
    this walk. Tool arguments, tool results and message text stay in the
    transcript: the ledger is not a place where a secret pasted into a command
    can reappear.
    """
    resolve = session_id if callable(session_id) else (lambda _ts: session_id)
    # The transcript's own id, not its location: Claude Code names transcripts
    # by UUID, so the stem identifies the conversation without putting a
    # filesystem path — or anything a user typed — into the ledger. It exists so
    # the writer can replace exactly what this walk re-derived; see
    # `replace_session_token_rows`.
    source = os.path.splitext(os.path.basename(path))[0] or None
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
            context = _context_tokens(usage)
            entry_model = entry.get("model") or msg.get("model") or None
            if not isinstance(entry_model, str) or not entry_model.strip():
                entry_model = None
            row_session = resolve(ts)

            def _split(total: int, idx: int) -> int:
                base = total // n
                if idx == n - 1:
                    return total - base * (n - 1)
                return base

            for i, tu in enumerate(tool_uses):
                rows.append(
                    {
                        "ts": ts,
                        "session_id": row_session,
                        "tool_name": tu.get("name") or "(unknown)",
                        "input_tokens": _split(input_tokens, i),
                        "output_tokens": _split(output_tokens, i),
                        "cache_read": _split(cache_read, i),
                        "cache_create": _split(cache_create, i),
                        # None survives the split: an unmeasurable context stays
                        # unmeasurable per tool, it does not become a zero share.
                        "context_tokens": None if context is None else _split(context, i),
                        "model": entry_model,
                        "source": source,
                    }
                )
    return rows


#: Size ceiling for .tausik/token_metrics.jsonl. The file had no cap at all and
#: reached 191 MB on this project. Oldest rows are dropped first: token
#: attribution is only useful for recent sessions, and the DB keeps the
#: authoritative per-session totals regardless.
TOKEN_METRICS_MAX_BYTES = 32 * 1024 * 1024


def _surviving_lines(path: str, drop_keys: set, max_bytes: int) -> list[str]:
    """Existing lines to keep: not in `drop_keys`, newest within `max_bytes`.

    A key is `(session_id, source)` — the session a row was attributed to AND
    the transcript it was read from. Dropping on the session alone lost data:
    one TAUSIK session routinely spans several Claude Code transcripts, the
    SessionEnd hook walks only the newest one, and a session-wide drop therefore
    erased everything the earlier transcripts had contributed to that session.
    Keying on the pair keeps a re-walk idempotent (same transcript, same key)
    without letting one transcript speak for another.

    Streams the file and holds at most `max_bytes` of it, because the file this
    was written for was 191 MB — reading it whole would trade a disk problem for
    a memory one. Unparseable lines are dropped rather than aborting the write:
    losing one malformed metrics row is strictly better than losing the file.
    """
    kept: deque[str] = deque()
    size = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if (row.get("session_id"), row.get("source")) in drop_keys:
                        continue
                except (json.JSONDecodeError, AttributeError):
                    continue
                kept.append(line)
                size += len(line.encode("utf-8")) + 1
                while size > max_bytes and kept:
                    size -= len(kept.popleft().encode("utf-8")) + 1
    except OSError as exc:
        print(f"token_metrics.jsonl read failed: {exc}", file=sys.stderr)
        return []
    return list(kept)


def replace_session_token_rows(
    rows: list[dict],
    project_dir: str | None = None,
    max_bytes: int = TOKEN_METRICS_MAX_BYTES,
) -> str | None:
    """Record `rows` in .tausik/token_metrics.jsonl. Returns path or None on no-op.

    REPLACES the rows already stored for the (session, transcript) pairs present
    in `rows` rather than appending to them. `extract_token_rows` re-derives a
    transcript's *complete* row set on every call, so appending duplicated every
    row on every re-run of the SessionEnd hook — which is how the file reached
    191 MB. Replace-by-pair makes a re-run idempotent by construction, with no
    need to track offsets or per-row identity, and — unlike the earlier
    replace-by-session — does not let the newest transcript erase what earlier
    transcripts recorded for the same session.

    Known limit, stated rather than hidden: two Claude Code windows writing
    interleaved rows for the same session at the same time still overwrite each
    other's pair, because each walk claims the pair wholesale. Sequential work
    (the normal case) is exact.

    Writes via a temp file and os.replace so an interrupted run cannot leave a
    truncated metrics file behind.
    """
    if not rows:
        return None
    proj = project_dir or os.getcwd()
    tausik_dir = os.path.join(proj, ".tausik")
    if not os.path.isdir(tausik_dir):
        return None
    path = os.path.join(tausik_dir, "token_metrics.jsonl")

    new_lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    keys = {(r.get("session_id"), r.get("source")) for r in rows}
    budget = max(0, max_bytes - sum(len(s.encode("utf-8")) + 1 for s in new_lines))
    old_lines = _surviving_lines(path, keys, budget) if os.path.exists(path) else []

    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            for line in old_lines:
                fh.write(line + "\n")
            for line in new_lines:
                fh.write(line + "\n")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"token_metrics.jsonl write failed: {exc}", file=sys.stderr)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return None
    return path


def _project_transcripts(transcript_dir: str | None = None) -> list[str]:
    """Every transcript of this project, oldest first. [] when none are found.

    Without an explicit directory, `transcript_locator` decides — it matches on
    the `cwd` each transcript records about itself. The earlier rule guessed a
    directory name from the CWD and fell back to "the most recently touched
    project anywhere", which made three consecutive rebuilds read 42, 32 and 10
    transcripts from three different projects.
    """
    if transcript_dir is None:
        from transcript_locator import project_transcripts

        return project_transcripts()
    if not os.path.isdir(transcript_dir):
        return []
    found = [
        os.path.join(transcript_dir, name)
        for name in os.listdir(transcript_dir)
        if name.endswith(".jsonl")
    ]
    return sorted(found, key=lambda p: os.path.getmtime(p))


def rebuild_ledger(
    project_dir: str | None = None,
    transcript_dir: str | None = None,
    max_bytes: int = TOKEN_METRICS_MAX_BYTES,
) -> dict:
    """Re-derive .tausik/token_metrics.jsonl from EVERY transcript on disk.

    The incremental writer only ever sees the transcript that just ended, so a
    ledger built by it covers whatever happened to be walked — on this project
    that was 7 sessions out of 227, all from two days, while 42 transcripts
    going back a month sat unread. A longitudinal claim ("it got cheaper") needs
    the series that those transcripts hold, and re-derivation is exact: rows are
    a pure function of transcript plus session windows.

    Returns a receipt — counts, not a transcript — so the caller can report what
    was rebuilt without the ledger's contents crossing back through it.
    """
    from session_windows import make_session_resolver

    proj = project_dir or os.getcwd()
    tausik_dir = os.path.join(proj, ".tausik")
    if not os.path.isdir(tausik_dir):
        return {"error": f"no .tausik directory under {proj}", "transcripts": 0, "rows": 0}
    transcripts = _project_transcripts(transcript_dir)
    if not transcripts:
        return {"error": "no transcripts found", "transcripts": 0, "rows": 0}

    resolve = make_session_resolver(proj)
    rows: list[dict] = []
    unreadable: list[str] = []
    for path in transcripts:
        try:
            rows.extend(extract_token_rows(path, resolve))
        except OSError:
            unreadable.append(os.path.basename(path))

    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    kept: deque[str] = deque()
    size = 0
    for line in lines:
        kept.append(line)
        size += len(line.encode("utf-8")) + 1
        while size > max_bytes and kept:
            size -= len(kept.popleft().encode("utf-8")) + 1

    target = os.path.join(tausik_dir, "token_metrics.jsonl")
    tmp = f"{target}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            for line in kept:
                fh.write(line + "\n")
        os.replace(tmp, target)
    except OSError as exc:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return {"error": f"write failed: {exc}", "transcripts": len(transcripts), "rows": 0}

    attributed = sum(1 for r in rows if r.get("session_id") is not None)
    return {
        "path": target,
        "transcripts": len(transcripts),
        "unreadable": unreadable,
        "rows": len(rows),
        "rows_written": len(kept),
        "attributed": attributed,
        "unattributed": len(rows) - attributed,
        "sessions": len({r.get("session_id") for r in rows if r.get("session_id") is not None}),
        "context_missing": sum(1 for r in rows if r.get("context_tokens") is None),
    }
