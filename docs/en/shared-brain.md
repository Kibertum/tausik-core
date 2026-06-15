# Shared Brain — cross-project knowledge on Notion

**Status:** opt-in, pipeline complete. v1.4 ships an interactive setup wizard with an upfront prerequisites checklist, friendlier token-missing errors, and concrete URL/page-ID guidance. Bootstrap with `--interactive --init` offers to launch the wizard automatically; otherwise run `.tausik/tausik brain init`.

TAUSIK's per-project memory (`.tausik/tausik.db`) is the primary store for everything specific to *this* repository. The **Shared Brain** is the optional second layer: a Notion-backed knowledge base that only stores knowledge **generalizable across projects** — paid-for architectural insights, hard-won gotchas, stable patterns, and HTTP cache that benefits all your repos.

The split is deliberate. The local DB keeps project-specific traces (file paths, module names, client slugs) — anything that would leak context between unrelated codebases. The brain keeps what you'd want a fresh agent in a *different* repo to learn from.

## Philosophy

| Layer | Store | Scope | Example |
|---|---|---|---|
| Local | `.tausik/tausik.db` | This project only | "auth-middleware.py line 42 logs PII — fix in MR-1234" |
| Brain | Notion databases | Cross-project | "SHA256-based project hashes avoid leaking names while staying unique for N<1000" |

**Artifact taxonomy (v1.4):** shared vocabulary **artifact / pattern / snippet** for MCP `brain_store_*` and future snippet cards — see **[brain-artifact-taxonomy.md](brain-artifact-taxonomy.md)** (optional field + strict mode in `.tausik/config.json`).

**Editorial hygiene:** when to **merge** local memory rows vs add a new entry (orthogonal to scrubbing) — **[Memory merge guidelines](memory-merge-guidelines.md)**.

Nothing that identifies the project should ever reach the brain. Enforcement:
1. **Scrubbing linter** rejects writes with absolute paths, kebab-slugs ≥3 parts, `.tausik/tausik` commands, internal URLs.
2. **Classifier** decides whether a record is `local` or `brain`; only `brain`-classified records are pushed.
3. **Source Project Hash** — every record carries `SHA256(canonical_name)[:16]`, so even if a project-identifier accidentally slips through audit, the Notion-side reader can't cross-reference project names without the local registry.

## Architecture

```
                     ┌────────────────────┐
                     │  Notion workspace  │
                     │  (4 databases)     │
                     │  decisions         │
                     │  web_cache         │
                     │  patterns          │
                     │  gotchas           │
                     └─────────┬──────────┘
                               │  Notion REST API
                               │  (Bearer + Notion-Version)
              ┌────────────────▼─────────────────┐
              │  scripts/brain_notion_client.py  │  stdlib urllib,
              │  throttle 350ms, 429/5xx retry   │  zero deps
              └────────────────┬─────────────────┘
                               │
                  ┌────────────┴─────────────┐
                  │                          │
         pages_create             iter_database_query
         (write path)             (pull with delta)
                  │                          │
                  │                          ▼
                  │           ┌──────────────────────────┐
                  │           │ scripts/brain_sync.py    │
                  │           │ map Notion→SQLite rows   │
                  │           │ upsert by page_id        │
                  │           │ advance sync_state       │
                  │           └────────────┬─────────────┘
                  │                        │
                  │                        ▼
                  │           ┌──────────────────────────┐
                  │           │ ~/.tausik-brain/brain.db │
                  │           │ brain_schema + FTS5      │
                  │           │ unicode61 tokenizer      │
                  │           └────────────┬─────────────┘
                  │                        │
                  │                        ▼
                  │           ┌──────────────────────────┐
                  │           │ scripts/brain_search.py  │
                  │           │ bm25-ranked local search │
                  │           └────────────┬─────────────┘
                  │                        │
                  └────────────┬───────────┘
                               │
                  ┌────────────▼──────────────┐
                  │ scripts/brain_config.py   │
                  │ load/validate config      │
                  │ project hash, token env   │
                  └───────────────────────────┘
```

## Modules (shipped)

