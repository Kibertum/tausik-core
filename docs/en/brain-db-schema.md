**English** | [Русский](../ru/brain-db-schema.md)

# Brain Notion Databases — Schema v1

Design document for the `shared-brain` subsystem. Defines the structure of 4 Notion databases that form TAUSIK's cross-project knowledge base: `decisions`, `web_cache`, `patterns`, `gotchas`. All projects write generalizable knowledge here; project-specific traces stay in local `.tausik/tausik.db`.

Status: implemented in v1.3.0. See also: [shared-brain.md](shared-brain.md), [architecture.md](architecture.md).

## 1. Why exactly 4 databases

The alternative — one "flat" database with a `type` discriminator — was rejected: in the Notion UI you lose native column-level filters and views (each entity has its own field set: `gotchas` has `Wrong Way` / `Right Way`, `web_cache` does not). The cost is a slightly more complex pull-sync (4 cursors instead of one), but that's a one-off in client code.

A three-table alternative (merging `patterns` + `gotchas`) was also rejected: opposite semantics (one is "how to", the other is "how NOT to") blur the search results.

## 2. Privacy boundary

Goal: from the contents of the brain it must be impossible to determine **which specific projects** the agent is being used in. The invariants follow from this:

- Every record has a `Source Project Hash` field = `SHA256(project_name_canonical)[:16]` — 16 hex characters = 64 bit; for N=1000 projects the collision probability is ≈ 2.7e-14. That is enough for unique identification without revealing the name.
- `project_name_canonical` is the normalized project name: `name.lower().strip().replace(" ", "-")`. It is fixed at the moment a project is registered in `~/.tausik-brain/projects.json` (task `brain-project-registry`).
- A project **never** writes its own name into the brain, nor file paths, private module names, internal URLs, or any values that may end up in `.tausik/` as `scope` or `notes`. Filtering is the responsibility of `brain-scrubbing` (a pre-write linter).
- The hash is **not reversible** without a dictionary of all canonical names. The hash cannot be used to attribute a decision to a specific project "from the outside" — only inside the user's own environment, where the registry exists.

Why a hash and not plaintext: if the user later opens the integration up to a team, the hash will not reveal that, say, project `kareta-jira-workspace` exists at all.

## 3. Notion API constraints (v2022-06-28)

| Constraint | Value | Schema implication |
|---|---|---|
| Rate limit | 3 req/s (burst tolerated, throttle is strict) | client waits ≥350 ms between writes |
| `rich_text` block length | 2000 characters | long `Content` is split into N `rich_text` array elements |
| `rich_text` blocks per property | ~100 | content >200 KB is written as page child-blocks; the property keeps a pointer |
| `multi_select` options | ~100 per property | as the limit nears, migrate to a relation `tags` database (v2 — not now) |
| `title` length | 2000 characters | titles are truncated; the full version goes into `Content`/`Description` |
| pagination | cursor-based, `start_cursor` + `has_more` | pull-sync runs a while-loop until exhaustion |
| Error `409 Conflict` | concurrent write | should not occur for a single-writer client; retry |
| Error `429` / `502` / `503` / `504` | rate-limit / transient | exponential backoff with jitter, max 5 retries |

## 4. Databases

### 4.1 `decisions` — architectural decisions

Stores generalizable decisions: "we picked urllib over requests — here is the context and the why".

| Property | Notion type | Required | Purpose |
|---|---|---|---|
| `Name` | title | yes | Short statement of the decision (≤200 chars) |
| `Context` | rich_text | yes | The problem/situation |
| `Decision` | rich_text | yes | What we decided to do |
| `Rationale` | rich_text | yes | Why exactly this way |
| `Tags` | multi_select | no | Domains: `architecture`, `testing`, `db`, `security`, `api`, `devops`, `performance`, `dx`, … |
| `Stack` | multi_select | no | `python`, `typescript`, `go`, `rust`, `java`, … |
| `Date` | date | yes | When the decision was made (ISO `YYYY-MM-DD`) |
| `Source Project Hash` | rich_text | yes | 16 hex characters |
| `Generalizable` | checkbox | yes | Default `true`. If the agent sets it to `false`, the record is marked as "should not have been here" and is filtered out on sync |
| `Superseded By` | url | no | Link to another `decisions` record if the decision was replaced |

**JSON payload (`POST /v1/pages`):**

