**English** | [Русский](/ru/docs/cli)

# TAUSIK CLI — Command Reference (v1.5)

All commands are invoked via the wrapper: `.tausik/tausik <command> [subcommand] [arguments]`.
On Windows the wrapper is `.tausik/tausik.cmd`. The same surface is also available via MCP (`tausik_*` tools); see `mcp.md`.

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
metrics tokens [--since ISO] [--until ISO] [--task SLUG]    # Token rollup per task (sum input/output/cache tokens)
                                # Source: PostToolUse hook scripts/hooks/posttool_usage.py writes one
                                #   usage_events row per tool call (source='posttool', tool_name=<tool>)
                                #   attributed to the currently active task.
                                # Pricing: scripts/cost_pricing.py — single source of truth.
                                # See docs/{en,ru}/cost-telemetry.md.
doctor                         # Health check: venv + DB + MCP + skills + drift
```

## Hierarchy

```bash
epic add <slug> <title> [--description TEXT]
epic list
epic done <slug>
epic delete <slug>             # CASCADE: deletes all stories + tasks

story add <epic_slug> <slug> <title> [--description TEXT]
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
task next [--agent AGENT_ID]    # Pick next planning task (by score)
task list [--status STATUS] [--story STORY] [--epic EPIC] [--role ROLE] [--stack STACK] [--limit N]
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
task block <slug> [--reason TEXT]
task unblock <slug>             # blocked -> active
task review <slug>              # active -> review
task update <slug> [--title T] [--goal G] [--notes N] [--acceptance-criteria AC]
                  [--scope S] [--scope-exclude S] [--stack S] [--complexity C] [--role ROLE]
                  [--call-budget N] [--tier TIER]
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

**Optional Claude model hints:** When `.tausik/config.json` contains `{"task_next":{"model_hint":true}}`, `task next` and `hud` print an extra non-blocking line recommending a Claude model from task complexity (same mapping as `suggest-model`). Opt-in only; missing key or `false` preserves previous behavior.

**Allowed stacks (DEFAULT_STACKS, 25):** python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker. Custom stacks are added via `.tausik/config.json` → `custom_stacks`.

**Tier ↔ call_budget map:** trivial ≤10, light ≤25, moderate ≤60, substantial ≤150, deep ≤400. Budgets >400 are accepted; tier label caps at `deep`.

## Verification

**v1.5 Verify-First Contract.** Heavy gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint) live on the `verify` trigger, not `task-done`. This decouples "task closure" (milliseconds) from "full verification" (potentially minutes on large projects). The `verify` result is cached in the `verification_runs` table for 10 minutes (TTL is configurable via `verify_cache_ttl_seconds` in config.json), and `task done` uses the cache for instant closure.

```bash
verify [--task SLUG] [--scope {lightweight,standard,high,critical,manual}]
                                # Run scoped verify-trigger gates ad-hoc; records into verify cache.
                                # With --task: gates scoped to the task's relevant_files.
                                # Without --task: gates with empty file scope (full suite for pytest).
                                # Cache hit (same files_hash, < 10 min) skips the run.
                                # Security-sensitive files (auth/payment/hooks) bypass the cache.
```

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

## RENAR drift detectors (§3.11)

RENAR §3.11 defines 8 drift classes. 2 are implemented (audit recommendation R4),
both in **warning mode** — findings never block; the agent reads the listing and
reacts.

```bash
drift                          # Run every implemented detector
drift --detector schema        # drift-1 only (artifact schema)
drift --detector provenance    # drift-7 only (TC↔requirement provenance)
```

- **drift-1 (schema)** — re-validates SPEC/ADAPT against the closed lists +
  cross-field invariants a DB CHECK cannot express: `delta_n ↔ parent_adapt`
  (delta_n>0 without a parent_adapt / delta_n=0 with a parent_adapt),
  `signed ↔ dual signature` (§7.5),
  blank version. Catches direct-DB tampering and migration gaps.
- **drift-7 (TC↔requirement provenance)** — TAUSIK has no first-class TC; the
  verification unit is a task (its acceptance_criteria == the "TC") linked to a
  SPEC (the requirement) via `task_specs`. Two signals: `stale-verification`
  (done task whose SPEC was edited after the link → verification predates the
  current requirement version) and `deprecated-requirement` (in-flight task
  linked to a deprecated SPEC).

Also wired as gates `renar_drift_schema` / `renar_drift_provenance`
(severity=warn, trigger=task-done). The other 6 classes are out of scope.

## RENAR conformance (§14.4)

```bash
renar conformance              # Generate RENAR-CONFORMANCE.yaml (to stdout)
renar conformance --write      # Write RENAR-CONFORMANCE.yaml at the project root
renar conformance --assessor <id>
renar export [--out DIR] [--check]  # Serialize specs+adapts+conformance to a derived renar/ tree; --check is a CI drift gate (exit 1 if stale)
```

A self-assessment manifest with every §14.4.2 mandatory field. The RENAR-1..5
level is **computed honestly from live DB state** (§14.4.3), never declared: any
unmet mandatory clause → `pre_adoption: true` + `level: null` (the kai pattern,
audit §0.2.3). The `assessment-evidence` section reports raw counts + per-signal
met/unmet and exactly where the level is blocked, so an agent sees what is missing
to reach the next level. Machinery clauses (closed lists, V1–V6, QG-0/QG-2,
schema-validation hook = our drift-1) are confirmed by capability; data clauses
(`adapt-per-tz`) only when artifacts exist.

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
decide <text> [--task SLUG] [--rationale TEXT]
decisions [--limit N]           # List decisions (default: 20)

memory add <type> <title> <content> [--tags T1 T2 ...] [--task SLUG]
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
             [--include-invalid] [--limit N]

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
```

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

## Shared Brain (cross-project)

```bash
brain init                      # Initialize brain: 4 Notion DBs + config
brain status                    # Mirror freshness, sync state, registered projects (v1.5: also `stale: N min`)
brain sync [--category C] [--json]  # Pull updates from Notion into the local mirror (v1.5)
brain move <source_id> --to-brain --kind {decision,pattern,gotcha} [--keep-source]
brain move <notion_page_id> --to-local --category {decisions,patterns,gotchas,web_cache} [--force]
```

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

## Events (Audit Log)

```bash
events [--entity {task,epic,story}] [--id SLUG] [--limit N]
```

## Maintenance

```bash
update-claudemd [--claudemd PATH] [--dry-run]  # Update <!-- DYNAMIC --> section in CLAUDE.md AND its AGENTS.md sibling (v1.5: --dry-run prints diff and exits 1 if drift). A file without the marker is skipped with a notice.
fts optimize                          # Optimize FTS5 indexes
hud                                   # Live one-screen dashboard: task + session + gates + logs
suggest-model [complexity]            # Recommend Claude model: simple→Haiku, medium→Sonnet, complex→Opus
```

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
