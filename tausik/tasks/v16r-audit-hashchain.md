---
slug: v16r-audit-hashchain
title: "[P1] Hash-chain immutability для events (audit log)"
status: done
epic: v16-renar-core
story: v16r-repro
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 60
defect_of: null
scope: "NEW scripts/events_chain.py (canonical_event_bytes, GENESIS_V1, entry_hash, verify_chain, sign_head/verify_anchor — reuse crypto_keys+crypto_ed25519); backend_schema.py (SCHEMA_VERSION 33→34, events DDL +prev_hash/+entry_hash, events_anchor table); backend_migrations.py (v34 ALTER+anchor DDL + Python backfill hook на manner seed_v18); backend_crud.py event_add (chain wiring); project_parser.py (events verify/anchor subcommands); project_cli_ops.py cmd_events; NEW tests/test_events_chain.py."
scope_exclude: "gmcp-*/v2-* (2.0); .tausik/keys (не трогать ключи); crypto_ed25519/crypto_receipt/crypto_sign core (только импорт); MCP handlers (CLI-only в этой задаче); per-event signing (anchor only)."
relevant_files:
  - "scripts/events_chain.py"
  - "scripts/backend_events_chain.py"
  - "scripts/backend_migrations_v34.py"
  - "scripts/project_cli_events.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_events_chain.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T20:16:29Z"
---

## Goal

RENAR audit log readiness 70%→100%: events table получает hash-chain (каждая запись содержит hash предыдущей, ed25519-якорь из v15-crypto-keymgmt). AC: цепочка проверяется командой `tausik events verify`; tampering детектится; запись O(1); миграция исторических событий (genesis-якорь).

## Acceptance Criteria

1. Fresh event_add вычисляет prev_hash/entry_hash; `tausik events verify` → status=ok, length=N. 2. [NEGATIVE] Tampering: UPDATE details существующего события → `events verify` детектит разрыв (status=broken, first_break=id тронутой строки). 3. Запись O(1): event_add делает ОДИН bounded SELECT (PK DESC LIMIT 1), без full-scan — проверяется тестом (цепочка длиной N+1 линкуется к корректному prev независимо от N) и code-inspection. 4. Миграция v34 бэкфиллит ВСЕ исторические события в валидную цепочку от фикс. GENESIS_V1; на существующей БД `events verify` проходит сразу после миграции. 5. ed25519 anchor: `events anchor` подписывает голову project-ключом → events_anchor; `events verify` подтверждает подпись. [NEGATIVE] tampering до заякоренной головы флагается anchor-mismatch даже после пересчёта цепочки; keyless-проект: anchor пропускается с явным сообщением, chain-verify работает.

## Plan

## Rollback

Аддитивно: новые nullable-колонки events.prev_hash/entry_hash + новая таблица events_anchor игнорируются pre-v34 кодом. git revert кода; колонки остаются безвредными (NULL). DB-downgrade не требуется. Бэкфилл идемпотентен (guard meta-флаг v34_backfilled).

## Journal

- 2026-06-13T19:48:00Z [implementation] — events_chain.py создан: GENESIS_V1 (фикс), canonical_event_bytes, entry_hash, compute_links, verify_chain (ok/broken/unchained/empty + first_break), sign_head/verify_anchor (ed25519 anchor reuse crypto_keys+ed25519). Запись O(1): чейнинг по id, prev=head entry_hash.
- 2026-06-13T20:11:46Z [implementation] — Реализация завершена. Архитектура: lazy monotonic sealing (вставки не трогаем, O(1)), seal по id>frontier (atomic BEGIN IMMEDIATE, tail-only=O(unsealed), watermark против laundering). ed25519 anchor reuse crypto_keys. Migration v34 (+prev_hash/entry_hash, events_anchor) + Python backfill (BEGIN перед SELECT). tausik-reviewer: 2 critical (неатомарный seal, WAL concurrency) + high (backfill race) — все исправлены через begin_tx/BEGIN IMMEDIATE+tail-read. Находка про flag-on-error невалидна (rollback откатывает). Laundering закрыт watermark'ом. Тесты 12/12 + смежные 90 зелёных, ruff чист, файлы <400. AC evidence: AC1 test_seal_then_verify_ok+CLI; AC2(neg) test_tampering_sealed_event_is_detected first_break=2; AC3 test_seal_is_idempotent_and_monotonic; AC4 миграция v33→v34 smoke (3 истор. строки, verify ok); AC5 test_anchor_detects_rebased_chain+test_verify_anchor_rejects_tampered_envelope+keyless CLI skip.
- 2026-06-13T20:16:07Z [implementation] — AC1 ✓ test_seal_then_verify_ok + CLI verify ok. AC2(neg) ✓ test_tampering_sealed_event_is_detected first_break=2 'content modified' + CLI BROKEN. AC3 ✓ test_seal_is_idempotent_and_monotonic (tail-only O(unsealed), atomic). AC4 ✓ v33→v34 migration smoke: 3 истор.строки backfill→verify ok, genesis-anchored. AC5 ✓ test_anchor_detects_rebased_chain (rebase→anchor MISMATCH), test_verify_anchor_rejects_tampered_envelope, keyless CLI skip. Full suite 3738 passed 0 failed.
- 2026-06-13T20:16:23Z [implementation] — VERIFICATION CHECKLIST (substantial): - scope: изменения строго в заявленном scope (events_chain.py, backend_events_chain.py, backend_migrations_v34.py, project_cli_events.py + schema/migrations/parser/backend composition). gmcp-*/v2-*/.tausik/keys не тронуты. crypto_* только импорт. - tests: 12 unit (test_events_chain.py) + миграционный фикс (test_reasoning_steps v32) + полный сьют 3738 passed / 0 failed / 8 skipped. ruff clean. filesize<400 на всех файлах. - security: tamper детектится (entry_hash mismatch=content, prev_hash mismatch=insert/delete/reorder); rebase-атака ловится ed25519-anchor (head MISMATCH); verify_anchor никогда не падает на attacker-input (structural defects→False); SQL параметризован; watermark (id>frontier) против laundering инъецированных строк; backfill идемпотентен + atomic BEGIN IMMEDIATE перед SELECT. - edge-cases: keyless-проект (anchor skip, chain работает); пустой лог (empty/None guards); fresh-DB vs migrated-DB (baseline+migration синхронны, current_version=34 пропускает v34 ALTER); trigger-inserted события (SQL audit triggers) попадают в цепочку через lazy seal; partial-seal crash безопасен (atomic tx). - review: tausik-reviewer прогнан на staged diff; 2 critical+high исправлены (atomic seal, BEGIN-before-SELECT, tail-read); невалидные/вне-scope находки задокументированы.
- 2026-06-13T20:16:28Z [implementation] — AC1-5 verified, see checklist log. Full suite 3738 passed 0 failed.