```json
{
  "parent": {"database_id": "<decisions_db_id>"},
  "properties": {
    "Name": {
      "title": [{"text": {"content": "Use urllib instead of requests"}}]
    },
    "Context": {
      "rich_text": [{"text": {"content": "Need an HTTP client for Notion API in TAUSIK, convention #19 (zero external deps)."}}]
    },
    "Decision": {
      "rich_text": [{"text": {"content": "Implement the client on stdlib `urllib.request` + `http.client`, no `requests`/`httpx`."}}]
    },
    "Rationale": {
      "rich_text": [{"text": {"content": "Adding a dependency breaks the zero-deps principle and complicates bootstrap. At the cost of ~100 LOC of boilerplate we get full control over throttle/retry."}}]
    },
    "Tags": {"multi_select": [{"name": "architecture"}, {"name": "dx"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {
      "rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]
    },
    "Generalizable": {"checkbox": true}
  }
}
```

### 4.2 `web_cache` — HTTP response cache (WebFetch)

When the agent runs `WebFetch`, the PostToolUse hook [`scripts/hooks/brain_post_webfetch.py`](../scripts/hooks/brain_post_webfetch.py) writes a record (url + content + prompt as query). Before the next `WebFetch`/`WebSearch` the PreToolUse hook [`scripts/hooks/brain_search_proactive.py`](../scripts/hooks/brain_search_proactive.py) checks `brain_web_cache`: exact-URL hit for `WebFetch`, FTS5 by query for `WebSearch` — if there is a fresh record (within `ttl_web_cache_days`), the network call is blocked.

**What is skipped:** private URLs (`brain.private_url_patterns`), HTTP errors (code ≥ 400), empty responses, URLs already mirrored within TTL, responses > 200 KB (trim to 200 KB). `WebSearch` responses are not cached directly (multiple URLs in a single blob → no canonical URL); `WebSearch` queries are served via FTS5 over existing `WebFetch` content.

**Non-blocking:** the hook always exits 0; a failed write (scrub block, Notion down) does not break the main flow — diagnostics go to stderr only when `TAUSIK_BRAIN_HOOK_DEBUG=1`.

| Property | Notion type | Required | Purpose |
|---|---|---|---|
| `Name` | title | yes | Page title or original WebSearch query (≤200 chars) |
| `URL` | url | yes for WebFetch | Canonical URL; empty for WebSearch |
| `Query` | rich_text | yes for WebSearch | Search query; for WebFetch duplicates URL |
| `Content` | rich_text (N blocks) | yes | Markdown content. If >180 KB it is stored as child-blocks of the page; the property keeps a marker `[see page body]` |
| `Fetched At` | date (with time) | yes | ISO `YYYY-MM-DDTHH:MM:SS.000Z` |
| `TTL Days` | number | yes | Default 30. `docs.*` — 90, SERP — 7, changelog/release pages — 3 |
| `Domain` | select | yes | URL host (for WebSearch — `serp:google` / `serp:ddg`) |
| `Tags` | multi_select | no | Topics (`notion-api`, `python-stdlib`, `sqlite-fts`) |
| `Source Project Hash` | rich_text | yes | The project that first cached the page (audit, not ACL) |
| `Content Hash` | rich_text | yes | SHA256(content)[:16] — dedup on pull |

**Why `Content Hash`:** if the same URL is fetched by 2 projects, you get 2 records with identical content. The classifier on pull-sync looks at `Content Hash` and ignores the duplicate.

**JSON payload:**

```json
{
  "parent": {"database_id": "<web_cache_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "Notion API — Create a page"}}]},
    "URL": {"url": "https://developers.notion.com/reference/post-page"},
    "Query": {"rich_text": [{"text": {"content": "https://developers.notion.com/reference/post-page"}}]},
    "Content": {
      "rich_text": [
        {"text": {"content": "# Create a page\n\nCreates a new page..."}},
        {"text": {"content": "... (chunk 2, up to 2000 chars)"}}
      ]
    },
    "Fetched At": {"date": {"start": "2026-04-23T10:15:00.000Z"}},
    "TTL Days": {"number": 90},
    "Domain": {"select": {"name": "developers.notion.com"}},
    "Tags": {"multi_select": [{"name": "notion-api"}, {"name": "docs"}]},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Content Hash": {"rich_text": [{"text": {"content": "9f8e7d6c5b4a3210"}}]}
  }
}
```

