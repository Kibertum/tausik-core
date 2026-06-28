**English** | [Русский](/ru/docs/memory-merge-guidelines)

# Memory: merge vs new entry

How to keep **local** project memory (`.tausik/tausik.db`) and optional **Shared Brain** (Notion) free of noise. This guide is about *editorial* choice. It **complements**, not replaces:

- **`scripts/brain_classifier.py`** (`classify()`) — routes content to **local** vs **brain** using markers and blocklist.
- **`brain_scrubbing`** (pre–Notion write) — **blocks** unsafe content regardless of your merge decision (see *Scrubbing wins* below).

## Decision table

| Situation | Prefer |
|-----------|--------|
| Same topic, adding nuance, typo fix, or tightening wording | **Merge**: update the existing memory row (single source of truth). |
| Same *symptom*, different **root cause** | **New** entry; optionally relate rows with [`memory link`](cli.md#knowledge) / graph tools so searches surface both. |
| Verbatim duplicate (copy-paste) | **Delete** the redundant row after confirming it adds nothing. |
| Insight tied to a closed task but potentially reusable | Capture locally first; generalize wording before any brain publish (`move_to_brain`, MCP store, or `brain publish`). |

If unsure, run **`tausik search`** / **`memory_search`** (and brain search if enabled) before writing.

## Alignment with the classifier

`classify(content, category)` only answers **where** a write may go (`local` vs `brain`). It does **not** deduplicate or merge rows. Conservative signals (paths, long slugs, blocklisted names) → **local** — you should still apply merge-vs-new discipline **inside** local memory so FTS stays usable.

Categories used by the classifier for patterns/gotchas/web_cache line up with **[Shared Brain](shared-brain.md)** routing; **task-linked** decisions stay local by policy (`service_knowledge.decide` when `task_slug` is set).

## Negative exception: scrubbing overrides merge intent

You may merge two notes into one “clean” summary for the brain — but if the merged body still contains **absolute paths**, **emails**, **private URLs**, or **blocklisted project names**, the scrubbing layer refuses the Notion write (`scrub_blocked`). **Privacy rules win:** rewrite to generic language first, then publish. This does *not* contradict merge guidance; it bounds **where** consolidated text may land.

## Short examples

1. **Merge:** Two `pattern` rows both describe “pytest `tmp_path` for SQLite” — keep one title, combine bullets, delete the weaker row.
2. **New:** One note “flakey test” caused by async timing; another “flakey test” caused by shared global state — two gotchas, cross-link if helpful.
3. **Scrubber:** Merging notes accidentally pulls in `D:\Work\…` — scrub blocks brain write until paths are removed or redacted.

## Hygiene CLI (B9, v1.4 polish)

When the project has been running long enough that memory FTS noise hides relevant rows, two read-safe hygiene commands help — both are scoped to the **local** `.tausik/tausik.db` and never touch the brain.

```bash
# Soft-archive: hide rows older than the given duration from `memory list/search`.
# Dry-run by default; --confirm stamps `archived_at` (idempotent).
tausik memory archive --before 90d            # preview
tausik memory archive --before 90d --confirm  # apply

# Find near-duplicate pairs above a similarity threshold (read-only).
tausik memory dedupe                  # default threshold 0.85
tausik memory dedupe --threshold 0.9 --limit 500
```

Duration grammar: `<int><unit>` with `unit ∈ d|w|m|y` (`m=30 days`, `y=365 days`). Anything else errors.

`memory list` and `memory search` filter `archived_at IS NOT NULL` by default; pass `--include-archived` (CLI) or `include_archived: true` (MCP) to opt back in. Archived rows still answer `memory show <id>` so you can recover content before reusing it.

Dedupe uses `SequenceMatcher.ratio()` over `title || content` and only considers rows of the **same type** — a `pattern` will never be suggested as a merge candidate for a `gotcha`. The command is suggest-only; consolidate manually with `memory show` + `memory delete`, or rewrite one row to subsume the other.

## Universality heuristic (B3, v1.4 polish)

When you write a memory or decision whose body mentions a well-known cross-project topic, TAUSIK prints a one-line stderr hint:

```
Universal pattern(s) detected: jwt, retry — consider promoting via `brain_draft_artifact` (or skip with `confirm: cross-project`).
```

The hint is **advisory only** — it never blocks the write, never raises, and is silent when nothing matches. Detection runs after a successful write in `service_knowledge.memory_add` and in `brain_runtime.try_brain_write_decision` / `try_brain_write_web_cache` success paths.

Topics covered (regex/keyword, case-insensitive, word-boundary aware):

- `rbac` — RBAC, role-based access
- `jwt` — JWT, JSON Web Tokens
- `oauth` — OAuth / OAuth2
- `rate-limit` — rate-limit(ed/ing/er), throttle
- `pagination` — paginate, cursor pagination
- `retry` — retry, retries, exponential backoff
- `idempotency` — idempotent, idempotency-key
- `webhook` — webhook(s)
- `csrf` — CSRF, XSRF, Cross-Site Request Forgery
- `graphql` — GraphQL, gql query/mutation/subscription/schema/resolver
- `feature-flag` — feature flag, feature toggle
- `circuit-breaker` — circuit breaker, bulkhead pattern

Word-boundary guards prevent false positives (e.g. `aggregate` does not trigger `rate-limit`). To extend, edit `_TOPIC_PATTERNS` in [scripts/brain_universality.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_universality.py).

## Semantic universality layer (C2, v1.4 polish)

The regex layer above is fast but blind to **synonyms** ("access control" → `rbac`, "token bucket" → `rate-limit`). The semantic layer fixes this without adding ML dependencies: it queries the local brain mirror via FTS5 and surfaces topics from existing brain entries whose tags match a known universal topic AND whose bm25 score is strong against your new content.

```
Semantic universality hint: rbac — new content resembles existing brain entries on these topics (consider promoting via `brain_draft_artifact`).
```

How it works:

1. After the regex layer runs, the new content is tokenized (lowercase, stopwords dropped, length ≥ 4).
2. Up to 8 distinctive tokens are searched against the local brain mirror (FTS5 over `brain_decisions` / `brain_patterns` / `brain_gotchas` / `brain_web_cache`).
3. Each hit's `tags` are intersected with `KNOWN_UNIVERSAL_TOPICS`. Topics with bm25 score ≤ threshold (default 8.0; lower = stronger match) are emitted.
4. Topics already caught by the regex layer are **deduped** so you only see new signal.

Activation gate (`scripts/brain_config.py` defaults):

- `brain.enabled` is `true`
- `brain.semantic_universality_enabled` is `true` (default; set `false` to disable semantic layer)
- The brain mirror file exists on disk

Implementation: [scripts/brain_universality_semantic.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_universality_semantic.py). Pure stdlib; reuses [scripts/brain_search.py](https://github.com/Kibertum/tausik-core/blob/main/scripts/brain_search.py) FTS5 infrastructure. Never raises, never blocks. Empty mirror → silent no-op. Synonym discovery improves as you promote more entries to the brain.

## See also

- [Shared Brain](shared-brain.md) — setup, sync, privacy model.
- [Brain artifact taxonomy](brain-artifact-taxonomy.md) — draft/publish, `risk_blocked`, `confirm_high_risk`.
- [Brain DB schema](brain-db-schema.md) — scrubbing responsibilities.
- [CLI — Knowledge](cli.md#knowledge) — `memory add`, `memory link`, search.
