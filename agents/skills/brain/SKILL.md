---
name: brain
description: "Query, store, or inspect cross-project knowledge in the Shared Brain (Notion + local SQLite mirror). Use when user says '/brain', 'brain query', 'brain store', 'brain show', 'check the brain', or wants to search/save knowledge across projects."
effort: fast
context: inline
---

# /brain — Shared Brain UI

Conversational front-end for the TAUSIK Shared Brain — a cross-project knowledge store (Notion-backed) that sits alongside the per-project `.tausik/tausik.db`. Read-path and write-path both exist as MCP tools; this skill wraps them with a UX that doesn't require remembering tool names or flag sets.

> **ARCHITECTURE — read this before running `brain init`:**
>
> The Shared Brain is **ONE set of 4 Notion databases per workspace, shared by ALL projects**. Categories: `decisions`, `patterns`, `gotchas`, `web_cache`. Per-project privacy is enforced via the `Source Project Hash` column on every row, **NOT** by giving each project its own copies of the four databases.
>
> If a project's `.tausik/config.json` does not yet have brain configured but the user already has BRAIN databases in their Notion workspace from another project, **DO NOT run plain `brain init` — that creates a SECOND independent set, splitting the knowledge store in two**. Use `tausik brain init --join-existing` instead. The wizard auto-discovers canonical-titled BRAIN databases via Notion search; pass explicit `--decisions-id / --web-cache-id / --patterns-id / --gotchas-id` only if auto-discovery fails (e.g. the integration was not invited to the existing parent page).
>
> `--force-create` exists as an escape hatch for the rare case of an intentional brand-new workspace (different Notion account/integration). Default refuses to create duplicates.

**When to use:** user asks you to search or save knowledge that applies across projects (generalizable decisions, reusable patterns, cross-cutting gotchas, cached web fetches).

**When NOT to use:** project-specific memory — use `tausik memory add` instead. The Memory Policy rule is strict: project traces stay local, only generalizable knowledge goes to the brain.

## Argument Dispatch

### `$ARGUMENTS = "query <text>"` or just `<text>`

Search the brain and return the top hits.

1. Call `brain_search` MCP tool with `query=<text>`. Optional args: `category` (one of `decisions`, `web_cache`, `patterns`, `gotchas`), `limit` (default 10), `use_notion_fallback=true` (default).
2. Render the returned markdown directly — `brain_mcp_read.format_search_results` already formats each hit as a short block with the notion_page_id, name, category, and a snippet.
3. If zero hits, suggest: (a) broadening the query, (b) dropping the category filter if one was used, (c) falling back to the local TAUSIK search via `.tausik/tausik search "<text>"`.

**Examples:**
- `/brain query notion rate limits` → decisions + gotchas + web_cache across projects
- `/brain query --category=patterns async retry` → only patterns db

### `$ARGUMENTS = "store <decision|pattern|gotcha> <text>" `

Save a record to the brain.

1. **For decisions**, prefer `.tausik/tausik decide "<text>" --rationale "<why>"` — the auto-routing classifier decides between local-only and brain based on content markers (src paths, project names, etc.). Don't bypass the classifier unless the user explicitly says `--scope brain`.
2. **For patterns or gotchas**, call the matching MCP tool directly:
   - Pattern → `brain_store_pattern` with `name`, `description`, `when_to_use`, `example`, `tags[]`, `stack[]`.
   - Gotcha → `brain_store_gotcha` with `name`, `description`, `wrong_way`, `right_way`, `severity`, `tags[]`, `stack[]`.
3. Surface the formatted result (stored/not-mirrored/scrub-blocked/notion-error) returned by `brain_mcp_write.format_store_result`. Scrub blocks list detector names only — never surface the raw matched text to the user, it may carry the PII/project-name that triggered the block.
4. If brain is disabled, fall through to local-only: `.tausik/tausik memory add <type> "<title>" "<content>"`.

**Examples:**
- `/brain store decision "Prefer HTTP/2 with ALPN over manual SPDY negotiation"`
- `/brain store pattern "Exponential backoff with jitter"`
- `/brain store gotcha "Notion FTS5 treats hyphens as column operators"`

### `$ARGUMENTS = "show <notion_page_id> [<category>]"`

Render a single record in full.

1. Call `brain_get` MCP tool with `id=<notion_page_id>` and `category=<decisions|patterns|gotchas|web_cache>`. If category is omitted, ask the user — `brain_get` requires both.
2. Render via `brain_mcp_read.format_record`.
3. If not found locally, the MCP handler auto-falls back to Notion; warnings are surfaced below the body.

### `$ARGUMENTS = "move <id> --to-brain --kind <decision|pattern|gotcha>"` or `"move <notion_page_id> --to-local --category <decisions|patterns|gotchas>"`

Move a record between local TAUSIK and the shared brain. Useful when a record landed in the wrong store and should be reclassified.

