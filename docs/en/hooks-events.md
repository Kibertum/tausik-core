**English** | [Русский](../ru/hooks-events.md)

# Hook events and the coverage of file writes

<!-- doc-map: reader=maintainer; zone=quality -->

A review of the TAUSIK hook contract (task `l26-hook-contract-review`, Decision #162). It
answers the question of AC1: which events intercept file writes, and whether a write through
Bash/NotebookEdit is covered natively.

## Why this matters

QG-0 (SENAR Rule 1, "no code without a task") and the scope ACL (Rule 2) are **PreToolUse
hooks** bound to the matchers of specific tools. So their reach is exactly the tools listed in
the matcher. A write tool that did not make it into the matcher bypasses the check entirely —
while the gate report looks equally green. That is not a hypothesis: in sessions #117/#118 the
same file was blocked through `Write` and then created through a Bash heredoc without a single
objection.

## The events TAUSIK uses today

The source of truth is `bootstrap/bootstrap_hooks.py::build_hooks_dict` (it generates the
`hooks` block of `.claude/settings.json`). Verifiable from the code:

| Event | Matchers | Role |
|---|---|---|
| `PreToolUse` | `Write\|Edit\|MultiEdit\|NotebookEdit` | `task_gate` (QG-0), `scope_write_gate` (the ACL), `secret_scan`; `memory_pretool_block` — on `Write\|Edit\|MultiEdit\|Bash` |
| `PreToolUse` | `Bash` | `bash_firewall`, **`bash_write_gate` (QG-0 plus the ACL for writes from a shell)** |
| `PreToolUse` | `Bash(git push *)` | `git_push_gate` |
| `PostToolUse` | Write/Bash/Read/… | the formatter, usage/activity events, the cost budget, `task_done_verify` |
| `SessionStart` / `UserPromptSubmit` / `Stop` / `SessionEnd` | `` | the start injection, the keyword detector, cleanup, metrics |

## The coverage of file writes

| Write vector | Tool/command | Coverage before 1.8 | Coverage from 1.8 |
|---|---|---|---|
| A direct edit | `Write`, `Edit` | ✅ QG-0 plus ACL | ✅ |
| A multi-edit | `MultiEdit` | ⚠️ the ACL only (the QG-0 matcher was `Write\|Edit`) | ✅ QG-0 plus ACL |
| A notebook | `NotebookEdit` | ❌ not covered | ✅ QG-0 plus ACL (by `notebook_path`) |
| A shell redirect / heredoc | `cat > f`, `echo >> f` | ❌ bypass | ✅ `bash_write_gate` |
| In-place editors and writers | `sed -i`, `tee`, `dd of=`, `cp`/`mv`/`install` (including `-t`), `truncate`, `touch`, `curl -o`, `wget -O`, `tar -x -C`, `unzip -d` | ❌ bypass | ✅ `bash_write_gate` |
| Interpreter code | `python -c "open(f,'w')"` | ❌ bypass | ⚠️ only a literal `open(...)` is caught |

Natively — through the host's own mechanism — a write through Bash/NotebookEdit is **not**
covered: Claude Code emits no separate "write" event, it hands the hook a raw `tool_input`. So
the coverage is achieved by parsing the command inside `bash_write_gate` rather than by relying
on an event from the host.

## The 2026 event landscape (from the analysis of 2026-07-18)

The set of Claude Code hook events grew in 2026 (to roughly three dozen: `PermissionRequest`,
`PermissionDenied` with retry, `PostToolUseFailure`, `SubagentStart/Stop`,
`PreCompact/PostCompact`, `TaskCreated/TaskCompleted`, `WorktreeCreate/Remove` and others).
None of them turns a Bash write into a separately observable "a file was written" event, so the
review's conclusion is that the hole cannot be closed by subscribing to a new event — the
command has to be parsed. Those events are candidates for future telemetry (for example
`PostToolUseFailure` for fail-open supervision) but were outside the scope of that task. The
list above is the result of a design-level survey of the landscape, not a verified
specification of the host's API.

## The residual boundary

`bash_write_gate` is best-effort by design. What it deliberately does not catch, and why, is in
[`agent-contract.md`](agent-contract.md#the-boundary-of-hook-enforcement-what-is-covered-and-what-is-not)
(obfuscation, a path held in a variable, a writer behind a wrapper). AC2 allowed "close it OR
document the boundary explicitly"; here it is documented.
