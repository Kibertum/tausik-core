# Shared Brain — cross-project knowledge on Notion

**Status:** opt-in, pipeline complete, setup wizard pending.

TAUSIK's per-project memory (`.tausik/tausik.db`) is the primary store for everything specific to *this* repository. The **Shared Brain** is the optional second layer: a Notion-backed knowledge base that only stores knowledge **generalizable across projects** — paid-for architectural insights, hard-won gotchas, stable patterns, and HTTP cache that benefits all your repos.

The split is deliberate. The local DB keeps project-specific traces (file paths, module names, client slugs) — anything that would leak context between unrelated codebases. The brain keeps what you'd want a fresh agent in a *different* repo to learn from.

## Philosophy

| Layer | Store | Scope | Example |
|---|---|---|---|
| Local | `.tausik/tausik.db` | This project only | "auth-middleware.py line 42 logs PII — fix in MR-1234" |
| Brain | Notion databases | Cross-project | "SHA256-based project hashes avoid leaking names while staying unique for N<1000" |

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
| [scripts/brain_config.py](../../scripts/brain_config.py) | Config parsing + validation; `compute_project_hash`, `get_brain_mirror_path` |
| [scripts/brain_schema.py](../../scripts/brain_schema.py) | Local SQLite DDL (4 tables + FTS5 + triggers, `unicode61` tokenizer) |
| [scripts/brain_notion_client.py](../../scripts/brain_notion_client.py) | Stdlib Notion REST client (throttle + retry + pagination iterator) |
| [scripts/brain_sync.py](../../scripts/brain_sync.py) | Delta-pull Notion → local; maps Notion page JSON → SQLite rows |
| [scripts/brain_search.py](../../scripts/brain_search.py) | Local FTS5 search with bm25 ranking and SQL `snippet()` |
| [references/brain-db-schema.md](../../references/brain-db-schema.md) | Design doc — database properties, JSON payload examples, trade-offs |

## Setup

Prerequisite: a Notion workspace you control.

### 1. Create the parent page

In your Notion sidebar, create a new page named "TAUSIK Shared Brain" (or whatever you like). This hosts the 4 databases the wizard will create.

### 2. Create the integration

1. https://www.notion.so/my-integrations → "New integration".
2. Name it "TAUSIK Brain".
3. Type: Internal.
4. Capabilities: Read content, Update content, Insert content.
5. Copy the **internal integration token** (starts with `secret_`).

### 3. Share the parent page with the integration

Open your "TAUSIK Shared Brain" page → top-right `...` → "Add connections" → select "TAUSIK Brain". The wizard creates databases under this page, so the integration must have access.

### 4. Export the token

```bash
export NOTION_TAUSIK_TOKEN='secret_xxx'
```

On Windows:

```powershell
setx NOTION_TAUSIK_TOKEN "secret_xxx"
```

### 5. Run the wizard

Interactive (prompts for parent page ID and confirms):

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

1. Calls `POST /v1/databases` four times to create `decisions`, `web_cache`, `patterns`, `gotchas` with the schemas from [references/brain-db-schema.md](../../references/brain-db-schema.md).
2. Writes `.tausik/config.json` atomically with `brain.enabled=true`, the 4 `database_ids`, `notion_integration_token_env`, and your project name (for the scrubbing blocklist).
3. **Never** stores the token itself — only the env var name.

Re-running on an already-configured project fails loudly unless you pass `--force`.

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

## Privacy

1. **No plaintext project names leave the machine.** The only per-project identifier in the brain is `SHA256(canonical_name)[:16]`. Canonical name comes from `project_names[0]` in your local `.tausik/config.json` and is not itself pushed anywhere.
2. **Scrubbing linter** (task `brain-scrubbing`, pending) will intercept every write before it hits the client. Rejects: absolute Windows/POSIX paths, internal domain URLs, any text matched by `brain.private_url_patterns` regex list, kebab-slugs that look like internal identifiers.
3. **Classifier** (task `brain-classifier`, pending) picks `local` vs `brain` per-record. Only `brain`-class records are pushed. Conservative-default: ambiguous → `local`.
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

## Alternative: Outline (TODO)

Outline (https://www.getoutline.com/) is a self-hostable markdown-first alternative. Potential advantages: no rate limits you don't control, simpler data model, open-source. Tradeoffs: no native "databases" construct — everything is markdown pages, so filters/views are less rich. Not implemented yet; tracked separately.

## What ships in this release

- Full read-path (Notion → pull → mirror → bm25 search) — **tested offline end-to-end** via mocked `urlopen`
- Typed error hierarchy (`NotionAuthError`, `NotionNotFoundError`, `NotionRateLimitError`, `NotionServerError`)
- 102/102 new tests green; 0 external dependencies

## Still TODO (planning)

`brain-mcp-tools-write`, `brain-mcp-tools-read`, `brain-mcp-server-wiring`, `brain-webfetch-hook`, `brain-classifier`, `brain-scrubbing`, `brain-decide-auto-route`, `brain-search-proactive`, `brain-skill-ui`, `brain-project-registry`, `brain-init-wizard`, `brain-fallback-offline`, `brain-notion-space` (manual), `brain-integration-token` (manual).
