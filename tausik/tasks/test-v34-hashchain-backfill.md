---
slug: test-v34-hashchain-backfill
title: "Test-хардненинг: покрыть maybe_backfill_v34 (необратимый hash-chain seal)"
status: done
epic: null
story: null
complexity: simple
role: qa
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "Новый tests/test_v34_hashchain_backfill.py. НЕ трогать: scripts/backend_migrations_v34.py (только покрываем тестами, не меняем)."
scope_exclude: "scripts/* (это test-only задача)"
relevant_files:
  - "tests/test_v34_hashchain_backfill.py"
  - "scripts/backend_migrations_v34.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T08:56:05Z"
---

## Goal

Ревью (test-агент) ранжировал v34 event-hash-chain backfill как CRITICAL непокрытую дыру: maybe_backfill_v34 — одноразовая необратимая операция (SHA-256 seal каждого event-row, ставит meta-флаг v34_backfilled), 0 тестов. Регрессия молча портит audit-chain при апгрейде. Покрыть тестами: корректность цепочки от GENESIS_V1, идемпотентность (флаг), no-op при отсутствии колонок, mixed sealed/unsealed.

## Acceptance Criteria

1. Тест строит минимальную схему (events+meta), вставляет unsealed events, запускает maybe_backfill_v34, проверяет: цепочка entry_hash/prev_hash совпадает с events_chain.entry_hash от GENESIS_V1, возвращён правильный count. 2. Идемпотентность: 2-й запуск возвращает 0 и не меняет хэши; meta-флаг v34_backfilled установлен. 3. No-op при предустановленном флаге (returns 0). 4. Negative/boundary: таблица events без колонок entry_hash/prev_hash → returns 0, не падает. 5. Mixed: предзапечатанный первый row → prev для следующего берётся из stored entry_hash, только unsealed запечатываются. 6. Пустая таблица events → returns 0, флаг ставится. 7. pytest зелёный, ruff чист.

## Plan

## Rollback

## Journal

- 2026-06-14T08:55:55Z [implementation] — Wrote tests/test_v34_hashchain_backfill.py — 6 tests, in-memory minimal schema (events+meta). Setup gotcha: maybe_backfill_v34 does BEGIN IMMEDIATE, so seeded rows must be committed first (mirrors production where prior-session events are committed before migration runs). 6 passed, ruff clean.
- 2026-06-14T08:56:05Z [implementation] — AC-1: ✓ chain from GENESIS_V1, count==3, stored links == events_chain.compute_links recomputation, verify_chain status=='ok' — tested via tests/test_v34_hashchain_backfill.py::test_seals_unsealed_chain_from_genesis. AC-2: ✓ 2nd run returns 0, hashes unchanged, meta flag=='1' — test_second_run_is_noop_and_sets_flag. AC-3: ✓ preset flag → returns 0, rows stay unsealed — test_noop_when_flag_preset_leaves_events_unsealed. AC-4 (negative): ✓ no chain columns → returns 0, no raise, flag NOT set — test_noop_without_chain_columns_does_not_raise. AC-5: ✓ pre-sealed first row → unsealed tail chains off STORED hash not GENESIS, only 2 sealed — test_mixed_uses_stored_hash_as_prev_for_unsealed_tail. AC-6: ✓ empty events → returns 0, flag set — test_empty_events_table_sets_flag_returns_zero. AC-7: ✓ 6 passed, ruff clean. Domain: verify_chain confirms the sealed chain is cryptographically valid end-to-end, not just that the function returns a count.