| File | Purpose |
|---|---|
| [scripts/brain_config.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_config.py) | Config parsing + validation; `compute_project_hash`, `get_brain_mirror_path` |
| [scripts/brain_schema.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_schema.py) | Local SQLite DDL (4 tables + FTS5 + triggers, `unicode61` tokenizer) |
| [scripts/brain_notion_client.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_notion_client.py) | Stdlib Notion REST client (throttle + retry + pagination iterator) |
| [scripts/brain_sync.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_sync.py) | Delta-pull Notion → local; maps Notion page JSON → SQLite rows |
| [scripts/brain_search.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_search.py) | Local FTS5 search with bm25 ranking and SQL `snippet()` |
| [brain-db-schema.md](brain-db-schema.md) | Design doc — database properties, JSON payload examples, trade-offs |

## Setup

Prerequisite: a Notion workspace you control.

### 1. Create the parent page

In your Notion sidebar, create a new page named "TAUSIK Shared Brain" (or whatever you like). This hosts the 4 databases the wizard will create.

### 2. Create the integration

1. https://www.notion.so/my-integrations → "New integration".
2. Name it "TAUSIK Brain".
3. Type: Internal.
4. Capabilities: Read content, Update content, Insert content.
5. Copy the **internal integration token** (starts with `ntn_` or legacy `secret_`).

### 3. Share the parent page with the integration

Open your "TAUSIK Shared Brain" page → top-right `...` → "Add connections" → select "TAUSIK Brain". The wizard creates databases under this page, so the integration must have access.

### 4. Store the token (pick one — v1.3.2+ supports a cascade)

The Notion token is resolved via this priority order:

1. **`os.environ[NOTION_TAUSIK_TOKEN]`** — env var. Highest priority. Best for CI / shared boxes.
2. **`.tausik/.env`** — project-local `KEY=VALUE` file. **Recommended for individual developers**: gitignored, persists without shell-rc edits, survives reboots.
3. **`brain.notion_integration_token`** in `.tausik/config.json` — emits a stderr warning ("stored inline; prefer .tausik/.env"). Allowed but not encouraged.

**Recommended path — `.tausik/.env`:**

```bash
echo "NOTION_TAUSIK_TOKEN=ntn_xxx" >> .tausik/.env
```

**If you prefer environment variables:**

```bash
# Linux / macOS — persisted by adding to ~/.bashrc / ~/.zshrc / ~/.profile
export NOTION_TAUSIK_TOKEN='ntn_xxx'
```

```powershell
# Windows — persisted at User level (survives reboot, IDE restart picks up)
[System.Environment]::SetEnvironmentVariable('NOTION_TAUSIK_TOKEN', 'ntn_xxx', 'User')
# Apply to current PowerShell session too:
$env:NOTION_TAUSIK_TOKEN = 'ntn_xxx'
```

After persisting, **restart the IDE** (Claude Code / Cursor / etc.) so the MCP subprocess picks up the new env. With `.tausik/.env`, no IDE restart needed — the token is read at brain-call time.

### 5. Run the wizard

> **One set of databases per workspace, shared by all projects.** Per-project privacy comes from the `Source Project Hash` column on each row, not from giving each project its own copies of the four databases. The wizard enforces this — see "Common mistakes" below.

**First project — create the 4 databases:**

```bash
.tausik/tausik brain init
```

Non-interactive (for CI / scripted setup):

```bash
.tausik/tausik brain init \
  --parent-page-id 'abc123...' \
  --token-env NOTION_TAUSIK_TOKEN \
  --project-name my-project \
  --yes --non-interactive
```

The parent page ID is the 32-char hex after `notion.so/...-` in the URL (with or without hyphens). The wizard:

1. **Pre-flight workspace search** (v1.3.3+): looks for canonical-titled BRAIN databases (`Brain · Decisions / Patterns / Gotchas / Web Cache`) already shared with the integration. If a full set is found, refuses to create duplicates and points at `--join-existing`.
2. Calls `POST /v1/databases` four times to create `decisions`, `web_cache`, `patterns`, `gotchas` with the schemas from [brain-db-schema.md](brain-db-schema.md).
3. Writes `.tausik/config.json` atomically with `brain.enabled=true`, the 4 `database_ids`, `notion_integration_token_env`, and your project name (for the scrubbing blocklist).
4. **Never** stores the token itself in `config.json` — only the env var **name**. The token lives in `.tausik/.env` (recommended) or your shell environment.

