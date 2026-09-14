"""Does the generated half of the rules file earn its cost? Cost + usage proxies.

arXiv 2602.11988 (ETH Zurich, 438 tasks, 4 agents): model-GENERATED context
files cost +20-23% and lose 0.5-2% success; human-written ones gain +4%. Our
CLAUDE.md / AGENTS.md are hybrid: handwritten rules plus a DYNAMIC section
(`## Current State`, the memory tail, the shared-knowledge block) that
`update-claudemd` regenerates every session and the harness delivers with
EVERY request. Nothing had measured whether the agent reads it.

This audit measures two things it CAN measure and names the one it cannot:

* cost — bytes and approximate tokens of each part, as a share of the median
  per-call context (276,702; measurement #230);
* usage, from this machine's transcripts of this project —
  proxy A (state block): a status / session_current / session_open call within
  the first 8 tool calls is a re-fetch of what the block already carries;
  proxy B (memory tail): a memory id the agent cites that no earlier tool
  result or human message in that transcript contained can only have come
  from the injected tail — credited only when the tail actually carried that
  id at some point in the rules file's git history, so a hallucinated id
  earns nothing;
* NOT measured: task success, the paper's metric — that needs paired runs.

    python scripts/context_block_audit.py <transcripts>... [--rules CLAUDE.md]
        [--repo .] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MEDIAN_CONTEXT_TOKENS = 276_702  # measurement #230, docs/ru/agent-contract.md
CHARS_PER_TOKEN = 4
FIRST_CALLS = 8

STATE_HEADING = "## Current State"
TAIL_HEADING = "### Memory tail"
SHARED_HEADING = "**Shared knowledge"
DYNAMIC_START = "<!-- DYNAMIC:START -->"

_MEMORY_ID = re.compile(r"(?<![\w/])#(\d{2,5})\b")
# `#425` is a memory or decision id unless the word before it says otherwise:
# sessions, verify runs, receipts, attempts, PRs and steps are numbered the
# same way, and a session "#249" must not be credited as memory #249.
_NOT_MEMORY_BEFORE = re.compile(
    r"(?:session|sessions|смен[аыуе]|сесси[яию]|run|runs|verify|receipt|attempt|attempts|"
    r"pr|mr|issue|epic|step|шаг|line|строк[аи]|commit|hook|round|раунд|turn|call)\s*$",
    re.I,
)


# Below this number a bare `#N` is as likely a session as a memory (this
# project's sessions run past #249, its memory past #690): such an id is
# credited only when the word before it names memory or a decision. The
# spot-check that forced this: "Передача #226", "#228 открыта" — handoff and
# session numbers that the first cut credited to the tail.
SESSION_CEILING = 300
_MEMORY_WORD_BEFORE = re.compile(
    r"(?:memory|memories|memor\w*|памят\w*|decision\w*|решени\w*|gotcha|pattern|convention"
    r"|context|dead[\s_-]?end|норм\w*|правил\w*|запис\w*|тупик\w*|конвенци\w*|паттерн\w*)"
    r"\W{0,3}$",
    re.I,
)


def cited_ids(text: str, *, tail: bool = False) -> set[int]:
    """Memory/decision ids named in `text`, session-style numbers excluded.

    Inside the tail itself (`tail=True`) every `#N` is an id by construction.
    In agent prose a low number needs a memory word in front of it."""
    out: set[int] = set()
    for m in _MEMORY_ID.finditer(text):
        before = text[max(0, m.start() - 24) : m.start()]
        if _NOT_MEMORY_BEFORE.search(before):
            continue
        mid = int(m.group(1))
        if tail or mid >= SESSION_CEILING or _MEMORY_WORD_BEFORE.search(before):
            out.add(mid)
    return out


_REFETCH_BASH = re.compile(r"tausik\s+(?:status|session\s+(?:current|open))\b")
_REFETCH_MCP = {
    "mcp__tausik-project__tausik_status",
    "mcp__tausik-project__tausik_session_current",
    "mcp__tausik-project__tausik_session_open",
}

# --- the parts of the rules file ---------------------------------------------------------


def split_parts(text: str) -> dict[str, str]:
    """Handwritten | state | tail | shared, cut at the generator's own markers.

    The DYNAMIC block starts at its marker (or at the state heading in a file
    that predates the marker); inside it the tail and the shared block start
    at their headings. Anything before the block is handwritten.
    """
    start = text.find(DYNAMIC_START)
    if start < 0:
        start = text.find(STATE_HEADING)
    if start < 0:
        return {"handwritten": text, "state": "", "tail": "", "shared": ""}
    hand, dyn = text[:start], text[start:]
    tail_at = dyn.find(TAIL_HEADING)
    shared_at = dyn.find(SHARED_HEADING)
    ends = [i for i in (tail_at, shared_at) if i >= 0]
    state = dyn[: min(ends)] if ends else dyn
    tail = dyn[tail_at : (shared_at if shared_at > tail_at else len(dyn))] if tail_at >= 0 else ""
    shared = dyn[shared_at:] if shared_at >= 0 else ""
    return {"handwritten": hand, "state": state, "tail": tail, "shared": shared}


def cost_of(text: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, part in split_parts(text).items():
        b = len(part.encode("utf-8"))
        tokens = round(b / CHARS_PER_TOKEN)
        out[name] = {
            "bytes": b,
            "tokens": tokens,
            "context_share_pct": round(100.0 * tokens / MEDIAN_CONTEXT_TOKENS, 3),
        }
    return out


def tail_ids(text: str) -> set[int]:
    """Memory ids the tail (and the state block's Active/Blocked lines) carry."""
    parts = split_parts(text)
    return cited_ids(parts["tail"], tail=True)


def tail_ids_in_history(repo: str, rules: str = "CLAUDE.md", limit: int = 400) -> set[int]:
    """Union of ids the tail ever carried, over the rules file's git history."""
    try:
        shas = subprocess.run(
            ["git", "-C", repo, "log", f"-{limit}", "--format=%H", "--", rules],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return set()
    ids: set[int] = set()
    for sha in shas:
        shown = subprocess.run(
            ["git", "-C", repo, "show", f"{sha}:{rules}"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if shown.returncode == 0:
            ids |= tail_ids(shown.stdout)
    return ids


# --- transcripts -------------------------------------------------------------------------


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def _blocks(rec: dict[str, Any]) -> list[dict[str, Any]]:
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [c for c in content or [] if isinstance(c, dict)]


def _flat(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


@dataclass
class SessionUse:
    refetch_in_first_calls: bool = False
    tool_calls_seen: int = 0
    tail_sourced_ids: set[int] = field(default_factory=set)
    unverified_ids: set[int] = field(default_factory=set)


def session_use(path: Path, tail_history: set[int]) -> SessionUse:
    """Walk one Claude Code transcript in order, tracking what the agent has seen."""
    use = SessionUse()
    seen_ids: set[int] = set()
    for rec in _iter_jsonl(path):
        kind = rec.get("type")
        if kind == "user":
            for blk in _blocks(rec):
                seen_ids |= cited_ids(_flat(blk.get("content") or blk.get("text") or ""))
        elif kind == "assistant":
            for blk in _blocks(rec):
                if blk.get("type") == "tool_use":
                    use.tool_calls_seen += 1
                    if use.tool_calls_seen <= FIRST_CALLS and _is_refetch(blk):
                        use.refetch_in_first_calls = True
                    cited = _flat(blk.get("input") or {})
                else:
                    cited = str(blk.get("text") or "")
                for mid in sorted(cited_ids(cited)):
                    if mid in seen_ids:
                        continue
                    if mid in tail_history:
                        use.tail_sourced_ids.add(mid)
                    else:
                        use.unverified_ids.add(mid)
                    seen_ids.add(mid)  # once cited, a later mention is not a second sourcing
    return use


def _is_refetch(block: dict[str, Any]) -> bool:
    name = str(block.get("name") or "")
    if name in _REFETCH_MCP:
        return True
    if name == "Bash":
        return bool(_REFETCH_BASH.search(str((block.get("input") or {}).get("command") or "")))
    return False


def jsonl_files(paths: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            out.extend(sorted(path.rglob("*.jsonl")))
        elif path.is_file():
            out.append(path)
    return out


# --- the report ---------------------------------------------------------------------------


def usage_report(paths: Iterable[str], tail_history: set[int]) -> dict[str, Any]:
    sessions = 0
    refetch = 0
    with_tail = 0
    tail_ids_total: set[int] = set()
    unverified_total: set[int] = set()
    for path in jsonl_files(paths):
        use = session_use(path, tail_history)
        if use.tool_calls_seen == 0:
            continue  # not an agent session
        sessions += 1
        refetch += int(use.refetch_in_first_calls)
        with_tail += int(bool(use.tail_sourced_ids))
        tail_ids_total |= use.tail_sourced_ids
        unverified_total |= use.unverified_ids
    pct = (lambda n: round(100.0 * n / sessions, 1)) if sessions else (lambda n: None)
    return {
        "sessions": sessions,
        "state_refetch_sessions": refetch,
        "state_refetch_pct": pct(refetch),
        "tail_sourced_sessions": with_tail,
        "tail_sourced_pct": pct(with_tail),
        "tail_sourced_ids": len(tail_ids_total),
        "unverified_ids": len(unverified_total),
        "tail_history_ids": len(tail_history),
    }


def render(cost: dict[str, dict[str, float]], usage: dict[str, Any]) -> str:
    lines = ["rules file cost per request (delivered every turn):"]
    for name, c in cost.items():
        lines.append(
            f"  {name:<12} {int(c['bytes']):>6} B  ~{int(c['tokens']):>5} tok  "
            f"{c['context_share_pct']:>6}% of median context"
        )
    if not usage["sessions"]:
        lines.append("usage: NO agent sessions in the given transcripts — nothing measured.")
        return "\n".join(lines)
    lines += [
        f"usage over {usage['sessions']} session(s):",
        f"  proxy A  state block re-fetched in first {FIRST_CALLS} calls: "
        f"{usage['state_refetch_sessions']} ({usage['state_refetch_pct']}%)",
        f"  proxy B  tail-sourced memory citation in session: "
        f"{usage['tail_sourced_sessions']} ({usage['tail_sourced_pct']}%), "
        f"{usage['tail_sourced_ids']} distinct id(s); {usage['unverified_ids']} cited id(s) "
        f"never in the tail (uncredited); tail history carried {usage['tail_history_ids']} id(s)",
        "not measured: task success (paired A/B runs needed).",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cost and usage of the generated rules-file block")
    ap.add_argument("paths", nargs="*", help="transcript files or directories (*.jsonl)")
    ap.add_argument("--rules", default="CLAUDE.md")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    text = Path(args.repo, args.rules).read_text(encoding="utf-8")
    cost = cost_of(text)
    history = tail_ids_in_history(args.repo, args.rules) | tail_ids(text)
    usage = usage_report(args.paths, history)
    if args.json:
        print(json.dumps({"cost": cost, "usage": usage}, ensure_ascii=False, indent=2))
    else:
        print(render(cost, usage))
    return 0


if __name__ == "__main__":
    sys.exit(main())
