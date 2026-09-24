---
slug: "1-10-sostav-dopolnen-istoriey-i-otkrytye-defekty-vladelets"
task: null
date: "2026-09-23"
edges: []
---

## Decision

1.10 — СОСТАВ ДОПОЛНЕН ИСТОРИЕЙ I: ОТКРЫТЫЕ ДЕФЕКТЫ. Владелец, смена #266: «не забудь посмотреть открытые тикеты, баги, и тоже взять их в 1.10». Замер: GitLab core — 4 открытых тикета (#8, #10, #11, #18), все уже в историях B и C (gitlab#18 привязан к задаче о падении обновления); GitHub — 22 открытых kind/bug вне v1.10.0 (15 Planning, 6 v2.0.0, 1 v1.11.0), внешних issue и PR нет. Все 22 перенесены в release110-open-defects, включая шесть, отнесённых часом ранее к паритету хостов 2.0 (#91, #104, #105, #121, #138, #141, #164) и поиск без словоформ (#124). Правило на 1.10: известный баг не переезжает в следующую версию. Дополняет #376 и #378. Состав: release110-sessions-are-not-gates, release110-verification-is-cheap, release110-the-update-reaches-the-user, release110-tracker-promises, release110-rag-and-memory-tell-the-truth, release110-senar-15-claimed-honestly, release110-renar-11-first-party-and-spec-uc, release110-site-docs-and-hygiene, release110-open-defects

## Rationale

Указание владельца; список 22 issue снят командой gh issue list --label kind/bug вне milestone v1.10.0 в смене #266.
