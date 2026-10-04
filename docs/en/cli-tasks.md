**English** | [Русский](../ru/cli-tasks.md)

# CLI: tasks and sessions

<!-- doc-map: reader=user; zone=core-surface -->

File, start, drive and close work. Part of the command reference. Start, and the working set, in [cli.md](cli.md).
## Initialization

```bash
--version                      # Print the installed TAUSIK release; needs no project or database
init --name <slug>             # Initialize project (creates .tausik/tausik.db)
init --template aidd [--force] # Scaffold AIDD layers (idea.md/vision.md/conventions.md) into project root.
demo [--keep]                  # Watch TAUSIK catch a false "tests pass" in a throwaway sandbox: no network, no LLM key, your project untouched
                               #   Existing files trigger a 4-option prompt: overwrite / merge-append / skip / abort-all.
                               #   Default (Enter) = skip. `--force` overwrites without prompting.
                               #   Unknown --template values exit non-zero with a stderr error.
aidd autogen [--write] [--force] # Draft a vision.md pre-seeded with repo signals (package name+description,
                               #   README title/intro, top-level source dirs, detected languages, test framework).
                               #   Default prints the draft to stdout (writes nothing); --write persists to vision.md
                               #   reusing the AIDD conflict prompt (--force overwrites). Missing signal → placeholder,
                               #   never crashes. Stdlib-only, no LLM call.
aidd validate                  # Check conventions.md ## Code claims (language/version pin, lint/format tool,
                               #   testing framework, max file-size) against actual repo state. Each claim →
                               #   ok / drift / unverifiable. Exit 1 on hard drift, 2 if conventions.md missing,
                               #   0 otherwise. Blank/unparseable claim → unverifiable, never crashes. Stdlib-only.
status [--compact]             # Project overview + SENAR session duration warning (active vs wall); --compact → one-line JSON
update-check [--now]           # Refresh the status/doctor cache (at most daily unless --now); session start always checks fresh
metrics                        # SENAR metrics: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
metrics target NAME min|max VALUE --basis "..."   # Set a target; refused without --basis (SENAR §9.4(c))
                                # The report prints method, population and period per figure,
                                # "no population" instead of 0% over an empty denominator, and each
                                # target with its basis; a crossing writes one metric_target_crossed event
metrics [--cost]               # With --cost: rollup usage_events by task_slug (same as `metrics cost`)
metrics record-session         # Persist LLM usage (tokens/cost/tool/model) for current or explicit session
metrics log-usage              # Append one manual usage_events row (--task-slug optional; no session_usage_metrics overwrite)
metrics cost [--since ISO] [--until ISO]   # SUM tokens/cost + COUNT rows grouped by task (NULL slug excluded)
metrics answers [--last N] [--json]   # Shape of the agent's final answers: words (median/p90), verdict-first %, list share, filler
metrics calls [--last N]             # Tool calls per closed task by kind (read/edit/run/script/ceremony/other), per complexity
metrics cohorts [--json]             # Natural accepted-task cohorts by TAUSIK version and observed model
metrics compare [selectors] [--json] # Compare two natural version/model/time cohorts
metrics tokens [--host claude|codex|kilo] [--last N] [--rebuild] [--json]
                                                   # Native host usage; Claude keeps the legacy per-tool view
                                # Source: .tausik/token_metrics.jsonl, written by the SessionEnd hook
                                #   scripts/hooks/session_metrics.py, which walks the transcript and
                                #   splits message-level usage across the tool_use blocks in a message.
                                # THE COLUMN THAT MATTERS IS ctx_*: the message's full input context
                                #   (input + cache_creation + cache_read). That is the quantity a
                                #   token-economy claim is about. The in_* column is
                                #   NOT the input: with prompt caching on it is the uncached remainder
                                #   — literally 2 tokens per message on this project — so it is a
                                #   doubled call counter wearing a cost label.
                                # --rebuild re-derives the whole ledger from EVERY transcript of this
                                #   project on disk. Needed because the incremental writer only ever
                                #   sees the transcript of the session that just ended, and its
                                #   coverage can be far narrower than the history that exists.
                                # The COVERAGE line in the report header names the denominator: how
                                #   many of all sessions carry rows, and since when. A value that is
                                #   absent from the data prints as "не измерено", never as 0.
                                # Not to be confused with `metrics cost`, which sums money from
                                #   usage_events in the DB.
                                # See docs/{en,ru}/cost-telemetry.md.
doctor                         # Health check: venv + DB + MCP + skills + drift + stale bytecode
doctor --fix-bytecode          # Purge EXACTLY the .pyc whose co_filename names another directory (after a tree move)
```

