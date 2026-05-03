**English** | [Русский](../ru/memory-merge-guidelines.md)

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

## See also

- [Shared Brain](shared-brain.md) — setup, sync, privacy model.
- [Brain artifact taxonomy](brain-artifact-taxonomy.md) — draft/publish, `risk_blocked`, `confirm_high_risk`.
- [Brain DB schema](brain-db-schema.md) — scrubbing responsibilities.
- [CLI — Knowledge](cli.md#knowledge) — `memory add`, `memory link`, search.
