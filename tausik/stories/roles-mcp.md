---
slug: roles-mcp
title: "Full CRUD MCP for roles (hybrid SQLite + markdown storage)"
status: done
epic: v13-mcp-and-discipline
---

Roles get first-class storage: row in SQLite `roles` table (slug, title, created_at) + markdown profile in agents/roles/{slug}.md. CLI parity (tausik role list/show/create/update/delete) + MCP wrappers. Migration of existing free-text role usages.
