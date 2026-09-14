# Enforcement boundary: what is covered and what is not

> Split out of [`../ru/agent-contract.md`](../ru/agent-contract.md) while closing
> `powershell-tool-bypasses-bash-firewall` — the topic stands on its own, and
> together with the channel-coverage matrix it no longer fit inside the contract
> (filesize gate). RU original: [`../ru/enforcement-coverage.md`](../ru/enforcement-coverage.md).

Full event/coverage reference: [`hooks.md`](hooks.md). In short:

QG-0 (Rule 1) and the scope ACL (Rule 2) historically hung on `Write|Edit` only,
so **a file write through Bash bypassed both**: `cat > f <<EOF`, `sed -i`, `tee`,
`dd of=`, `python -c "open(f,'w')"` created and edited files with no active task
and outside the declared `scope_paths` (demonstrated live in sessions #117/#118).
Since 1.8 `bash_write_gate` closes that hole, and `MultiEdit`/`NotebookEdit` were
added to the `task_gate`/`scope_write_gate` matchers. Since 1.9 (GitHub PR #5,
Okianiwa) every write guard reads ONE list of write tools —
`scripts/hooks/write_tools.py`: the built-in editors plus the serena and
windows-mcp editors — and one list of payload fields (`file_path`,
`notebook_path`, `path`, `relative_path`, `destination`), so a notebook or an
MCP edit reaches the same gates as a Write on the hook-bearing hosts (Claude,
Qwen, Codex — the ones that take `build_hooks_dict`; OpenCode's QG-0 plugin
keeps its own list of that host's editors); `tests/test_pr5_hook_coverage.py`
holds the bootstrap matchers to that list and refuses an unlisted write without
a task.

**What the gate catches:** redirections (`>`, `>>`, `&>`, `N>`, including the
heredoc header line), `tee`, `dd of=`, `sed -i` (GNU and the BSD `-i ''` form),
`cp`/`mv`/`install` (destination **and** `-t`/`--target-directory=`), `truncate`,
`touch`, `curl -o`/`--output`, `wget -O`/`--output-document`, `tar -x … -C DIR`,
`unzip … -d DIR`, a literal `open(path, 'w'|'a'|'x')` inside `python`/`perl`/
`ruby -c` — and, on the PowerShell side, `Set-Content`, `Add-Content`,
`Clear-Content`, `Out-File`, `New-Item`, `Tee-Object`, `Copy-Item`/`Move-Item`
destinations, `Invoke-WebRequest -OutFile`, `Export-Csv`. Heredoc BODIES are not
scanned (a `->`/`>` in prose or code inside the body would manufacture a phantom
target and block an honest write). Only targets **inside** the project tree are
gated, exactly as for Write; the scratchpad, `/tmp`, `/dev/null` and other repos
are allowed.

**Python AST catalogue.** `python_source_writes.RECOGNISED_PYTHON_WRITE_FORMS`
is the single declared list: literal `open` with a write mode; literal
`Path`/`pathlib.Path` `write_text`, `write_bytes`, write-mode `open`, `unlink`,
`mkdir` and `rename`; `shutil.copy`/`move` to a literal destination; and
`os.replace`'s literal source and destination. A simple string bound earlier in
the same straight-line Python scope is accepted as a `Path` argument. The same
reader handles `python -c`, Python script files, and `python - <<PY` when its
header proves Python receives the body on stdin.

**What it does NOT catch (the explicit residual).** A shell is Turing-complete,
so a total gate is impossible. Not intercepted: a path built or passed through a
variable (`f=scripts/x.py; echo >$f`, `echo > $SCRATCH/x`, `$env:TEMP\x` — a
token carrying `$` is treated as unresolvable and dropped); `base64 -d | sh` and
other obfuscation; a command assembled from STDIN (`… | xargs -I{} bash -c '…'`)
or executed on another host (`ssh host 'cmd'` — this project's paths mean nothing
there); `curl -O`/`wget` without `-O`; `tar`/`unzip` extraction into the current
directory with no `-C`/`-d`; arbitrary interpreter code that writes a file by a
form outside that declared Python AST catalogue.

**The `bash -c` / `sh -c` wrapper — CLOSED.** `bash -c 'echo x > scripts/foo.py'`
used to yield NO target at all: the redirection lives inside one quoted argument
and the parser never descended into the payload. Rule 1 and the scope ACL were
bypassable by a one-liner of the class Decision #162 closed for heredocs — while
the residual boundary claimed the cost of a bypass had been raised to "you must
deliberately obfuscate". `bash -c` is written every day and is not obfuscation;
the claim was overstated. The parser now descends RECURSIVELY into the payload of
`bash`/`sh`/`zsh`/`dash`/`ksh`/`ash`/`busybox` under `-c` (including the combined
`-lc`, `-ec` forms), with a declared nesting bound (`_MAX_WRAPPER_DEPTH`) so
`bash -c "bash -c '…'"` cannot spin. A quoted mention (`echo 'bash -c "x > y"'`),
`bash script.sh` without `-c`, and the long option `--color` are not targets.

**Transparent prefixes — CLOSED.** `env bash -c '…'` hid the wrapper exactly the
way the wrapper hid the redirection: the shell test looked at the first token,
and that token was `env`. Found by adversarially reviewing the wrapper FIX
(convention #276), not the code it replaced. `env`, `sudo`, `doas`, `nohup`,
`nice`, `ionice`, `stdbuf`, `timeout`, `command`, `exec` are now stripped before
the command is identified — along with their flags, `VAR=val` assignments and the
numeric argument of `timeout`/`nice`. That also closed the "writer behind a
wrapper" (`sudo tee`) previously listed as uncaught: the writer was hidden not by
`tee` but by the word in front of it. A token that merely STARTS like a prefix
(`environment.py`, `timeout_test.sh`) is not one.

`TAUSIK_SKIP_HOOKS=1` still disables everything — but that bypass is
telemetered (`emit_supervision_bypass`); there is no silent disabling.

**An unparseable command.** If a command does not tokenize (unbalanced quote),
the parser falls back to a regex that deliberately OVER-detects.
`bash_write_gate` (QG-0) accepts that answer: the worst case is being asked for a
task the write needed anyway. `memory_pretool_block` does not: its block accuses
the agent of leaking knowledge and offers only two exits (a marker that would be
a lie, and a permanent config exemption for a one-off command), so a false
positive costs more than a miss and trains the bypass. The miss is not silent —
`fail_open_unparseable_<channel>` is recorded (`…_bash`, `…_powershell`: the
reason names the parser that failed rather than filing everything under Bash) —
and the in-tree half of the deny-list is judged again by the `memory_route` gate
and the pre-commit hook before anything can be committed.

## Coverage BY RULE, not by whole host

The notice an agent reads answers two different questions, and the second exists
because the first was not enough. "No real-time mechanism is deployed on this
host" is true and coarser than the truth: on Kilo every task closure, every
knowledge write and every task opening IS refused, because those go through our
own tools. One sentence about a whole host cannot carry both answers, and
carrying only the first lies to the user in the other direction.

The split follows WHO PERFORMS THE ACTION:

| What holds the rule | Which rules | Where it works |
|---|---|---|
| Our surface (`tausik_*` / CLI) | QG-0, QG-2, session limit (9.2), memory routing | EVERY host: the enforcement point is inside our code, and the MCP server is what an otherwise bare install still has |
| Intercepting the host's action | Rule 1 (no code without a task), Rule 2 (scope boundaries), Rule 10.12 (secrets) | ONLY where the artifact carrying that particular rule is deployed |

The second column is derived from the deployment, not from a list: each rule
names its artifact (`hook:task_gate.py`, `plugin:tausik-qg0.js`), and "is it
covered here" is the question "is that artifact in the profile". So OpenCode,
which ships one QG-0 plugin, shows as covering Rule 1 and NOT covering Rule 2 or
Rule 10.12 — which is the truth, rather than "the host is covered".

Measured at the MCP boundary (session #232, AST): 146 declared tools, 44 mutating
handlers, and not one reaching the backend directly. The service layer's refusals
do travel to the boundary — and that is checked by driving the handlers, not by
reasoning about them: `tests/test_rule_coverage.py` closes a task through
`tausik_task_done` with no receipt and requires the task to stay open.

`.tausik/tausik doctor` prints both lines: coverage by host, and the split by
rule.

### Two conditions for an interception, and the scan sees one

"Is that artifact in the profile" is the condition a scan can answer. On a
host that guards its hook mechanism there is a second one the scan cannot: the
host must be WILLING to run the project's hooks. Codex runs a project's
`.codex/hooks.json` only after the user has trusted it, and the two states are
byte-identical on disk. Measured live in the 1.9 acceptance run (session #251):
with the generated profile present but untrusted, the forbidden
`Path('outside.txt').write_text(...)` completed and the file existed — no hook
ran; the same operation under a trusted profile was refused before the write.
So for Rule 1 and Rule 2 on Codex the honest statement is "hard once the hooks
are trusted", `doctor` reports only the first condition and says so, and an
untrusted generated profile is NOT protected and is not described as such —
see the [Codex enforcement matrix](model-providers.md#codex-enforcement-matrix).

## Channel-coverage matrix

Supervision can be holed not only by RULE but by CHANNEL, and the second kind is
harder to notice: every test is green, because every test asks the covered
channel. On win32 — the platform this project calls primary — the agent is handed
TWO shell tools, `Bash` and `PowerShell`, and until
`powershell-tool-bypasses-bash-firewall` the second matched no PreToolUse hook.

| Gate | Write/Edit | Bash | PowerShell |
|---|---|---|---|
| `task_gate` (Rule 1) | ✅ | — ¹ | — ¹ |
| `scope_write_gate` (Rule 2) | ✅ | — ¹ | — ¹ |
| `bash_write_gate` (Rules 1 + 2 for shells) | n/a | ✅ | ✅ |
| `bash_firewall` (dangerous commands) | n/a | ✅ | ✅ |
| `git_push_gate` (push ticket) | n/a | ✅ | ✅ |
| `memory_pretool_block` (memory-route) | ✅ | ✅ | ✅ |
| `secret_scan` (Rule 10.12) | ✅ | ✅ ² | ✅ ² |

¹ Not a gap: the shell vector is judged by `bash_write_gate`, which IMPORTS
`scope_write_gate`'s decisions rather than copying them. A shell event carries no
`file_path`, so there is nothing for those two hooks to read.

² **Gap closed** (`secret-scan-covers-no-shell-channel`, Decision #178).
`secret_scan` is now on `SHELL_MATCHER` in both bootstraps and admits the shell
tools via `shell_channel.is_shell_tool` — on both channels at once, because
closing it on one shell would put the channels back out of step. The whole
command string is scanned (a strict superset of extracting the written value: it
catches a heredoc body and `Set-Content -Value`, plus `export KEY=…` — the secret
literal in context, which Rule 10.12 also covers) with no new shell parsing. The
residual is the same as for paths: a secret passed by variable/env
(`--token "$TOKEN"`) is not a literal anywhere, so it is not resolved and not
flagged — the correct way to pass it, not a gap.

### PowerShell data-carrying constructs: closed, or named

"Is this a command or is this text?" must be asked of EVERY construct, not one.
It had been answered for quotes and left unasked for here-strings — and the gate
blocked this project's own routine `git commit -m @'...'@`, because a `>` in the
message's prose read as a redirection. The audit, one by one:

| Construct | Status | How |
|---|---|---|
| `@'…'@`, `@"…"@` (here-string) | **closed** | The body is ONE token. The opening quote must end its line, and the terminator `'@` is recognised only at the START of a line — as PowerShell itself requires. Relaxing either condition re-exposes the body as live shell. |
| `'…'`, `"…"` | closed since the first version | A quoted mention arrives as one token and never forms a statement. |
| `{…}` (script block) | **deliberately NOT data** | Braces are separators; the contents are read as ordinary statements. A script block IS executable — `… \| ForEach-Object { Remove-Item -Recurse C:\ }` must stay visible. Prose does not live inside braces. |
| `$(…)`, `@(…)` | **residual, named** | Not treated as a nesting level; a token carrying `$` is marked unresolvable and dropped rather than guessed. The same residual the POSIX gate documents for `$VAR`. |

**The dialect follows the TOOL; the line is not offered to both judges.** The
tempting phrasing — "read it with both tokenizers and block if either sees a
push" — sounds like a tightening and is a loosening: each dialect misreads the
other's syntax, so of two judges the INCOMPETENT one wins. What actually
happened: the POSIX lexer does not know a here-string, broke out at the
apostrophe in "PowerShell's", and the `git push --force` in a commit message's
prose blocked an ordinary commit. Tokenization goes through `shell_channel` by
`tool_name` — the same single table as write targets.

Push-gate residual, named explicitly: a push inside a wrapper payload
(`powershell -Command 'git push'`) is one quoted token to its dialect and is NOT
ticketed. `bash_firewall` does descend into payloads, so a force-push that way is
still blocked; an ordinary push that way is not. Closing this via `scan_target`
(which joins an interpreter's payload back RAW) is NOT acceptable — it would
block an honest `python -c "print('git push')"`, trading one false block for
another.

The symptom to look for next time: a detector that can tell text from command in
one place and not in the place beside it. The cost of that asymmetry is not a
miss but a FALSE BLOCK on a routine operation, and that trains the bypass more
expensively than the missed command would have cost (#291).

**PowerShell-channel residual** (on top of the shell-wide "obfuscated write"): a
target arriving by PIPELINE (`Get-ChildItem C:\ | Remove-Item -Recurse`) is not an
operand of the deleting cmdlet and is not seen; `-EncodedCommand <base64>` is not
decoded; .NET calls (`[IO.File]::Delete`) are not parsed. `Remove-Item` of a
project file is not reported as a write — exact parity with Bash, where `rm` is
not a writer either; that gap is common to both channels and is closed
separately rather than on one side only. A script path carrying a QUOTE
character (`python "a'b\helper.py"`) keeps its backslashes and is left
unresolved on POSIX — the quote rule that protects a `-c` payload from the
separator rewrite covers it too; a token with a quote is read as source, not
as a path (review #208, record #22).

**Mixed scope (Rule 2, AC3).** As soon as ANY active task declares
`scope_paths`, ACL enforcement switches on for ALL co-active tasks: a parallel
task with no declared scope loses its legacy freedom and must either declare its
own surface or have writes outside the union of declared ACLs blocked (through
Write and through both shells). This closes the "keep one undeclared task active
to bypass scope" trick. Legacy freedom remains only when NOBODY declared a scope.
