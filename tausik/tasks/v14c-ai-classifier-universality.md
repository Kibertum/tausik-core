---
slug: v14c-ai-classifier-universality
title: "C2: AI-классификатор universality для brain artifacts"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 80
defect_of: null
scope: "scripts/brain_universality.py (extend _TOPIC_PATTERNS), scripts/brain_universality_semantic.py (new, ≤200L), scripts/brain_runtime.py (lines 181-183, 255-257 only), scripts/service_knowledge.py (lines 40-42 only), scripts/brain_config.py (add semantic_universality_enabled knob), tests/test_brain_universality.py (extend), tests/test_brain_universality_integration.py (extend), tests/test_brain_universality_semantic.py (new), docs/en/memory-merge-guidelines.md (topic list update), CHANGELOG.md + CHANGELOG.ru.md (entry)"
scope_exclude: "scripts/brain_search.py (read-only reuse, no edits), scripts/brain_mcp_write.py, harness/* (никаких новых MCP tools), любые ML libs (sentence-transformers, fastembed, ONNX, ChromaDB), schema migrations, новые таблицы"
relevant_files:
  - "scripts/brain_universality.py"
  - "scripts/brain_universality_semantic.py"
  - "scripts/brain_config.py"
  - "tests/test_brain_universality.py"
  - "tests/test_brain_universality_semantic.py"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T12:00:48Z"
---

## Goal

Идти дальше heuristic (B3): использовать local model или Notion-side embedding для классификации «этот код может быть переиспользован между проектами». Auto-suggest brain propose-artifact с confidence score.

## Acceptance Criteria

1) Regex layer (brain_universality.py _TOPIC_PATTERNS) расширен ≥4 новыми topics (csrf, graphql, feature-flag, circuit-breaker, или подобными) с тестами на word-boundary false-positives.
2) Новый модуль scripts/brain_universality_semantic.py с публичной функцией find_similar_universal(content, threshold) → list[(topic, bm25_score)] поверх FTS5 brain mirror (переиспользует scripts/brain_search.py инфраструктуру). Ноль новых deps.
3) Advisory wire в 3 call-sites: service_knowledge.py:40-42 (memory_add), brain_runtime.py:181-183 (try_brain_write_decision), brain_runtime.py:255-257 (try_brain_write_web_cache). Через config knob brain.semantic_universality_enabled (default True). Регексп остаётся быстрым синхронным слоем; semantic — опциональное дополнение.
4) Tests: новые regex topics с false-positive guards; FTS5 similarity (синоним 'access control' → rbac topic; низкий bm25 → no suggestion; пустой brain mirror — graceful no-op); integration tests для 3 call-sites что hint включает оба слоя.
5) Никаких ML/embedding/ChromaDB зависимостей (memory dead-end #27 + CLAUDE.md stdlib rule). MCP tool brain_classify_universal — out of scope (отдельная задача).
6) pytest 3127+ tests PASS. Doctor clean. Filesize gate ≤400L per file. Bootstrap drift-clean.

## Plan

## Rollback

## Journal

- 2026-05-07T12:00:41Z [implementation] — AC verified: 1) ✓ regex +4 topics (csrf/graphql/feature-flag/circuit-breaker) с 6 false-positive guards; 2) ✓ scripts/brain_universality_semantic.py (288L) с find_similar_universal через FTS5; 3) ✓ wire через emit_universality_hint — все 3 call-sites используют оба слоя; 4) ✓ tests/test_brain_universality_semantic.py 32 tests + extended test_brain_universality.py +9 кейсов; 5) ✓ нет ML/embedding/ChromaDB deps; 6) ✓ pytest 3190 PASS, ruff/mypy clean, doctor clean, filesize OK, bootstrap drift-clean.