## Hierarchy

```bash
epic add <slug> <title> [--description TEXT]
epic update <slug> [--title T] [--description TEXT]   # the group's intent can be edited
epic list [--stale-over N]     # stale = tasks created since the description was last edited; a report, not a gate
epic list
epic done <slug>
epic delete <slug>             # CASCADE: deletes all stories + tasks

story add <epic_slug> <slug> <title> [--description TEXT]
story update <slug> [--title T] [--description TEXT]
story list [--epic E] [--stale-over N]
story list [--epic EPIC_SLUG]
story done <slug>
story delete <slug>            # CASCADE: deletes all tasks
```

## Tasks

```bash
task add <title> [--story STORY_SLUG] [--slug SLUG] [--stack STACK]
                 [--complexity {simple,medium,complex}] [--goal TEXT] [--role ROLE]
                 [--defect-of PARENT_SLUG]
                 [--call-budget N] [--tier {trivial,light,moderate,substantial,deep}]
task quick <title> [--goal TEXT] [--role ROLE] [--stack STACK]
task next [--agent AGENT_ID]    # Next planning task: declared order first, then
                                # score. Names the basis of the choice and how
                                # many tasks were withheld behind predecessors
task depends <slug> --after <slug>    # Declare that a task comes AFTER another
task undepends <slug> --after <slug>  # Withdraw a declared order
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
          [--full] [--top-n N] [--max-lines N]   # >25 rows roll up by status/role; --full = full table
task show <slug>                # Full info: plan, notes, decisions, defect_of, AC
task show <slug> --package      # Bounded deterministic agent context (default 8192 B)
task show <slug> --package --max-bytes 4096
task start <slug> [--package]   # planning -> active; package returns bounded context in this call
                                #   session time and call capacity are advice in the output, not a refusal (1.10, #376)
                                #   --force is retired: the flag is refused with the reason
task obsolete <slug> --reason "..."   # close a task time resolved: kept on record, no QG-2, left out of
                                #   FPSR/DER/cycle/lead/calibration; reason >=10 chars; CLI-only (#390)
task done <slug> --ac-verified [--no-knowledge] [--relevant-files FILE1 FILE2 ...] [--evidence "..."]
                                # QG-2: --ac-verified confirms AC verification (requires evidence in notes
                                #       OR --evidence inline). v1.5 Verify-First Contract: heavy gates
                                #       (pytest, tsc, cargo, ...) NO LONGER fire here — they live on the
                                #       separate `verify` command. task done checks the verify cache for
                                #       a fresh green (10 min TTL, same files_hash) and closes in
                                #       milliseconds. If no verify run exists → blocks with remediation.
                                #       Opt-out: .tausik/config.json → {"task_done":{"auto_verify":true}}
                                #       restores the legacy "heavy gates inline" behavior. NO --force.
                                # --gates-not-applicable (1.9): CLOSE ON A RUN IN WHICH NO GATE
                                #       EXECUTED. SENAR 1.4 §8.6(e): the absence of a negative
                                #       finding is NOT a positive verdict, so `verify
                                #       --no-tests-expected` records the declaration and this flag
                                #       is the SEPARATE, RECORDED act of accepting it. For work that
                                #       honestly maps to no test: documentation, config, an
                                #       investigation. It does NOT rescue a run in which a gate was
                                #       APPLICABLE and still did not execute (COULD_NOT_RUN) — that
                                #       one is fixed, not acknowledged.
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked -> active
task review <slug>              # active -> review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER] [--ticket REF ...]
                                # --ticket (1.9): the external ticket(s) this task answers.
                                #   SPACE-separated, never comma: --ticket github#7 gitlab#12
                                #   Form `<tracker>#<id>` or a full https ticket URL. The tracker
                                #   name is REQUIRED and a bare `#7` is refused at write time:
                                #   this repo has two trackers, and GitHub #7 and GitLab #7 are
                                #   DIFFERENT tickets by different authors. `task add` takes it too.
                                #   Closing the task PRINTS a reminder to answer the author. Nothing
                                #   is sent anywhere and no ticket is closed: the ticket may have
                                #   described more than the task closed.
