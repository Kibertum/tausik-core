"""`tausik metrics calls` — what a closed task spends its tool calls on.

Cache is ~94% of the bill and every call re-sends the whole prefix, so the lever is the
NUMBER of calls. This splits them by what they did — read, edit, run, script, ceremony,
other — per closed task, by complexity. Calls are attributed to the task between its
`task start` and `task done` in the host transcript; a call outside any such window is
counted as unattributed, not dropped.
"""

from __future__ import annotations

import json
import os
import re
from statistics import median
from pathlib import Path
from typing import Any, Iterable

CATEGORIES = ("read", "edit", "run", "script", "ceremony", "other")

_READ_TOOLS = {"Read", "Grep", "Glob", "NotebookRead", "mcp__codebase-rag__search_code"}
_EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
_SHELL_TOOLS = {"Bash", "PowerShell"}
_READ_CMDS = {
    "grep",
    "rg",
    "cat",
    "head",
    "tail",
    "ls",
    "wc",
    "find",
    "Get-Content",
    "Select-String",
    "Get-ChildItem",
}
_RUN_CMDS = {"pytest", "ruff", "mypy", "npm", "npx", "go", "cargo", "make"}
_GIT_READ = {"log", "show", "diff", "grep", "status", "blame"}
#: Leading `VAR=value` assignments and `cd dir &&` hops. They hid the real command from
#: the first histogram (PYTHONUTF8=1 came out as the third most used "command").
_PREFIX = re.compile(
    r"^(?:\s*(?:cd\s+[^;&|]+|[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S*))\s*(?:&&|;)?\s*)+"
)
_TAUSIK = re.compile(r"(?:^|/)(?:\.tausik/)?tausik(?:\.cmd)?$|project\.py$")
_START = re.compile(r"\btask\s+start\s+([a-z0-9][a-z0-9-]*)")
_DONE = re.compile(r"\btask\s+(?:done|obsolete)\s+([a-z0-9][a-z0-9-]*)")
_CODEX_RUN = re.compile(r"\b(?:pytest|ruff|mypy|npm|npx|cargo|go test)\b", re.I)


def shell_category(command: str) -> str:
    """The category of one shell command, judged by its first real word."""
    cmd = _PREFIX.sub("", command or "").strip()
    words = cmd.split()
    if not words:
        return "other"
    head = words[0].strip("\"'")
    base = os.path.basename(head)
    if _TAUSIK.search(head) or (
        base.startswith("python") and len(words) > 1 and words[1].endswith("project.py")
    ):
        return "ceremony"
    if base == "git":
        return "read" if len(words) > 1 and words[1] in _GIT_READ else "other"
    if base == "sed":
        return "edit" if any(w.startswith("-i") for w in words[1:3]) else "read"
    if base in _READ_CMDS:
        return "read"
    if base in _RUN_CMDS:
        return "run"
    if base.startswith("python"):
        if len(words) > 2 and words[1] == "-m" and words[2] in _RUN_CMDS:
            return "run"
        if len(words) > 1 and words[1] in ("-", "-c"):
            return "script"
        return "run"
    return "other"


def category(tool: str, tool_input: dict[str, Any]) -> str:
    if tool in _READ_TOOLS:
        return "read"
    if tool in _EDIT_TOOLS:
        return "edit"
    if tool.startswith("mcp__tausik"):
        return "ceremony"
    if tool in _SHELL_TOOLS:
        return shell_category(str(tool_input.get("command", "")))
    return "other"


def _slug_event(tool: str, tool_input: dict[str, Any]) -> tuple[str, str] | None:
    """("start"|"done", slug) when this call opens or closes a task."""
    if tool.startswith("mcp__tausik"):
        slug = tool_input.get("slug")
        if isinstance(slug, str):
            if tool.endswith("task_start"):
                return "start", slug
            if tool.endswith(("task_done", "task_obsolete")):
                return "done", slug
        return None
    if tool in _SHELL_TOOLS:
        cmd = str(tool_input.get("command", ""))
        m = _DONE.search(cmd)
        if m:
            return "done", m.group(1)
        m = _START.search(cmd)
        if m:
            return "start", m.group(1)
    return None