### 4.3 `patterns` — proven patterns

Reusable recipes: "how to do X correctly in Y". Difference from `decisions` — a pattern is universal, a decision is context-dependent.

| Property | Notion type | Required | Purpose |
|---|---|---|---|
| `Name` | title | yes | Short pattern name |
| `Description` | rich_text | yes | What it does, what problem it solves |
| `When to Use` | rich_text | yes | Application context (and when NOT to use it) |
| `Example` | rich_text | yes | Code example; for long ones — child-blocks |
| `Tags` | multi_select | no | `async`, `di`, `testing`, `error-handling`, `caching`, … |
| `Stack` | multi_select | yes | Language/framework — where it applies |
| `Source Project Hash` | rich_text | yes | Where it came from (audit) |
| `Date` | date | yes | When it was added |
| `Confidence` | select | yes | `experimental` (1 application) / `tested` (2–3) / `proven` (4+) |

**Example payload:**

```json
{
  "parent": {"database_id": "<patterns_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "Mixin composition over inheritance for the Service Layer"}}]},
    "Description": {"rich_text": [{"text": {"content": "Split a large service into mixins by functionality (TaskMixin, KnowledgeMixin). The main class inherits all of them."}}]},
    "When to Use": {"rich_text": [{"text": {"content": "When a service class is >400 lines and has >2 orthogonal method groups. Do NOT apply if the methods share state — that's a signal for separate services."}}]},
    "Example": {"rich_text": [{"text": {"content": "class ProjectService(SessionMixin, HierarchyMixin, TaskMixin):\n    def __init__(self, backend):\n        self.backend = backend"}}]},
    "Tags": {"multi_select": [{"name": "architecture"}, {"name": "oop"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Confidence": {"select": {"name": "proven"}}
  }
}
```

### 4.4 `gotchas` — traps and dead-ends

| Property | Notion type | Required | Purpose |
|---|---|---|---|
| `Name` | title | yes | Brief problem description |
| `Description` | rich_text | yes | What exactly happens, how it manifests |
| `Wrong Way` | rich_text | yes | What does NOT work (code/approach) |
| `Right Way` | rich_text | yes | What works |
| `Tags` | multi_select | no | — |
| `Stack` | multi_select | yes | — |
| `Source Project Hash` | rich_text | yes | — |
| `Date` | date | yes | — |
| `Severity` | select | yes | `low` (cosmetic) / `medium` (lost an hour) / `high` (≥4 hours of debugging) |
| `Evidence URL` | url | no | Link to a GitHub issue / StackOverflow / commit |

**Example payload:**

```json
{
  "parent": {"database_id": "<gotchas_db_id>"},
  "properties": {
    "Name": {"title": [{"text": {"content": "SQLite FTS5 MATCH with Cyrillic breaks without unicode61 tokenizer"}}]},
    "Description": {"rich_text": [{"text": {"content": "The default ascii tokenizer in FTS5 doesn't know Cyrillic — MATCH on a Russian word returns no results."}}]},
    "Wrong Way": {"rich_text": [{"text": {"content": "CREATE VIRTUAL TABLE fts USING fts5(content);"}}]},
    "Right Way": {"rich_text": [{"text": {"content": "CREATE VIRTUAL TABLE fts USING fts5(content, tokenize='unicode61 remove_diacritics 2');"}}]},
    "Tags": {"multi_select": [{"name": "sqlite"}, {"name": "fts"}, {"name": "i18n"}]},
    "Stack": {"multi_select": [{"name": "python"}]},
    "Date": {"date": {"start": "2026-04-23"}},
    "Source Project Hash": {"rich_text": [{"text": {"content": "a1b2c3d4e5f67890"}}]},
    "Severity": {"select": {"name": "medium"}},
    "Evidence URL": {"url": "https://sqlite.org/fts5.html#unicode61_tokenizer"}
  }
}
```

## 5. Delta-pull and indexes

Notion returns a system field `last_edited_time` on every page (ISO timestamp, with milliseconds). The pull-sync scheme:

1. The client stores `sync_state.last_pull_at` (per-category) in local SQLite.
2. Query: `POST /v1/databases/<id>/query` with a `filter` on `last_edited_time >= last_pull_at` and `sort` on `last_edited_time` asc.
3. Pagination loop over `has_more`/`next_cursor`.
4. After a successful pass, update `last_pull_at` = `max(last_edited_time)` from the batch.

