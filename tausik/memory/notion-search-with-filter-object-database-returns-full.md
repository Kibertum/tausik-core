---
slug: notion-search-with-filter-object-database-returns-full
title: "Notion search() with filter object=database returns full property schema in-line"
type: pattern
tags:
  - api
  - brain
  - discovery
  - notion
task: v14b-defect-brain-enable-no-discovery
edges: []
---

POST /v1/search with body filter={property:object,value:database} returns each result with the COMPLETE database object — id, title, parent, archived, AND properties (each property dict carries its name, id, type and the type-specific config). No follow-up databases_retrieve() call is needed for schema inspection. brain_discovery.find_workspace_brain_databases exploits this: schema-fallback validates per-category required props from the same response that listed the database, paying zero extra API calls. Useful pattern for any Notion integration that needs to "find existing dbs by structure" — search-then-filter is cheaper than search-then-retrieve-each.
