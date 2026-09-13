**English** | [Русский](../ru/cli.md)

# TAUSIK CLI — Command Reference (v1.5)

All commands are invoked via the wrapper: `.tausik/tausik <command> [subcommand] [arguments]`.
On Windows the wrapper is `.tausik/tausik.cmd`. The same surface is also available via MCP (`tausik_*` tools); see `mcp.md`.

> **Arguments containing `>`, `<`, `&` or `|` on Windows.** The `.cmd` wrapper runs under `cmd.exe`, which parses those characters as operators **before** the batch file starts — even when the caller passed an argument list and never asked for a shell. Measured: of nine hostile arguments, five were corrupted and two were corrupted **silently** — `48->49` arrived as `48-` with exit code 0 while the output was diverted into a stray file named `49`, and `a&b` arrived as `a` with the tail `b` executed as a command. That is how session #200 stored a truncated handoff and reported success.
>
> Such a call now **exits 3** and prints to stderr what was on the command line, what reached the process, and the name of the stray file if `cmd.exe` had already created one. A corrupted value is never stored in silence.
>
> What to do instead: call the POSIX wrapper `.tausik/tausik` from bash (it passes `"$@"` and cannot lose an argument) or use the MCP tools — neither goes through a shell. If the redirection was **deliberate** (a script writing `cmd /c "tausik.cmd status > out.txt"`, say), set `TAUSIK_CMDLINE_GUARD=off`.
>
> Redirection typed by hand in an interactive console (`tausik status > out.txt`) is left alone: there `%CMDCMDLINE%` holds only the shell's own startup line and names no arguments.

## Initialization

```bash
init --name <slug>             # Initialize project (creates .tausik/tausik.db)
init --template aidd [--force] # Scaffold AIDD layers (idea.md/vision.md/conventions.md) into project root.
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
metrics                        # SENAR metrics: Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task
metrics [--cost]               # With --cost: rollup usage_events by task_slug (same as `metrics cost`)
metrics record-session         # Persist LLM usage (tokens/cost/tool/model) for current or explicit session
metrics log-usage              # Append one manual usage_events row (--task-slug optional; no session_usage_metrics overwrite)
metrics cost [--since ISO] [--until ISO]   # SUM tokens/cost + COUNT rows grouped by task (NULL slug excluded)
metrics tokens [--last N] [--rebuild] [--json]   # Context volume per tool over the last N sessions
                                # Source: .tausik/token_metrics.jsonl, written by the SessionEnd hook
                                #   scripts/hooks/session_metrics.py, which walks the transcript and
                                #   splits message-level usage across the tool_use blocks in a message.
                                # THE COLUMN THAT MATTERS IS ctx_*: the message's full input context
                                #   (input + cache_creation + cache_read). That is the quantity a
                                #   token-economy claim is about (decision #338). The in_* column is
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
task start <slug> [--force]     # planning -> active (QG-0: requires goal + AC + negative scenario)
                                # --force bypasses session capacity gate (audit event + note)
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

**Optional Claude model hints:** When `.tausik/config.json` contains `{"task_next":{"model_hint":true}}`, `task next` and `hud` print an extra non-blocking line recommending a Claude model from task complexity (same mapping as `suggest-model`). Opt-in only; missing key or `false` preserves previous behavior.

**Allowed stacks (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom stacks are added via `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Budgets >400 are accepted; tier label caps at `deep`.

## Verification

**v1.5 Verify-First Contract.** Heavy gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeconform, hadolint, ansible-lint) live on the `verify` trigger, not `task-done`. This decouples "task closure" (milliseconds) from "full verification" (potentially minutes on large projects). The `verify` result is cached in the `verification_runs` table for 10 minutes (TTL is configurable via `verify_cache_ttl_seconds` in config.json), and `task done` uses the cache for instant closure.

```bash
verify [--task SLUG] [--relevant-files PATH ...]
       [--scope {lightweight,standard,high,critical,manual}]
       [--no-tests-expected]
                                # Run scoped verify-trigger gates ad-hoc; records into verify cache.
                                # With --task: gates scoped to the task's relevant_files.
                                # Without --task: gates with empty file scope (full suite for pytest).
                                # Cache hit (same files_hash, < 10 min) skips the run.
                                # Security-sensitive files (auth/payment/hooks) bypass the cache.
```

