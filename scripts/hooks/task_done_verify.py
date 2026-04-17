#!/usr/bin/env python3
"""PostToolUse hook — adversarial evidence audit after task_done.

Fires after a real `tausik task done` call (MCP tool or Bash CLI), applies 5
rule-based heuristics to the task's notes; if 2+ fail, emits a stderr warning
nudging the agent to re-verify. Always exits 0 (non-blocking).

Inspired by oh-my-claudecode Ralph mode (verify/fix loop). Rule-based
first-line defence; the agent is expected to run `/review` if warnings appear.

Skipped via TAUSIK_SKIP_HOOKS=1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _common import (  # noqa: E402
    extract_task_done_slug_from_bash,
    is_task_done_invocation,
    tausik_path,
)


MAX_NOTES = 12_000

_AC_MARKER_RE = re.compile(r"[✓✔]|\b(passed|verified|ok|complete[d]?)\b", re.IGNORECASE)
_FILE_RE = re.compile(
    r"\b[\w/.-]+\.(py|js|ts|tsx|jsx|go|rs|java|kt|php|md|json|yaml|yml|sql|sh)\b"
)
_TEST_COUNT_RE = re.compile(
    r"\b\d+\s*(passed|failed|tests?|assertions?)\b", re.IGNORECASE
)
_FILE_REF_PATTERNS = (
    re.compile(r"\b\w+\.\w+:\d+"),
    re.compile(r"\b(def|class|function)\s+\w+"),
    re.compile(r"#L\d+"),
    re.compile(r"\(line\s+\d+\)"),
)
_LINT_MARKERS = ("ruff", "lint", "mypy", "eslint", "tsc", "fmt", "format")


def _extract_notes_section(task_show_output: str) -> str:
    """Return only the notes portion of `tausik task show` output.

    Reduces false-positive marker matches on task title / goal / AC prose.
    """
    if not task_show_output:
        return ""
    # `task show` layout keeps notes at the end, after fields like "notes:" or logs
    # marker. Fall back to full output if we can't locate a clear separator.
    lower = task_show_output.lower()
    for sep in ("\nnotes:\n", "\nlogs:\n", "\nnotes\n---", "\nlog entries:\n"):
        idx = lower.find(sep)
        if idx >= 0:
            return task_show_output[idx + len(sep) :]
    return task_show_output


def _fetch_task_show(tausik_cmd: str, slug: str, project_dir: str) -> str:
    try:
        result = subprocess.run(
            [tausik_cmd, "task", "show", slug],
            capture_output=True,
            text=True,
            timeout=4,
            cwd=project_dir,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _check_file_paths(notes: str) -> bool:
    return bool(_FILE_RE.search(notes))


def _check_ac_checkmarks(notes: str) -> bool:
    """Count ✓ / passed / verified / ok / complete(d) tokens on word boundaries.

    Word-boundary regex prevents 'complete' from matching 'incomplete' or 'completion'.
    """
    return len(_AC_MARKER_RE.findall(notes)) >= 2


def _check_test_numbers(notes: str) -> bool:
    return bool(_TEST_COUNT_RE.search(notes))


def _check_file_references(notes: str) -> bool:
    return any(p.search(notes) for p in _FILE_REF_PATTERNS)


def _check_lint_status(notes: str) -> bool:
    lowered = notes.lower()
    return any(marker in lowered for marker in _LINT_MARKERS)


CHECKS = (
    ("file_paths", "reference concrete files", _check_file_paths),
    ("ac_checkmarks", "tick off AC criteria (✓/passed/verified)", _check_ac_checkmarks),
    ("test_numbers", "include test counts", _check_test_numbers),
    ("file_refs", "reference specific code sections", _check_file_references),
    ("lint_status", "mention lint/type-check status", _check_lint_status),
)


def evaluate_notes(notes: str) -> tuple[int, list[str]]:
    if len(notes) > MAX_NOTES:
        notes = notes[:MAX_NOTES]
    failures: list[str] = []
    for name, desc, fn in CHECKS:
        if not fn(notes):
            failures.append(f"- {name}: evidence should {desc}")
    return len(failures), failures


def _extract_slug(tool_input: dict) -> str:
    slug = tool_input.get("slug")
    if slug:
        return str(slug)
    return extract_task_done_slug_from_bash(tool_input.get("command") or "")


def main() -> int:
    if os.environ.get("TAUSIK_SKIP_HOOKS"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    if not is_task_done_invocation(tool_name, tool_input):
        return 0

    tool_result = payload.get("tool_result") or payload.get("tool_response") or {}
    if isinstance(tool_result, dict) and tool_result.get("is_error"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tausik_db = os.path.join(project_dir, ".tausik", "tausik.db")
    if not os.path.exists(tausik_db):
        return 0

    slug = _extract_slug(tool_input)
    if not slug:
        return 0

    tausik_cmd = tausik_path(project_dir)
    if not tausik_cmd:
        return 0

    raw = _fetch_task_show(tausik_cmd, slug, project_dir)
    if not raw:
        return 0

    notes = _extract_notes_section(raw)
    failed_count, failures = evaluate_notes(notes)
    if failed_count < 2:
        return 0

    lines = [
        f"[TAUSIK verify-fix-loop] Task '{slug}' closed, but the AC evidence looks thin:",
        *failures,
        "",
        "Recommend: run `/review` for an adversarial pass, or reopen the task "
        "with `tausik_task_update status=active` if you skipped steps.",
    ]
    print("\n".join(lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