1. Run `.tausik/tausik brain move <id> --to-brain --kind <kind> [--keep-source]` for local→brain.
2. Run `.tausik/tausik brain move <notion_page_id> --to-local --category <category> [--force] [--keep-source]` for brain→local.
3. Cross-project ownership: `--to-local` refuses when the brain row's `source_project_hash` doesn't match the current project. Override with `--force` (you'll claim another project's data — rarely correct).
4. `web_cache` cannot be moved to local (no counterpart table). The CLI refuses.
5. Source row is deleted on success unless `--keep-source` is passed. For `--to-local`, the Notion page is archived (`pages.update(archived=true)`) and the mirror row deleted.

**Examples:**
- `/brain move 42 --to-brain --kind decision` — promote local decision #42 to the shared brain
- `/brain move npg-abc123 --to-local --category patterns` — pull a brain pattern back into local memory
- `/brain move 7 --to-brain --kind gotcha --keep-source` — copy without deleting the local row

### `$ARGUMENTS = "status"`

Snapshot brain health: enabled flag, mirror path/size/last-modified, per-category row counts and last_pull_at / last_error from `sync_state`, registered projects, last `web_cache` write.

1. Run `.tausik/tausik brain status` — returns markdown.
2. For machine-readable output use `.tausik/tausik brain status --json` (same data structure as `brain_status.collect_status()`).
3. If brain is disabled, the report is short — just enabled flag + project list. Suggest `tausik brain init` to enable.

**Examples:**
- `/brain status` → human-readable health report
- `/brain status --json` → JSON for piping into another tool

### `$ARGUMENTS = ""` or `"help"`

Print a four-line usage reminder (query / store / show / status) and link to [docs/en/shared-brain.md](../../../docs/en/shared-brain.md).

## Bypass markers

Two user-controlled escape hatches to know about:

- **`refresh: web_cache`** — put this on a line by itself in your next prompt to force a network WebFetch/WebSearch even when `brain_search_proactive` would block on a fresh cache hit. See [scripts/hooks/brain_search_proactive.py](../../../scripts/hooks/brain_search_proactive.py).
- **`confirm: cross-project`** — put this on a line by itself to allow a Write/Edit into `~/.claude/projects/*/memory/` from inside a TAUSIK project. Project-specific content should use `tausik memory add` instead; this marker exists only for genuine cross-project user preferences.

Markers are anchored — they must sit on a line of their own, outside fenced code blocks and outside 4+-space indented blocks. Quoting the hook's own error text in a fenced block will NOT re-enable the bypass.

## Brain disabled?

If `brain.enabled=false` in the project config, every subcommand short-circuits with a "not configured" message.

**First, ASK the user before running any command.** Two paths:

1. **User already has BRAIN databases in another project's Notion workspace** — wire this project to them with `tausik brain init --join-existing`. The wizard auto-discovers the canonical 4 databases via Notion search. If auto-discovery fails (integration not shared on the parent page), pass explicit IDs: `--decisions-id ... --web-cache-id ... --patterns-id ... --gotchas-id ...`. **This is the common case** when adding TAUSIK to a second/third project.

2. **User has no BRAIN at all yet** — `tausik brain init --parent-page-id <id>` creates the 4 databases under the supplied parent page. The Notion integration token must be set per `docs/{en,ru}/shared-brain.md` (env var, `.tausik/.env`, or inline in config.json — cascade resolution).

**NEVER guess.** If you don't know whether the user already has BRAIN somewhere, ask. Creating duplicate sets of 4 databases in the same workspace silently splits the knowledge store; the wizard's pre-flight workspace search will refuse this by default but only `--force-create` overrides — agents must not invent that flag without explicit user instruction.

Setup docs: [docs/en/shared-brain.md](../../../docs/en/shared-brain.md) (EN), [docs/ru/shared-brain.md](../../../docs/ru/shared-brain.md) (RU). Schema reference: [references/brain-db-schema.md](../../../references/brain-db-schema.md).

## Subcommand status

All four subcommands are now implemented: `query`, `store`, `show`, `move`, `status`. See examples above for usage.

## Gotchas

- **Don't invent tool names.** Every subcommand in this skill maps to an MCP tool (`brain_search`, `brain_get`, `brain_store_*`) or an existing CLI (`.tausik/tausik decide`, `.tausik/tausik search`, `.tausik/tausik memory add`). If a subcommand doesn't exist, say so.
- **Never leak raw scrub matches.** `brain_mcp_write.store_record` returns `issues: list[dict]` with a `match` key that may contain the PII/project-name that triggered the block. Surface `detector` names only — that's what `_format_scrub_detectors` in `brain_runtime.py` does for CLI callers.
- **Store category matters for `show`.** `brain_get` needs both `id` and `category`; the local mirror table is picked by category. Guess wrong → empty result with a misleading warning.
- **Local-first classifier.** `tausik decide` defaults to local when content has project markers (abs paths, src refs, kebab slugs, `.tausik/tausik` commands). Force brain only with `--scope brain` if you're sure the content is generalizable.
- **Brain writes are cross-project.** Data written here is visible to every project that shares the same Notion databases. Treat it like you'd treat a public wiki — no secrets, no client names, no internal URLs (the `private_url_patterns` regex list catches some of this, but don't rely on it).