Re-running on an already-configured project fails loudly unless you pass `--force`.

**Second / third / Nth project — join the existing databases:**

```bash
.tausik/tausik brain init --join-existing
```

The wizard searches your Notion workspace for the canonical 4 BRAIN databases (auto-discovers via `POST /v1/search`) and writes their IDs into this project's `.tausik/config.json`. **No new databases are created.** All projects pointed at the same 4 IDs share one knowledge store; the `Source Project Hash` column keeps per-project rows distinguishable.

**Auto-discovery is two-pass (v1.4-polish):**

1. **Title-match.** Databases titled exactly `Brain · Decisions / Web Cache / Patterns / Gotchas` (the canonical names the wizard creates) are wired by name.
2. **Schema-fallback.** For any category not matched by title, the wizard inspects each remaining visible database's `properties` schema. A database whose properties contain the per-category required set (e.g. `decisions` requires `Name`, `Decision`, `Rationale`, `Source Project Hash`) is wired regardless of its title. Catches databases renamed in Notion (UI rename, emoji prefix, translation) and databases created outside the wizard.

When auto-discovery returns 0 hits but the integration sees other databases, the error lists those candidates so you can either rename them canonically or pass IDs explicitly. When the integration sees nothing at all, the error points at the share-with-integration step.

If auto-discovery cannot find the databases (e.g. the integration was not invited to the parent page), pass IDs explicitly:

```bash
.tausik/tausik brain init --join-existing \
  --decisions-id  '...' \
  --web-cache-id  '...' \
  --patterns-id   '...' \
  --gotchas-id    '...' \
  --token-env NOTION_TAUSIK_TOKEN \
  --non-interactive --yes
```

**Escape hatch — `--force-create`.** If you genuinely need a separate, brand-new set of 4 databases (different Notion account, intentionally siloed knowledge), pass `--force-create`. The wizard will skip the duplicate-DB pre-flight and create new ones. **Use sparingly** — projects pointed at the original set will not see records from the new one and vice versa.

### Common mistakes

- ❌ **Running plain `brain init` in a second project that shares the workspace** → creates a parallel set of 4 BRAIN databases. Knowledge silently splits in two; some projects see one half, some see the other. The v1.3.3 pre-flight check refuses this by default — **do not bypass with `--force-create` unless you genuinely want two independent brains**.
- ❌ **Per-project copies "for privacy"** → unnecessary. Use the `Source Project Hash` column (already on every row) to filter by project; share the four databases.
- ❌ **Editing `database_ids` in `config.json` by hand without verifying** → use `--join-existing --decisions-id ...` so the wizard verifies each ID against Notion before saving.

### 6. Smoke-test

```python
from brain_config import load_brain, validate_brain, get_brain_mirror_path
from brain_notion_client import NotionClient
from brain_sync import open_brain_db, sync_all
import os

brain = load_brain()
errors = validate_brain()
assert not errors, errors

client = NotionClient(os.environ["NOTION_TAUSIK_TOKEN"])
conn = open_brain_db(get_brain_mirror_path())
result = sync_all(client, conn, brain["database_ids"])
print(result)
```

`get_brain_mirror_path()` accepts three input shapes: `None` (consults
`load_config()` internally), a top-level project dict
`{"brain": {...}}`, or an already-merged brain dict
`{"enabled": ..., "local_mirror_path": ...}` (the shape `load_brain()`
returns). All three resolve the same absolute path.

Expected: 4 keys (decisions/web_cache/patterns/gotchas), each with `{fetched: N, upserted: N, last_edited_time: ...}` or `{error: ...}`. On a fresh empty setup, all four are `{fetched: 0, upserted: 0, last_edited_time: null}`.

## Metrics (v1.4)

To answer the recurring question "is the brain actually helping me?" v1.4 records every brain operation into a per-project `brain_events` table (in `.tausik/tausik.db`, NOT in the Notion mirror — keeping the dispersion firewall intact). `tausik metrics` surfaces a `Shared Brain` block once any events exist:

```
--- Shared Brain (v1.4) ---
Session: 6 searches, 4 hits, 2 writes, 0 ignored (hit rate: 66.7%)
All-time: 142 searches, 87 hits, 18 writes (hit rate: 61.3%)
```

