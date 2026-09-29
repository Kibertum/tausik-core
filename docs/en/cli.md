**English** | [Русский](../ru/cli.md)

# TAUSIK CLI — Command Reference

<!-- doc-map: reader=user; zone=core-surface -->

All commands are invoked via the wrapper: `.tausik/tausik <command> [subcommand] [arguments]`.
On Windows the wrapper is `.tausik/tausik.cmd`. The same surface is also available via MCP (`tausik_*` tools); see `mcp.md`.

## The working set

The surface is 54 top-level commands, and there is no reason to read them in order. This
project's database records 6930 calls into the TAUSIK surface across 74 distinct tools;
**the twelve commands below are 81% of them**, and twenty-eight are 95%. The measurement
describes this work, not yours — a project with a different rhythm will have a different
set. It is still where to start.

| Command | What for | Share of calls |
|---|---|---|
| `task update` | change a field on a started task — criteria, budget, scope | 11.3% |
| `task log` | record a step: how it ended and what became known | 10.4% |
| `task start` | open the work; the goal and acceptance criteria are checked here | 10.2% |
| `task add` | file a task — a finding, a defect, the next step of the composition | 9.0% |
| `task show` | read a task whole: criteria, scope, journal | 7.5% |
| `task done` | close it with a verification receipt | 6.1% |
| `memory add` | record a pattern, a convention or a dead end of this project | 5.6% |
| `task step` | mark a phase inside a task | 5.2% |
| `decide` | record a decision and what it rejected | 4.9% |
| `verify` | run the gates over the task's scope and get a receipt | 4.6% |
| `update-claudemd` | refresh the dynamic part of `CLAUDE.md` | 3.4% |
| `session handoff` | leave the next agent the state of the session | 2.9% |

Every flag of each is in `.tausik/tausik <command> --help`. The help text lives in the
parser rather than on this page: a page goes stale in silence, `--help` cannot.

> **Arguments containing `>`, `<`, `&` or `|` on Windows.** The `.cmd` wrapper runs under `cmd.exe`, which parses those characters as operators **before** the batch file starts — even when the caller passed an argument list and never asked for a shell. Measured: of nine hostile arguments, five were corrupted and two were corrupted **silently** — `48->49` arrived as `48-` with exit code 0 while the output was diverted into a stray file named `49`, and `a&b` arrived as `a` with the tail `b` executed as a command. That is how a truncated handoff was once stored while the command reported success.
>
> Such a call now **exits 3** and prints to stderr what was on the command line, what reached the process, and the name of the stray file if `cmd.exe` had already created one. A corrupted value is never stored in silence.
>
> What to do instead: call the POSIX wrapper `.tausik/tausik` from bash (it passes `"$@"` and cannot lose an argument) or use the MCP tools — neither goes through a shell. If the redirection was **deliberate** (a script writing `cmd /c "tausik.cmd status > out.txt"`, say), set `TAUSIK_CMDLINE_GUARD=off`.
>
> Redirection typed by hand in an interactive console (`tausik status > out.txt`) is left alone: there `%CMDCMDLINE%` holds only the shell's own startup line and names no arguments.

## The rest of the surface, by what you came for

The reference is cut by the reader's errand, not alphabetically.

| Page | What is on it |
|---|---|
| [cli-tasks.md](cli-tasks.md) | `init`, the project hierarchy, tasks whole, sessions |
| [cli-quality.md](cli-quality.md) | `verify`, gates, RENAR drift and conformance, reviews, the periodic audit, the record a bypassed gate leaves |
| [cli-knowledge.md](cli-knowledge.md) | knowledge and memory, dead ends, exploration, search, events, snippets, redaction |
| [cli-admin.md](cli-admin.md) | state in git, stacks, roles, skills, multi-agent, hygiene, batch execution, generated documents, maintenance, constants |

## See also

- [quickstart.md](quickstart.md) — the first hour, not the full list
- [glossary.md](glossary.md) — the words this page uses without explaining them
- [workflow.md](workflow.md) — the order these commands add up to
- [troubleshooting.md](troubleshooting.md) — when a command refused
