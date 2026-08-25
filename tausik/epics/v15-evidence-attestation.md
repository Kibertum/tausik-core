---
slug: v15-evidence-attestation
title: "v1.5: Evidence attestation & governance hardening (borrow-from-Walko)"
status: done
---

Заимствование примитивов governance-инфры (вдохновлено Walko Systems / Sift) для закрытия находок аудита 2026-05-18. Ключевая идея: один ed25519-примитив на трёх поверхностях — proof-of-done (signed receipts), scope (ACL hard-gate, SENAR Rule 2), supply-chain (signed releases). Плюс risk-score на закрытие, селективный L3, no-SDK endpoint и fail-closed аудит. См. brain decision 3666b6ed + decision #87. Приоритеты P0/P1/P2 в заголовках задач.
