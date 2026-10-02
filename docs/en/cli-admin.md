**English** | [Русский](../ru/cli-admin.md)

# CLI: project maintenance

<!-- doc-map: reader=user; zone=core-surface -->

State, stacks, roles, skills, hygiene, constants. Part of the command reference. Start, and the working set, in [cli.md](cli.md).
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
skill bundle list               # List bundles declared by configured third-party skill repos.
skill bundle show <name>        # Show one bundle's contents (skill names + descriptions).
skill bundle install <name>     # Install every skill in the bundle (per-skill error continues).
skill bundle uninstall <name>   # Uninstall every skill in the bundle.
```

Negative scenarios (unknown skill, untrusted repo URL, missing skill) print
a friendly `Error: ...` line on stderr and exit `1`. They never produce
a Python traceback (v1.5: `SkillManagerError` is caught alongside
`ServiceError` in `main()`).

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
                                # Does NOT shrink the tree: the exporter selects
                                # FROM tasks with no archived_at filter.

hygiene unarchive --slug S      # Dry-run: what clearing archived_at on S would unhide.
hygiene unarchive --archived-within DAYS
                                # Select by recency instead — undoes a batch just applied.
                                # Not "older than": the oldest archived rows are the ones
                                # meant to stay hidden.
                                # A selector is REQUIRED; a bare unarchive is refused.
      ... --confirm             # Write: clears archived_at only. status and completed_at
                                # are untouched, so the row is unhidden, not reopened.
                                # Works with task_archive.enabled=false: the config gates
                                # hiding, not recovery.
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

## Maintenance

```bash
update-claudemd [--claudemd PATH] [--dry-run]  # Update <!-- DYNAMIC --> section in CLAUDE.md AND its AGENTS.md sibling (v1.5: --dry-run prints diff and exits 1 if drift). A file without the marker is skipped with a notice.
fts optimize                          # Optimize FTS5 indexes
hud                                   # Live one-screen dashboard: task + session + gates + logs
suggest-model [complexity]            # Recommend Claude model: simple→Haiku, medium→Sonnet, complex→Opus
```

## Commands not covered by the sections above

This section exists because of a measurement: of the 53 commands
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
                               # CLI only, deliberately: not an MCP tool (scripts/mcp_cli_only.py)
redact list                    # show the redactions already applied

# --- release and network ---
publish snapshot --from <ref> --parent <sha> [--dry-run]   # the public snapshot: the filtered tree on top of the public head
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
| Session time | A signal with threshold `session_max_minutes` on active time (idle: `session_idle_threshold_minutes`); never refuses |

### Cost in money: `token_price` in `.tausik/config.json`

`tausik metrics tokens` reports FOUR billing kinds — output, input (uncached),
cache_create, cache_read — and, when rates are set, the price of each. Rates live
in `.tausik/config.json`:

```json
{ "token_price": { "claude-opus": { "output": 75.0, "input": 15.0,
                                    "cache_create": 18.75, "cache_read": 1.5 } } }
```

The key is a model-name PREFIX (longest match wins) and the values are dollars per
million tokens. No default rates ship, deliberately: a rate is an external fact
with a date and a contract behind it, list prices move, agreements differ, and a
number baked into the code would be right for nobody and would rot without a
sound. A model with no entry is reported UNPRICED rather than zero — a zero would
read as free work.

Below it, the same cost PER TASK, with the turn count and the cache-hit share.
Measured over 5964 calls: cache_read is 99.5% of all input, so the
spend is almost entirely the prefix being re-sent. Hence the rule — measure cost
per COMPLETED TASK rather than per request: one extra turn costs on the order of
half a million cache_read tokens, and a change that saves request tokens at the
price of a turn loses by about two orders of magnitude.

## Changelog entries

User-visible changes go directly into both `CHANGELOG.md` and `CHANGELOG.ru.md`.
The closing gate requires substantive additions in every configured changelog; use
`--no-changelog` only for work that changes no shipped behaviour.
