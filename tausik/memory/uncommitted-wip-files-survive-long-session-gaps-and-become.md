---
slug: uncommitted-wip-files-survive-long-session-gaps-and-become
title: "Uncommitted WIP files survive long session gaps and become orphaned"
type: gotcha
tags:
  - commit-discipline
  - git
  - handoff
  - session-hygiene
task: null
edges: []
---

When a session gets interrupted mid-flight (process kill, IDE crash, multi-day gap), uncommitted files from that session and earlier sessions can pile up uncommitted in working tree. By the time someone resumes, the file authorship is unclear: which task, which session?

Concrete instance (session #52 resume on 2026-05-06): 3 unattributed files were found in working tree — scripts/validate_prompt_caching.py + tests/test_validate_prompt_caching.py (no task slug), and tests/test_verify_git_diff_stdin.py + scripts/verify_git_diff.py mod (the docstring named v14b-defect-mcp-task-done-stdin-hang but the fix wasn't included in commit 5a50003 for session #49).

Mitigation: at /end, before saving handoff, always cross-check `git status --short` against the session's done tasks. Any new/modified file NOT in a closed-task scope is suspect — either link it to a task explicitly in handoff, or open a tracking task before ending. Don't let uncommitted files become orphaned across session boundaries.

Detection heuristic: if a file's docstring/comments name a defect or task slug that isn't in the current session's `task_list --status done`, the file is from an earlier session that never committed.
