---
slug: v15-snippet-ast-detect
title: "AST-based snippet clone detection — tausik snippet detect"
status: done
epic: v15-snippet-system
story: v15-snippet-foundation
complexity: complex
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/snippet_detect.py (new engine), scripts/project_cli_snippet.py (new CLI handler), scripts/project_parser.py (+snippet subparser), scripts/project.py (+dispatch), tests/test_snippet_detect.py (new). Bootstrap sync after."
scope_exclude: "snippet_storage.py (frozen API), backend_schema_snippets.py (schema frozen), brain_snippet_detect.py (classifier, separate), no new MCP tool."
relevant_files:
  - "scripts/snippet_detect.py"
  - "scripts/project_cli_snippet.py"
  - "tests/test_snippet_detect.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T23:28:09Z"
---

## Goal

Реальная детекция дубликатов кода. CLI команда `tausik snippet detect [--path X] [--threshold N]` — обходит RAG-индекс (mcp__codebase-rag__search_code), собирает chunk-и, парсит AST через ast.parse (Python first, потом языко-агностичный fallback на токены), нормализует (имена переменных → placeholder), считает hash subtree. Кластеризует по hash, threshold для размера (≥10 line / ≥3 statements). Пишет кластеры в snippets table (созданную в v15-snippet-table). Tests: AST normalization, cluster detection, false-positive guards (boilerplate exclusion). Это (3/5) v15 — самая complex часть.

## Acceptance Criteria

1. `tausik snippet detect [--path X] [--threshold N]` walks .py files under path, AST-parses, normalizes identifiers/constants to placeholders, hashes subtrees, clusters by hash, writes clusters (≥2 members) into snippets table (taxonomy_kind='clone', fts_rank=cluster_size). 2. Type-2 clone detected: two functions identical modulo variable names cluster together. 3. NEGATIVE: structurally different code does NOT cluster; boilerplate (docstring/pass-only, tiny blocks below threshold) excluded — no false-positive cluster. 4. Idempotent: re-running detect on same source does not create duplicate snippet rows (dedup on hash). 5. Unparseable file is skipped (finding, not crash). 6. Tests cover: normalization equivalence, cluster detection, false-positive guards, idempotency, syntax-error skip. All gates green.

## Plan

## Rollback

git revert the feature commit; new files are additive (snippet_detect.py, project_cli_snippet.py, test) and the dispatch/parser entries removed by the revert. No schema migration involved, snippets table already exists from v37.

## Journal

- 2026-06-13T23:13:20Z [implementation] — Implemented: snippet_detect.py (engine: iter_python_files, normalized signature with type-2 placeholders + CONST, candidate=def/class ≥min_lines & ≥min_stmts significant, clusters ≥2 keyed by sha256), project_cli_snippet.py (cmd_snippet → add_snippet, taxonomy_kind=clone, fts_rank=size), parser+dispatch wired, tests/test_snippet_detect.py (10 tests: rename/literal equivalence, structural distinctness, cross-file+intra-file detection, false-positive guards, syntax-skip, noise-dir prune, idempotent persistence).
- 2026-06-13T23:24:54Z [implementation] — tausik-reviewer triage (1 CRIT, 5 HIGH): FIXED CRIT (Global/Nonlocal names list collapse → removed from _NAME_FIELDS, _dump recurses preserving arity; regression test added), HIGH#3 (written-counter lied on re-run → before/after count_snippets delta), HIGH#5/#6 (boilerplate guard: docstring exclusion now leading-only + recursive significance so stub-method classes score 0; regression tests added), HIGH#2 (--threshold 0 no longer coerced to 10). MEDIUM (non-deterministic representative code → occurrences sorted, posix-normalized paths, deterministic cluster sort). ACCEPTED-as-design HIGH#4 (ast.walk emits nested candidates — detecting nested clones is intentional). Out-of-scope: assert in snippet_storage (frozen API). 17 unit tests green, ruff+mypy clean, all files <400 lines. Added CLI doc to docs/ru/cli.md.
- 2026-06-13T23:27:44Z [implementation] — QG-2 verification-checklist: scope=snippet_detect.py+project_cli_snippet.py+parser/dispatch+tests (no schema/MCP touched, snippet_storage frozen). tests=tests/test_snippet_detect.py 17 cases (normalization equiv, type-2 positive cross/intra-file, structural-distinct negative, boilerplate+stub-class+short-block guards, global-cardinality regression, non-leading-string, syntax-skip, noise-dir prune, idempotent persist, CLI honest-write-count). security=pure stdlib ast+hashlib, no network/subprocess/user-SQL; reads files read-only. edge-cases=syntax-error file → skipped(finding not crash), get_source_segment None → skip, --threshold 0 respected, empty path default '.'. Full suite 3890 passed (1 unrelated pre-existing CLAUDE.md v1.0-draft drift, separate defect).
- 2026-06-13T23:28:08Z [implementation] — AC verified: 1.✓ tausik snippet detect walks/parses/normalizes/clusters→snippets (smoke: tests dir → 43 clusters written, taxonomy_kind=clone). 2.✓ type-2 rename clone clusters: test_detects_rename_clone_across_files + test_signature_equal_under_rename. 3.✓ NEGATIVE structural-distinct no cluster (test_distinct_code_does_not_cluster) + boilerplate guards (test_stub_method_class_not_clustered, test_boilerplate_below_stmt_threshold_excluded, test_short_block). 4.✓ idempotent (test_persisted_clusters_dedup_on_rerun, test_cmd_snippet_reports_honest_write_count: re-run wrote 0 new). 5.✓ syntax-error skipped (test_syntax_error_file_skipped, scanned=2 skipped=broken.py). 6.✓ tests cover all; verify run #748 pytest PASS.
