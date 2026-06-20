# Shared Brain — artifact taxonomy (v1.4)

This note fixes vocabulary for upcoming **snippet cards** and MCP publish flows without yet adding a fifth Notion database.

## Definitions

| Term | Meaning | Storage in v1 |
|------|---------|---------------|
| **Artifact** | Logical knowledge unit intended to travel across repos (concept + evidence). May surface as several physical rows over time. | Not a standalone DB row; classify via `artifact_taxonomy_kind` on write. |
| **Pattern** | Reusable recipe / idiomatic approach (**how to do X**). | Notion **`patterns`** table (existing). |
| **Snippet** | Smallest reusable excerpt (code fragment, YAML stanza, short command recipe). Narrower than a full pattern narrative. | v1: same **`patterns`** table; mark intent with `artifact_taxonomy_kind: "snippet"` (optional). A dedicated snippets DB is backlog. |

**Gotchas** remain **anti-patterns** (**how NOT to do X**) in the **`gotchas`** table. Taxonomy distinguishes *shape* (`pattern` vs `snippet` vs umbrella `artifact`); semantic “gotcha” is still the DB category.

## Minimal JSON card (logical)

Used for specs, MCP clients, and future validation — not persisted verbatim in Notion v1:

```json
{
  "scope": "testing",
  "artifact_taxonomy_kind": "snippet",
  "name": "pytest caplog assert",
  "description": "Capture logs in tests via caplog.records",
  "example": "with caplog.at_level(logging.ERROR):\n    run()\nassert \"boom\" in caplog.text",
  "tags": ["pytest", "logging"],
  "stack": ["python"]
}
```

## External repository URL (optional)

Optional **`external_repo_url`** on **`brain_store_pattern`**, **`brain_store_gotcha`**, and **`brain_draft_artifact`**: an `http(s)` link to the canonical repository, submodule documentation, or similar.

- **Security / opt-in:** By default TAUSIK performs a **short outbound HTTP GET** (limited bytes read) to verify the URL responds (reject dead links and obvious HTTP errors such as **404** / **410**). This is **egress from the machine running MCP** — only pass URLs you intend to fetch. Schemes other than **`http`/`https`** are rejected.
- **Offline / CI:** Set **`brain.skip_external_repo_url_reachability_check`: `true`** in `.tausik/config.json` to validate only URL syntax (scheme + host), with **no network**.
- **Notion v1:** Like **`scope`**, this field is validated and **stripped** before `pages.create` — there is no dedicated Notion column yet.

## MCP field

- Tools: **`brain_store_pattern`**, **`brain_store_gotcha`** accept optional **`artifact_taxonomy_kind`** (`artifact` \| `pattern` \| `snippet`).
- Tools accept optional **`scope`** (logical only): empty string is rejected (**`card_schema_blocked`**); set **`brain.require_artifact_scope`: `true`** to require `scope` on every pattern/gotcha write.
- Optional logical fields (**`artifact_taxonomy_kind`**, **`scope`**) are **not** written to Notion properties in v1; they are validated and stripped server-side before `pages.create`.
- **Strict mode:** set **`brain.require_artifact_taxonomy_kind`: `true`** in `.tausik/config.json`. Then pattern/gotcha writes **must** include a valid taxonomy kind; omission or invalid values return **`taxonomy_blocked`**.

JSON Schema (draft 2020-12): [`harness/schemas/brain-artifact-card.schema.json`](../../harness/schemas/brain-artifact-card.schema.json).

**Publish flow (v1.4):** MCP tool **`brain_draft_artifact`** (no Notion I/O) runs the same gates as store plus a **classifier risk** level. If the text looks project-specific (path markers, blocklist, etc.), `brain_store_pattern` / `brain_store_gotcha` return **`risk_blocked`** unless you pass **`confirm_high_risk: true`** (human gate). CLI: `tausik brain draft` / `tausik brain publish` (JSON via `--json` or `--file`). A successful publish logs a **write** row in `brain_events` (`artifact_publish:...`).

See also [shared-brain.md](shared-brain.md) and [brain-db-schema.md](brain-db-schema.md).