**`--relevant-files`.** Declares the task's scope AND verifies it in one step.
Requires `--task`: the scope is a property of a task, and there is nowhere else
to record it. The paths are PERSISTED to the task, so `task done` reads the same
scope and hits the cache — one source of truth, the task row.

Without a declared scope every scoped gate is `[SKIP]` and the receipt is still
signed: it certifies emptiness. Before this flag the only working move
(`task update <slug> --relevant-files ...`) was named in no message at all,
while the warning offered a flag `verify` did not have — which made ignoring the
warning the RATIONAL response rather than a careless one.

**The paths are SPACE-separated** — `--relevant-files a.py b.py`, on `verify`,
`task update` and `task done` alike; the list is stored as JSON, which is the
storage shape, not the input format. A value like `"a.py,b.py"` is ONE argument
to argparse and used to be stored as one path, so scoped gates ran over nothing
and the refusal came from `verify` worded as "no tests mapped" (GitLab #13).
Since 1.9 an element that carries a comma and resolves to no file is refused at
the write, naming the right form; a path with a comma in its name that exists
is accepted as it is, and a declared path that does not exist yet is accepted
with a note — the task may be about to create it.

**`--no-tests-expected`.** A run in which no gate actually executed (everything
`[SKIP]`) blocks: it proves nothing, and a green recorded against it would stay
valid for the whole TTL across arbitrary tree changes. For documentation,
config and migrations that is a dead end — no test maps to those files and none
ever will. The flag declares this EXPLICITLY: the run is recorded green under
`no_tests_declared = 1`.

The flag buys visibility, not permission. The closure still happens with no gate
executed; what changes is that such closures are now countable with one query
instead of being indistinguishable from verified ones:

```sql
SELECT task_slug, ran_at FROM verification_runs WHERE no_tests_declared = 1;
```

It applies only to SKIPPED gates. A failing gate stays red and `verify` still
exits 1.

**Verify-first workflow:**

```bash
.tausik/tausik task start my-task                    # QG-0
# … work on code …
.tausik/tausik verify --task my-task                 # heavy: pytest etc.
.tausik/tausik task done my-task --ac-verified       # lightweight: cache lookup
```

**Legacy opt-out (CI/inline behavior):** add to `.tausik/config.json`:

```json
{ "task_done": { "auto_verify": true } }
```

Now `task done` runs the verify gates inline within its transaction — the v1.3 behavior. Useful for CI where a single long step is preferable to two.

**Pytest fast lane (v1.5.x).** The default pytest configuration (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts = "-m 'not slow'"`) skips tests marked `@pytest.mark.slow` (subprocess-heavy bootstrap, MCP integration, e2e, stress). This drops a clean `tausik verify` run from ~12 minutes to ~1.5 minutes on the TAUSIK repo. Three escape hatches when you need the full battery:

```bash
# 1. Direct pytest, override the addopts
pytest --override-ini='addopts=' tests/

# 2. Marker-only filter (overrides the inherited -m 'not slow')
pytest -m '' tests/                        # all tests
pytest -m 'slow' tests/                    # only slow tests (CI nightly)

# 3. Through the verify gate — set the env var before invoking tausik
TAUSIK_VERIFY_FULL=1 .tausik/tausik verify --task my-task
```

To mark a new test slow: file-level `pytestmark = pytest.mark.slow` (preferred for whole files) or per-test `@pytest.mark.slow`. Reach for it when a test spawns subprocesses, hits the network/MCP, or sleeps > 200 ms — anything that breaks the < 60 s interactive verify budget.

**Terminology:** [Verify / QG glossary](verify-glossary.md) — opt-out vs bypass vs test shim.

## Quality Gates

```bash
gates status                    # Show all quality gates and their configuration
gates list                      # List gates with enabled/disabled status
gates enable <name>             # Enable gate
gates disable <name>            # Disable gate
```

The `test_dedupe` gate (block, on task-done and commit) reddens on GROWTH in
structurally indistinguishable tests. The baseline is a ratchet in the committed
`tausik/gates.json`, so existing debt blocks nobody. The subject is
DISTINGUISHABILITY, not count: the gate never measures how many tests exist, so
deleting tests can never satisfy it. Full per-group report:

```bash
python scripts/audit_pytest_dedupe.py            # markdown report by group
python scripts/audit_pytest_dedupe.py --json     # the same, machine-readable
```

## RENAR drift detectors (§4.11)

RENAR §4.11 defines 8 drift classes. 2 are implemented (audit recommendation R4),
both in **warning mode** — findings never block; the agent reads the listing and
reacts.

```bash
drift                          # Run every implemented detector
drift --detector schema        # drift-1 only (artifact schema)
drift --detector provenance    # drift-7 only (TC↔requirement provenance)
drift --detector supersession  # ADR-007: a delta-ADAPT on a superseded parent
drift --detector standard      # THE STANDARD moving (corpus vs our declarations)
```

- **drift-1 (schema)** — re-validates SPEC/ADAPT against the closed lists +
  cross-field invariants a DB CHECK cannot express: `delta_n ↔ parent_adapt`
  (delta_n>0 without a parent_adapt / delta_n=0 with a parent_adapt),
  `approved ↔ architect signature` (§7.5 — the client signature was withdrawn
  by ADR-011; surviving records are NAMED as `signature-role-withdrawn`, never
  erased),
  blank version. Catches direct-DB tampering and migration gaps.
- **drift-7 (TC↔requirement provenance)** — TAUSIK has no first-class TC; the
  verification unit is a task (its acceptance_criteria == the "TC") linked to a
  SPEC (the requirement) via `task_specs`. Two signals: `stale-verification`
  (done task whose SPEC was edited after the link → verification predates the
  current requirement version) and `deprecated-requirement` (in-flight task
  linked to a deprecated SPEC).

- **standard (the corpus moved)** — the only detector that compares OUR
  DECLARATIONS WITH THE STANDARD ITSELF rather than the database with our
  declarations: the closed lists (SPEC types §8.3, finding categories §7.4.4,
  ADAPT statuses §7.8.1), the corpus edition, and accepted ADRs this repository
  never mentions. The source is a local checkout named by
  `renar_standard_corpus` in `.tausik/config.json`; without it the command
  prints "standard corpus: NOT CHECKED" and does NOT report "no drift".
  Proposed ADRs are never findings.

Also wired as gates `renar_drift_schema` / `renar_drift_provenance`
(severity=warn, trigger=task-done). `standard` is not wired as a gate: not every
machine carries the corpus. The other 5 classes are out of scope.

## RENAR conformance (§13.4)

```bash
renar conformance              # Generate RENAR-CONFORMANCE.yaml (to stdout)
renar conformance --write      # Write RENAR-CONFORMANCE.yaml at the project root
renar conformance --assessor <id>
renar export [--out DIR] [--check]  # Serialize specs+adapts+conformance to a derived renar/ tree; --check is a CI drift gate (exit 1 if stale)
```

A self-assessment manifest with every §13.4.2 mandatory field. The RENAR-1..5
level is **computed honestly from live DB state** (§13.4.3), never declared: any
unmet mandatory clause → `pre_adoption: true` + `level: null` (the kai pattern,
the adoption audit). The `assessment-evidence` section reports raw counts + per-signal
met/unmet and exactly where the level is blocked, so an agent sees what is missing
to reach the next level. Machinery clauses (closed lists, V1–V6, QG-0/QG-2,
schema-validation hook = our drift-1) are confirmed by capability; data clauses
(`adapt-per-tz`) only when artifacts exist.

## State in git (state / sync)

Projection of durable DB state (`.tausik/tausik.db`) into a git-native `tausik/`
tree — one deterministic .md file per entity (tasks, task_logs, epics, stories,
decisions, memory, memory edges). The DB is the working cache; the `tausik/` tree
is the canonical, branch-coupled source of truth. Round-trip: `export` (DB → files),
`import` (files → DB, git wins on divergence). `sync` is a short alias for
`state import`, the command you run after `git pull` / `git checkout`.

```bash
state export [--out DIR] [--check]   # Serialize DB → tausik/ tree (one file per entity).
                                     # --check: exit 1 if the tree is stale vs live DB (CI gate,
                                     # same contract as renar export --check).
state import [--out DIR] [--dry-run] # Rebuild the DB cache from the tausik/ tree (idempotent delta).
                                     # --dry-run: show the add/update/journal/edge plan without writing.
sync [--out DIR] [--dry-run]         # Alias for `state import`. Run after git pull/checkout.
```

Example: `.tausik/tausik state export` before committing a branch; `.tausik/tausik sync`
right after `git pull` so the local DB cache catches up to the tree. Round-trip
automation (export on durable write, divergence detection on session start) is gated
by the `state.auto_export` config key.

## Stacks

```bash
stack info <stack>              # Show resolved stack: gates per language + user override info
stack list                      # List built-in + custom stacks
stack export <stack>            # Print resolved stack declaration as JSON
stack diff <stack>              # Diff between built-in and user override
stack reset <stack>             # Remove user override at .tausik/stacks/<stack>/
stack lint                      # Validate user-override stack.json files against schema
stack scaffold <name>           # Create .tausik/stacks/<name>/{stack.json,guide.md} skeleton
```

## Roles

```bash
role list
role show <slug>
role create <slug> <title> [--description TEXT] [--extends BASE_ROLE]
role update <slug> [--title T] [--description D]
role delete <slug>
role seed                       # Bootstrap role rows from harness/roles/*.md and existing task usage
```

Role storage is hybrid: SQLite metadata + `harness/roles/{role}.md` profile markdown. Roles remain free-text on tasks (`--role developer/architect/qa/...`).

## Sessions

```bash
session start                   # Start new session (returns ID)
session end [--summary TEXT]    # End active session
session current                 # Show active session
session list [--limit N]        # Recent sessions (default: 10)
session handoff <json_data>     # Save handoff JSON for next session
session last-handoff            # Get handoff from last session
session extend [--minutes N]    # Extend session beyond 180-min active limit (SENAR Rule 9.2)
session recompute               # Retro: compare wall-clock vs active (gap-based) minutes for past sessions
```

Session limit is 180 min **active** time (gap-based, paused after 10 min idle). Threshold is configurable via `.tausik/config.json` → `session_idle_threshold_minutes`. See `session-active-time.md`.
On `session end`, TAUSIK also performs a best-effort usage capture via `scripts/hooks/session_metrics.py --auto --record` (supports both Claude and Cursor transcript roots).

## Knowledge

```bash
decide <text> [--task SLUG] [--rationale TEXT] [--global]   # --global: the shared store ~/.tausik-knowledge, no project row
decisions [--limit N]           # List decisions (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG] [--global]
memory list [--type TYPE] [--limit N]
memory search <query>           # FTS5 full-text search
memory show <id>
memory delete <id>

# Graph memory (Graphiti-inspired)
memory link <source_type> <source_id> <target_type> <target_id> <relation>
            [--confidence 0.0-1.0] [--created-by AGENT]
memory unlink <edge_id> [--replacement EDGE_ID]   # Soft-invalidate (never deletes)
memory related <node_type> <node_id> [--hops N] [--include-invalid]
memory graph [--type {memory,decision}] [--id N]
             [--relation {supersedes,caused_by,relates_to,contradicts}]
             [--include-invalid] [--limit N] [--format {table,mermaid}]
             # --format mermaid: emit the graph in Mermaid notation (for doc rendering); default table

# Aggregators
memory block [--max-decisions N] [--max-conventions N] [--max-deadends N] [--max-lines N]
memory compact [--last N]

# Hygiene (v1.5)
memory archive --before <duration> [--confirm]    # Soft-archive memory older than duration
                                                   # (90d / 12w / 2m / 1y). Dry-run by default;
                                                   # --confirm stamps archived_at, idempotent.
memory dedupe [--threshold 0.85] [--limit 200]     # List near-duplicate pairs above similarity
                                                   # threshold (difflib.SequenceMatcher.ratio()
                                                   # over title || content). Read-only.
```

**Memory types:** pattern, gotcha, convention, context, dead_end
**Graph node types:** memory, decision
**Relation types:** supersedes, caused_by, relates_to, contradicts

## Dead End Documentation (SENAR Rule 9.4)

```bash
dead-end <approach> <reason> [--task SLUG] [--tags T1 T2 ...]
# Documents a failed approach with reason. Saved as memory type dead_end.
```

## Exploration (SENAR Section 5.1)

```bash
explore start <title> [--time-limit MINUTES]    # Start investigation (default: 30 min)
explore end [--summary TEXT] [--create-task]    # End (--create-task creates a task from findings)
explore current                                 # Show active exploration with elapsed time
```

## Periodic Audit (SENAR Rule 9.5)

```bash
audit check                     # Show whether periodic audit is overdue
audit mark                      # Mark audit as completed
audit vendors [--json]          # Audit cloned vendor skill repos (read-only): classifies each as
                                # 'installed' (in installed_skills config) or 'vendored_unused'
                                # (candidate for `skill repo remove`). Never deletes.
audit research [--min-age-days N] [--json]
                                # Audit docs/{en,ru}/research/ for stale unreferenced files
                                # (default >30 days, no refs in tests/scripts/CHANGELOG/README).
                                # Read-only — surfaces candidates for docs/_archive/research/.
audit evidence [--json] [--no-git]
                                # Do the test citations in closed tasks still resolve?
                                # Read-only and NEVER blocking: renaming a test is legitimate,
                                # the point is that the decay becomes VISIBLE.
```

`audit evidence` has four buckets, deliberately not merged into one "broken" number:

| bucket | meaning |
|---|---|
| `ROTTED` | the target WAS in git history and is gone — renamed or deleted after closure. The reference decayed; the coverage may be intact. |
| `NEVER_EXISTED` | the target was never in history — a citation invented at closure time. |
| `ILLUSTRATIVE` | an EXAMPLE, not a citation: `tests/foo.py`, `tests/test_does_not_exist.py`, `tests/../scripts/prod.py`. Such names are quoted by tasks whose SUBJECT is the citation format itself. |
| `UNKNOWN_HISTORY` | git refused to answer — the verdict is withheld, not guessed. Appears under `--no-git`. |

`ILLUSTRATIVE` was split off in session #209 on a measurement: of the 25 refs then in `NEVER_EXISTED`, 13 were examples and 3 were genuine, so the headline over-reported real rot by a factor of two beside 22 `ROTTED` entries a reader was being taught to skim. Examples are **counted separately, not dropped**: a number that silently loses entries is the next version of the same problem, and the rule that fired is printed next to each entry. The notion of an example path is shared with the `stale_file` detector of `memory lint` (`scripts/illustrative_paths.py`) — a second copy of the placeholder list is exactly how the two detectors drifted apart.

## Reviews (SENAR Rule 10.15) — v1.5

Track L1/L2/L3 review runs and surface the **ADR** (Adversarial Defect Rate) metric.

```bash
review record --task <slug> --type {L1|L2|L3} \
              [--critical N] [--warnings N] [--notes "..."]
review list   [--task <slug>] [--type {L1|L2|L3}] [--limit N] [--json]
review metrics                  # ADR = critical_findings / L3_reviewed_tasks * 100
```

The `/review` skill calls `review record --type L3` automatically (it spawns 6 adversarial reviewer subagents in a separate context). `tausik metrics` includes an `Adversarial Review` block once any L3 reviews exist.

## Multi-agent

```bash
team                            # Tasks grouped by agents (claimed_by)
```

## Skills

```bash
skill list                      # List skills: active, vendored, available from configured repos
skill install <name>            # Install a skill from a configured repo (clone + copy + activate)
skill uninstall <name>          # Uninstall a skill (deactivate + drop from config)
skill activate <name>           # Activate a vendored skill (copy from vendor/ to .claude/skills/)
skill deactivate <name>         # Deactivate an active skill (remove from .claude/skills/)
skill repo add <url> [--force]  # Add TAUSIK skill repo; --force required for URLs other than github.com/Kibertum/tausik-skills
skill repo remove <name>        # Remove a configured skill repo
skill repo list                 # List configured repos and their skills
skill catalog [<repo>] [--json] # Discovery: name/category/repo/description across cloned repos

# Profile + bundle helpers (v1.5)
skill rebuild [--force]         # Re-merge SKILL.md variants for the active (ide, model) profile;
                                # idempotent (sha256 cache skips unchanged files).
skill bundle list               # List the 6 logical bundles defined in skills-official/bundles.json
                                # (integrations, data-formats, quality-pro, automation, workflow-helpers,
                                # ru-locale) + their skill counts.
skill bundle show <name>        # Show one bundle's contents (skill names + descriptions).
skill bundle install <name>     # Install every skill in the bundle (per-skill error continues).
skill bundle uninstall <name>   # Uninstall every skill in the bundle.
```

Negative scenarios (unknown skill, untrusted repo URL, missing skill) print
a friendly `Error: ...` line on stderr and exit `1`. They never produce
a Python traceback (v1.5: `SkillManagerError` is caught alongside
`ServiceError` in `main()`).

## Search and Navigation

```bash
roadmap [--include-done]        # Full tree epic -> story -> task
search <query> [--scope {all,tasks,memory,decisions}]
```

## Hygiene (v1.5)

Project-hygiene helpers. The default `archive` call lists candidates; `--confirm`
stamps `archived_at` on matching rows (idempotent — re-running is safe). Archived
rows stay queryable (`task_show`, FTS, metrics see them) and `task list` filters
them out unless `--include-archived` is passed.

```bash
hygiene archive                 # Dry-run: list done tasks older than task_archive.done_age_days
                                # (no-op when task_archive.enabled is false / missing).
                                # Active / blocked / planning / review tasks are
                                # NEVER included regardless of config.
hygiene archive --confirm       # Write: stamps archived_at (UTC ISO8601) on each candidate.
                                # Does NOT bypass task_archive.enabled=false.
```

Spec: `docs/en/task-archive-spec.md`. Exclusion rules and developer-side
audit scripts (orphan files, stale docs, unused Python, pytest dedupe)
are documented in `docs/en/dev-doc-checks.md`.

## Batch Execution

```bash
run <plan-file.md>              # Parse and display batch-run plan summary
```

Plans are markdown files with numbered tasks, goals, and file lists. Use `/run plan.md` in an interactive session to execute autonomously.

## Document Extraction

```bash
doc extract <path>              # Convert DOCX/PPTX/XLSX/HTML/EPUB/PDF to markdown via markitdown
```

Opt-in: requires `markitdown` and Python ≥3.11. See `docs/en/markitdown-integration.md`.

## A bypassed gate leaves a record (SENAR 1.4 §8.6(j))

Editing a task's artifact by a route no gate stands in front of — INCLUDING a
direct edit by the supervisor — admits the effect QG-0 declared without a
positive verdict; §8.6(h) counts that as a bypass regardless of intent. This is
NOT a prohibition but a regulated exception: the legitimate cases the standard
names stay open — an incident while agent capacity is unavailable, an
environment where the agent does not run. What is required is a RECORD.

```bash
events emit-supervision --vector direct_edit --task <slug> \
    --rationale "incident, agent capacity unavailable" \
    --risk-accepted "the fix ships without a scoped verify" \
    --remediation "re-run verify and re-close the task" \
    --approved-by "owner"
```

A record with no `--rationale` is REFUSED (exit 2): a bypass without a reason is
the form filled in without looking. What is refused is the RECORD, never the
edit — the edit has already happened.

WHY THE METRIC IS COMPUTED FROM RECORDS AND NOT FROM SELF-REPORT (§9.2, §9.3): a
self-reported figure is a CLAIM, not a measurement; it satisfies neither §8.6(c)
nor §8.6(d), and the standard cannot demand of gates what it does not demand of
its own measure of compliance.

THE TWO FREQUENCIES ARE NESTED AND SHALL NOT BE ADDED (§8.6(i)): manual
interventions are a SUBSET of bypasses, so `metrics` prints them as "of which"
rather than as a second total. Summed, they double-count, and the threshold
fires on a team doing nothing wrong.

## Generated Documents

```bash
doc constants [--check]         # docs/_generated/constants.json from pyproject + MCP counts
doc roadmap [--check]           # ROADMAP.md from the live DB; --check exits 1 when stale
```

`doc roadmap` reissues the release roadmap at the project root. The release
composition comes from the owner's decisions (the newest decision naming the
release stories), the counters from the live DB — nothing in the file is typed
by hand. Closing a task moves those counters, so the reissue belongs **after
`task done` and before the commit**; otherwise `tests/test_release_roadmap.py`
goes red and names this same command.

## Events (Audit Log)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
       [--full] [--top-n N] [--max-lines N]
```

Above 25 rows the output rolls up by entity-type and action (a compact,
deterministic aggregate) instead of dumping every event; `--top-n` / `--max-lines`
cap the group lines and a footer names how many are hidden. `--full` prints the
per-event dump unchanged. `task list` takes the same three flags (rolls up by
status and role).

## Snippets / clone detection (v15-snippet)

```bash
snippet detect [--path X] [--threshold N]  # AST clone detection: normalizes
                                           #   identifiers/literals to placeholders,
                                           #   hashes def/class subtrees, clusters
                                           #   >=2 matches and writes them to the
                                           #   snippets table (taxonomy_kind='clone').
                                           #   --threshold = minimum candidate line
                                           #   count (default 10).
                                           #   Idempotent (deduped by hash).
```

## Redacting from memory (v1.9, decision #258)

The task journal is append-only, memory has no `update`, decisions have only
`list`. That is deliberate: a record that can be quietly rewritten stops being
evidence. But irrevocability must have a paired mechanism, or the first line
recorded in error becomes permanent.

`redact` is that mechanism. It is an **overwrite that leaves a trace**, not a
deletion.

```bash
# Dry run — THE DEFAULT. Writes nothing, shows what it would touch.
tausik redact --pattern "internal.example.com" --label internal-host \
              --reason "a private host address does not travel to a public repo"

# Apply. IRREVERSIBLE.
tausik redact --pattern "internal.example.com" --label internal-host \
              --reason "..." --apply

# By regular expression instead of a literal
tausik redact --regex --pattern "alpha|beta|gamma" --label third-party-project --reason "..."

# What has been redacted in this project
tausik redact list --limit 50
```

**A bad regular expression is refused in words, not in a traceback.** `--regex`
with an unparseable pattern gives a named refusal with exit code 1: the command
names the pattern AS TYPED and quotes `re`'s explanation together with the error
position. The pattern is printed without repr quotes on purpose — `re` reports
the fault BY POSITION, and repr doubles backslashes and would shift every index.
The refusal happens BEFORE any read or write, and it is distinguishable from the
neighbouring "zero matches" outcome: an unparseable pattern and an empty result
are different answers with different remedies.

**What happens to the text.** A match is replaced by the visible marker
`[redacted: <label>]`. The reader must see that something stood here: a silently
shortened sentence is indistinguishable from one that always read that way.

**What happens to the trace.** Every touched column gets a row in the
`redactions` table: the entity, the field, the CLASS of what was redacted, the
reason, the number of replacements, the time. The trace is neither deleted nor
edited — it is the only reason an irrevocable journal can still be trusted once
rewriting became possible.

**`--label` names the class, not the value.** A trace quoting the secret would
put the leak back into the database, in a column nobody would think to scan.

**Scope.** Prose columns only, declared in one place —
`scripts/redact_scope.py`. Structural columns (`slug`, `status`, timestamps,
foreign keys) are excluded: those are addresses, not text, and rewriting an
address breaks the rows that reference it while removing nothing a human wrote.

**There is no restore.** The original text is stored nowhere — not in the trace,
not in a shadow copy. The only way back is a backup of `.tausik/tausik.db` taken
BEFOREHAND; the dry run says so before anything is written.

**After applying, run `tausik state export`** — the projection is generated from
the database, and until it is rebuilt the tree still shows the old text.

**Zero matches is its own outcome, not a success.** The command says "no match"
in its own words: a caller convinced there is a leak must learn that the pattern
was wrong, rather than receive a clean exit indistinguishable from real work.

## Maintenance

```bash
update-claudemd [--claudemd PATH] [--dry-run]  # Update <!-- DYNAMIC --> section in CLAUDE.md AND its AGENTS.md sibling (v1.5: --dry-run prints diff and exits 1 if drift). A file without the marker is skipped with a notice.
fts optimize                          # Optimize FTS5 indexes
hud                                   # Live one-screen dashboard: task + session + gates + logs
suggest-model [complexity]            # Recommend Claude model: simple→Haiku, medium→Sonnet, complex→Opus
```

## Commands not covered by the sections above

This section exists because of a measurement (session #235): of the 53 commands
the parser declares, fourteen were named nowhere in this file, so an agent had
no way to learn they existed. Alphabetical within groups; `--help` carries the
detail for each.

```bash
# --- the RENAR contract line ---
actz create|point|sign|verify|show|list|delta|link|unlink|delete|search
actz decided-in|decided-in-remove|final-tz|orphans   # ACTZ acts and the final TZ
adapt create|interpret|finding|sign|verify|show|list|delta|link|unlink|delete|search
                                                    # adapting a norm to this project
spec list|show|add|update|delete|link|unlink|search  # requirements and their links
at create|show|list|delete|search                    # acceptance tests
at check-freshness|record-result|diagnose|release-readiness

# --- evidence and signatures ---
key init                       # create the project keypair under .tausik/keys/
key show                       # print the public key fingerprint
receipt show                   # print AND re-verify the latest signed receipt
receipt export|verify          # export a receipt, or check one on its own

# --- code navigation (see graph.md and symbol-index.md) ---
graph build                    # fill the artifact graph: index plus both edge layers
graph show <path>              # what relates to a file, and on what evidence
graph status                   # how much is stored, what is stale, which roots
symbol <name>                  # a definition, its file:line and its callers
coherence [--json]             # collect the tree's coherence material for a judge

# --- tree and store maintenance ---
knowledge export|restore|import-brain   # the shared knowledge store to a file and back
knowledge export --to <dir> --redacted  # a copy meant to travel: paths, e-mails, private URLs, project names -> placeholders
db prune                       # delete the oldest .tausik/tausik.db.bak.* files
config show                    # the resolved configuration, with the tier each value came from
config set <key> <value>       # persist an override into .tausik/config.json
redact --pattern <pattern>     # scrub a secret from the knowledge history (--apply: not a dry run)
redact list                    # show the redactions already applied

# --- release and network ---
publish snapshot --from <ref> --parent <sha> [--dry-run]   # the public snapshot: the filtered tree on top of the public head (decision #368)
publish verify --snapshot <sha> --from <ref>               # snapshot == the filtered tree of the source, byte for byte
push-ok [--ttl N]              # issue a git-push ticket (60 seconds by default)
serve [--host H] [--port P]    # run the local receipt-verification endpoint
```

> `serve` binds `127.0.0.1` by default. Exposing it needs `--yes-expose` — a
> separate, explicit consent rather than a flag anyone sets by habit.
>
> The endpoint does NOT share its port. On Windows the `SO_REUSEADDR` that
> `http.server` enables by default permits binding an address already in
> ACTIVE use, and before 1.9 two servers really did bind one port with both
> calls succeeding. The second is now refused: an endpoint whose port can be
> silently shared is not one whose answers about receipts can be relied on.
> On POSIX the flag stays, where it only means rebinding a `TIME_WAIT` port.

## Constants

| Concept | Values |
|---------|--------|
| Task statuses | `planning -> active -> blocked <-> active -> review -> done` |
| Slug format | `^[a-z0-9][a-z0-9-]*$` (max 64 characters) |
| Complexity → SP | simple=1, medium=3, complex=8 |
| Tiers (call calls) | trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400 |
| Memory types | pattern, gotcha, convention, context, dead_end |
| Roles | Free text (no enum); registry under `harness/roles/{slug}.md` |
| SENAR gates | QG-0 (Context Gate on `task start`), QG-2 (Implementation Gate on `task done`) |
| Session limit | 180 min **active** by default (configurable: `session_max_minutes`, idle threshold: `session_idle_threshold_minutes`) |