task delete <slug>
task delegate <slug>            # Orchestrator-worker: mark a complexity<=medium task delegated to a worker sub-agent (records recommended model + parent session; complex refused)
task undelegate <slug>          # Clear a task's delegation
task handoff <slug>             # Print the deterministic worker handoff contract (JSON: goal/AC/scope/model/skills) for the Agent-tool spawn
task summary-back <slug> "<summary>" [--changed F] [--gates S] [--ac-evidence E] [--follow-ups U]  # Worker -> coordinator structured result
task plan <slug> <step1> <step2> ...   # Set plan steps
task step <slug> <step_number>  # Mark step N as completed (1-indexed)
task log <slug> <message>       # Append timestamped note (crash-safe journal)
task logs <slug> [--phase PHASE] # Read structured log entries (planning/implementation/review/testing/done)
task reason-step <slug> <kind> <content>  # RENAR reasoning step (kind: intent|premise|action|verification)
task replay <slug> [--output FILE]  # Chronological timeline: logs + reasoning + events + verification
task move <slug> <new_story>    # Move task to another story
task claim <slug> <agent_id>    # Multi-agent: claim a task
task unclaim <slug>             # Release a task
```

### Work order is an edge, not a number

`task depends B --after A` means: B is not offered until A is `done`. Not
`active`, not `review` -- done. "After" is a statement about COMPLETED work, and
handing out B while A is still being written hands it into an unready world.

An edge rather than a priority integer, because that is the shape the plan
already uses: "this one first", "that one only after it". A number would have to
be re-derived for the whole queue on every insertion, and it would record the
order while losing the reason.

A cycle is refused at declaration and the message prints the whole path --
"cycle detected" tells an author they are wrong without telling them WHICH of
their earlier statements the new one contradicts. Re-declaring the same edge is
not an error: a plan script must converge on re-run, not fail halfway.

`task next` now distinguishes three states that used to collapse into "No
available tasks": the backlog is empty; the backlog exists but every task waits
on an unfinished predecessor; a task is available. The second is a stalled plan,
and reading it as a finished one is the failure this replaced.

The edge TRAVELS in the projection (`depends_on` in the task frontmatter),
because it is intent rather than telemetry: a plan that evaporates on clone is
the defect the mechanism was built against.

**Optional model hints:** When `.tausik/config.json` contains `{"task_next":{"model_hint":true}}`, `task next` and `hud` print an extra non-blocking route from task complexity. The route uses the active model family when it is known (Claude, OpenAI/Codex or GLM); otherwise it falls back to the configured default family. Opt-in only; missing key or `false` preserves previous behavior.

`task delegate` can apply that route only by creating a fresh bounded worker context. Claude Code and Codex expose model selection for a spawned sub-agent; Kilo/GLM remains advisory until its host-side spawn surface is verified. The running coordinator is never reported as switched. A selected route becomes `applied` only when the worker starts the delegated task; an abandoned or failed spawn remains `selected`. Delegation depth is capped at one, and the coordinator retains verification, evidence and closure.

**Allowed stacks (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom stacks are added via `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Budgets >400 are accepted; tier label caps at `deep`.

## Sessions

```bash
session start [--host-id ID]    # Fresh release check, then start; newer TAUSIK refuses, unknown warns; --host-id is idempotent
session end [--summary TEXT] [--host-id ID]  # End the active one; with --host-id exactly that host's session
session current                 # Show active session
session list [--limit N]        # Recent sessions (default: 10); the handoff column shows which carry one
session handoff [json] [--host-id ID]  # Handoff generated from the journal; json = authored next_steps/warnings on top (1.10)
session last-handoff [--session N]  # The live handoff; with --session, session N's (missing session / no handoff are distinct refusals)
session extend [--minutes N]    # Raise the active-time advisory threshold (`session_max_minutes`; advice, not a gate)
session recompute               # Retro: compare wall-clock vs active (gap-based) minutes for past sessions
```

Session time is counted as **active** time (gap-based, paused after 10 min idle), not wall clock; the `session_max_minutes` threshold is advice, not a refusal (1.10). See `session-active-time.md`.
On `session end`, TAUSIK also performs a best-effort usage capture via `scripts/hooks/session_metrics.py --auto --record` (supports both Claude and Cursor transcript roots).
