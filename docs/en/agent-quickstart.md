**English** | [Русский](../ru/agent-quickstart.md)

# Agent quickstart: connect TAUSIK, then work under it

You are an AI agent. This page is written for you, in the order you will need
it: how to connect the framework to a project on the host you are running in,
how to check that it is actually there, and how to do work once it is — as
exact calls, with the replies and refusals you will actually see. Every
command, tool name and refusal text here is taken from a live run of this
version, not remembered; a test holds them to the code
(`tests/test_agent_quickstart.py`).

The human version of this walkthrough is [quickstart.md](quickstart.md). The
rules themselves are in [AGENTS.md](../../AGENTS.md); this page is the
procedure that follows from them.

## 1. Connect

TAUSIK is a git submodule plus one bootstrap. From the project root:

```bash
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init --ide <host>
```

`<host>` is one of the hosts bootstrap scaffolds — **claude, cursor, qwen,
kilo, opencode, codex** — or `all`. Pick the one you are running in; `all`
deploys every profile side by side (they share one database in `.tausik/`).

| You are running in | `--ide` | What lands | What enforces the rules in real time |
|---|---|---|---|
| Claude Code / VS Code Claude Extension | `claude` | `.claude/` (skills, hooks, MCP), `.mcp.json`, `CLAUDE.md`, `AGENTS.md` | PreToolUse hooks (`.claude/settings.json`) |
| Cursor / Composer | `cursor` | `.cursor/mcp.json`, `.cursorrules`, `AGENTS.md` | nothing at the tool boundary — you self-enforce Rule 1 (see §5) |
| Qwen Code | `qwen` | `.qwen/` (skills, settings), `QWEN.md`, `AGENTS.md` | hooks (a subset of Claude's) |
| Kilo Code | `kilo` | `.kilo/`, `.kilocode/mcp.json`, `AGENTS.md` | nothing at the tool boundary — MCP gates only |
| OpenCode | `opencode` | `.opencode/` (one QG-0 plugin), `opencode.json` | the QG-0 plugin for Rule 1; nothing for Rule 2 |
| Codex CLI | `codex` | `.codex/` (config.toml with MCP, skills, agents, hooks.json), `AGENTS.md` | `.codex/hooks.json` — **only after the user trusts the project hooks in Codex**; an untrusted profile enforces nothing (measured live) |

After bootstrap: **restart the host** (MCP servers are read at startup), then
check. Two equivalent checks — the MCP tool if your host exposes `tausik_*`
tools, the CLI otherwise:

```
tausik_status                       ← MCP
.tausik/tausik status               ← CLI (Windows cmd/PowerShell: .tausik/tausik.cmd status)
```

Expected on a fresh project:

```
Tasks: 0/0 done
Session: none active
```

If the MCP tools are not there after a restart, run `.tausik/tausik doctor`
(or `tausik_doctor`) — it names the missing piece; the CLI works regardless.
Every `tausik_*` tool has a CLI twin, so nothing below depends on MCP.

**Codex specifically.** Codex runs a project's hooks only once the user has
trusted them. Until then `bootstrap --check` is clean and the hook file lists
every gate, and none of them fires. Do not report Rule 1/Rule 2 as enforced on
Codex unless the trusted state has been confirmed; the
[enforcement matrix](model-providers.md#codex-enforcement-matrix) carries the
same condition.

## 2. The cycle, as calls

One task at a time, every step recorded. MCP tool on the left, CLI twin on the
right; the reply is what you will see.

**Open a session.**

```
tausik_session_start                 .tausik/tausik session start
→ Session #1 started.
```

**Create the task with a goal AND acceptance criteria.** QG-0 refuses to
start a task without them, and one criterion must be a negative (error or
boundary) case.

```
tausik_task_quick(title="Demo feature", goal="Show the gate",
  acceptance="AC-1: the feature returns the answer. AC-2: an empty input is refused with an error.")
.tausik/tausik task quick "Demo feature" --goal "Show the gate" --ac "AC-1: … AC-2: an empty input is refused with an error."
→ Task 'demo-feature' created.
```

**Start it.** This is the moment the write gates open for you.

```
tausik_task_start(slug="demo-feature")      .tausik/tausik task start demo-feature
→ Task 'demo-feature' started (attempt #1).
```

If you skipped a criterion, the refusal is exact and names the fix:

```
Error: QG-0 Context Gate: 'demo-feature' cannot start — missing acceptance_criteria. Fix: .tausik/tausik task update demo-feature --goal '...' --acceptance-criteria '...'
Error: QG-0 Start Gate: 'demo-feature' AC has no negative scenario. SENAR requires at least one error/boundary case in acceptance criteria.
```

**Declare what you will touch, then edit.** `relevant_files` is the scope the
gates read; paths are space-separated.

```
tausik_task_update(slug="demo-feature", …)   .tausik/tausik task update demo-feature --relevant-files src/feature.py tests/test_feature.py
```

**Log as you go.** Every meaningful step, and every criterion's evidence —
the closure reads these lines.

```
tausik_task_log(slug, message)      .tausik/tausik task log demo-feature "AC-1: ✓ tests/test_feature.py::test_answer  AC-2: ✓ tests/test_feature.py::test_empty_is_refused (negative: empty input raises)"
```

**Verify.** Heavy gates (linters, the scoped tests) run once, here, and the
green is recorded for the close.

```
tausik_verify(task_slug="demo-feature")       .tausik/tausik verify --task demo-feature
→ [PASS] ruff
  [PASS] pytest  SCOPE: scoped run over 1 of 1 test file(s) mapped from relevant_files …
  Recorded verification_run #8 (task_slug=demo-feature, exit=0).
```

In a project with a signing key the reply ends with a **verify handle** — pass
it to the close. Without a key it says so and gives the close that works:

```
Verify handle: none — no project key, so no signed receipt (`tausik key init` enables them). Close without --verify-handle: `.tausik/tausik task done demo-feature --ac-verified` uses the freshness lookup.
```

**Close.** `--ac-verified` is your statement; the logged evidence is what the
gate checks.

```
tausik_task_done(slug="demo-feature", ac_verified=true, verify_handle="<from verify>")
.tausik/tausik task done demo-feature --ac-verified [--verify-handle <handle>]
→ Task 'demo-feature' completed.
```

Two refusals you will meet if you rush it, both exact:

```
Error: QG-2: 'demo-feature' cannot complete — acceptance criteria not verified. Verify each criterion, then: .tausik/tausik task done demo-feature --ac-verified
Error: QG-2: 'demo-feature' has 2 acceptance criteria but no verification evidence in task notes. Log verification: .tausik/tausik task log demo-feature "AC verified: 1. ✓ 2. ✓ ..."
```

**Hand off and end.** A handoff is what the next session starts from.

```
tausik_session_handoff(handoff={...})    .tausik/tausik session handoff '<json>'
tausik_session_end                        .tausik/tausik session end
→ Session #1 ended.
```

## 3. What the host enforces and what you enforce

Two kinds of rules, two kinds of enforcement — the split is by WHO performs
the action, not by host:

* **Rules our surface holds, everywhere.** QG-0 (no start without goal + AC),
  QG-2 (no close without evidence and a fresh verify), the session limit, the
  memory route. These refuse inside `tausik_*` / the CLI, so they hold on a
  host with no hooks at all.
* **Rules that intercept YOUR action.** Rule 1 (no file write without an
  active task), Rule 2 (no write outside the declared scope), the shell
  firewall, the push gate. These exist only where a hook runs before the
  tool: Claude Code, Qwen Code, Codex (once trusted), and Rule 1 alone on
  OpenCode. On Cursor and Kilo nothing stands between you and the file — you
  are the hook: start the task before the first edit.

Where the hook does run, a write without an active task is refused before the
file changes:

```
BLOCKED: No active task. TAUSIK requires a task before code changes (SENAR Rule 1).
  Create one:   /plan   (or describe the task and ask to start it)
  Resume one:   .tausik/tausik task list --status planning
                .tausik/tausik task start <slug>
```

`docs/en/enforcement-coverage.md` has the rule-by-rule table, and
`.tausik/tausik doctor` prints what is deployed for THIS host.

## 4. Memory: what to write, and where not to

* `tausik_memory_add` / `.tausik/tausik memory add` — a pattern, gotcha or
  convention of THIS project, when you learned something the next agent must
  not relearn.
* `tausik_dead_end` / `.tausik/tausik dead-end "approach" "reason"` — an
  approach that failed and why. Cheaper than the next agent trying it again.
* `tausik_decide` / `.tausik/tausik decide` — a decision with its rationale.
* **Do not write to `~/.claude/`** from a non-Claude host, and do not put
  TAUSIK's own rules there from any host: that directory is a Claude profile,
  not project memory. Project knowledge goes through the tools above.

## 5. If your host has no slash commands

`/start`, `/plan`, `/ship` and the rest are procedures written as Markdown.
When the host does not expand them, open `harness/skills/<name>/SKILL.md`
(deployed under `.claude/skills/`, `.qwen/skills/`, `.codex/skills/`) and run
the numbered steps yourself. The tools they call are the ones in §2.

## See also

* [AGENTS.md](../../AGENTS.md) — the rules and the host matrix
* [quickstart.md](quickstart.md) — the same walkthrough for a person
* [mcp.md](mcp.md) — every `tausik_*` tool and its parameters
* [cli.md](cli.md) — every CLI command
* [enforcement-coverage.md](enforcement-coverage.md) — what is enforced where, by rule
* [model-providers.md](model-providers.md) — host notes, including the Codex trust condition
