---
slug: fts5-query-where-alias-match-aliased-fts-table-in-match
title: "FTS5 query WHERE <alias> MATCH ? (aliased fts table in MATCH)"
type: dead_end
tags: []
task: null
edges: []
---

Approach: FTS5 query WHERE <alias> MATCH ? (aliased fts table in MATCH)
Reason: Raises 'no such column: <alias>' — FTS5 MATCH needs the bare virtual-table name (WHERE fts_snippets MATCH ?), even when the table is aliased for the JOIN/rank. Use the table name in MATCH, alias only for f.rank.