def _bucket(per: dict[str, dict[str, int]], slug: str) -> dict[str, int]:
    return per.setdefault(slug, {**dict.fromkeys(CATEGORIES, 0), "responses": 0})


def _codex_call(payload: dict[str, Any]) -> tuple[str, str, tuple[str, str] | None]:
    """Map one native Codex call without persisting its command or arguments."""
    name = str(payload.get("name") or "")
    raw = (
        payload.get("input")
        if payload.get("type") == "custom_tool_call"
        else payload.get("arguments")
    )
    source = raw if isinstance(raw, str) else json.dumps(raw or {})
    event = None
    match = _DONE.search(source) or _START.search(source)
    if match:
        event = ("done" if _DONE.search(source) else "start", match.group(1))
    if event or "mcp__tausik" in name:
        kind = "ceremony"
    elif name == "exec":
        if "tools.apply_patch" in source:
            kind = "edit"
        elif _CODEX_RUN.search(source):
            kind = "run"
        elif "tools.exec_command" in source or "tools.view_image" in source:
            kind = "read"
        else:
            kind = "script"
    else:
        kind = "other"
    return name, kind, event


def attribute(paths: Iterable[str]) -> tuple[dict[str, dict[str, int]], int]:
    """Task tool calls plus model responses; only tasks whose done is seen survive."""
    per: dict[str, dict[str, int]] = {}
    closed: set[str] = set()
    unattributed = 0
    for path in paths:
        current: str | None = None
        codex_response_tasks: set[str] = set()
        codex_seen_responses: set[str] = set()
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                payload = rec.get("payload") or {}
                if rec.get("type") == "event_msg" and payload.get("type") == "task_started":
                    continue
                if rec.get("type") == "response_item" and payload.get("type") in {
                    "custom_tool_call",
                    "function_call",
                }:
                    _, kind, event = _codex_call(payload)
                    if event and event[0] == "start":
                        current = event[1]
                    if current:
                        _bucket(per, current)[kind] += 1
                        codex_response_tasks.add(current)
                    else:
                        unattributed += 1
                    if event and event[0] == "done":
                        closed.add(event[1])
                        if event[1] == current:
                            current = None
                    continue
                if rec.get("type") == "token_usage_record":
                    response_id = payload.get("response_id")
                    if isinstance(response_id, str) and response_id not in codex_seen_responses:
                        for slug in codex_response_tasks:
                            _bucket(per, slug)["responses"] += 1
                        codex_seen_responses.add(response_id)
                        codex_response_tasks = set()
                    continue
                if rec.get("type") == "event_msg" and payload.get("type") == "task_complete":
                    for slug in codex_response_tasks:
                        _bucket(per, slug)["responses"] += 1
                    codex_response_tasks = set()
                    continue
                msg = rec.get("message") or {}
                if rec.get("type") != "assistant" or not isinstance(msg.get("content"), list):
                    continue
                response_tasks: set[str] = set()
                for block in msg["content"]:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tool, tin = str(block.get("name", "")), block.get("input") or {}
                    event = _slug_event(tool, tin)
                    if event and event[0] == "start":
                        current = event[1]
                    if current:
                        bucket = _bucket(per, current)
                        bucket[category(tool, tin)] += 1
                        response_tasks.add(current)
                    else:
                        unattributed += 1
                    if event and event[0] == "done":
                        closed.add(event[1])
                        if event[1] == current:
                            current = None
                for slug in response_tasks:
                    per[slug]["responses"] += 1
    return {s: c for s, c in per.items() if s in closed}, unattributed


