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


def attribute(paths: Iterable[str]) -> tuple[dict[str, dict[str, int]], int]:
    """{slug: {category: calls}} for tasks whose done is seen, plus unattributed calls."""
    per: dict[str, dict[str, int]] = {}
    closed: set[str] = set()
    unattributed = 0
    for path in paths:
        current: str | None = None
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                msg = rec.get("message") or {}
                if rec.get("type") != "assistant" or not isinstance(msg.get("content"), list):
                    continue
                for block in msg["content"]:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tool, tin = str(block.get("name", "")), block.get("input") or {}
                    event = _slug_event(tool, tin)
                    if event and event[0] == "start":
                        current = event[1]
                    if current:
                        bucket = per.setdefault(current, dict.fromkeys(CATEGORIES, 0))
                        bucket[category(tool, tin)] += 1
                    else:
                        unattributed += 1
                    if event and event[0] == "done":
                        closed.add(event[1])
                        if event[1] == current:
                            current = None
    return {s: c for s, c in per.items() if s in closed}, unattributed


def report(per: dict[str, dict[str, int]], complexity: dict[str, str], unattributed: int) -> str:
    """Per-complexity medians by category. Never a blended median alone."""
    lines = [
        f"Closed tasks attributed: {len(per)}; calls outside any task window: {unattributed}.",
        "Per complexity (median calls per task):",
        "  " + f"{'class':<10}{'n':>4}{'total':>7}" + "".join(f"{c:>9}" for c in CATEGORIES),
    ]
    for cls in ("simple", "medium", "complex", "undeclared"):
        rows = [c for s, c in per.items() if (complexity.get(s) or "undeclared") == cls]
        if not rows:
            continue
        totals = [sum(r.values()) for r in rows]
        cells = "".join(f"{median(r[c] for r in rows):>9}" for c in CATEGORIES)
        lines.append(f"  {cls:<10}{len(rows):>4}{median(totals):>7}{cells}")
    all_calls = sum(sum(c.values()) for c in per.values()) or 1
    share = ", ".join(
        f"{c} {100 * sum(r[c] for r in per.values()) / all_calls:.1f}%" for c in CATEGORIES
    )
    lines.append(f"Share of attributed calls: {share}.")
    return "\n".join(lines)


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
    paths = newest_project_transcripts(project_dir, int(getattr(args, "last", 10) or 10))
    if not paths:
        print("No host transcripts found for this project.")
        return
    per, unattributed = attribute(paths)
    complexity = {t["slug"]: t.get("complexity") for t in (svc.be.task_list() or [])}
    print(f"Transcripts read: {len(paths)} (newest).")
    print(report(per, complexity, unattributed))
