---
slug: audit-hash-chain-lazy-monotonic-sealing-ed25519-head-anchor
task: v16r-audit-hashchain
date: "2026-06-13"
edges: []
---

## Decision

Audit hash-chain: lazy monotonic sealing + ed25519 head-anchor вместо per-event подписи

## Rationale

События пишутся и Python event_add, и SQL audit-триггерами (нет sha256/JCS в SQLite) — чейнинг на insert невозможен. Решение: вставки не трогаем (O(1)), seal по id>frontier on-demand (atomic, tail-only, watermark против laundering). ed25519 подписывает только голову (events_anchor), не каждое событие — keyless-проекты работают, rebase-атака ловится head-mismatch. Genesis=фикс.константа GENESIS_V1 для offline-backfill в миграции v34.