**Why asc, not desc:** so that if the client crashes in the middle of a batch it doesn't break monotonicity — the last processed timestamp is the high-water mark.

**Notion views** (created manually in Notion at setup, not via API):
- `By Date` — sort desc by `Date`, default.
- `By Stack` — group by `Stack`.
- `By Project Hash` — group by `Source Project Hash` (for personal retrospective).
- `High Severity` (gotchas) — filter `Severity = high`.
- `Fresh cache` (web_cache) — filter `Fetched At > now-7d`.

Views do not affect the API and aren't required by the code; they are documented in `brain-onboarding-docs` as recommended post-setup.

## 6. Pagination and rate-limit — client side

- All writes go through a single throttle queue with an interval of ≥350 ms.
- 429 → `Retry-After` header + exponential backoff `min(2^attempt, 30)` with jitter ±20%.
- 5xx → backoff like 429, max 5 attempts.
- 404 on `pages.retrieve` for a known page_id → delete the record from the local mirror (ISR).
- 401/403 → immediate error, disable brain-flag until the next wizard run.

## 7. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| 4 separate databases | 1 flat database with `type` | Native Notion UI / filters; schema-driven properties; acceptable sync overhead |
| `multi_select` for `Tags` | relation to a `tags` database | Cheaper (1 API call instead of 2), simpler; the 100-options limit is far away |
| `rich_text` chunks for Content | page child-blocks | Chunks for ≤180 KB are cheap; child-blocks only for >180 KB (rare) |
| `SHA256(name)[:16]` hash | Plaintext name / UUID4 | Privacy without revealing clients; stable across regenerations |
| Separate `Content Hash` | Hash the URL | URL → different content over time (SPA, A/B tests); content-hash is more reliable for dedup |
| `Confidence` as select | Number (count of uses) | UI filtering is easier, semantics clearer; for point-in-time inflation, use a separate `Uses` number in v2 |
| `Generalizable` checkbox | Don't store private decisions at all | The classifier can be wrong → set a flag and filter on sync; easier than a full rollback |

## 8. Negative scenarios (mandatory fallbacks in code)

| Scenario | Reaction |
|---|---|
| Integration has no access to a database (403) | Disable the brain globally, log + message to user "run brain init", fall back to local-FTS |
| Missing database_id (404 on query) | Disable the brain, same message |
| Rate-limit 429 | Retry with backoff; if ≥5 in a row, temp-disable for 1 minute |
| Network timeout / DNS fail | Fall back to the local-FTS mirror, notify in UI |
| `Generalizable = false` detected after a write | Pull-sync ignores such records; the record stays in Notion for manual review |
| Sensitive data slipped past scrubbing | Manual deletion in Notion → the next local pull deletes it (404 on retrieve) |
| Content >180 KB | Property: `[see page body]` + rich_text chunks with a trimmed version; full text in child-blocks |
| Title >2000 chars | Truncate to 200 chars + "…", full version in Description/Content |

## 9. Out of scope for v1

- Relation databases for Tags/Stack — wait for the signal that 100 options is near.
- Version-history entries — Notion UI shows page history; an API-level rewrite isn't needed yet.
- Cross-entity links (patterns → gotchas) — separate relation property, planned for v2.
- Attachments (images, diagrams) — a separate task; requires the upload API.
- Shared access (team) — single-user in v1.
- Full-text search via Notion API — we only use query + a local FTS5 mirror for search.

## 10. Relation to the local schema

The local SQLite mirror (`~/.tausik-brain/brain.db`, task `brain-local-schema`) mirrors these 4 tables 1:1:

- Each Notion column → an SQLite column with a compatible type (rich_text → TEXT, multi_select → JSON TEXT array, date → TEXT ISO, number → INTEGER/REAL, checkbox → INTEGER 0/1, select → TEXT).
- Primary key — `notion_page_id` (UUID string from Notion).
- `last_edited_time TEXT` is indexed for delta-pull.
- For each table — an FTS5 virtual table with `content=<table>`, `content_rowid=<pk>` and fields `Name`/textual properties.
- Table `sync_state` (PK=category) holds `last_pull_at` and `last_error`.

Local schema details — see [shared-brain.md](shared-brain.md) and [architecture.md](architecture.md).