def report(per: dict[str, dict[str, int]], complexity: dict[str, str], unattributed: int) -> str:
    """Per-complexity medians by category. Never a blended median alone."""
    lines = [
        f"Closed tasks attributed: {len(per)}; calls outside any task window: {unattributed}.",
        "Per complexity (median calls per task):",
        "  "
        + f"{'class':<10}{'n':>4}{'responses':>10}{'tools':>7}"
        + "".join(f"{c:>9}" for c in CATEGORIES),
    ]
    for cls in ("simple", "medium", "complex", "undeclared"):
        rows = [c for s, c in per.items() if (complexity.get(s) or "undeclared") == cls]
        if not rows:
            continue
        totals = [sum(r.get(c, 0) for c in CATEGORIES) for r in rows]
        cells = "".join(f"{median(r[c] for r in rows):>9}" for c in CATEGORIES)
        responses = median(r.get("responses", 0) for r in rows)
        lines.append(f"  {cls:<10}{len(rows):>4}{responses:>10}{median(totals):>7}{cells}")
    all_calls = sum(sum(row.get(c, 0) for c in CATEGORIES) for row in per.values()) or 1
    share = ", ".join(
        f"{c} {100 * sum(r[c] for r in per.values()) / all_calls:.1f}%" for c in CATEGORIES
    )
    lines.append(f"Share of attributed calls: {share}.")
    return "\n".join(lines)


def completed_only(
    per: dict[str, dict[str, int]], tasks: Iterable[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    """Keep transcript windows whose task is actually complete in project state.

    A transcript records the attempted ``task done`` call before its result.  Treating
    that attempt as success made a gate-blocked task look closed and understated its
    later rework.  Project state is the authority for acceptance.
    """
    done = {str(task.get("slug")) for task in tasks if task.get("status") == "done"}
    return {slug: counts for slug, counts in per.items() if slug in done}


def codex_transcripts(project_dir: str, last: int) -> list[str]:
    """Newest native Codex sessions whose session metadata proves the project cwd."""
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"
    target = str(Path(project_dir).resolve()).replace("\\", "/").casefold()
    matched = []
    for path in root.rglob("*.jsonl") if root.is_dir() else []:
        try:
            with path.open(encoding="utf-8", errors="replace") as stream:
                for _, line in zip(range(50), stream):
                    record = json.loads(line)
                    payload = record.get("payload") or {}
                    if record.get("type") != "session_meta":
                        continue
                    cwd = payload.get("cwd")
                    if (
                        isinstance(cwd, str)
                        and str(Path(cwd).resolve()).replace("\\", "/").casefold() == target
                    ):
                        matched.append(path)
                    break
        except (OSError, ValueError, TypeError):
            continue
    matched.sort(key=lambda path: path.stat().st_mtime)
    return [str(path) for path in matched[-max(1, last) :]]


def add(metrics_sub: Any) -> None:
    p = metrics_sub.add_parser(
        "calls",
        help="Tool calls per closed task by what they did (read/edit/run/script/ceremony/other), "
        "per complexity, over the last N host transcripts",
    )
    p.add_argument("--last", type=int, default=10, help="Last N transcripts (default: 10)")


def run(svc: Any, args: Any) -> None:
    import sys

    hooks = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks")
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    from project_config import find_tausik_dir
    from transcript_locator import newest_project_transcripts

    tdir = find_tausik_dir()
    project_dir = os.path.dirname(tdir) if tdir else os.getcwd()
    last = int(getattr(args, "last", 10) or 10)
    groups = [
        ("claude-compatible", newest_project_transcripts(project_dir, last)),
        ("codex", codex_transcripts(project_dir, last)),
    ]
    if not any(paths for _, paths in groups):
        print("No host transcripts found for this project.")
        return
    tasks = svc.be.task_list() or []
    complexity = {t["slug"]: t.get("complexity") for t in tasks}
    for host, paths in groups:
        if not paths:
            continue
        per, unattributed = attribute(paths)
        per = completed_only(per, tasks)
        print(f"Host: {host}; transcripts read: {len(paths)} (newest).")
        print(report(per, complexity, unattributed))
