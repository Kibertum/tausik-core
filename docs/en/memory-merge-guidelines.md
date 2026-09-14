**English** | [Русский](../ru/memory-merge-guidelines.md)

# Memory: merge vs new entry

How to keep **local** project memory (`.tausik/tausik.db`) and the **shared local store** (`~/.tausik-knowledge`) free of noise. This guide is about *editorial* choice. It **complements**, not replaces:

- **`publication_boundary`** — the one place shared-store content passes on its way off the machine (`knowledge export --redacted`): absolute paths, e-mails, private URLs and project names become typed placeholders regardless of your merge decision (see *The boundary wins* below).

## Decision table

| Situation | Prefer |
|-----------|--------|
| Same topic, adding nuance, typo fix, or tightening wording | **Merge**: update the existing memory row (single source of truth). |
| Same *symptom*, different **root cause** | **New** entry; optionally relate rows with [`memory link`](cli.md#knowledge) / graph tools so searches surface both. |
| Verbatim duplicate (copy-paste) | **Delete** the redundant row after confirming it adds nothing. |
| Insight tied to a closed task but potentially reusable | Capture locally first; generalize wording before `memory add --global`, and again before a redacted export. |

If unsure, run **`tausik search`** / **`memory_search`** (the shared store is folded into the results) before writing.

## What comes back on its own: relevance, on top of recency

Two things pull memory back into the window without a search. The **recency tail** in CLAUDE.md (newest decisions, conventions, dead ends, context) is the core and is always there. On **`task start`**, on resume (`task start` of an already active task) and in **`task show`**, a `Relevant memory (N)` block is added on top of it: one FTS5 query built from the task's own declaration — title and slug words, the stems and path segments of `relevant_files` / `scope_paths`, its story, the tags of decisions linked to it — with OR semantics, ranked by bm25 and then by *where* a term matched (a tag counts 3, a title 2, the body 1). Up to eight live rows, each with the terms that matched it; a superseded row yields to its replacement.

An empty answer is **named**, never silent: `Relevant memory: none matched <terms>` lists what was tried, so silence cannot be read as "no memory on this topic". A failing search degrades to the same kind of line and never stops `task start`. Measured on session #189: the task whose files name the scoped registry now gets #425 (the retired five-names rule) second; the process gotcha #428 (a receipt is not a commit) reaches the candidate set through `gate` but competes with dozens of gate-tagged rows in the live store — that kind of row is the recency tail's job.

## Alignment with the publication boundary

The boundary answers only **what may leave** and **in what form**. It does **not** choose a destination, and it does **not** deduplicate or merge rows — you should still apply merge-vs-new discipline **inside** local memory so FTS stays usable.

Nothing routes itself. **You** pick the destination: the project by default, the local shared store with `--global` (decision #221). Recording a decision publishes it nowhere — the local copy is unconditional (`service_decide.record`) — and there is no outward transport since 1.9 (decision #358).

## Negative exception: the boundary overrides merge intent

You may merge two notes into one “clean” summary for the shared store — but if the merged body still contains **absolute paths**, **emails**, **private URLs**, or **project names**, a redacted export replaces them with `[REDACTED:…]` placeholders. **Privacy rules win:** rewrite to generic language first if the text is meant to travel. This does *not* contradict merge guidance; it bounds **what** consolidated text may carry off the machine.

## Short examples

1. **Merge:** Two `pattern` rows both describe “pytest `tmp_path` for SQLite” — keep one title, combine bullets, delete the weaker row.
2. **New:** One note “flakey test” caused by async timing; another “flakey test” caused by shared global state — two gotchas, cross-link if helpful.
3. **Boundary:** Merging notes accidentally pulls in an absolute path — a redacted export turns it into `[REDACTED:path]` until it is removed.

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
Universal pattern(s) detected: jwt, retry — consider `memory add --global` (or skip with `confirm: cross-project`).
```

The hint is **advisory only** — it never blocks the write, never raises, and is silent when nothing matches. Detection runs after a successful write in `service_knowledge.memory_add`. It is the regex layer alone: the FTS layer that used to follow it searched the Notion mirror and left with the transport.

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

## See also

- [CLI — Knowledge](cli.md#knowledge) — `memory add`, `memory link`, search.
