---
slug: ast-clone-detector-design-tausik-snippet-detect
title: "AST clone detector design (tausik snippet detect)"
type: pattern
tags: []
task: v15-snippet-ast-detect
edges: []
---

Engine in snippet_detect.py (pure stdlib ast+hashlib, no DB/CLI). Pipeline: iter_python_files (prune _SKIP_DIRS) → ast.parse (SyntaxError/OSError → result.skipped, finding not crash) → _iter_candidates (def/class with line_span>=min_lines AND _significant_count>=min_stmts) → normalized signature (_dump: scalar idents+literals→placeholders, drop lineno/ctx/type_comment) → sha256 → group, clusters>=2 members. Boilerplate guard: _significant_count excludes leading-docstring-only + bare pass + stub def/class (recursive significance) so interface-shaped classes score 0. Idempotent: snippet_storage.add_snippet dedups on hash. CLI persists taxonomy_kind='clone', fts_rank=cluster_size; honest write-count via before/after count_snippets delta (INSERT OR IGNORE makes per-loop counter lie on re-run).
