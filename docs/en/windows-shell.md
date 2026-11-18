# Windows shell hygiene for agents

<!-- doc-map: reader=agent; zone=getting-started -->

On Windows, nested quotes and remote one-liners fail often and burn turns.
Prefer a **file**, not a one-liner. This page is the day-0 surface; the warn-only
PreToolUse hook `windows_shell_hygiene.py` names the same rules at call time.

## Rules

1. **Nested quotes → write a file.** Put the script in `.ps1` / `.cmd` / `.py`,
   then run that file. Do not nest `"…'…\"…\"…"` in a Shell one-liner.
2. **Nothing after `-EncodedCommand`.** PowerShell rejects trailing arguments
   after the base64 blob (dead_end #1019).
3. **`gh api --jq` with braces breaks in PowerShell.** Prefer `--jq` via a file
   argument, or run under `cmd /c` / Git Bash without PowerShell parsing
   (gotcha #975).
4. **SSH / remote bash:** write a local LF script, `scp` it, then `ssh … bash
   script.sh`. Avoid heredocs from a Windows CRLF shell (#1063).
5. **MCP-first still wins.** Prefer `tausik_*` MCP tools over shell when a twin
   exists; shell is for chaining and file-fed multi-line args.

## Related

- Consumer export-only git: [quickstart](quickstart.md) (product + `tausik/`)
- Hooks overview: [hooks](hooks.md)
