---
slug: v1-5-rasshiren-temoy-evidence-attestation-governance
task: null
date: "2026-05-20"
edges: []
---

## Decision

v1.5 расширен темой 'evidence attestation & governance hardening' — новый эпик v15-evidence-attestation (8 stories, 18 задач), заимствующий примитивы governance-инфры у Walko Systems/Sift. Всё уложено в один релиз v1.5 (не разбивать на 1.5/1.6).

## Rationale

Аудит 2026-05-18 выявил конкретные дыры (evidence не attested, Rule 2 Scope warning-only, supply-chain без signed releases, vendor lock-in, бинарные гейты без градации). Walko-входящий показал зрелые примитивы для ровно этих дыр. Ключевая экономия: один ed25519-примитив (story A) переиспользуется в proof-of-done (B), scope-ACL (C) и supply-chain (F) — три находки закрываются одним инфраструктурным куском. Приоритеты P0/P1/P2 в заголовках; рекомендуемый порядок: A→B/C→D→E, F/G/H в конце. Связь с источником: brain decision 3666b6ed + decision #87 (Chrome headless для аудит-PDF).