Counters:
- `searches` — every call to `brain_search` / `search_with_fallback`.
- `hits` — searches that returned ≥1 result (proxy for "did the brain answer the question?").
- `writes` — successful `try_brain_write_decision` / `try_brain_write_web_cache` operations (Notion ack received). Failed writes are NOT counted.
- `ignored` — `tausik_memory_quick brain.ignored:<id>` entries written when an agent flags a brain suggestion as irrelevant (next session won't re-surface it).

The `hit_rate_pct` is `hits / searches * 100`. A consistently low session hit-rate (<20%) suggests either (a) the brain is empty/stale and needs `tausik brain sync` + new writes, or (b) queries are too project-specific (the classifier should send those to local memory, not brain). The two failure modes look the same in metrics, so investigate by reading recent `brain_events` rows.

Telemetry never blocks the actual operation: if `brain_events.INSERT` fails (locked DB, permissions), the search/write proceeds and the row is silently dropped.

## Privacy

1. **No plaintext project names leave the machine.** The only per-project identifier in the brain is `SHA256(canonical_name)[:16]`. Canonical name comes from `project_names[0]` in your local `.tausik/config.json` and is not itself pushed anywhere.
2. **Scrubbing linter** (`scripts/brain_scrubbing.py`, shipped) intercepts every write before it hits the client. Rejects: absolute Windows/POSIX paths, internal domain URLs, any text matched by `brain.private_url_patterns` regex list, kebab-slugs that look like internal identifiers.
3. **Classifier** (`scripts/brain_classifier.py`, shipped) picks `local` vs `brain` per-record. Only `brain`-class records are pushed. Conservative-default: ambiguous → `local`.
4. **You can revoke at any time.** Revoke the Notion integration or unset `NOTION_TAUSIK_TOKEN`; the next sync/write fails cleanly with `NotionAuthError`, and the local mirror continues working for read-only searches.

## Edge cases / failure modes

| Scenario | What happens | User action |
|---|---|---|
| **Revoked integration token** | Next API call raises `NotionAuthError` (401/403) without retry | Regenerate or restore token; no data loss — local mirror intact |
| **Rate-limit 429** | Client retries honoring `Retry-After`; exhausted → `NotionRateLimitError` | Usually automatic. If persistent: reduce sync frequency |
| **Offline / DNS fail** | `URLError` retried with backoff; exhausted → `NotionError` | `brain_search.search_local()` still works over local mirror |
| **Content >180 KB** | Property `[see page body]`; full text in child blocks | Keep notes concise; large web pages are truncated by spec |
| **Sensitive data slipped past scrubbing** | Delete the Notion page manually; next pull-sync detects 404 | Improve `private_url_patterns` regex to catch the pattern going forward |
| **Database schema drift** | Missing properties read as NULL; extra properties ignored | Re-run setup step 2 to add missing properties |
| **Two projects with identical canonical name** | Hash collision — records mix in Notion views | Rename one in `project_names[]` |

## Pros / Cons

| Pros | Cons |
|---|---|
| Write once, search across all projects | Requires Notion account + setup |
| Notion UI for browsing/editing | Rate limits (3 req/s) during bulk writes |
| bm25 local search works offline | Integration-token management overhead |
| Zero external Python deps (stdlib urllib) | Must actively filter what's "generalizable" |
| Privacy-preserving hash, no plaintext project names | Accidental leaks possible before `brain-scrubbing` ships |
| FTS5 supports Cyrillic / diacritics | No shared-team mode (single-user v1) |

## What ships in v1.4

The full brain stack lands in v1.4 — read AND write paths, MCP tools on both sides, hook-driven WebFetch capture, classifier + scrubbing, init wizard, offline fallback, search-proactive hook. Modules: `brain_mcp_read.py`, `brain_mcp_write.py`, `brain_classifier.py`, `brain_scrubbing.py`, `brain_search.py` (bm25 ranking with stack boost), `brain_init.py` (init wizard), `brain_project_registry.py`, `brain_fallback.py`, `brain_universality.py` + `brain_universality_semantic.py` (cross-project promotion heuristics). Typed error hierarchy: `NotionAuthError`, `NotionNotFoundError`, `NotionRateLimitError`, `NotionServerError`. Manual one-time steps (`brain-notion-space`, `brain-integration-token`) are documented in `tausik brain init` wizard output.
